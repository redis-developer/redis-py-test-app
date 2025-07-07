"""
Metrics collection and export for Redis test application with OpenTelemetry support.
"""
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Deque
import statistics
import json
import os

# Prometheus imports (for backward compatibility)
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# OpenTelemetry imports
from opentelemetry import metrics as otel_metrics
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export import BatchSpanProcessor
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

    def __init__(self, enable_prometheus: bool = True, prometheus_port: int = 8000,
                 enable_otel: bool = True, otel_endpoint: str = None,
                 service_name: str = "redis-load-test", service_version: str = "1.0.0",
                 otel_export_interval_ms: int = 5000, app_name: str = "python",
                 instance_id: str = None, version: str = None):
        self.logger = get_logger()
        self.enable_prometheus = enable_prometheus
        self.prometheus_port = prometheus_port
        self.enable_otel = enable_otel
        self.otel_endpoint = otel_endpoint
        self.service_name = service_name
        self.service_version = service_version
        self.otel_export_interval_ms = otel_export_interval_ms
        self.app_name = app_name
        self.instance_id = instance_id or f"{app_name}-{int(time.time())}"
        self.version = version or "unknown"

        # Thread-safe metrics storage
        self._lock = threading.RLock()
        self._metrics: Dict[str, OperationMetrics] = defaultdict(OperationMetrics)
        self._start_time = time.time()
        self._last_reset_time = time.time()

        # Connection metrics
        self._connection_attempts = 0
        self._connection_failures = 0
        self._reconnection_count = 0
        self._reconnection_duration = 0.0

        # OpenTelemetry setup (single collection method)
        if self.enable_otel:
            self._setup_opentelemetry()

    def _setup_opentelemetry(self):
        """Setup OpenTelemetry metrics and tracing."""
        try:
            # Create resource with minimal service information to reduce label duplication
            resource = Resource.create({
                "service.name": self.app_name,  # Use app_name instead of service_name
                "service.version": self.version
            })

            # Setup metrics
            if self.otel_endpoint:
                # OTLP exporter for metrics
                metric_exporter = OTLPMetricExporter(
                    endpoint=self.otel_endpoint,
                    insecure=True
                )
                metric_reader = PeriodicExportingMetricReader(
                    exporter=metric_exporter,
                    export_interval_millis=self.otel_export_interval_ms
                )
            else:
                # Prometheus exporter as fallback
                metric_reader = PrometheusMetricReader()

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
                name="redis_operation_duration_ms",
                description="Duration of Redis operations in milliseconds",
                unit="1"
            )

            self.otel_connections_counter = self.meter.create_counter(
                name="redis_connections_total",
                description="Total number of Redis connection attempts",
                unit="1"
            )

            self.otel_reconnection_duration = self.meter.create_histogram(
                name="redis_reconnection_duration_ms",
                description="Duration of Redis reconnection attempts in milliseconds",
                unit="1"
            )

            # Setup tracing
            if self.otel_endpoint:
                trace_exporter = OTLPSpanExporter(
                    endpoint=self.otel_endpoint,
                    insecure=True
                )
                trace_provider = TracerProvider(resource=resource)
                trace_provider.add_span_processor(
                    BatchSpanProcessor(trace_exporter)
                )
                otel_trace.set_tracer_provider(trace_provider)
                self.tracer = otel_trace.get_tracer(self.service_name, self.service_version)

            # Note: Using manual instrumentation instead of automatic Redis instrumentation
            # to have full control over operation labeling and avoid "BATCH" aggregation
            # RedisInstrumentor().instrument() is NOT called to prevent operation aggregation

            self.logger.info(f"OpenTelemetry setup completed with endpoint: {self.otel_endpoint}")

        except Exception as e:
            self.logger.error(f"Failed to setup OpenTelemetry: {e}")
            self.enable_otel = False

    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics with multi-app support."""
        # Base labels for all metrics
        base_labels = ['app_name', 'service_name', 'instance_id']

        # 1. Total number of successful/failed operations
        self.prom_operations_total = Counter(
            'redis_operations_total',
            'Total number of Redis operations',
            ['operation', 'status'] + base_labels
        )

        # 2. Operation latency (for percentiles)
        self.prom_operation_duration = Histogram(
            'redis_operation_duration_seconds',
            'Duration of Redis operations',
            ['operation'] + base_labels,
            buckets=[0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        )

        # 3. Connection metrics
        self.prom_connections_total = Counter(
            'redis_connections_total',
            'Total number of connection attempts',
            ['status'] + base_labels
        )

        self.prom_active_connections = Gauge(
            'redis_active_connections',
            'Number of active Redis connections',
            base_labels
        )

        # 4. Reconnection duration
        self.prom_reconnection_duration = Histogram(
            'redis_reconnection_duration_seconds',
            'Duration of reconnection attempts',
            base_labels,
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )

        # 5. Error rate percentage
        self.prom_error_rate = Gauge(
            'redis_error_rate_percent',
            'Current error rate percentage',
            base_labels
        )

        # 6. Average latency gauge (for quick overview)
        self.prom_avg_latency = Gauge(
            'redis_average_latency_seconds',
            'Average operation latency',
            ['operation'] + base_labels
        )
    
    def _start_prometheus_server(self):
        """Start Prometheus metrics server."""
        try:
            start_http_server(self.prometheus_port)
            self.logger.info(f"Prometheus metrics server started on port {self.prometheus_port}")
        except Exception as e:
            self.logger.error(f"Failed to start Prometheus server: {e}")
            self.enable_prometheus = False
    
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

        # Update OpenTelemetry metrics with cleaned-up labels
        if self.enable_otel and hasattr(self, 'otel_operations_counter'):
            status = 'success' if success else 'error'
            labels = {
                "operation": operation,
                "status": status,
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "version": self.version,
                "error_type": error_type or "none"
            }
            self.otel_operations_counter.add(1, labels)

            duration_labels = {
                "operation": operation,
                "status": status,
                "app_name": self.app_name,
                "instance_id": self.instance_id,
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

        # Update OpenTelemetry metrics with cleaned-up labels
        if self.enable_otel and hasattr(self, 'otel_connections_counter'):
            status = 'success' if success else 'error'
            labels = {
                "status": status,
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "version": self.version
            }
            self.otel_connections_counter.add(1, labels)

        # Connection metrics collected via OpenTelemetry only

    def record_reconnection(self, duration: float):
        """Record reconnection event."""
        with self._lock:
            self._reconnection_count += 1
            self._reconnection_duration += duration

        # Update OpenTelemetry metrics with cleaned-up labels
        if self.enable_otel and hasattr(self, 'otel_reconnection_duration'):
            labels = {
                "app_name": self.app_name,
                "instance_id": self.instance_id,
                "version": self.version
            }
            # Convert duration from seconds to milliseconds
            duration_ms = duration * 1000
            self.otel_reconnection_duration.record(duration_ms, labels)

        # Update Prometheus metrics with app identification
        if self.enable_prometheus and hasattr(self, 'prom_reconnection_duration'):
            labels = {
                'app_name': self.app_name,
                'service_name': self.service_name,
                'instance_id': self.instance_id
            }
            self.prom_reconnection_duration.labels(**labels).observe(duration)

    def update_active_connections(self, count: int):
        """Update active connections count."""
        # Update OpenTelemetry metrics
        if self.enable_otel and hasattr(self, 'otel_active_connections'):
            self.otel_active_connections.add(count)

        # Active connections tracked via OpenTelemetry only

    def update_calculated_metrics(self):
        """Update calculated metrics like throughput, error rate, and average latency."""
        if not self.enable_otel:
            return

        with self._lock:
            base_labels = {
                'app_name': self.app_name,
                'service_name': self.service_name,
                'instance_id': self.instance_id
            }

            # Calculate overall throughput and error rate
            total_ops = sum(m.total_count for m in self._metrics.values())
            total_errors = sum(m.error_count for m in self._metrics.values())

            if total_ops > 0:
                # Calculate current throughput (ops in last interval)
                current_time = time.time()
                if hasattr(self, '_last_metrics_update'):
                    time_diff = current_time - self._last_metrics_update
                    if time_diff > 0:
                        ops_diff = total_ops - getattr(self, '_last_total_ops', 0)
                        current_throughput = ops_diff / time_diff
                        # Calculated metrics are now handled by the OpenTelemetry Collector
                        # which exposes them via its Prometheus endpoint

                # Error rate and average latency calculations
                error_rate = (total_errors / total_ops) * 100
                # These calculated metrics are available via the collector's Prometheus endpoint

            # Store for next calculation
            self._last_metrics_update = current_time
            self._last_total_ops = total_ops

    def create_span(self, operation_name: str, **attributes):
        """Create an OpenTelemetry span for tracing Redis operations."""
        if self.enable_otel and hasattr(self, 'tracer'):
            return self.tracer.start_span(
                name=f"redis.{operation_name}",
                attributes={
                    "db.system": "redis",
                    "db.operation": operation_name,
                    **attributes
                }
            )
        else:
            # Return a no-op context manager if OpenTelemetry is not enabled
            from contextlib import nullcontext
            return nullcontext()
    
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
    
    def print_summary(self):
        """Print a summary of current metrics."""
        stats = self.get_overall_stats()
        
        print("\n" + "="*60)
        print("REDIS TEST METRICS SUMMARY")
        print("="*60)
        print(f"Test Duration: {stats['test_duration']:.2f}s")
        print(f"Total Operations: {stats['total_operations']:,}")
        print(f"Successful Operations: {stats['successful_operations']:,}")
        print(f"Failed Operations: {stats['failed_operations']:,}")
        print(f"Success Rate: {stats['overall_success_rate']:.2%}")
        print(f"Overall Throughput: {stats['overall_ops_per_second']:.2f} ops/sec")
        print(f"Connection Success Rate: {stats['connection_success_rate']:.2%}")
        if stats['reconnection_count'] > 0:
            print(f"Reconnections: {stats['reconnection_count']}")
            print(f"Avg Reconnection Duration: {stats['avg_reconnection_duration']:.2f}s")
        print("="*60)


# Global metrics collector instance
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def setup_metrics(enable_prometheus: bool = True, prometheus_port: int = 8000,
                 enable_otel: bool = True, otel_endpoint: str = None,
                 service_name: str = "redis-load-test", service_version: str = "1.0.0",
                 otel_export_interval_ms: int = 5000, app_name: str = "python",
                 instance_id: str = None, version: str = None) -> MetricsCollector:
    """Setup global metrics collector with multi-app support."""
    global _metrics_collector
    _metrics_collector = MetricsCollector(
        enable_prometheus=enable_prometheus,
        prometheus_port=prometheus_port,
        enable_otel=enable_otel,
        otel_endpoint=otel_endpoint,
        service_name=service_name,
        service_version=service_version,
        otel_export_interval_ms=otel_export_interval_ms,
        app_name=app_name,
        instance_id=instance_id,
        version=version
    )
    return _metrics_collector
