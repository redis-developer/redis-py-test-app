"""
Metrics collection and export for Redis test application with OpenTelemetry support.
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Deque, Any
import statistics
import json
import os
import uuid

# OpenTelemetry imports only

# OpenTelemetry imports
from opentelemetry import metrics as otel_metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
# Note: RedisInstrumentor import removed to prevent automatic instrumentation

from logger import get_logger


@dataclass
class OperationMetrics:
    """Metrics for a specific operation type."""
    total_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_duration: float = 0.0
    latencies: Deque[float] = field(default_factory=lambda: deque(maxlen=10000))
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

@dataclass
class Statistics:
    """Final test statistics in standardized format."""
    app_name: str = "python"
    instance_id: str = "unknown"
    run_id: str = "unknown"
    version: str = "unknown"
    workload_name: str = "unknown"
    run_start: float = 0.0
    run_end: float = 0.0
    total_commands_count: int = 0
    successful_commands_count: int = 0
    failed_commands_count: int = 0
    overall_throughput: float = 0.0
    reconnection_count: int = 0
    avg_reconnection_duration_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0

    def __post_init__(self):
        """Set run_start time if not provided."""
        if self.run_start == 0.0:
            self.run_start = time.time()



class MetricsCollector:
    """Centralized metrics collection for Redis operations with OpenTelemetry support."""

    def __init__(self, otel_endpoint: str,
                 service_name: str = "redis-load-test", service_version: str = "1.0.0",
                 otel_export_interval_ms: int = 1000, app_name: str = "python",
                 instance_id: str = None, run_id: str = None, version: str = None):
        self.logger = get_logger()
        self.otel_endpoint = otel_endpoint
        self.service_name = service_name
        self.service_version = service_version
        self.otel_export_interval_ms = otel_export_interval_ms
        self.app_name = app_name
        self.instance_id = instance_id if instance_id and instance_id.strip() else f"{app_name}-{str(uuid.uuid4())[:8]}"
        self.run_id = run_id if run_id and run_id.strip() else str(uuid.uuid4())
        self.version = version or "unknown"

        # Thread-safe metrics storage
        self._lock = threading.RLock()
        self._metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self._start_time = time.time()
        self._last_reset_time = time.time()

        # Connection metrics
        self._network_errors = 0

        # Setup OpenTelemetry metrics (single collection method)
        self._setup_opentelemetry()

    def _setup_opentelemetry(self):
        """Setup OpenTelemetry metrics and tracing."""
        try:
            # Create resource with minimal service information to reduce label duplication
            resource = Resource.create({
                "service.name": self.app_name,  # Use app_name instead of service_name
                "service.version": self.version
            })

            # Setup OTLP metrics exporter
            metric_exporter = OTLPMetricExporter(
                endpoint=self.otel_endpoint,
                insecure=True
            )
            metric_reader = PeriodicExportingMetricReader(
                exporter=metric_exporter,
                export_interval_millis=self.otel_export_interval_ms
            )

            # Initialize metrics provider
            metrics_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader]
            )
            otel_metrics.set_meter_provider(metrics_provider)

            # Get meter and create instruments
            self.meter = otel_metrics.get_meter(self.service_name, self.service_version)

            # Redis operations metrics
            self.otel_operations_counter = self.meter.create_counter(
                name="redis_operations_total",
                description="Total number of Redis operations",
                unit="1"
            )

            self.otel_operation_duration = self.meter.create_histogram(
                name="redis_operation_duration",
                description="Duration of Redis operations in milliseconds",
                unit="ms"
            )

            self.otel_client_init_duration = self.meter.create_histogram(
                name="redis_client_init_duration",
                description="Duration of Redis client init (connect)",
                unit="ms"
            )

            self.otel_connections_counter = self.meter.create_counter(
                name="redis_connections_total",
                description="Total number of Redis connection attempts",
                unit="1"
            )

            self.otel_network_errors_counter = self.meter.create_counter(
                name="redis_network_errors_total",
                description="Total number of Redis network errors",
                unit="1"
            )

            # Pub/Sub specific metrics (unified)
            self.otel_pubsub_operations_counter = self.meter.create_counter(
                name="redis_pubsub_operations_total",
                description="Total number of Redis pub/sub operations (publish and receive)",
                unit="1"
            )

            self.logger.info(f"OpenTelemetry setup completed with endpoint: {self.otel_endpoint}")

        except Exception as e:
            self.logger.error(f"Failed to setup OpenTelemetry: {e}")
            raise
    

    
    def record_operation(self, operation: str, duration: float, success: bool, error_type: str = None):
        """Record metrics for a Redis operation."""
        with self._lock:
            metrics = self._metrics[operation]
            metrics.total_count += 1
            metrics.total_duration += duration
            metrics.latencies.append(duration)

            if success:
                metrics.success_count += 1
            else:
                metrics.error_count += 1
                if error_type:
                    metrics.errors_by_type[error_type] += 1

        # Update OpenTelemetry metrics
            status = 'success' if success else 'error'
            labels = {
                "operation": operation,
                "status": status,
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "run_id": self.run_id,
                "version": self.version,
                "error_type": error_type or "none"
        }
        self.otel_operations_counter.add(1, labels)

        duration_labels = {
                "operation": operation,
                "status": status,
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "run_id": self.run_id,
                "version": self.version
        }
        # Convert duration from seconds to milliseconds
        duration_ms = duration * 1000
        self.otel_operation_duration.record(duration_ms, duration_labels)

        # Metrics are now only collected via OpenTelemetry (OTLP push)

    def record_pubsub_operation(self, channel: str, operation_type: str, subscriber_id: str = None, success: bool = True, error_type: str = None):
        """Record metrics for a pub/sub operation (publish or receive)."""

        # Update OpenTelemetry metrics
        labels = {
            "app_name": self.app_name,
            "instance_id": self.instance_id,
            "version": self.version,
            "run_id": self.run_id,
            "status": "success" if success else "error",
            "error_type": error_type or "none",
            "channel": channel,
            "operation_type": operation_type,
            "subscriber_id": subscriber_id or "",

        }
        self.otel_pubsub_operations_counter.add(1, labels)

    def record_network_error(self): #TODO call this
        """Record a network error."""
        self._network_errors += 1
        self.otel_network_errors_counter.add(1)

    def record_client_init_duration(self, duration: float, client: str = "standalone-sync"):
        """Record the duration of a Redis connection initialization."""
        labels = {
            "app_name": self.app_name,
            "instance_id": self.instance_id,
            "version": self.version,
            "run_id": self.run_id,
            "client": client
        }
        duration_ms = duration * 1000
        print(f"Recording connection init duration: {duration_ms}ms")
        self.otel_client_init_duration.record(duration_ms, labels)


    def get_overall_stats(self) -> Dict:
        """Get overall statistics across all operations."""
        with self._lock:
            current_time = time.time()
            total_duration = current_time - self._start_time

            total_ops = sum(m.total_count for m in self._metrics.values())
            total_success = sum(m.success_count for m in self._metrics.values())
            total_errors = sum(m.error_count for m in self._metrics.values())
            
            stats = {
                'total_operations': total_ops,
                'successful_operations': total_success,
                'failed_operations': total_errors,
                'network_errors': self._network_errors,
                'run_start': self._start_time,
                'run_end': current_time,
                'overall_throughput': total_ops / total_duration if total_duration > 0 else 0,
                'overall_success_rate': total_success / total_ops if total_ops > 0 else 0,
            }
            
            return stats
        
    def reset_interval_metrics(self):
        """Reset interval-based metrics (for periodic reporting)."""
        with self._lock:
            self._last_reset_time = time.time()
        
    def get_final_test_summary(self) -> 'Statistics':
        """Get final test summary in standardized format."""
        stats = self.get_overall_stats()

        # Extract workload name from app_name (format: {app-name}-{workload-profile})
        workload_name = "unknown"
        if "-" in self.app_name:
            # Split on last dash to handle app names with dashes
            parts = self.app_name.rsplit("-", 1)
            if len(parts) == 2:
                workload_name = parts[1]

        # Calculate overall latency percentiles across all operations
        all_latencies = []
        with self._lock:
            for metrics in self._metrics.values():
                all_latencies.extend(list(metrics.latencies))

        # Calculate latency percentiles in milliseconds (convert from seconds)
        latency_stats = {}
        if all_latencies:
            # Convert to milliseconds for consistency with other duration metrics
            latencies_ms = [lat * 1000 for lat in all_latencies]
            latency_stats = {
                "min_latency_ms": round(min(latencies_ms), 2),
                "max_latency_ms": round(max(latencies_ms), 2),
                "median_latency_ms": round(statistics.median(latencies_ms), 2),
                "p95_latency_ms": round(statistics.quantiles(latencies_ms, n=20)[18] if len(latencies_ms) >= 20 else max(latencies_ms), 2),
                "p99_latency_ms": round(statistics.quantiles(latencies_ms, n=100)[98] if len(latencies_ms) >= 100 else max(latencies_ms), 2),
                "avg_latency_ms": round(sum(latencies_ms) / len(latencies_ms), 2)
            }

        summary = Statistics(self.app_name, self.instance_id, self.run_id, self.version, workload_name)
        summary.total_commands_count = stats['total_operations']
        summary.successful_commands_count = stats['successful_operations']
        summary.failed_commands_count = stats['failed_operations']
        summary.run_start = stats['run_start']
        summary.run_end = stats['run_end']
        summary.overall_throughput = round(stats['overall_throughput'],2)
        summary.avg_reconnection_duration_ms = 0  # TODO: Implement reconnection duration tracking

        # Update latencies
        summary.min_latency_ms = latency_stats.get("min_latency_ms", 0.0)
        summary.max_latency_ms = latency_stats.get("max_latency_ms", 0.0)
        summary.median_latency_ms = latency_stats.get("median_latency_ms", 0.0)
        summary.p95_latency_ms = latency_stats.get("p95_latency_ms", 0.0)
        summary.p99_latency_ms = latency_stats.get("p99_latency_ms", 0.0)
        summary.avg_latency_ms = latency_stats.get("avg_latency_ms", 0.0)

        return summary

    def export_final_summary_to_json(self, file_path: str):
        """Export final test summary to JSON file."""
        summary = self.get_final_test_summary()
        # Convert dataclass to dictionary for JSON serialization
        summary_dict = {
            'app_name': summary.app_name,
            'instance_id': summary.instance_id,
            'run_id': summary.run_id,
            'version': summary.version,
            'workload_name': summary.workload_name,
            'run_start': summary.run_start,
            'run_end': summary.run_end,
            'total_commands_count': summary.total_commands_count,
            'successful_commands_count': summary.successful_commands_count,
            'failed_commands_count': summary.failed_commands_count,
            'overall_throughput': summary.overall_throughput,
            'reconnection_count': summary.reconnection_count,
            'avg_reconnection_duration_ms': summary.avg_reconnection_duration_ms,
            'min_latency_ms': summary.min_latency_ms,
            'max_latency_ms': summary.max_latency_ms,
            'median_latency_ms': summary.median_latency_ms,
            'p95_latency_ms': summary.p95_latency_ms,
            'p99_latency_ms': summary.p99_latency_ms,
            'avg_latency_ms': summary.avg_latency_ms
        }
        with open(file_path, 'w') as f:
            json.dump(summary_dict, f, indent=2)

    def print_summary(self):
        """Print final test summary in standardized format."""
        summary = self.get_final_test_summary()

        print("\n" + "="*60)
        print("FINAL TEST SUMMARY")
        print("="*60)
        print(f"Workload Name: {summary.workload_name}")
        print(f"Total test run time: {summary.run_end - summary.run_start:.2f}s")
        print(f"Total Commands: {summary.total_commands_count:,}")
        print(f"Successful Commands: {summary.successful_commands_count:,}")
        print(f"Failed Commands: {summary.failed_commands_count:,}")
        success_rate = (
                    summary.successful_commands_count / summary.total_commands_count) if summary.total_commands_count > 0 else 0.0
        print(f"Success Rate: {success_rate:.2%}")
        print(f"Overall Throughput: {summary.overall_throughput:,} ops/sec")
        if summary.reconnection_count > 0:
            print(f"Avg Reconnection Duration: {summary.avg_reconnection_duration_ms:.1f}ms")
        print("="*60)

# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def setup_metrics(otel_endpoint: str,
                 service_name: str = "redis-load-test", service_version: str = "1.0.0",
                 otel_export_interval_ms: int = 1000, app_name: str = "python",
                 instance_id: str = None, run_id: str = None, version: str = None) -> MetricsCollector:
    """Setup global metrics collector with OpenTelemetry only."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(
        otel_endpoint=otel_endpoint,
        service_name=service_name,
        service_version=service_version,
        otel_export_interval_ms=otel_export_interval_ms,
        app_name=app_name,
        instance_id=instance_id,
        run_id=run_id,
        version=version
    )
    return _metrics_collector
