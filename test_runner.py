"""
Main test execution engine with multi-threading support.
"""

import time
import threading
import signal
from typing import List, Optional, Dict, Any

from config import RunnerConfig
from redis_client import RedisClient
from workloads import WorkloadFactory, initialize_value_cache
from logger import setup_logging
from metrics import setup_metrics
from redis.exceptions import ConnectionError, TimeoutError


class TestRunner:
    """Main test runner that orchestrates Redis load testing."""

    def __init__(self, config: RunnerConfig):
        self.config = config
        self.logger = setup_logging(config.log_level, config.log_file).get_logger()
        self.metrics = setup_metrics(
            otel_endpoint=config.otel_endpoint,
            service_name=config.otel_service_name,
            service_version=config.otel_service_version,
            otel_export_interval_ms=config.otel_export_interval_ms,
            app_name=config.app_name,
            instance_id=config.instance_id,
            run_id=config.run_id,
            version=config.version,
        )

        # Test control
        self._stop_event = threading.Event()
        self._worker_threads: List[threading.Thread] = []
        self._stats_thread: Optional[threading.Thread] = None
        self._redis_clients: List[RedisClient] = []

        # Thread health tracking
        self._thread_lock = threading.Lock()
        self._failed_threads = 0
        self._started_threads = 0

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.stop()

    def _create_redis_client(self) -> RedisClient:
        """Create a single Redis client instance."""
        return RedisClient(self.config.redis)

    def _worker_thread(
        self, client_id: int, thread_id: int, shared_client: RedisClient
    ):
        """Worker thread that executes workload operations with a shared Redis client."""
        thread_name = f"Client-{client_id}-Thread-{thread_id}"
        self.logger.debug(f"Starting {thread_name}")

        # Mark thread as started
        with self._thread_lock:
            self._started_threads += 1

        workload = None

        try:
            # Create workload using the shared Redis client
            workload = WorkloadFactory.create_workload(
                self.config.test.workload, shared_client
            )
            self.logger.info(f"{thread_name}: Using shared Redis client")

            # Calculate per-thread target ops/sec
            total_threads = (
                self.config.test.clients * self.config.test.threads_per_client
            )
            thread_target_ops = None
            if self.config.test.target_ops_per_second:
                thread_target_ops = (
                    self.config.test.target_ops_per_second / total_threads
                )

            # Run workload
            start_time = time.time()
            operation_count = 0

            while not self._stop_event.is_set():
                try:
                    # Execute operation
                    ops_executed = workload.execute_operation()

                    # Update operation count for rate limiting
                    operation_count += ops_executed if ops_executed > 0 else 0

                    # Rate limiting
                    if thread_target_ops:
                        elapsed = time.time() - start_time
                        expected_ops = elapsed * thread_target_ops
                        if operation_count > expected_ops:
                            sleep_time = (
                                operation_count - expected_ops
                            ) / thread_target_ops
                            if sleep_time > 0:
                                time.sleep(min(sleep_time, 0.1))  # Cap sleep time

                except Exception as e:
                    self.logger.exception(
                        f"{thread_name}: Error in operation: {e}", stack_info=True
                    )
                    time.sleep(0.1)  # Brief pause on error

            self.logger.debug(f"{thread_name}: Completed {operation_count} operations")

        except Exception as e:
            # Handle workload creation or execution failure
            self.logger.error(f"{thread_name}: Error: {e}")

            # Track failed thread and check if we should stop the entire test
            with self._thread_lock:
                self._failed_threads += 1
                failed_count = self._failed_threads
                total_threads = (
                    self.config.test.clients * self.config.test.threads_per_client
                )

            self.logger.error(
                f"{thread_name}: Stopping this thread due to error ({failed_count}/{total_threads} threads failed)"
            )

            # If all threads have failed, stop the entire test
            if failed_count >= total_threads:
                self.logger.error("All worker threads failed. Stopping test.")
                self._stop_event.set()

            return

        finally:
            # Cleanup
            if workload and hasattr(workload, "cleanup"):
                try:
                    workload.cleanup()
                except Exception as e:
                    self.logger.warning(
                        f"{thread_name}: Error during workload cleanup: {e}"
                    )

            # Note: Redis clients are shared and will be closed by the main thread
            self.logger.debug(f"{thread_name}: Thread finished")

    def _stats_reporter(self):
        """Background thread for periodic stats reporting."""
        while not self._stop_event.is_set():
            try:
                time.sleep(self.config.metrics_interval)

                if not self.config.quiet:
                    current_time = time.time()

                    stats = self.metrics.get_overall_stats()

                    success_rate = (
                        stats.get("successful_operations", 0)
                        / stats.get("total_operations", 0)
                        if stats.get("total_operations", 0) > 0
                        else 0
                    )
                    self.logger.info(
                        f"Stats: {stats.get('total_operations', 0):,} ops, "
                        f"{stats.get('overall_throughput', 0):.1f} ops/sec avg, "
                        f"{success_rate:.2%} success rate"
                    )

                    last_report_time = current_time
                    # self.metrics.reset_interval_metrics()

            except Exception as e:
                self.logger.error(f"Error in stats reporter: {e}")

    def start(self):
        """Start the load test."""
        self.logger.info("Starting Redis load test...")
        self.logger.info(f"Run ID: {self.config.run_id}")
        self.logger.info(
            f"Configuration: {self.config.test.clients} Redis clients, {self.config.test.threads_per_client} threads per client"
        )

        # Log duration configuration
        if self.config.test.duration:
            self.logger.info(f"Test duration: {self.config.test.duration} seconds")
        else:
            self.logger.info("Test duration: unlimited (until interrupted)")

        try:
            # Create Redis clients (one per client instance)
            self.logger.info(
                f"Creating {self.config.test.clients} Redis client instances..."
            )
            for client_id in range(self.config.test.clients):
                try:
                    self.logger.info(
                        f"Client-{client_id}: Starting creation of Redis client..."
                    )
                    client = self._create_redis_client()
                    self._redis_clients.append(client)
                    self.logger.info(
                        f"Client-{client_id}: Successfully added Redis client"
                    )
                except Exception as e:
                    self.logger.error(f"Failed to create Redis client {client_id}: {e}")
                    # Clean up any created clients and exit
                    for existing_client in self._redis_clients:
                        existing_client.close()
                    raise e

            # Initialize value cache for better performance (before creating threads)
            self.logger.info("Initializing value cache for optimal performance...")
            initialize_value_cache(self.config.test.workload)
            self.logger.info("Value cache initialized successfully")

            # Start stats reporter
            if not self.config.quiet:
                self._stats_thread = threading.Thread(
                    target=self._stats_reporter, daemon=True
                )
                self._stats_thread.start()

            # Start worker threads (multiple threads per Redis client)
            for client_id in range(self.config.test.clients):
                shared_client = self._redis_clients[client_id]
                for thread_id in range(self.config.test.threads_per_client):
                    thread = threading.Thread(
                        target=self._worker_thread,
                        args=(client_id, thread_id, shared_client),
                        name=f"Client-{client_id}-Thread-{thread_id}",
                    )
                    thread.daemon = True
                    thread.start()
                    self._worker_threads.append(thread)

            self.logger.info(
                f"Started {len(self._worker_threads)} worker threads across {self.config.test.clients} Redis clients ({self.config.test.threads_per_client} threads per client)"
            )

            # Give threads a moment to initialize and report their status
            time.sleep(1.0)

            with self._thread_lock:
                successful_threads = self._started_threads - self._failed_threads
                if self._failed_threads > 0:
                    self.logger.warning(
                        f"Thread health: {successful_threads}/{self._started_threads} threads started successfully"
                    )
                else:
                    self.logger.info(
                        f"Thread health: All {successful_threads} threads started successfully"
                    )

            # Wait for completion or interruption
            if self.config.test.duration:
                # Wait for specified duration
                self.logger.info(
                    f"Running test for {self.config.test.duration} seconds..."
                )
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
        for thread in self._worker_threads:
            try:
                thread.join(timeout=5.0)
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread.name} did not stop gracefully")
            except Exception as e:
                self.logger.warning(f"Error joining thread {thread.name}: {e}")

        # Close shared Redis clients
        for i, client in enumerate(self._redis_clients):
            try:
                client.close()
                self.logger.debug(f"Closed Redis client {i}")
            except Exception as e:
                self.logger.warning(f"Error closing Redis client {i}: {e}")

        # Output final test summary
        self._output_final_summary()

        self.logger.info("Load test stopped")

    def _output_final_summary(self):
        """Output final test summary - to file if --output-file specified, otherwise to stdout."""
        try:
            if self.config.output_file:
                # Write final summary to file
                self.metrics.export_final_summary_to_json(self.config.output_file)
                self.logger.info(
                    f"Final test summary exported to {self.config.output_file}"
                )
            elif not self.config.quiet:
                # Print final summary to stdout (unless quiet mode) with config info
                self.metrics.print_summary(
                    clients=self.config.test.clients,
                    threads_per_client=self.config.test.threads_per_client,
                )

        except Exception as e:
            self.logger.error(f"Failed to output final summary: {e}")
