"""
Main test execution engine with multi-threading support.
"""
import time
import threading
import signal
import sys
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

from config import RunnerConfig
from redis_client import RedisClientManager, RedisClientPool
from workloads import WorkloadFactory, BaseWorkload
from logger import get_logger, setup_logging
from metrics import get_metrics_collector, setup_metrics


class TestRunner:
    """Main test runner that orchestrates Redis load testing."""
    
    def __init__(self, config: RunnerConfig):
        self.config = config
        self.logger = setup_logging(config.log_level, config.log_file).get_logger()
        self.metrics = setup_metrics(
            enable_prometheus=config.metrics_enabled,
            prometheus_port=config.metrics_port,
            enable_otel=config.otel_enabled,
            otel_endpoint=config.otel_endpoint,
            service_name=config.otel_service_name,
            service_version=config.otel_service_version,
            otel_export_interval_ms=config.otel_export_interval_ms,
            app_name=config.app_name,
            instance_id=config.instance_id,
            run_id=config.run_id,
            version=config.version
        )
        
        # Test control
        self._stop_event = threading.Event()
        self._client_pools: List[RedisClientPool] = []
        self._workload_threads: List[threading.Thread] = []
        self._stats_thread: Optional[threading.Thread] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()
    
    def _create_client_pools(self) -> List[RedisClientPool]:
        """Create Redis client pools for each client instance."""
        pools = []
        
        for i in range(self.config.test.client_instances):
            try:
                pool = RedisClientPool(
                    self.config.redis,
                    pool_size=self.config.test.connections_per_client
                )
                pools.append(pool)
                self.logger.info(f"Created client pool {i+1} with {self.config.test.connections_per_client} connections")
                
            except Exception as e:
                self.logger.error(f"Failed to create client pool {i+1}: {e}")
                # Continue with fewer pools rather than failing completely
        
        return pools
    
    def _worker_thread(self, pool: RedisClientPool, thread_id: int):
        """Worker thread that executes workload operations."""
        thread_name = f"Worker-{thread_id}"
        self.logger.debug(f"Starting {thread_name}")
        
        client = None
        workload = None
        
        try:
            # Get client from pool
            client = pool.get_client()
            if not client:
                self.logger.error(f"{thread_name}: Failed to get Redis client from pool")
                return
            
            # Create workload
            workload = WorkloadFactory.create_workload(self.config.test.workload, client)

            # Calculate per-thread target ops/sec
            total_threads = self.config.test.client_instances * self.config.test.threads_per_client
            thread_target_ops = None
            # Note: target_ops_per_second is not in the current config structure
            # if self.config.target_ops_per_second:
            #     thread_target_ops = self.config.target_ops_per_second / total_threads
            
            # Run workload
            start_time = time.time()
            operation_count = 0
            
            while not self._stop_event.is_set():
                try:
                    # Check duration limit - using workload max_duration for now
                    # if self.config.duration:
                    #     elapsed = time.time() - start_time
                    #     if elapsed >= self.config.duration:
                    #         break
                    
                    # Execute operation
                    start_op_time = time.time()
                    ops_executed = workload.execute_operation()
                    end_op_time = time.time()

                    # # Record metrics for each operation executed
                    # if ops_executed > 0:
                    #     operation_duration = (end_op_time - start_op_time) / ops_executed
                    #     for _ in range(ops_executed):
                    #         self.metrics.record_operation("BATCH", operation_duration, True)
                    #     operation_count += ops_executed
                    # else:
                    #     # Record failed operation
                    #     operation_duration = end_op_time - start_op_time
                    #     self.metrics.record_operation("BATCH", operation_duration, False, "Operation failed")
                    
                    # Rate limiting
                    if thread_target_ops:
                        elapsed = time.time() - start_time
                        expected_ops = elapsed * thread_target_ops
                        if operation_count > expected_ops:
                            sleep_time = (operation_count - expected_ops) / thread_target_ops
                            if sleep_time > 0:
                                time.sleep(min(sleep_time, 0.1))  # Cap sleep time
                    
                except Exception as e:
                    self.logger.error(f"{thread_name}: Error in operation: {e}")
                    time.sleep(0.1)  # Brief pause on error
            
            self.logger.debug(f"{thread_name}: Completed {operation_count} operations")
            
        except Exception as e:
            self.logger.error(f"{thread_name}: Fatal error: {e}")
            
        finally:
            # Cleanup
            if workload and hasattr(workload, 'cleanup'):
                try:
                    workload.cleanup()
                except Exception as e:
                    self.logger.warning(f"{thread_name}: Error during workload cleanup: {e}")
            
            if client and pool:
                try:
                    pool.return_client(client)
                except Exception as e:
                    self.logger.warning(f"{thread_name}: Error returning client to pool: {e}")
    
    def _stats_reporter(self):
        """Background thread for periodic stats reporting."""
        last_report_time = time.time()
        
        while not self._stop_event.is_set():
            try:
                time.sleep(self.config.metrics_interval)

                if not self.config.quiet:
                    current_time = time.time()
                    interval = current_time - last_report_time
                    
                    stats = self.metrics.get_overall_stats()
                    
                    # Calculate interval metrics
                    interval_ops = stats.get('total_operations', 0)
                    interval_ops_per_sec = interval_ops / interval if interval > 0 else 0
                    
                    self.logger.info(
                        f"Stats: {stats.get('total_operations', 0):,} ops, "
                        f"{stats.get('overall_ops_per_second', 0):.1f} ops/sec avg, "
                        f"{interval_ops_per_sec:.1f} ops/sec current, "
                        f"{stats.get('overall_success_rate', 0):.2%} success rate"
                    )
                    
                    last_report_time = current_time
                    self.metrics.reset_interval_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in stats reporter: {e}")
    
    def start(self):
        """Start the load test."""
        self.logger.info("Starting Redis load test...")
        self.logger.info(f"Configuration: {self.config.test.client_instances} clients, "
                        f"{self.config.test.connections_per_client} connections/client, "
                        f"{self.config.test.threads_per_client} threads/client")

        # Log duration configuration
        if self.config.test.duration:
            self.logger.info(f"Test duration: {self.config.test.duration} seconds")
        else:
            self.logger.info("Test duration: unlimited (until interrupted)")
        
        try:
            # Create client pools
            self._client_pools = self._create_client_pools()
            if not self._client_pools:
                raise RuntimeError("Failed to create any Redis client pools")
            
            # Start stats reporter
            if not self.config.quiet:
                self._stats_thread = threading.Thread(target=self._stats_reporter, daemon=True)
                self._stats_thread.start()

            # Start worker threads
            thread_id = 0
            for pool in self._client_pools:
                for _ in range(self.config.test.threads_per_client):
                    thread = threading.Thread(
                        target=self._worker_thread,
                        args=(pool, thread_id),
                        name=f"Worker-{thread_id}"
                    )
                    thread.daemon = True
                    thread.start()
                    self._workload_threads.append(thread)
                    thread_id += 1
            
            total_threads = len(self._workload_threads)
            self.logger.info(f"Started {total_threads} worker threads")

            # Wait for completion or interruption
            if self.config.test.duration:
                # Wait for specified duration
                self.logger.info(f"Running test for {self.config.test.duration} seconds...")
                try:
                    # Check stop event every second while waiting for duration
                    start_time = time.time()
                    while not self._stop_event.is_set():
                        elapsed = time.time() - start_time
                        if elapsed >= self.config.test.duration:
                            self.logger.info("Test duration completed")
                            break
                        time.sleep(min(1, self.config.test.duration - elapsed))
                except KeyboardInterrupt:
                    self.logger.info("Test interrupted by user")
            else:
                # Wait for interruption (unlimited duration)
                try:
                    while not self._stop_event.is_set():
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.logger.info("Test interrupted by user")
            
        except Exception as e:
            self.logger.error(f"Error during test execution: {e}")
            raise
        
        finally:
            self.stop()
    
    def stop(self):
        """Stop the load test gracefully."""
        if self._stop_event.is_set():
            return  # Already stopping
        
        self.logger.info("Stopping load test...")
        self._stop_event.set()
        
        # Wait for worker threads to complete
        for thread in self._workload_threads:
            try:
                thread.join(timeout=5.0)
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread.name} did not stop gracefully")
            except Exception as e:
                self.logger.warning(f"Error joining thread {thread.name}: {e}")
        
        # Close client pools
        for pool in self._client_pools:
            try:
                pool.close_all()
            except Exception as e:
                self.logger.warning(f"Error closing client pool: {e}")
        
        # Output final test summary
        self._output_final_summary()
        
        self.logger.info("Load test stopped")
    
    def _output_final_summary(self):
        """Output final test summary - to file if --output-file specified, otherwise to stdout."""
        try:
            if self.config.output_file:
                # Write final summary to file
                self.metrics.export_final_summary_to_json(self.config.output_file)
                self.logger.info(f"Final test summary exported to {self.config.output_file}")
            elif not self.config.quiet:
                # Print final summary to stdout (unless quiet mode)
                self.metrics.print_summary()

        except Exception as e:
            self.logger.error(f"Failed to output final summary: {e}")

    def get_current_stats(self) -> Dict[str, Any]:
        """Get current test statistics."""
        return self.metrics.get_detailed_stats()
