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
        self._connection_attempts = 0
        self._connection_failures = 0
        self._connection_drops = 0
        self._reconnection_count = 0
        self._reconnection_duration = 0.0

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

            self.otel_connections_counter = self.meter.create_counter(
                name="redis_connections_total",
                description="Total number of Redis connection attempts",
                unit="1"
            )

            self.otel_connection_drops_counter = self.meter.create_counter(
                name="redis_connection_drops_total",
                description="Total number of Redis connection drops",
                unit="1"
            )

            self.otel_reconnection_duration = self.meter.create_histogram(
                name="redis_reconnection_duration_ms",
                description="Duration of Redis reconnection attempts in milliseconds",
                unit="1"
            )

            self.otel_active_connections = self.meter.create_gauge(
                name="redis_active_connections",
                description="Number of active Redis connections",
                unit="1"
            )

            # Pub/Sub specific metrics (unified)
            self.otel_pubsub_operations_counter = self.meter.create_counter(
                name="redis_pubsub_operations_total",
                description="Total number of Redis pub/sub operations (publish and receive)",
                unit="1"
            )

            # Note: Using manual instrumentation instead of automatic Redis instrumentation
            # to have full control over operation labeling and avoid "BATCH" aggregation
            # RedisInstrumentor().instrument() is NOT called to prevent operation aggregation

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
    
    def record_connection_attempt(self, success: bool):
        """Record connection attempt."""
        with self._lock:
            self._connection_attempts += 1
            if not success:
                self._connection_failures += 1

        # Update OpenTelemetry metrics
            status = 'success' if success else 'error'
            labels = {
                "status": status,
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "run_id": self.run_id,
                "version": self.version
        }
        self.otel_connections_counter.add(1, labels)

        # Connection metrics collected via OpenTelemetry only

    def record_connection_drop(self, error_type: str = "connection_lost"):
        """Record connection drop event."""
        with self._lock:
            self._connection_drops += 1

        # Update OpenTelemetry metrics
        labels = {
            "error_type": error_type,
            "app_name": self.app_name,
            "instance_id": self.instance_id,
            "run_id": self.run_id,
            "version": self.version
        }
        self.otel_connection_drops_counter.add(1, labels)

    def record_reconnection(self, duration: float):
        """Record reconnection event."""
        with self._lock:
            self._reconnection_count += 1
            self._reconnection_duration += duration

        # Update OpenTelemetry metrics
            labels = {
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "run_id": self.run_id,
                "version": self.version
        }
        # Convert duration from seconds to milliseconds
        duration_ms = duration * 1000
        self.otel_reconnection_duration.record(duration_ms, labels)

    def update_active_connections(self, count: int):
        """Update active connections count."""
        # Update OpenTelemetry metrics
        labels = {
            "app_name": self.app_name,
            "instance_id": self.instance_id,
            "version": self.version
        }
        # Use set() for gauge metrics, not add()
        self.otel_active_connections.set(count, labels)

    def record_pubsub_operation(self, channel: str, operation_type: str, subscriber_id: str = None, success: bool = True, error_type: str = None):
        """Record metrics for a pub/sub operation (publish or receive)."""

        # Update OpenTelemetry metrics
        labels = {
            "app_name": self.app_name,
            "instance_id": self.instance_id,
            "version": self.version,
            "run_id": self.run_id,
            "channel": channel,
            "operation_type": operation_type,
            "subscriber_id": subscriber_id or "",
            "status": "success" if success else "error"
        }
        self.otel_pubsub_operations_counter.add(1, labels)

    def get_operation_stats(self, operation: str) -> Dict:
        """Get statistics for a specific operation."""
        with self._lock:
            metrics = self._metrics[operation]
            if metrics.total_count == 0:
                return {}
            
            latencies = list(metrics.latencies)
            
            stats = {
                'total_count': metrics.total_count,
                'success_count': metrics.success_count,
                'error_count': metrics.error_count,
                'success_rate': metrics.success_count / metrics.total_count,
                'avg_duration': metrics.total_duration / metrics.total_count,
                'errors_by_type': dict(metrics.errors_by_type)
            }
            
            if latencies:
                stats.update({
                    'min_latency': min(latencies),
                    'max_latency': max(latencies),
                    'median_latency': statistics.median(latencies),
                    'p95_latency': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies),
                    'p99_latency': statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
                })
            
            return stats
    
    def get_overall_stats(self) -> Dict:
        """Get overall statistics across all operations."""
        with self._lock:
            current_time = time.time()
            total_duration = current_time - self._start_time
            interval_duration = current_time - self._last_reset_time
            
            total_ops = sum(m.total_count for m in self._metrics.values())
            total_success = sum(m.success_count for m in self._metrics.values())
            total_errors = sum(m.error_count for m in self._metrics.values())
            
            stats = {
                'test_duration': total_duration,
                'interval_duration': interval_duration,
                'total_operations': total_ops,
                'successful_operations': total_success,
                'failed_operations': total_errors,
                'overall_success_rate': total_success / total_ops if total_ops > 0 else 0,
                'overall_ops_per_second': total_ops / total_duration if total_duration > 0 else 0,
                'interval_ops_per_second': total_ops / interval_duration if interval_duration > 0 else 0,
                'connection_attempts': self._connection_attempts,
                'connection_failures': self._connection_failures,
                'connection_drops': self._connection_drops,
                'connection_success_rate': (self._connection_attempts - self._connection_failures) / self._connection_attempts if self._connection_attempts > 0 else 0,
                'reconnection_count': self._reconnection_count,
                'avg_reconnection_duration': self._reconnection_duration / self._reconnection_count if self._reconnection_count > 0 else 0
            }
            
            return stats
    
    def get_detailed_stats(self) -> Dict:
        """Get detailed statistics for all operations."""
        overall_stats = self.get_overall_stats()
        operation_stats = {}
        
        with self._lock:
            for operation in self._metrics.keys():
                operation_stats[operation] = self.get_operation_stats(operation)
        
        return {
            'overall': overall_stats,
            'operations': operation_stats,
            'timestamp': time.time()
        }
    
    def reset_interval_metrics(self):
        """Reset interval-based metrics (for periodic reporting)."""
        with self._lock:
            self._last_reset_time = time.time()
    
    def export_to_json(self, file_path: str):
        """Export metrics to JSON file."""
        stats = self.get_detailed_stats()
        with open(file_path, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def get_final_test_summary(self) -> Dict[str, Any]:
        """Get final test summary in standardized format."""
        stats = self.get_overall_stats()

        # Extract workload name from app_name (format: {app-name}-{workload-profile})
        workload_name = "unknown"
        if "-" in self.app_name:
            # Split on last dash to handle app names with dashes
            parts = self.app_name.rsplit("-", 1)
            if len(parts) == 2:
                workload_name = parts[1]

        # Format duration as string with unit
        duration_seconds = stats['test_duration']
        if duration_seconds < 60:
            duration_str = f"{duration_seconds:.1f}s"
        elif duration_seconds < 3600:
            duration_str = f"{duration_seconds/60:.1f}m"
        else:
            duration_str = f"{duration_seconds/3600:.1f}h"

        # Format success rate as percentage string
        success_rate = stats['overall_success_rate'] * 100

        # Format connection success rate as percentage string
        connection_success_rate = stats['connection_success_rate'] * 100

        # Convert reconnection duration to milliseconds
        avg_reconnection_duration_ms = stats['avg_reconnection_duration'] * 1000

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

        # Calculate timestamps
        current_time = time.time()
        start_time = current_time - duration_seconds

        summary = {
            "app_name": self.app_name,
            "instance_id": self.instance_id,
            "run_id": self.run_id,
            "version": self.version,
            "test_duration": duration_str,
            "workload_name": workload_name,
            "total_commands_count": stats['total_operations'],
            "successful_commands_count": stats['successful_operations'],
            "failed_commands_count": stats['failed_operations'],
            "success_rate": f"{success_rate:.2f}%",
            "overall_throughput": round(stats['overall_ops_per_second']),
            "connection_attempts": stats['connection_attempts'],
            "connection_failures": stats['connection_failures'],
            "connection_drops": stats['connection_drops'],
            "connection_success_rate": f"{connection_success_rate:.2f}%",
            "reconnection_count": stats['reconnection_count'],
            "avg_reconnection_duration_ms": round(avg_reconnection_duration_ms, 1),
            "run_start": start_time,
            "run_end": current_time
        }

        # Add latency percentiles if available
        summary.update(latency_stats)

        return summary

    def export_final_summary_to_json(self, file_path: str):
        """Export final test summary to JSON file."""
        summary = self.get_final_test_summary()
        with open(file_path, 'w') as f:
            json.dump(summary, f, indent=2)

    def print_summary(self):
        """Print final test summary in standardized format."""
        summary = self.get_final_test_summary()

        print("\n" + "="*60)
        print("FINAL TEST SUMMARY")
        print("="*60)
        print(f"Test Duration: {summary['test_duration']}")
        print(f"Workload Name: {summary['workload_name']}")
        print(f"Total Commands: {summary['total_commands_count']:,}")
        print(f"Successful Commands: {summary['successful_commands_count']:,}")
        print(f"Failed Commands: {summary['failed_commands_count']:,}")
        print(f"Success Rate: {summary['success_rate']}")
        print(f"Overall Throughput: {summary['overall_throughput']:,} ops/sec")
        print(f"Connection Attempts: {summary['connection_attempts']}")
        print(f"Connection Failures: {summary['connection_failures']}")
        print(f"Connection Drops: {summary['connection_drops']}")
        print(f"Connection Success Rate: {summary['connection_success_rate']}")
        print(f"Reconnection Count: {summary['reconnection_count']}")
        if summary['reconnection_count'] > 0:
            print(f"Avg Reconnection Duration: {summary['avg_reconnection_duration_ms']:.1f}ms")
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
