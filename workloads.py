"""
Redis workload implementations for different operation types.
"""
import time
import random
import string
import threading
import asyncio
from typing import List, Dict, Any, Optional, Callable
from abc import ABC, abstractmethod
import json

from config import WorkloadConfig
from redis_client import RedisClient
from logger import get_logger, log_error_with_traceback
from metrics import get_metrics_collector


class BaseWorkload(ABC):
    """Base class for Redis workloads."""
    
    def __init__(self, config: WorkloadConfig, client: RedisClient):
        self.config = config
        self.client = client
        self.logger = get_logger()
        self.metrics = get_metrics_collector()
        
        # Generate random data for operations
        self._key_counter = 0
        self._key_lock = threading.Lock()
    
    def _generate_key(self) -> str:
        """Generate a unique key for operations."""
        with self._key_lock:
            key_range = self.config.get_option("keyRange", 10000)
            if key_range > 0:
                key_id = random.randint(0, key_range - 1)
            else:
                key_id = self._key_counter
                self._key_counter += 1

            key_prefix = self.config.get_option("keyPrefix", "rw_test")
            return f"{key_prefix}:{key_id}"

    def _generate_value(self) -> str:
        """Generate a random value with configured size."""
        value_size = self.config.get_option("valueSize", 100)
        # For backward compatibility, check for min/max size options
        value_size_min = self.config.get_option("valueSizeMin", value_size)
        value_size_max = self.config.get_option("valueSizeMax", value_size)

        if value_size_min == value_size_max:
            size = value_size
        else:
            size = random.randint(value_size_min, value_size_max)

        return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

    def _choose_operation(self) -> str:
        """Choose an operation based on configured weights."""
        operations = self.config.get_option("operations", [])
        operation_weights = self.config.get_option("operation_weights", {})

        if not operations:
            # Fallback to workload type-based operations
            return self._get_default_operation()

        if not operation_weights:
            return random.choice(operations)

        # Weighted random selection
        ops = list(operation_weights.keys())
        weights = list(operation_weights.values())
        return random.choices(ops, weights=weights)[0]

    def _get_default_operation(self) -> str:
        """Get default operation based on workload type."""
        workload_type = self.config.type
        if workload_type == "high_throughput":
            return random.choice(["SET", "GET", "INCR"])
        elif workload_type == "list_operations":
            return random.choice(["LPUSH", "LRANGE", "LPOP"])
        elif workload_type == "pubsub_heavy":
            return random.choice(["PUBLISH", "SUBSCRIBE"])
        else:
            return random.choice(["SET", "GET"])
    
    @abstractmethod
    def execute_operation(self) -> int:
        """Execute operation(s). Returns number of operations executed (0 if failed)."""
        pass
    
    def run_continuous(self, duration: Optional[int] = None, target_ops_per_second: Optional[int] = None):
        """Run workload continuously for specified duration."""
        start_time = time.time()
        operation_count = 0
        
        while True:
            # Check duration limit
            if duration and (time.time() - start_time) >= duration:
                break
            
            # Execute operation
            try:
                success = self.execute_operation()
                operation_count += 1
                
                # Rate limiting
                if target_ops_per_second:
                    elapsed = time.time() - start_time
                    expected_ops = elapsed * target_ops_per_second
                    if operation_count > expected_ops:
                        sleep_time = (operation_count - expected_ops) / target_ops_per_second
                        time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                self.logger.info("Workload interrupted by user")
                break
            except Exception as e:
                log_error_with_traceback("Error in workload execution", e)


class BasicWorkload(BaseWorkload):
    """Basic Redis operations: SET, GET, DEL, INCR."""
    
    def execute_operation(self) -> int:
        """Execute a basic Redis operation."""
        operation = self._choose_operation()

        try:
            if operation == "SET":
                key = self._generate_key()
                value = self._generate_value()
                self.client.set(key, value)

            elif operation == "GET":
                key = self._generate_key()
                self.client.get(key)

            elif operation == "DEL":
                key = self._generate_key()
                self.client.delete(key)

            elif operation == "INCR":
                key = self._generate_key()
                self.client.incr(key)

            else:
                self.logger.warning(f"Unknown operation: {operation}")
                return 0

            return 1  # One operation executed

        except Exception as e:
            self.logger.error(f"Failed to execute {operation}: {e}")
            return 0  # No operations executed


