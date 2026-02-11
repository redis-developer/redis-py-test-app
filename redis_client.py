"""
Redis client management with support for standalone, cluster, and TLS connections.
"""

import time
import ssl
from typing import Optional, List, Dict, Any, Union
import redis
import redis.sentinel
from redis.cluster import ClusterNode, RedisCluster
from redis.maint_notifications import MaintNotificationsConfig
from redis.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff
from redis.exceptions import ConnectionError, TimeoutError, ClusterDownError


from config import RedisConnectionConfig
from logger import get_logger
from metrics import get_metrics_collector


def _convert_ssl_min_version(version_str: Optional[str]) -> Optional[ssl.TLSVersion]:
    """Convert string SSL version to ssl.TLSVersion enum."""
    if not version_str:
        return None

    # Mapping of string values to ssl.TLSVersion enum values
    version_mapping = {
        "TLSv1": ssl.TLSVersion.TLSv1,
        "TLSv1_1": ssl.TLSVersion.TLSv1_1,
        "TLSv1_2": ssl.TLSVersion.TLSv1_2,
        "TLSv1_3": ssl.TLSVersion.TLSv1_3,
        # Also support lowercase variants
        "tlsv1": ssl.TLSVersion.TLSv1,
        "tlsv1_1": ssl.TLSVersion.TLSv1_1,
        "tlsv1_2": ssl.TLSVersion.TLSv1_2,
        "tlsv1_3": ssl.TLSVersion.TLSv1_3,
        # Support numeric versions
        "1.0": ssl.TLSVersion.TLSv1,
        "1.1": ssl.TLSVersion.TLSv1_1,
        "1.2": ssl.TLSVersion.TLSv1_2,
        "1.3": ssl.TLSVersion.TLSv1_3,
    }

    if version_str in version_mapping:
        return version_mapping[version_str]
    else:
        raise ValueError(
            f"Unsupported SSL version: {version_str}. "
            f"Supported versions: {list(version_mapping.keys())}"
        )


def _convert_ssl_cert_reqs(cert_reqs: Union[str, int]) -> Union[ssl.VerifyMode, int]:
    """Convert string cert requirements to ssl.VerifyMode enum."""
    if isinstance(cert_reqs, int):
        return cert_reqs

    # Mapping of string values to ssl.VerifyMode enum values
    cert_reqs_mapping = {
        "none": ssl.CERT_NONE,
        "optional": ssl.CERT_OPTIONAL,
        "required": ssl.CERT_REQUIRED,
        # Also support uppercase variants
        "NONE": ssl.CERT_NONE,
        "OPTIONAL": ssl.CERT_OPTIONAL,
        "REQUIRED": ssl.CERT_REQUIRED,
    }

    if cert_reqs in cert_reqs_mapping:
        return cert_reqs_mapping[cert_reqs]
    else:
        raise ValueError(
            f"Unsupported SSL cert requirements: {cert_reqs}. "
            f"Supported values: {list(cert_reqs_mapping.keys())}"
        )


