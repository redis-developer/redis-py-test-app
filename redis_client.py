"""
Redis client management with support for standalone, cluster, and TLS connections.
"""
import time
import threading
from typing import Optional, List, Dict, Any, Union
import redis
import redis.sentinel
from redis.cluster import RedisCluster
from redis.exceptions import (
    ConnectionError, TimeoutError, RedisError,
    ClusterDownError, ResponseError
)
import ssl
# import asyncio
# import aioredis

from config import RedisConnectionConfig
from logger import get_logger, log_error_with_traceback
from metrics import get_metrics_collector


class RedisClientManager:
    """Manages Redis connections with automatic reconnection and error handling."""
    
    def __init__(self, config: RedisConnectionConfig):
        self.config = config
        self.logger = get_logger()
        self.metrics = get_metrics_collector()
        
        self._client: Optional[Union[redis.Redis, RedisCluster]] = None
        self._connection_lock = threading.RLock()
        self._last_connection_attempt = 0
        self._connection_backoff = 1.0
        
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
            'retry_on_timeout': self.config.retry_on_timeout,
            'health_check_interval': self.config.health_check_interval,
        }
        
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
        with self._connection_lock:
            start_time = time.time()
            
            try:
                if self.config.cluster_mode:
                    self._connect_cluster()
                else:
                    self._connect_standalone()
                
                # Test connection
                self._client.ping()
                
                connection_duration = time.time() - start_time
                self.logger.info(f"Successfully connected to Redis in {connection_duration:.3f}s")
                self.metrics.record_connection_attempt(True)
                self.metrics.update_active_connections(1)
                
                # Reset backoff on successful connection
                self._connection_backoff = 1.0
                
                return True
                
            except Exception as e:
                connection_duration = time.time() - start_time
                self.logger.error(f"Failed to connect to Redis: {e}")
                self.metrics.record_connection_attempt(False)
                
                # Exponential backoff
                if self.config.exponential_backoff:
                    self._connection_backoff = min(self._connection_backoff * 2, 60.0)
                
                self._client = None
                return False
    
    def _connect_standalone(self):
        """Connect to standalone Redis instance."""
        self._client = redis.Redis(
            host=self.config.host,
            port=self.config.port,
            db=self.config.database,
            **self._pool_kwargs
        )
    
    def _connect_cluster(self):
        """Connect to Redis Cluster."""
        if self.config.cluster_nodes:
            startup_nodes = self.config.cluster_nodes
        else:
            startup_nodes = [{"host": self.config.host, "port": self.config.port}]
        
        self._client = RedisCluster(
            startup_nodes=startup_nodes,
            decode_responses=False,
            skip_full_coverage_check=True,
            **self._pool_kwargs
        )
    
    def _ensure_connection(self) -> bool:
        """Ensure we have a valid connection, reconnecting if necessary."""
        if self._client is None:
            return self._reconnect()
        
        try:
            # Quick health check
            self._client.ping()
            return True
        except (ConnectionError, TimeoutError, ClusterDownError) as e:
            self.logger.warning(f"Connection lost ({type(e).__name__}), attempting to reconnect...")
            self.metrics.record_connection_drop(type(e).__name__.lower())
            return self._reconnect()
        except Exception as e:
            self.logger.error(f"Unexpected error during connection check: {e}")
            self.metrics.record_connection_drop("unexpected_error")
            return self._reconnect()
    
    def _reconnect(self) -> bool:
        """Reconnect to Redis with retry logic."""
        current_time = time.time()
        
        # Rate limit reconnection attempts
        if current_time - self._last_connection_attempt < self._connection_backoff:
            return False
        
        self._last_connection_attempt = current_time
        
        self.logger.info("Attempting to reconnect to Redis...")
        reconnect_start = time.time()
        
        for attempt in range(self.config.retry_attempts):
            if self._connect():
                reconnect_duration = time.time() - reconnect_start
                self.metrics.record_reconnection(reconnect_duration)
                self.logger.info(f"Reconnected successfully after {attempt + 1} attempts")
                return True
            
            if attempt < self.config.retry_attempts - 1:
                delay = self.config.retry_delay * (2 ** attempt) if self.config.exponential_backoff else self.config.retry_delay
                self.logger.info(f"Reconnection attempt {attempt + 1} failed, retrying in {delay:.2f}s...")
                time.sleep(delay)
        
        self.logger.error(f"Failed to reconnect after {self.config.retry_attempts} attempts")
        return False
    

    
    def pipeline(self, transaction: bool = True):
        """Create a pipeline for batch operations."""
        if not self._ensure_connection():
            raise ConnectionError("No Redis connection available")
        
        return self._client.pipeline(transaction=transaction)
    
    def pubsub(self, **kwargs):
        """Create a pub/sub object."""
        if not self._ensure_connection():
            raise ConnectionError("No Redis connection available")
        
        return self._client.pubsub(**kwargs)
    
    def close(self):
        """Close the Redis connection."""
        with self._connection_lock:
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
                    self.metrics.update_active_connections(0)
    
    def get_info(self) -> Dict[str, Any]:
        """Get Redis server information."""
        return self._client.info()
    
    def is_connected(self) -> bool:
        """Check if client is connected to Redis."""
        return self._client is not None and self._ensure_connection()

    def _execute_with_metrics(self, operation_name: str, client_method, *args, **kwargs):
        """Helper method to execute Redis operations with metrics tracking."""
        start_time = time.time()
        try:
            result = client_method(*args, **kwargs)
            duration = max(0.0, time.time() - start_time)  # Ensure non-negative duration
            self.metrics.record_operation(operation_name, duration, True)
            return result
        except Exception as e:
            duration = max(0.0, time.time() - start_time)  # Ensure non-negative duration
            self.metrics.record_operation(operation_name, duration, False, type(e).__name__)
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


class RedisClientPool:
    """Pool of Redis clients for multi-threaded access."""
    
    def __init__(self, config: RedisConnectionConfig, pool_size: int = 10):
        self.config = config
        self.pool_size = pool_size
        self.logger = get_logger()
        
        self._clients: List[RedisClientManager] = []
        self._available_clients: List[RedisClientManager] = []
        self._lock = threading.Lock()
        
        # Initialize client pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the client pool."""
        for i in range(self.pool_size):
            try:
                client = RedisClientManager(self.config)
                self._clients.append(client)
                self._available_clients.append(client)
            except Exception as e:
                self.logger.error(f"Failed to create Redis client {i}: {e}")
    
    def get_client(self) -> Optional[RedisClientManager]:
        """Get an available client from the pool."""
        with self._lock:
            if self._available_clients:
                return self._available_clients.pop()
            
            # If no clients available, try to create a new one
            if len(self._clients) < self.pool_size * 2:  # Allow some overflow
                try:
                    client = RedisClientManager(self.config)
                    self._clients.append(client)
                    return client
                except Exception as e:
                    self.logger.error(f"Failed to create additional Redis client: {e}")
            
            return None
    
    def return_client(self, client: RedisClientManager):
        """Return a client to the pool."""
        with self._lock:
            if client in self._clients and client not in self._available_clients:
                self._available_clients.append(client)
    
    def close_all(self):
        """Close all clients in the pool."""
        with self._lock:
            for client in self._clients:
                client.close()
            self._clients.clear()
            self._available_clients.clear()