class ListWorkload(BaseWorkload):
    """List operations: LPUSH, LRANGE, LPOP, RPUSH, RPOP."""
    
    def execute_operation(self) -> int:
        """Execute a list operation."""
        operation = self._choose_operation()
        
        try:
            if operation == "LPUSH":
                key = self._generate_key()
                value = self._generate_value()
                self.client.lpush(key, value)

            elif operation == "RPUSH":
                key = self._generate_key()
                value = self._generate_value()
                self.client.rpush(key, value)

            elif operation == "LRANGE":
                key = self._generate_key()
                start = random.randint(0, 10)
                end = start + random.randint(1, 20)
                self.client.lrange(key, start, end)

            elif operation == "LPOP":
                key = self._generate_key()
                self.client.lpop(key)

            elif operation == "RPOP":
                key = self._generate_key()
                self.client.rpop(key)
                
            else:
                self.logger.warning(f"Unknown list operation: {operation}")
                return False
            
            return 1

        except Exception as e:
            self.logger.error(f"Failed to execute {operation}: {e}")
            return 0


class PipelineWorkload(BaseWorkload):
    """Pipeline operations for batch processing with individual operation metrics."""

    def execute_operation(self) -> int:
        """Execute a batch of operations using pipeline with individual metrics tracking."""
        try:
            pipe = self.client.pipeline(transaction=False)

            # Add multiple operations to pipeline and track them individually
            pipeline_size = self.config.get_option("pipelineSize", 10)
            operations_added = 0
            operation_list = []  # Track operations for individual metrics

            for _ in range(pipeline_size):
                operation = self._choose_operation()

                if operation == "SET":
                    key = self._generate_key()
                    value = self._generate_value()
                    pipe.set(key, value)
                    operations_added += 1
                    operation_list.append(operation)

                elif operation == "GET":
                    key = self._generate_key()
                    pipe.get(key)
                    operations_added += 1
                    operation_list.append(operation)

                elif operation == "INCR":
                    key = self._generate_key()
                    pipe.incr(key)
                    operations_added += 1
                    operation_list.append(operation)

            # Execute pipeline only if we have operations
            if operations_added > 0:
                start_time = time.time()
                result = pipe.execute()
                duration = time.time() - start_time

                # Record individual operation metrics
                avg_duration = duration / operations_added if operations_added > 0 else 0
                for operation in operation_list:
                    self.metrics.record_operation(operation, avg_duration, True)

                return operations_added  # Return number of operations executed
            else:
                self.logger.warning(f"No operations added to pipeline. Available operations: {self.config.get_option('operations', [])}")
                return 0

        except Exception as e:
            self.logger.error(f"Failed to execute pipeline: {e}")
            return 0


class TransactionWorkload(BaseWorkload):
    """Transaction operations using MULTI/EXEC."""
    
    def execute_operation(self) -> int:
        """Execute a transaction with multiple operations."""
        try:
            pipe = self.client.pipeline(transaction=True)

            # Add operations to transaction
            transaction_size = self.config.get_option("transactionSize", 5)
            operations_added = 0

            for _ in range(transaction_size):
                operation = self._choose_operation()

                if operation == "SET":
                    key = self._generate_key()
                    value = self._generate_value()
                    pipe.set(key, value)
                    operations_added += 1

                elif operation == "GET":
                    key = self._generate_key()
                    pipe.get(key)
                    operations_added += 1

                elif operation == "INCR":
                    key = self._generate_key()
                    pipe.incr(key)
                    operations_added += 1

            # Execute transaction
            pipe.execute()
            return operations_added  # Return number of operations in transaction

        except Exception as e:
            self.logger.error(f"Failed to execute transaction: {e}")
            return 0


