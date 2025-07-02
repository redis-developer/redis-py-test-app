# Redis Test App Metrics Reference

Complete reference for all metrics collected by the Redis testing applications with multi-app support.

## 🏷️ Multi-Application Support

All metrics include labels for filtering by application name:

- **`app_name`**: Application name (python, go, java, etc.)
- **`service_name`**: Service identifier (redis-py-test-app, redis-go-test-app, etc.)
- **`instance_id`**: Unique instance identifier

## 📊 Core Metrics

### **1. Total Operations (Success/Error)**
```
redis_operations_total{operation="SET", status="success", app_name="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Counter
- **Description**: Total number of Redis operations
- **Labels**: operation, status, app_name, service_name, instance_id
- **Values**: Increments on each operation

### **2. Operation Latency (Percentiles)**
```
redis_operation_duration_seconds{operation="GET", app_name="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Histogram
- **Description**: Duration of Redis operations for percentile calculation
- **Labels**: operation, app_name, service_name, instance_id
- **Buckets**: 0.0001s to 10s (optimized for high-performance Redis)

### **3. Throughput (Operations per Second)**
```
redis_operations_per_second{app_name="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Gauge
- **Description**: Current operations per second
- **Labels**: app_name, service_name, instance_id
- **Updates**: Real-time calculation

### **4. Error Rate Percentage**
```
redis_error_rate_percent{sdk="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Gauge
- **Description**: Current error rate as percentage
- **Labels**: sdk, service_name, instance_id
- **Range**: 0-100%

### **5. Reconnection Duration**
```
redis_reconnection_duration_seconds{sdk="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Histogram
- **Description**: Time taken for reconnection attempts
- **Labels**: sdk, service_name, instance_id
- **Buckets**: 0.1s to 60s

### **6. Active Connections**
```
redis_active_connections{sdk="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Gauge
- **Description**: Current number of active Redis connections
- **Labels**: sdk, service_name, instance_id

### **7. Connection Attempts**
```
redis_connections_total{status="success", sdk="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Counter
- **Description**: Total connection attempts
- **Labels**: status, sdk, service_name, instance_id

### **8. Average Latency**
```
redis_average_latency_seconds{operation="SET", sdk="python", service_name="redis-py-test-app", instance_id="python-redis-test-1"}
```
- **Type**: Gauge
- **Description**: Average operation latency (for quick overview)
- **Labels**: operation, sdk, service_name, instance_id

## 🎯 Grafana Query Examples

### **Filter by Application Type**
```promql
# Python app operations only
redis_operations_total{app_name="python"}

# Go app operations only
redis_operations_total{app_name="go"}

# Java app operations only
redis_operations_total{app_name="java"}
```

### **Compare Applications**
```promql
# Throughput comparison across app types
sum(rate(redis_operations_total[5m])) by (app_name)

# Latency comparison (95th percentile)
histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket[5m])) by (app_name)

# Error rate comparison
avg(redis_error_rate_percent) by (app_name)
```

### **Multi-Instance Monitoring**
```promql
# All Python instances
redis_operations_per_second{app_name="python"}

# Specific instance
redis_operations_per_second{instance_id="python-redis-test-1"}

# Instance comparison
sum(rate(redis_operations_total[5m])) by (instance_id)
```

### **Operation-Specific Analysis**
```promql
# SET operation latency across all apps
histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket{operation="SET"}[5m])) by (app_name)

# GET operation throughput by app type
sum(rate(redis_operations_total{operation="GET"}[5m])) by (app_name)

# Error rate for specific operations
rate(redis_operations_total{operation="LPUSH", status="error"}[5m]) / rate(redis_operations_total{operation="LPUSH"}[5m]) * 100
```

## 🔧 Configuration for Different Apps

### **Python App (.env.docker)**
```bash
APP_NAME=redis-py-6.2.0
INSTANCE_ID=python-redis-test-1
OTEL_SERVICE_NAME=redis-py-test-app
```

### **Go App (example)**
```bash
APP_NAME=go-9.3.2
INSTANCE_ID=go-redis-test-1
OTEL_SERVICE_NAME=redis-go-test-app
```

### **Java App (example)**
```bash
APP_NAME=jedis-6.0.0
INSTANCE_ID=java-redis-test-1
OTEL_SERVICE_NAME=redis-java-test-app
```

## 📈 Dashboard Panels

### **Overview Panel**
```promql
# Total operations across all apps
sum(rate(redis_operations_total[5m]))

# Success rate across all apps
sum(rate(redis_operations_total{status="success"}[5m])) / sum(rate(redis_operations_total[5m])) * 100
```

### **Performance Comparison Panel**
```promql
# Throughput by app type
sum(rate(redis_operations_total[5m])) by (app_name)

# Average latency by app type
avg(redis_average_latency_seconds) by (app_name)
```

### **Error Analysis Panel**
```promql
# Error rate by app type
avg(redis_error_rate_percent) by (app_name)

# Errors by operation and app type
sum(rate(redis_operations_total{status="error"}[5m])) by (operation, app_name)
```

## 🚀 Benefits

### **Multi-App Monitoring**
- ✅ **Compare performance** across different language implementations
- ✅ **Identify bottlenecks** in specific app types
- ✅ **Track improvements** across Redis client libraries
- ✅ **Isolate issues** to specific applications or instances

### **Comprehensive Coverage**
- ✅ **All required metrics** from your specification
- ✅ **Operation-specific tracking** for detailed analysis
- ✅ **Real-time calculations** for throughput and error rates
- ✅ **Percentile support** for latency analysis

### **Production Ready**
- ✅ **Scalable labeling** for large deployments
- ✅ **Efficient storage** with appropriate metric types
- ✅ **Standard formats** compatible with all monitoring tools
- ✅ **Easy filtering** and aggregation in Grafana

This metrics setup gives you complete visibility into Redis performance across all your testing applications! 🎯
