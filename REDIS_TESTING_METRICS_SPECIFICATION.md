# Redis Testing Applications - Metrics Specification

## Overview

This document defines the standardized metrics that all Redis testing applications (Python, Go, Java, Node.js, etc.) must implement to ensure consistent monitoring and observability across different programming languages and frameworks.

All applications will send metrics to a shared OpenTelemetry Collector, which exposes them to Prometheus for Grafana visualization.

## Architecture

```
Redis Test Apps → OpenTelemetry Collector → Prometheus → Grafana
```

- **Collection Method**: Push-based using OpenTelemetry Protocol (OTLP)
- **Export Endpoint**: `http://otel-collector:4317` (gRPC) or `http://otel-collector:4318` (HTTP)
- **Export Interval**: 5 seconds (5000ms)
- **Metric Format**: OpenTelemetry metrics with standardized names and labels

## Required Metrics

| Metric Name | Type | Unit | Description | Labels | Buckets/Notes |
|-------------|------|------|-------------|--------|---------------|
| `redis_operations_total` | Counter | `1` | Total number of Redis operations executed | `operation`, `status`, `app_name`, `instance_id`, `version`, `error_type` | Records every Redis command |
| `redis_operation_duration` | Histogram | `ms` | Duration of Redis operations in milliseconds | `operation`, `status`, `app_name`, `instance_id`, `version` | Buckets: `[0.1, 0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]` |
| `redis_connections_total` | Counter | `1` | Total number of Redis connection attempts | `status`, `app_name`, `instance_id`, `version` | Tracks connection success/failure |
| `redis_reconnection_duration_ms` | Histogram | `ms` | Duration of Redis reconnection attempts | `app_name`, `instance_id`, `version` | Buckets: `[100, 500, 1000, 2000, 5000, 10000, 30000, 60000]` |

### Label Definitions

| Label | Type | Description | Example Values |
|-------|------|-------------|----------------|
| `operation` | string | Redis command name | `SET`, `GET`, `DEL`, `INCR`, `LPUSH`, `HSET`, etc. |
| `status` | string | Operation/connection result | `success`, `error` |
| `app_name` | string | Application identifier | `python-basic-rw`, `go-high-throughput`, `java-pipeline` |
| `instance_id` | string | Unique instance identifier | `550e8400-e29b-41d4-a716-446655440000` (UUID) |
| `version` | string | Application/SDK version | `redis-py-5.0.1`, `1.0.0`, `dev` |
| `error_type` | string | Error classification | `none`, `timeout`, `connection_error`, `command_error`, `auth_error` |

### Metric Examples

```promql
# Operations counter
redis_operations_total{operation="SET", status="success", app_name="python-basic-rw", instance_id="abc123", version="1.0.0", error_type="none"} 1500
redis_operations_total{operation="GET", status="error", app_name="python-basic-rw", instance_id="abc123", version="1.0.0", error_type="timeout"} 5

# Connection attempts counter
redis_connections_total{status="success", app_name="python-basic-rw", instance_id="abc123", version="1.0.0"} 10
redis_connections_total{status="error", app_name="python-basic-rw", instance_id="abc123", version="1.0.0"} 2
```

## Label Standards

### App Name Convention
Format: `{language}-{workload-profile}`

Examples:
- `python-basic-rw`
- `python-high-throughput`
- `go-list-operations`
- `java-pipeline`
- `nodejs-pubsub`