class PubSubWorkload(BaseWorkload):
    """Publish/Subscribe operations."""
    
    def __init__(self, config: WorkloadConfig, client: RedisClient):
        super().__init__(config, client)
        self._pubsub = None
        self._subscriber_thread = None
        self._stop_subscriber = threading.Event()
        # Generate unique subscriber ID for this workload instance
        import uuid
        self._subscriber_id = f"subscriber_{uuid.uuid4().hex[:8]}"
    
    def _start_subscriber(self):
        """Start subscriber in a separate thread."""
        try:
            self._pubsub = self.client.pubsub()

            # Subscribe to configured channels
            channels = self.config.get_option("channels", ["test_channel"])
            for channel in channels:
                self._pubsub.subscribe(channel)

            # Listen for messages with timeout to allow graceful shutdown
            while not self._stop_subscriber.is_set():
                try:
                    # Use get_message with short timeout to be responsive to shutdown
                    start_time = time.time()
                    message = self._pubsub.get_message(timeout=0.5)

                    if message and message['type'] == 'message':
                        channel_name = message['channel'].decode() if isinstance(message['channel'], bytes) else str(message['channel'])

                        # Record receive metrics using unified pub/sub metric
                        self.metrics.record_pubsub_operation(channel_name, 'receive', self._subscriber_id, success=True)

                        self.logger.debug(f"Received message on {channel_name}: {message['data']}")

                except (ConnectionError, ValueError) as e:
                    # These are expected during shutdown, break quietly
                    break
                except Exception as e:
                    # Record error metrics if we have channel info
                    if not self._stop_subscriber.is_set():
                        # Use default channel for error tracking
                        channels = self.config.get_option("channels", ["test_channel"])
                        default_channel = channels[0] if channels else "unknown"
                        self.metrics.record_pubsub_operation(default_channel, 'receive', self._subscriber_id, success=False, error_type=type(e).__name__)
                        self.logger.debug(f"Subscriber error (continuing): {e}")
                    break

        except Exception as e:
            # Only log error if we're not shutting down
            if not self._stop_subscriber.is_set():
                self.logger.error(f"Error in subscriber: {e}")
        finally:
            # Ensure pubsub is closed
            if self._pubsub:
                try:
                    self._pubsub.close()
                except:
                    pass  # Ignore errors during cleanup
    
    def execute_operation(self) -> int:
        """Execute pub/sub operation."""
        operation = self._choose_operation()

        try:
            if operation == "PUBLISH":
                channels = self.config.get_option("channels", ["test_channel"])
                channel = random.choice(channels)
                message = self._generate_value()
                self.client.publish(channel, message)

            elif operation == "SUBSCRIBE":
                # Start subscriber if not already running
                if self._subscriber_thread is None or not self._subscriber_thread.is_alive():
                    self._subscriber_thread = threading.Thread(target=self._start_subscriber)
                    self._subscriber_thread.daemon = True
                    self._subscriber_thread.start()

            else:
                self.logger.warning(f"Unknown pub/sub operation: {operation}")
                return 0

            return 1
            
        except Exception as e:
            self.logger.error(f"Failed to execute {operation}: {e}")
            return 0
    
    def cleanup(self):
        """Cleanup pub/sub resources."""
        # Signal subscriber thread to stop
        self._stop_subscriber.set()

        # Wait for subscriber thread to finish
        if self._subscriber_thread and self._subscriber_thread.is_alive():
            try:
                self._subscriber_thread.join(timeout=2.0)  # Wait up to 2 seconds
            except Exception:
                pass  # Ignore join errors

        # Close pubsub connection
        if self._pubsub:
            try:
                self._pubsub.close()
            except Exception:
                pass  # Ignore close errors during cleanup


class WorkloadFactory:
    """Factory for creating workload instances."""
    
    @staticmethod
    def create_workload(config: WorkloadConfig, client: RedisClient) -> BaseWorkload:
        """Create appropriate workload based on configuration."""

        # Determine workload type based on workload type or operations
        workload_type = config.type
        operations = set(config.get_option("operations", []))
        use_pipeline = config.get_option("usePipeline", False)

        # Use workload type first, then fall back to operations
        if workload_type == "transaction_heavy" or (use_pipeline and "MULTI" in operations):
            return TransactionWorkload(config, client)
        elif workload_type == "high_throughput" or use_pipeline:
            return PipelineWorkload(config, client)
        elif workload_type == "pubsub_heavy" or operations.intersection({"PUBLISH", "SUBSCRIBE"}):
            return PubSubWorkload(config, client)
        elif workload_type == "list_operations" or operations.intersection({"LPUSH", "LRANGE", "LPOP", "RPUSH", "RPOP"}):
            return ListWorkload(config, client)
        else:
            return BasicWorkload(config, client)
