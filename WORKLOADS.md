# Redis Test App Workloads

This document describes all available workloads and their specific Redis operations.

## 🎯 Available Workloads

### **1. BasicWorkload (basic_rw)**
**Purpose**: Basic read/write operations for general testing
**Operations**:
- `SET` → `client.set(key, value)` - Set key-value pairs
- `GET` → `client.get(key)` - Retrieve values by key
- `DEL` → `client.delete(key)` - Delete keys
- `INCR` → `client.incr(key)` - Increment counters

**Use Cases**:
- General Redis performance testing
- Basic functionality validation
- Mixed read/write workloads

### **2. ListWorkload (list_operations)**
**Purpose**: List data structure operations
**Operations**:
- `LPUSH` → `client.lpush(key, value)` - Push to left of list
- `RPUSH` → `client.rpush(key, value)` - Push to right of list
- `LPOP` → `client.lpop(key)` - Pop from left of list
- `RPOP` → `client.rpop(key)` - Pop from right of list
- `LRANGE` → `client.lrange(key, start, end)` - Get range of elements

**Use Cases**:
- Queue implementations
- Stack operations
- List processing workloads

### **3. PipelineWorkload (high_throughput)**
**Purpose**: Batch operations using Redis pipelines
**Operations**:
- `SET` → `pipe.set(key, value)` - Batched sets
- `GET` → `pipe.get(key)` - Batched gets
- `INCR` → `pipe.incr(key)` - Batched increments

**Features**:
- Configurable batch size (default: 10)
- Reduced network round trips
- Higher throughput performance

**Use Cases**:
- High-throughput scenarios (your 700K+ ops/sec!)
- Bulk data operations
- Performance optimization testing

### **4. PubSubWorkload (pubsub_test)**
**Purpose**: Publish/Subscribe messaging patterns
**Operations**:
- `PUBLISH` → `client.publish(channel, message)` - Send messages
- `SUBSCRIBE` → Background subscriber thread - Receive messages

**Features**:
- Multi-channel support
- Background subscriber threads
- Real-time messaging testing

**Use Cases**:
- Real-time messaging systems
- Event-driven architectures
- Notification systems

### **5. TransactionWorkload (transaction_test)**
**Purpose**: Multi-command transactions with ACID properties
**Operations**:
- `MULTI` → Start transaction
- `SET/GET/INCR` → Queued operations
- `EXEC` → Execute transaction

**Use Cases**:
- ACID transaction testing
- Complex multi-step operations
- Data consistency validation

## 🔧 Configuration Examples

### **Basic Read/Write**
```bash
python main.py run --workload-profile basic_rw --target-ops-per-second 1000
```

### **High Throughput Pipeline**
```bash
python main.py run --workload-profile high_throughput --target-ops-per-second 100000
```

### **List Operations**
```bash
python main.py run --workload-profile list_operations --target-ops-per-second 5000
```

### **Pub/Sub Testing**
```bash
python main.py run --workload-profile pubsub_test --target-ops-per-second 1000
```

### **Transaction Testing**
```bash
python main.py run --workload-profile transaction_test --target-ops-per-second 500
```

## 📊 Metrics Per Operation

Each workload now provides **operation-specific metrics**:

### **Prometheus Metrics**
```
redis_operations_total{operation="SET", status="success"} 1234
redis_operations_total{operation="GET", status="success"} 5678
redis_operations_total{operation="LPUSH", status="success"} 910
redis_operations_total{operation="PUBLISH", status="success"} 112
```

### **Latency Histograms**
```
redis_operation_duration_seconds_bucket{operation="SET", le="0.001"} 800
redis_operation_duration_seconds_bucket{operation="GET", le="0.001"} 900
redis_operation_duration_seconds_bucket{operation="LPUSH", le="0.005"} 50
```

## 🎯 Grafana Dashboard Queries

### **Operations Rate by Type**
```promql
rate(redis_operations_total[5m]) by (operation, status)
```

### **Latency Percentiles by Operation**
```promql
histogram_quantile(0.95, rate(redis_operation_duration_seconds_bucket[5m])) by (operation)
```

### **Error Rate by Operation**
```promql
rate(redis_operations_total{status="error"}[5m]) / rate(redis_operations_total[5m]) by (operation)
```

## 🚀 Performance Characteristics

### **BasicWorkload**
- **Throughput**: 10K-50K ops/sec
- **Latency**: P95 < 5ms
- **Use Case**: General testing

### **PipelineWorkload** 
- **Throughput**: 100K-1M+ ops/sec (your current 700K+!)
- **Latency**: P95 < 10ms (batched)
- **Use Case**: Maximum performance

### **ListWorkload**
- **Throughput**: 5K-20K ops/sec
- **Latency**: P95 < 8ms
- **Use Case**: Data structure testing

### **PubSubWorkload**
- **Throughput**: 1K-10K msgs/sec
- **Latency**: P95 < 15ms
- **Use Case**: Messaging patterns

### **TransactionWorkload**
- **Throughput**: 500-5K txns/sec
- **Latency**: P95 < 20ms
- **Use Case**: ACID compliance

## 🔍 Operation-Specific Insights

With the new **direct Redis client method calls** (no more `execute_command`), you get:

### **🎯 True Operation-Level Metrics**
- **Direct method calls**: `client.set()`, `client.get()`, `client.lpush()`, etc.
- **Native Redis client**: Using the actual redis-py client methods
- **Proper operation names**: Each operation tracked with its real Redis command name
- **Accurate latencies**: Direct timing of actual Redis operations

### **📊 Benefits**
1. **Track per-operation performance** - See which Redis commands are fastest/slowest
2. **Identify bottlenecks** - Find operations causing latency spikes
3. **Optimize workloads** - Focus on problematic operation types
4. **Compare Redis versions** - See how different versions handle specific operations
5. **Detect memory leaks** - Monitor per-operation memory usage patterns
6. **True Redis testing** - Using the same methods your applications would use

### **🔧 Implementation Details**
- **Helper method**: `_execute_with_metrics()` reduces code duplication
- **Consistent timing**: All operations timed the same way
- **Error handling**: Proper exception propagation with metrics
- **Type safety**: Full type hints for all methods

This gives you **production-grade, operation-specific observability** into your Redis performance testing! 🚀
