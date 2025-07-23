"""
Redis client management - shared client instances with round-robin selection.
"""
import threading
from typing import List, Optional
from redis_client import RedisClient
from config import RedisConnectionConfig
from logger import get_logger


class RedisClientManager:
    """
    Client manager that shares Redis client instances across threads.

    - Create N RedisClient instances (each has its own redis.Redis with connection pool)
    - Worker threads share these instances using round-robin selection
    - No complex pooling, locking, or return logic needed
    """
    
    def __init__(self, config: RedisConnectionConfig, num_clients: int = 4):
        self.config = config
        self.num_clients = num_clients
        self.logger = get_logger()
        
        # Create Redis client instances
        self.clients: List[RedisClient] = []
        self._client_counter = 0
        self._lock = threading.Lock()
        
        # Initialize client instances
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Redis client instances."""
        self.logger.info(f"Creating {self.num_clients} Redis client instances...")
        
        for i in range(self.num_clients):
            try:
                client = RedisClient(self.config)
                self.clients.append(client)
                self.logger.info(f"Created Redis client {i+1}/{self.num_clients}")
            except Exception as e:
                self.logger.error(f"Failed to create Redis client {i+1}: {e}")
                # Continue with fewer clients rather than failing completely
        
        if not self.clients:
            raise RuntimeError("Failed to create any Redis client instances")
        
        self.logger.info(f"Successfully created {len(self.clients)} Redis client instances")
    
    def get_client(self) -> RedisClient:
        """
        Get a Redis client instance using round-robin selection.
        
        This is thread-safe and always returns immediately (no blocking).
        Each client instance is shared across multiple threads, which is safe
        because redis.Redis is thread-safe with its internal connection pool.
        
        Returns:
            RedisClient: A Redis client instance ready for use
        """
        with self._lock:
            client = self.clients[self._client_counter % len(self.clients)]
            self._client_counter += 1
            return client
    
    def get_client_stats(self) -> dict:
        """Get statistics for all client instances."""
        stats = {
            'total_clients': len(self.clients),
            'clients': []
        }
        
        for i, client in enumerate(self.clients):
            client_stats = {
                'client_id': i,
                'is_connected': client.is_connected(),
                'host': self.config.host,
                'port': self.config.port,
                'cluster_mode': self.config.cluster_mode
            }
            stats['clients'].append(client_stats)
        
        return stats
    
    def close_all(self):
        """Close all Redis client instances."""
        self.logger.info("Closing all Redis client instances...")
        
        for i, client in enumerate(self.clients):
            try:
                client.close()
                self.logger.debug(f"Closed Redis client {i+1}")
            except Exception as e:
                self.logger.error(f"Error closing Redis client {i+1}: {e}")
        
        self.clients.clear()
        self.logger.info("All Redis client instances closed")
    
    def __len__(self) -> int:
        """Return number of client instances."""
        return len(self.clients)
    
    def __str__(self) -> str:
        """String representation."""
        return f"RedisClientManager({len(self.clients)} clients, {self.config.host}:{self.config.port})"
