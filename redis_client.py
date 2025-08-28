"""
Redis client management with support for standalone, cluster, and TLS connections.
"""
import time
from typing import Optional, List, Dict, Any, Union
import redis
import redis.sentinel
from redis.cluster import RedisCluster
from redis.retry import Retry
from redis.backoff import ExponentialWithJitterBackoff
from redis.exceptions import (
    ConnectionError, TimeoutError, ClusterDownError
)
import ssl

from config import RedisConnectionConfig
from logger import get_logger
from metrics import get_metrics_collector


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
            'socket_timeout': self.config.socket_timeout,
            'socket_connect_timeout': self.config.socket_connect_timeout,
            'socket_keepalive': self.config.socket_keepalive,
            'socket_keepalive_options': self.config.socket_keepalive_options,
            'max_connections': self.config.max_connections,
        }

        # Create Retry object for client-level retries (network/connection issues)
        if self.config.client_retry_attempts > 0:
            kwargs['retry'] = Retry(ExponentialWithJitterBackoff(), self.config.client_retry_attempts)

        # Add authentication if provided
        if self.config.password:
            kwargs['password'] = self.config.password
        
        # Add SSL configuration if enabled
        if self.config.ssl:
            ssl_context = ssl.create_default_context()
            
            if self.config.ssl_cert_reqs == "none":
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
            elif self.config.ssl_cert_reqs == "optional":
                ssl_context.verify_mode = ssl.CERT_OPTIONAL
            else:
                ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            if self.config.ssl_ca_certs:
                ssl_context.load_verify_locations(self.config.ssl_ca_certs)
            
            if self.config.ssl_certfile and self.config.ssl_keyfile:
                ssl_context.load_cert_chain(self.config.ssl_certfile, self.config.ssl_keyfile)
            
            kwargs.update({
                'ssl': True,
                'ssl_context': ssl_context
            })
        
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
            #TODO: @elena-kolevska record connection metrics
            self.logger.info(f"Successfully connected to Redis in {connection_duration:.3f}s")

            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")

            self._client = None
            raise e
    
    def _connect_standalone(self):
        """Connect to standalone Redis instance."""
        start_time = time.time()
        if self.config.maintenance_events_enabled:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                maintenance_events_config = redis.maintenance_events.MaintenanceEventsConfig(enabled=self.config.maintenance_events_enabled),
                protocol=self.config.protocol,
                **self._pool_kwargs
            )
        else:
            self._client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.database,
                protocol=self.config.protocol,
                **self._pool_kwargs
            )
        self.metrics.record_client_init_duration(time.time() - start_time, client="standalone-sync")
    
    def _connect_cluster(self):
        """Connect to Redis Cluster."""
        if self.config.cluster_nodes:
            startup_nodes = self.config.cluster_nodes
        else:
            startup_nodes = [{"host": self.config.host, "port": self.config.port}]

        start_time = time.time()
        self._client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=False,
            skip_full_coverage_check=True,
            **self._pool_kwargs
        )
        self.metrics.record_client_init_duration(time.time() - start_time, client="cluster-sync")

    def pipeline(self, transaction: bool = True):
        """Create a pipeline for batch operations."""
        return self._client.pipeline(transaction=transaction)
    
    def pubsub(self, **kwargs):
        return self._client.pubsub(**kwargs)
    
    def close(self):
        """Close the Redis connection."""
        if self._client:
            try:
                if hasattr(self._client, 'close'):
                    self._client.close()
                elif hasattr(self._client, 'connection_pool'):
                    self._client.connection_pool.disconnect()
            except Exception as e:
                self.logger.warning(f"Error closing Redis connection: {e}")
            finally:
                self._client = None

    def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        return self._client.info()

    def _execute_with_metrics(self, operation_name: str, client_method, *args, **kwargs):
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

            self.logger.warning(f"Redis client error for {operation_name}: {error_type} - {e}")
            raise

        except Exception as e:
            # Track other Redis errors (like data type errors, etc.)
            duration = max(0.0, time.time() - start_time)
            error_type = type(e).__name__
            self.metrics.record_operation(operation_name, duration, False, error_type)

            self.logger.error(f"Redis operation error for {operation_name}: {error_type} - {e}")
            raise

    # Basic Redis operations with direct client method calls
    def set(self, key: str, value: str, **kwargs) -> bool:
        """Set a key-value pair."""
        return self._execute_with_metrics('SET', self._client.set, key, value, **kwargs)

    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return self._execute_with_metrics('GET', self._client.get, key)

    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        return self._execute_with_metrics('DELETE', self._client.delete, *keys)

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a key by amount."""
        if amount == 1:
            return self._execute_with_metrics('INCR', self._client.incr, key)
        else:
            return self._execute_with_metrics('INCR', self._client.incrby, key, amount)

    def decr(self, key: str, amount: int = 1) -> int:
        """Decrement a key by amount."""
        if amount == 1:
            return self._execute_with_metrics('DECR', self._client.decr, key)
        else:
            return self._execute_with_metrics('DECR', self._client.decrby, key, amount)

    # List operations
    def lpush(self, key: str, *values: str) -> int:
        """Push values to the left of a list."""
        return self._execute_with_metrics('LPUSH', self._client.lpush, key, *values)

    def rpush(self, key: str, *values: str) -> int:
        """Push values to the right of a list."""
        return self._execute_with_metrics('RPUSH', self._client.rpush, key, *values)

    def lpop(self, key: str, count: Optional[int] = None) -> Optional[str]:
        """Pop value from the left of a list."""
        if count is not None:
            return self._execute_with_metrics('LPOP', self._client.lpop, key, count)
        else:
            return self._execute_with_metrics('LPOP', self._client.lpop, key)

    def rpop(self, key: str, count: Optional[int] = None) -> Optional[str]:
        """Pop value from the right of a list."""
        if count is not None:
            return self._execute_with_metrics('RPOP', self._client.rpop, key, count)
        else:
            return self._execute_with_metrics('RPOP', self._client.rpop, key)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get a range of elements from a list."""
        return self._execute_with_metrics('LRANGE', self._client.lrange, key, start, end)

    def llen(self, key: str) -> int:
        """Get the length of a list."""
        return self._execute_with_metrics('LLEN', self._client.llen, key)

    # Pub/Sub operations
    def publish(self, channel: str, message: str) -> int:
        """Publish a message to a channel."""
        start_time = time.time()
        try:
            result = self._client.publish(channel, message)
            duration = max(0.0, time.time() - start_time)
            # Record both general operation metrics and pub/sub specific metrics
            self.metrics.record_operation('PUBLISH', duration, True)
            self.metrics.record_pubsub_operation(channel, 'PUBLISH', success=True)
            return result
        except Exception as e:
            duration = max(0.0, time.time() - start_time)
            self.metrics.record_operation('PUBLISH', duration, False, type(e).__name__)
            self.metrics.record_pubsub_operation(channel, 'PUBLISH', success=False, error_type=type(e).__name__)
            raise

    def pubsub(self):
        """Get a pubsub instance."""
        return self._client.pubsub()

    # Transaction operations
    def pipeline(self, transaction: bool = True):
        """Get a pipeline instance."""
        return self._client.pipeline(transaction=transaction)



