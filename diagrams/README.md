# Redis Test Application - Complete Architecture Documentation

This directory contains comprehensive diagrams documenting the Redis Test Application's architecture, class structure, code flow, and data flow.

## 📋 Diagram Overview

### 1. [Class Diagram](./class-diagram.md)
**Purpose**: Shows all classes, their properties, methods, and relationships
**Key Components**:
- **Configuration Classes**: `RunnerConfig`, `RedisConnectionConfig`, `TestConfig`, `WorkloadConfig`
- **Core Engine Classes**: `TestRunner`, `RedisClientManager`, `RedisClientPool`
- **Workload Classes**: `BaseWorkload` and 8 specialized implementations
- **Observability Classes**: `MetricsCollector`, `OperationMetrics`, `RedisTestLogger`
- **CLI Classes**: Command-line interface components

**Relationships**:
- Composition relationships between config classes
- Inheritance hierarchy for workload classes
- Dependency injection patterns for metrics and logging

### 2. [Code Flow Diagram](./code-flow-diagram.md)
**Purpose**: Illustrates the execution flow from application startup to operation completion
**Key Flows**:
- **Application Startup**: CLI → Configuration → TestRunner initialization
- **Thread Architecture**: Main thread spawning worker threads and stats reporter
- **Redis Operations**: Operation selection → execution → metrics recording
- **Metrics Collection**: Data aggregation → OpenTelemetry/Prometheus export

### 3. [Data Flow Diagram](./data-flow-diagram.md)
**Purpose**: Shows how data moves through the system components
**Key Data Flows**:
- **Configuration Data**: Environment variables → CLI args → merged config
- **Redis Connection Data**: Config → connection setup → pool management
- **Operation Data**: Key/value generation → Redis commands → response processing
- **Metrics Data**: Operation results → aggregation → export to observability stack

### 4. [System Architecture Diagram](./system-architecture-diagram.md)
**Purpose**: Provides high-level system architecture and deployment views
**Key Architectures**:
- **Overall System**: Layered architecture with clear separation of concerns
- **Component Interaction**: Runtime relationships between major components
- **Deployment Architecture**: Docker containerization and service orchestration
- **Error Handling**: Resilience patterns and failure recovery mechanisms

## 🏗️ Architecture Highlights

### Multi-Layered Design
```
┌─────────────────────────────────────┐
│           CLI Layer                 │
├─────────────────────────────────────┤
│       Configuration Layer           │
├─────────────────────────────────────┤
│         Core Engine                 │
├─────────────────────────────────────┤
│      Redis Connectivity             │
├─────────────────────────────────────┤
│       Workload Engine               │
├─────────────────────────────────────┤
│     Observability Layer             │
└─────────────────────────────────────┘
```

### Key Design Patterns

1. **Factory Pattern**: `WorkloadFactory` creates appropriate workload instances
2. **Pool Pattern**: `RedisClientPool` manages connection pooling
3. **Observer Pattern**: Metrics collection observes operation results
4. **Strategy Pattern**: Different workload implementations for various test scenarios
5. **Singleton Pattern**: Global metrics collector and logger instances

### Thread Architecture

```
TestRunner (Main)
├── Stats Reporter Thread (1x)
├── Client Pool 1
│   ├── Worker Thread 1-1
│   ├── Worker Thread 1-2
│   └── Worker Thread 1-N
├── Client Pool 2
│   ├── Worker Thread 2-1
│   ├── Worker Thread 2-2
│   └── Worker Thread 2-N
└── Client Pool N (client_instances)
    ├── Worker Thread N-1
    ├── Worker Thread N-2
    └── Worker Thread N-N
```

**Total Threads**: `client_instances × threads_per_client + 1 (stats reporter)`

### Configuration Hierarchy

```
RunnerConfig
├── RedisConnectionConfig
│   ├── Connection parameters (host, port, auth)
│   ├── SSL/TLS configuration
│   ├── Cluster mode settings
│   └── Connection pool settings
├── TestConfig
│   ├── Threading configuration
│   ├── Duration and rate limiting
│   └── WorkloadConfig
│       ├── Workload type selection
│       ├── Operation parameters
│       └── Workload-specific options
├── Metrics Configuration
│   ├── OpenTelemetry settings
│   ├── Prometheus configuration
│   └── Export intervals
└── Logging Configuration
    ├── Log levels
    ├── File output
    └── Console formatting
```

### Workload Types and Operations

| Workload Type | Primary Operations | Use Case |
|---------------|-------------------|----------|
| `basic_rw` | SET, GET, DEL, INCR | General Redis testing |
| `high_throughput` | Optimized operations | Performance testing |
| `list_operations` | LPUSH, RPOP, LLEN | List data structure testing |
| `set_operations` | SADD, SREM, SCARD | Set data structure testing |
| `sorted_set_operations` | ZADD, ZREM, ZCARD | Sorted set testing |
| `hash_operations` | HSET, HGET, HDEL | Hash data structure testing |
| `pipeline` | Batched operations | Pipeline performance testing |
| `pub_sub` | PUBLISH, SUBSCRIBE | Pub/Sub functionality testing |

### Metrics Collection Strategy

The application uses a **push-based metrics collection** approach:

1. **Operation Level**: Each Redis operation records metrics
2. **Thread Level**: Worker threads aggregate local metrics
3. **Application Level**: `MetricsCollector` centralizes all metrics
4. **Export Level**: OpenTelemetry exports to OTLP Collector
5. **Visualization Level**: Grafana displays metrics from Prometheus endpoint

### Error Handling and Resilience

- **Connection Resilience**: Automatic reconnection with exponential backoff
- **Operation Retry**: Configurable retry logic for failed operations
- **Pool Management**: Dynamic client pool sizing and health monitoring
- **Graceful Degradation**: Continues operation with reduced capacity during failures
- **Comprehensive Logging**: Detailed error tracking and debugging information

## 🚀 Getting Started with the Architecture

1. **Start with Class Diagram**: Understand the core classes and their relationships
2. **Follow Code Flow**: Trace execution from startup through operation completion
3. **Understand Data Flow**: See how configuration and operation data moves through the system
4. **Review System Architecture**: Get the big picture of component interactions
5. **Explore Deployment**: Understand how the system runs in containerized environments

## 📊 Observability Integration

The application integrates with modern observability stacks:

- **OpenTelemetry**: Standards-based metrics and tracing
- **Prometheus**: Time-series metrics storage and alerting
- **Grafana**: Rich visualization and dashboarding
- **Jaeger**: Distributed tracing and performance analysis

This comprehensive architecture enables high-performance Redis testing with full observability and operational insights.