### Instance ID
- **Format**: Random UUID (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- **Generation**: Generate new UUID on each application start
- **CLI Override**: Allow override via `--instance-id` parameter

### Version
- **SDK Version**: Use Redis client library version (e.g., `redis-py-5.0.1`)
- **CLI Override**: Allow override via `--version` parameter

### Error Types

| Error Type | Description | When to Use |
|------------|-------------|-------------|
| `none` | No error (success) | All successful operations |
| `timeout` | Operation timeout | Redis command takes too long |
| `connection_error` | Connection failure | Cannot connect to Redis |
| `command_error` | Invalid command or arguments | Malformed Redis commands |
| `memory_error` | Out of memory | Redis out of memory errors |
| `auth_error` | Authentication failure | Invalid credentials |
| `cluster_error` | Cluster-specific errors | Redis Cluster issues |
| `unknown` | Unclassified errors | Any other error types |

## OpenTelemetry Configuration

### Configuration Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Endpoint** | `http://otel-collector:4317` (gRPC)<br>`http://otel-collector:4318` (HTTP) | OpenTelemetry Collector endpoint |
| **Protocol** | OTLP | OpenTelemetry Protocol |
| **Export Interval** | 1000ms (1 second) | How often to export metrics |
| **Batch Size** | 1024 metrics | Metrics per batch |
| **Timeout** | 1 second | Export timeout |

### Resource Attributes

| Attribute | Value | Description |
|-----------|-------|-------------|
| `service.name` | `{app_name}` | Application identifier |
| `service.version` | `{version}` | Application version |

### Environment Variables

| Variable | Example Value | Description |
|----------|---------------|-------------|
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` | Collector endpoint |
| `OTEL_SERVICE_NAME` | `python-basic-rw` | Service name |
| `OTEL_SERVICE_VERSION` | `1.0.0` | Service version |
| `OTEL_EXPORT_INTERVAL` | `1000` | Export interval (ms) |

## Implementation Guidelines

### Metric Recording
1. **Operations**: Record every Redis command execution
2. **Timing**: Measure actual Redis operation time (exclude application logic)
3. **Errors**: Capture and classify all error types
4. **Connections**: Track connection lifecycle events
5. **Batching**: For pipeline operations, record individual command metrics

### Performance Considerations
1. **Async Export**: Use asynchronous metric export to avoid blocking operations
2. **Sampling**: No sampling required for counters and gauges
3. **Memory**: Limit histogram bucket count to prevent memory issues
4. **Buffering**: Use reasonable buffer sizes for metric batching

### Error Handling
1. **Metric Failures**: Log metric export failures but don't fail the application
2. **Fallback**: Continue operation even if metrics collection fails
3. **Retry**: Implement retry logic for transient export failures

## Testing and Validation

### Metric Verification
1. **Completeness**: Verify all required metrics are exported
2. **Labels**: Ensure all required labels are present and correctly formatted
3. **Values**: Validate metric values are reasonable and accurate
4. **Timing**: Confirm export intervals and timing accuracy

### Integration Testing
1. **Collector**: Test with OpenTelemetry Collector
2. **Prometheus**: Verify metrics appear in Prometheus
3. **Grafana**: Confirm dashboards display data correctly
4. **Multi-App**: Test with multiple applications running simultaneously

## Grafana Dashboard Variables

The shared Grafana dashboard uses these template variables:

- `$app_name` - Filter by application name (multi-select)
- `$instance_id` - Filter by instance ID (multi-select)  
- `$version` - Filter by version (multi-select)
- `$operation` - Filter by Redis operation (multi-select)

All metric queries should support these filters for consistent dashboard behavior.

## Example Grafana Queries

**Note on Time Ranges**: The `[10s]` in these queries represents a 10-second time window for rate calculations. This provides:
- **Near real-time response**: Changes visible within 10 seconds
- **Good balance**: Responsive enough for monitoring while reducing noise
- **Fast failure detection**: Quickly shows when Redis goes down



### Operations Rate by Status
```promql
# 10-second rate (recommended for near real-time monitoring)
sum(rate(redis_operations_total{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[10s])) by (operation, status)

# 5-minute rate (smoother, less responsive)
sum(rate(redis_operations_total{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[5m])) by (operation, status)
```

### Average Latency by Operation
```promql
# 5-minute average (recommended)
avg(rate(redis_operation_duration_sum{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[5m]) / rate(redis_operation_duration_count{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[5m])) by (operation)

# 1-minute average (more real-time)
avg(rate(redis_operation_duration_sum{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[1m]) / rate(redis_operation_duration_count{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[1m])) by (operation)
```

### 95th Percentile Latency
```promql
# 5-minute percentile (recommended)
histogram_quantile(0.95, sum(rate(redis_operation_duration_bucket{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[5m])) by (operation, le))

# 1-minute percentile (more real-time)
histogram_quantile(0.95, sum(rate(redis_operation_duration_bucket{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version"}[1m])) by (operation, le))
```

### Connection Success Rate
```promql
# 5-minute success rate (recommended)
sum(rate(redis_connections_total{app_name=~"$app_name", instance_id=~"$instance_id", version=~"$version", status="success"}[5m])) / sum(rate(redis_connections_total{app_name=~"$app_name", instance_id=~"$instance_id", version=~"$version"}[5m])) * 100

# 1-minute success rate (more real-time)
sum(rate(redis_connections_total{app_name=~"$app_name", instance_id=~"$instance_id", version=~"$version", status="success"}[1m])) / sum(rate(redis_connections_total{app_name=~"$app_name", instance_id=~"$instance_id", version=~"$version"}[1m])) * 100
```

### Error Rate by Operation
```promql
# 5-minute error rate (recommended)
sum(rate(redis_operations_total{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version", status="error"}[5m])) by (operation, error_type)

# 1-minute error rate (more real-time)
sum(rate(redis_operations_total{app_name=~"$app_name", instance_id=~"$instance_id", operation=~"$operation", version=~"$version", status="error"}[1m])) by (operation, error_type)
```

## Language-Specific Implementation Notes

### Python (OpenTelemetry)
```python
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Setup
meter = metrics.get_meter("redis-test-app", "1.0.0")
operations_counter = meter.create_counter(
    name="redis_operations_total",
    description="Total number of Redis operations",
    unit="1"
)

# Usage
operations_counter.add(1, {
    "operation": "SET",
    "status": "success",
    "app_name": "python-basic-rw",
    "instance_id": instance_id,
    "version": "1.0.0",
    "error_type": "none"
})
```

### Go (OpenTelemetry)
```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/metric"
)

meter := otel.Meter("redis-test-app")
operationsCounter, _ := meter.Int64Counter(
    "redis_operations_total",
    metric.WithDescription("Total number of Redis operations"),
    metric.WithUnit("1"),
)

operationsCounter.Add(ctx, 1, metric.WithAttributes(
    attribute.String("operation", "SET"),
    attribute.String("status", "success"),
    attribute.String("app_name", "go-basic-rw"),
    attribute.String("instance_id", instanceID),
    attribute.String("version", "1.0.0"),
    attribute.String("error_type", "none"),
))
```

### Java (OpenTelemetry)
```java
import io.opentelemetry.api.metrics.Meter;
import io.opentelemetry.api.metrics.LongCounter;
import io.opentelemetry.api.common.Attributes;

Meter meter = OpenTelemetry.getGlobalMeterProvider()
    .get("redis-test-app", "1.0.0");

LongCounter operationsCounter = meter
    .counterBuilder("redis_operations_total")
    .setDescription("Total number of Redis operations")
    .setUnit("1")
    .build();

operationsCounter.add(1, Attributes.of(
    AttributeKey.stringKey("operation"), "SET",
    AttributeKey.stringKey("status"), "success",
    AttributeKey.stringKey("app_name"), "java-basic-rw",
    AttributeKey.stringKey("instance_id"), instanceId,
    AttributeKey.stringKey("version"), "1.0.0",
    AttributeKey.stringKey("error_type"), "none"
));
```

### Node.js (OpenTelemetry)
```javascript
const { metrics } = require('@opentelemetry/api');

const meter = metrics.getMeter('redis-test-app', '1.0.0');
const operationsCounter = meter.createCounter('redis_operations_total', {
  description: 'Total number of Redis operations',
  unit: '1'
});

operationsCounter.add(1, {
  operation: 'SET',
  status: 'success',
  app_name: 'nodejs-basic-rw',
  instance_id: instanceId,
  version: '1.0.0',
  error_type: 'none'
});
```

## Deployment Configuration

### Docker Compose Example
```yaml
services:
  redis-test-app:
    image: your-redis-test-app
    environment:
      - OTEL_ENABLED=true
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
      - OTEL_SERVICE_NAME=python-basic-rw
      - OTEL_SERVICE_VERSION=1.0.0
      - APP_NAME=python-basic-rw
      - INSTANCE_ID=${RANDOM_UUID}
    depends_on:
      - otel-collector
```

### Kubernetes Example
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-test-app
spec:
  template:
    spec:
      containers:
      - name: redis-test-app
        env:
        - name: OTEL_ENABLED
          value: "true"
        - name: OTEL_EXPORTER_OTLP_ENDPOINT
          value: "http://otel-collector:4317"
        - name: OTEL_SERVICE_NAME
          value: "python-basic-rw"
        - name: APP_NAME
          value: "python-basic-rw"
        - name: INSTANCE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.uid
```

## Troubleshooting

### Common Issues

1. **No Data in Grafana**
   - Verify OpenTelemetry Collector is running and accessible
   - Check metric export endpoint configuration
   - Confirm Prometheus is scraping the collector
   - Validate metric names and labels match specification

2. **Missing Labels**
   - Ensure all required labels are included in metric calls
   - Check for typos in label names
   - Verify label values are not empty or null

3. **Incorrect Metric Types**
   - Use Counter for cumulative values (operations_total, connections_total)
   - Use Histogram for distributions (duration metrics)

4. **Performance Issues**
   - Reduce export frequency if needed
   - Increase batch sizes for high-throughput scenarios
   - Monitor collector resource usage

### Validation Checklist

- [ ] All 4 required metrics are implemented
- [ ] All required labels are present and correctly formatted
- [ ] App name follows naming convention
- [ ] Instance ID is unique per application instance
- [ ] Error types use standardized classifications
- [ ] Metric values are reasonable and accurate
- [ ] OpenTelemetry export is configured correctly
- [ ] Metrics appear in Prometheus targets
- [ ] Grafana dashboard displays data correctly

## Support and Updates

This specification may be updated as requirements evolve. All Redis testing applications should implement the current version to ensure compatibility with the shared monitoring infrastructure.

For questions or clarification, please refer to the reference Python implementation in the `redis-py-test-app` repository.