class RedisClient:
    """Manages Redis connections with automatic reconnection and error handling."""

    def __init__(self, config: RedisConnectionConfig):
        self.config = config
        self.logger = get_logger()
        self.metrics = get_metrics_collector()

        self._client: Optional[Union[redis.Redis, RedisCluster]] = None

        # Connection pool configuration
        self._pool_kwargs = self._build_pool_kwargs()

        # Initialize connection
        self._connect()

    def _build_pool_kwargs(self) -> Dict[str, Any]:
        """Build connection pool keyword arguments."""
        kwargs = {
            "socket_keepalive": self.config.socket_keepalive,
            "socket_keepalive_options": self.config.socket_keepalive_options,
            "max_connections": self.config.max_connections,
        }

        # Only add timeout parameters if they are not None (let redis-py use defaults)
        if self.config.socket_timeout is not None:
            kwargs["socket_timeout"] = self.config.socket_timeout
        if self.config.socket_connect_timeout is not None:
            kwargs["socket_connect_timeout"] = self.config.socket_connect_timeout

        # Create Retry object for client-level retries (network/connection issues)
        if self.config.client_retry_attempts >= 0:
            kwargs["retry"] = Retry(
                ExponentialWithJitterBackoff(), self.config.client_retry_attempts
            )
        else:
            kwargs["retry"] = Retry(ExponentialWithJitterBackoff(), 0)

        # Add authentication if provided
        if self.config.password:
            kwargs["password"] = self.config.password

        # Add SSL configuration if enabled
        if self.config.ssl:
            ssl_kwargs = {"ssl": True}

            # Add SSL parameters directly as redis-py expects them
            if self.config.ssl_keyfile is not None:
                ssl_kwargs["ssl_keyfile"] = self.config.ssl_keyfile
            if self.config.ssl_certfile is not None:
                ssl_kwargs["ssl_certfile"] = self.config.ssl_certfile
            if self.config.ssl_cert_reqs is not None:
                ssl_kwargs["ssl_cert_reqs"] = _convert_ssl_cert_reqs(
                    self.config.ssl_cert_reqs
                )
            if self.config.ssl_ca_certs is not None:
                ssl_kwargs["ssl_ca_certs"] = self.config.ssl_ca_certs
            if self.config.ssl_ca_path is not None:
                ssl_kwargs["ssl_ca_path"] = self.config.ssl_ca_path
            if self.config.ssl_ca_data is not None:
                ssl_kwargs["ssl_ca_data"] = self.config.ssl_ca_data
            if self.config.ssl_check_hostname is not None:
                ssl_kwargs["ssl_check_hostname"] = self.config.ssl_check_hostname
            if self.config.ssl_password is not None:
                ssl_kwargs["ssl_password"] = self.config.ssl_password
            if self.config.ssl_min_version is not None:
                # Handle both string and TLSVersion objects
                if isinstance(self.config.ssl_min_version, str):
                    ssl_kwargs["ssl_min_version"] = _convert_ssl_min_version(
                        self.config.ssl_min_version
                    )
                else:
                    ssl_kwargs["ssl_min_version"] = self.config.ssl_min_version
            if self.config.ssl_ciphers is not None:
                ssl_kwargs["ssl_ciphers"] = self.config.ssl_ciphers

            kwargs.update(ssl_kwargs)

        return kwargs

    def _connect(self) -> bool:
        """Establish connection to Redis."""
        start_time = time.time()

        try:
            if self.config.cluster_mode:
                self._connect_cluster()
            else:
                self._connect_standalone()

            # Test connection
            self._client.ping()

            connection_duration = time.time() - start_time
            # TODO: @elena-kolevska record connection metrics
            self.logger.info(
                f"Successfully connected to Redis in {connection_duration:.3f}s"
            )

            return True

        except Exception:
            self._client = None
            raise

    def _connect_standalone(self):
        """Connect to standalone Redis instance."""
        start_time = time.time()

        if self.config.maintenance_notifications_enabled is not False:
            # Build maintenance events config, only passing relaxed_timeouts if not None
            # maintenance_notifications_enabled can be True, False, or 'auto'
            maintenance_config_kwargs = {
                "enabled": self.config.maintenance_notifications_enabled
            }
            if self.config.maintenance_relaxed_timeout is not None:
                maintenance_config_kwargs["relaxed_timeout"] = (
                    self.config.maintenance_relaxed_timeout
                )

            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                maint_notifications_config=MaintNotificationsConfig(
                    **maintenance_config_kwargs
                ),
                protocol=self.config.protocol,
                **self._pool_kwargs,
            )
        else:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                protocol=self.config.protocol,
                **self._pool_kwargs,
            )
        self.metrics.record_client_init_duration(
            time.time() - start_time, client="standalone-sync"
        )

    def _connect_cluster(self):
        """Connect to Redis Cluster."""
        startup_nodes = []
        if self.config.cluster_nodes:
            for node in self.config.cluster_nodes:
                cluster_node = ClusterNode(node["host"], node["port"])
                startup_nodes.append(cluster_node)
        else:
            startup_nodes = [ClusterNode(self.config.host, self.config.port)]

        start_time = time.time()

        if self.config.maintenance_notifications_enabled is not False:
            # Build maintenance events config, only passing relaxed_timeouts if not None
            # maintenance_notifications_enabled can be True, False, or 'auto'
            maintenance_config_kwargs = {
                "enabled": self.config.maintenance_notifications_enabled
            }
            if self.config.maintenance_relaxed_timeout is not None:
                maintenance_config_kwargs["relaxed_timeout"] = (
                    self.config.maintenance_relaxed_timeout
                )

        else:
            maintenance_config_kwargs = {"enabled": False}

        self._client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=False,
            protocol=self.config.protocol,
            skip_full_coverage_check=True,
            maint_notifications_config=MaintNotificationsConfig(
                **maintenance_config_kwargs
            ),
            **self._pool_kwargs,
        )
        self.metrics.record_client_init_duration(
            time.time() - start_time, client="cluster-sync"
        )

    def pipeline(self, transaction: bool = True):
        """Create a pipeline for batch operations."""
        return self._client.pipeline(transaction=transaction)

    def pubsub(self, **kwargs):
        return self._client.pubsub(**kwargs)

    def close(self):
        """Close the Redis connection."""
        if self._client:
            try:
                if hasattr(self._client, "close"):
                    self._client.close()
                elif hasattr(self._client, "connection_pool"):
                    self._client.connection_pool.disconnect()
            except Exception as e:
                self.logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._client = None

    def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        return self._client.info()

    def _execute_with_metrics(
        self, operation_name: str, client_method, *args, **kwargs
    ):
        """
        Helper method to execute Redis operations with metrics tracking.

        This method tracks client-level errors immediately when they occur.
        The redis-py client with Retry object handles connection issues automatically.
        """
        start_time = time.time()

        try:
            # Execute the Redis operation - redis-py client handles connection/retry logic
            result = client_method(*args, **kwargs)
            duration = max(0.0, time.time() - start_time)
            self.metrics.record_operation(operation_name, duration, True)
            return result

        except (ConnectionError, TimeoutError, ClusterDownError) as e:
            # Track client-level network/connection errors immediately
            duration = max(0.0, time.time() - start_time)
            error_type = type(e).__name__
            self.metrics.record_operation(operation_name, duration, False, error_type)
            # TODO @elena-kolevska add a separate counter for network errors

            self.logger.warning(
                f"Redis client error for {operation_name}: {error_type} - {e}"
            )
            raise

        except Exception as e:
            # Track other Redis errors (like data type errors, etc.)
            duration = max(0.0, time.time() - start_time)
            error_type = type(e).__name__
            self.metrics.record_operation(operation_name, duration, False, error_type)

            self.logger.error(
                f"Redis operation error for {operation_name}: {error_type} - {e}"
            )
            raise

    # Basic Redis operations with direct client method calls
    def set(self, key: str, value: str, **kwargs) -> bool:
        """Set a key-value pair."""
        return self._execute_with_metrics("SET", self._client.set, key, value, **kwargs)

    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return self._execute_with_metrics("GET", self._client.get, key)

    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        return self._execute_with_metrics("DELETE", self._client.delete, *keys)

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key by amount."""
        if amount == 1:
            return self._execute_with_metrics("INCR", self._client.incr, key)
        else:
            return self._execute_with_metrics("INCR", self._client.incrby, key, amount)

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a key by amount."""
        if amount == 1:
            return self._execute_with_metrics("DECR", self._client.decr, key)
        else:
            return self._execute_with_metrics("DECR", self._client.decrby, key, amount)

    # List operations
    def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list."""
        return self._execute_with_metrics("LPUSH", self._client.lpush, key, *values)

    def rpush(self, key: str, *values: str) -> int:
        """Push values to the right of a list."""
        return self._execute_with_metrics("RPUSH", self._client.rpush, key, *values)

    def lpop(self, key: str, count: Optional[int] = None) -> Optional[str]:
        """Pop value from the left of a list."""
        if count is not None:
            return self._execute_with_metrics("LPOP", self._client.lpop, key, count)
        else:
            return self._execute_with_metrics("LPOP", self._client.lpop, key)

    def rpop(self, key: str, count: Optional[int] = None) -> Optional[str]:
        """Pop value from the right of a list."""
        if count is not None:
            return self._execute_with_metrics("RPOP", self._client.rpop, key, count)
        else:
            return self._execute_with_metrics("RPOP", self._client.rpop, key)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get a range of elements from a list."""
        return self._execute_with_metrics(
            "LRANGE", self._client.lrange, key, start, end
        )

    def llen(self, key: str) -> int:
        """Get the length of a list."""
        return self._execute_with_metrics("LLEN", self._client.llen, key)

    def ltrim(self, key: str, start: int, end: int) -> bool:
        """Trim a list to the specified range."""
        return self._execute_with_metrics("LTRIM", self._client.ltrim, key, start, end)

    # String operations
    def append(self, key: str, value: str) -> int:
        """Append a value to a string."""
        return self._execute_with_metrics("APPEND", self._client.append, key, value)

    def strlen(self, key: str) -> int:
        """Get the length of a string."""
        return self._execute_with_metrics("STRLEN", self._client.strlen, key)

    # Key operations
    def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        return self._execute_with_metrics("EXISTS", self._client.exists, *keys)

    def expire(self, key: str, time: int) -> bool:
        """Set a key's time to live in seconds."""
        return self._execute_with_metrics("EXPIRE", self._client.expire, key, time)

    def ttl(self, key: str) -> int:
        """Get the time to live for a key."""
        return self._execute_with_metrics("TTL", self._client.ttl, key)

    def type(self, key: str) -> str:
        """Get the type of a key."""
        return self._execute_with_metrics("TYPE", self._client.type, key)

    def incrby(self, key: str, amount: int) -> int:
        """Increment a key by a specific amount."""
        return self._execute_with_metrics("INCRBY", self._client.incrby, key, amount)

    def decrby(self, key: str, amount: int) -> int:
        """Decrement a key by a specific amount."""
        return self._execute_with_metrics("DECRBY", self._client.decrby, key, amount)

    # Set operations
    def sadd(self, key: str, *values: str) -> int:
        """Add members to a set."""
        return self._execute_with_metrics("SADD", self._client.sadd, key, *values)

    def srem(self, key: str, *values: str) -> int:
        """Remove members from a set."""
        return self._execute_with_metrics("SREM", self._client.srem, key, *values)

    def smembers(self, key: str) -> set:
        """Get all members of a set."""
        return self._execute_with_metrics("SMEMBERS", self._client.smembers, key)

    def scard(self, key: str) -> int:
        """Get the number of members in a set."""
        return self._execute_with_metrics("SCARD", self._client.scard, key)

    # Hash operations
    def hset(self, key: str, field: str, value: str) -> int:
        """Set a field in a hash."""
        return self._execute_with_metrics("HSET", self._client.hset, key, field, value)

    def hget(self, key: str, field: str) -> Optional[str]:
        """Get a field from a hash."""
        return self._execute_with_metrics("HGET", self._client.hget, key, field)

    def hdel(self, key: str, *fields: str) -> int:
        """Delete fields from a hash."""
        return self._execute_with_metrics("HDEL", self._client.hdel, key, *fields)

    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields and values from a hash."""
        return self._execute_with_metrics("HGETALL", self._client.hgetall, key)

    def hlen(self, key: str) -> int:
        """Get the number of fields in a hash."""
        return self._execute_with_metrics("HLEN", self._client.hlen, key)

    # Sorted Set operations
    def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        """Add members to a sorted set."""
        return self._execute_with_metrics("ZADD", self._client.zadd, key, mapping)

    def zrem(self, key: str, *members: str) -> int:
        """Remove members from a sorted set."""
        return self._execute_with_metrics("ZREM", self._client.zrem, key, *members)

    def zrange(self, key: str, start: int, end: int, withscores: bool = False) -> List:
        """Get a range of members from a sorted set."""
        return self._execute_with_metrics(
            "ZRANGE", self._client.zrange, key, start, end, withscores=withscores
        )

    def zcard(self, key: str) -> int:
        """Get the number of members in a sorted set."""
        return self._execute_with_metrics("ZCARD", self._client.zcard, key)

    def zscore(self, key: str, member: str) -> Optional[float]:
        """Get the score of a member in a sorted set."""
        return self._execute_with_metrics("ZSCORE", self._client.zscore, key, member)

    # Pub/Sub operations
    def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        start_time = time.time()
        try:
            result = self._client.publish(channel, message)
            duration = max(0.0, time.time() - start_time)
            # Record both general operation metrics and pub/sub specific metrics
            self.metrics.record_operation("PUBLISH", duration, True)
            self.metrics.record_pubsub_operation(channel, "PUBLISH", success=True)
            return result
        except Exception as e:
            duration = max(0.0, time.time() - start_time)
            self.metrics.record_operation("PUBLISH", duration, False, type(e).__name__)
            self.metrics.record_pubsub_operation(
                channel, "PUBLISH", success=False, error_type=type(e).__name__
            )
            raise

    def pubsub(self):
        """Get a pubsub instance."""
        return self._client.pubsub()

    # Transaction operations
    def pipeline(self, transaction: bool = True):
        """Get a pipeline instance."""
        return self._client.pipeline(transaction=transaction)
