# Redis Python Test Application

A high-performance Redis load testing application built with Python and redis-py. Designed to simulate high-volume operations for testing client resilience during database upgrades, capable of generating 50K+ operations per second with comprehensive observability.

## Features

- **High throughput** through multi-threaded architecture
- **Standalone & Cluster Redis** support with TLS/SSL
- **Intuitive workload profiles** with descriptive names
- **OpenTelemetry metrics** for observability
- **Environment variable configuration** with python-dotenv
- **Connection resilience** with auto-reconnect and retry logic
- **CLI interface** with extensive configuration options

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** with pip
- **Redis server** running (localhost:6379 by default)
- **Redis Metrics Stack** (optional, for observability - separate repository)

For metrics collection and visualization, you'll need the separate metrics stack:

```bash
# Clone and start the metrics stack (optional - separate repository)
git clone <redis-metrics-stack-repo-url>
cd redis-metrics-stack
make start
```

### 🛠️ Local Development (Recommended)

**Quick setup and testing:**

```bash
# Install dependencies
make install-deps-venv

# Test Redis connection
make test-connection

# Run basic test (60 seconds)
make test

# Run custom tests
python main.py run --workload-profile basic_rw --duration 30
python main.py run --workload-profile high_throughput --duration 60
python main.py run --workload-profile basic_rw # unlimited test run

# Custom value sizes
python main.py run --workload-profile basic_rw --value-size 500 --duration 30
python main.py run --operations SET,GET --value-size-min 100 --value-size-max 2000 --duration 60
```

**With metrics stack (optional):**
- **📊 Grafana**: http://localhost:3000 (admin/admin) - **Redis Test Dashboard**
- **📈 Prometheus**: http://localhost:9090 - Raw metrics

### 🐳 Docker Environment

**For testing containerized setup:**

```bash
# Build the application
make build

# Run with Docker (standalone)
docker run redis-py-test-app:latest \
  python main.py run --workload-profile basic_rw --duration 60

# Run with Docker (with metrics stack)
docker run --network redis-test-network \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 \
  redis-py-test-app:latest \
  python main.py run --workload-profile basic_rw --duration 60
```

## 🛠️ Local Development

### Setup Development Environment

```bash
# Install Python dependencies
make install-deps

# Copy environment configuration (optional)
cp .env.example .env
# Edit .env with your Redis configuration

# Test Redis connection
make test-connection
```

### Available Make Commands

```bash
make help              # Show all available commands
make install-deps      # Install Python dependencies
make test-connection   # Test Redis connection
make test              # Run basic test (60 seconds)
make build             # Build Docker image
make clean             # Clean up Python cache and virtual environment
```

### Access Services (with metrics stack)
- **📊 Grafana**: http://localhost:3000 (admin/admin) - **Redis Test Dashboard**
- **📈 Prometheus**: http://localhost:9090 - Raw metrics and queries
- **📡 Redis**: localhost:6379 - Database connection

### Development Workflow

#### **Quick Iteration (Recommended):**
```bash
# Run tests repeatedly (edit code between runs)
python main.py run --workload-profile basic_rw --duration 30
python main.py run --workload-profile high_throughput --duration 60
python main.py run --workload-profile list_operations --duration 45

# View real-time metrics in Grafana: http://localhost:3000
```

#### **Long-Running Tests (Unlimited Duration):**
```bash
# Run unlimited tests (until Ctrl+C)
python main.py run --workload-profile basic_rw
python main.py run --workload-profile high_throughput

# Monitor in real-time via Grafana: http://localhost:3000
# Stop test with Ctrl+C when ready
```

#### **Quick Tests:**
```bash
# Test Redis connection
make test-connection

# 60-second basic test
make test

# Build Docker image
make build
```

#### **Custom Test Examples:**

**Basic Read/Write Operations:**
```bash
# 30-second test
python main.py run --workload-profile basic_rw --duration 30

# Unlimited duration (until Ctrl+C)
python main.py run --workload-profile basic_rw
```

**High Throughput Testing:**
```bash
# 60-second high-load test
python main.py run --workload-profile high_throughput --duration 60 --threads-per-client 4

# Unlimited high-load test (for sustained performance monitoring)
python main.py run --workload-profile high_throughput --threads-per-client 4
```

**List Operations:**
```bash
# 45-second list operations test
python main.py run --workload-profile list_operations --duration 45

# Unlimited list operations (for memory usage monitoring)
python main.py run --workload-profile list_operations
```

**Async Mixed Workload:**
```bash
# 2-minute mixed workload test
python main.py run --workload-profile async_mixed --duration 120

# Unlimited mixed workload (for long-term stability testing)
python main.py run --workload-profile async_mixed
```

**Overriding Workload Operations:**
```bash
# Override basic_rw profile to use only SET and GET operations
python main.py run --workload-profile basic_rw --operations SET,GET --duration 60

# Override high_throughput profile with custom operations and weights
python main.py run --workload-profile high_throughput \
  --operations SET,GET,INCR,DEL \
  --operation-weights "{\"SET\": 0.3, \"GET\": 0.4, \"INCR\": 0.2, \"DEL\": 0.1}" \
  --duration 120

# Override list_operations profile to focus on LPUSH/LPOP only
python main.py run --workload-profile list_operations \
  --operations LPUSH,LPOP \
  --operation-weights "{\"LPUSH\": 0.6, \"LPOP\": 0.4}" \
  --duration 90

# Create custom workload from scratch (no profile)
python main.py run \
  --operations SET,GET,INCR,DECR \
  --operation-weights '{"SET": 0.25, "GET": 0.25, "INCR": 0.25, "DECR": 0.25}' \
  --value-size 200 \
  --key-prefix custom_test \
  --duration 60

# Override with single operation for focused testing
python main.py run --workload-profile basic_rw \
  --operations SET \
  --value-size 1000 \
  --duration 30
```

**Custom Configuration:**
```bash
# Multiple clients with custom threading
# Note: app-name will be concatenated with workload profile (python-dev-basic_rw)
python main.py run \
  --workload-profile basic_rw \
  --duration 300 \
  --clients 2 \
  --threads-per-client 3 \
  --max-connections 10 \
  --app-name python-dev \
  --version test-v1
```

**Environment Variable Configuration:**
```bash
# Set via environment variables
export TEST_DURATION=180
export TEST_CLIENT_INSTANCES=3
export TEST_THREADS_PER_CLIENT=2
export APP_NAME=python-custom
python main.py run --workload-profile high_throughput
```

### Available Make Commands
```bash
make help                    # Show all available commands
make dev-start               # Start complete development environment (first time)
make dev-start-metrics-stack # Start metrics stack only (quick iteration)
make dev-test                # Run quick test (60 seconds)
make dev-stop                # Stop metrics stack
make dev-logs                # View metrics stack logs
make status                  # Check service status
make install-deps            # Install Python dependencies
make build                   # Build Docker images
make clean                   # Clean up everything
```

### Monitoring Your Tests

**Real-time Grafana Dashboard:**
- Operations per second (live updates)
- Latency percentiles (95th, 50th, average)
- Error rates and success percentages
- Individual operation breakdowns (GET, SET, BATCH)
- Filterable by app name, version, and operation type

**Unlimited Test Monitoring:**
```bash
# Start long-running test in background
python main.py run --workload-profile high_throughput &

# Monitor in real-time
echo "Monitor at: http://localhost:3000"
echo "Stop test with: kill %1"

# Or run in foreground and stop with Ctrl+C
python main.py run --workload-profile basic_rw
# Press Ctrl+C when ready to stop
```

**Stop Development Environment:**
```bash
make dev-stop
```

## 📋 Workload Profiles & Configuration

### Available Workload Profiles

| Profile | Description | Operations | Use Case |
|---------|-------------|------------|----------|
| `basic_rw` | Basic read/write operations | GET, SET, DEL | General testing, development |
| `high_throughput` | Pipeline-based operations | Batched SET, GET, INCR | Performance testing, load testing |
| `list_operations` | Redis list operations | LPUSH, LRANGE, LPOP | List-specific workloads |
| `async_mixed` | Mixed async operations | GET, SET, INCR, DEL | Async pattern testing |

### Configuration Options

#### **CLI Parameters:**

**Redis Connection:**
```bash
--host HOST                      # Redis host (default: localhost)
--port PORT                      # Redis port (default: 6379)
--password PASSWORD              # Redis password
--db DB                          # Redis database number (default: 0)
--cluster                        # Use Redis Cluster mode
--cluster-nodes NODES            # Comma-separated cluster nodes (host:port)
--ssl-enabled                    # Use SSL/TLS connection
--ssl-cert-reqs LEVEL           # SSL certificate requirements (none/optional/required)
--ssl-ca-certs PATH             # Path to CA certificates file
--ssl-certfile PATH             # Path to client certificate file
--ssl-keyfile PATH              # Path to client private key file
--socket-timeout SECONDS        # Socket timeout (default: 5.0)
--socket-connect-timeout SECONDS # Socket connect timeout (default: 5.0)
--max-connections N             # Maximum connections per client (default: 50)
```

**Test Configuration:**
```bash
--duration SECONDS              # Test duration in seconds (unlimited if not specified)
--target-ops-per-second N       # Target operations per second
--clients N                     # Number of Redis client instances (default: 4)
--threads-per-client N          # Number of worker threads per client (default: 1)
```

**Workload Configuration:**
```bash
--workload-profile PROFILE     # Pre-defined workload profile
--operations OPS               # Comma-separated Redis operations (default: SET,GET)
--operation-weights JSON       # JSON string of operation weights
--key-prefix PREFIX            # Prefix for generated keys (default: test_key)
--key-range N                  # Range of key IDs to use (default: 10000)
--read-write-ratio RATIO       # Ratio of read operations 0.0-1.0 (default: 0.7)
--value-size BYTES             # Fixed value size in bytes (overrides min/max)
--value-size-min BYTES         # Minimum value size in bytes (default: 100)
--value-size-max BYTES         # Maximum value size in bytes (default: 1000)
```

**Pipeline & Advanced:**
```bash
--use-pipeline                 # Use Redis pipelining
--pipeline-size N              # Operations per pipeline (default: 10)
--async-mode                   # Use asynchronous operations
--transaction-size N           # Operations per transaction (default: 5)
--pubsub-channels CHANNELS     # Comma-separated pub/sub channels
```

**Application Identification:**
```bash
--app-name NAME                # Application name for filtering (default: python)
--instance-id ID               # Unique instance identifier (auto-generated)
--run-id ID                    # Unique run identifier (auto-generated)
--version VERSION              # Version identifier (defaults to redis-py version)
```

**Logging & Output:**
```bash
--log-level LEVEL              # Logging level (DEBUG/INFO/WARNING/ERROR)
--log-file PATH                # Log file path
--output-file PATH             # Output file for JSON test summary
--quiet                        # Suppress periodic stats output
```

**OpenTelemetry & Metrics:**
```bash
--otel-endpoint URL            # OpenTelemetry OTLP endpoint
--otel-service-name NAME       # OpenTelemetry service name (default: redis-load-test)
--otel-export-interval MS      # Export interval in milliseconds (default: 5000)
```

**Configuration Files:**
```bash
--config-file PATH             # Load configuration from YAML/JSON file
--save-config PATH             # Save current configuration to file
```

#### **App Naming Convention:**
The final app name in metrics is automatically concatenated as: `{app-name}-{workload-profile}`

**Examples:**
- `--app-name python --workload-profile basic_rw` → `python-basic_rw`
- `--app-name python-dev --workload-profile high_throughput` → `python-dev-high_throughput`
- `--app-name go-test --workload-profile list_operations` → `go-test-list_operations`

This allows easy filtering and identification of different workloads in Grafana dashboards.

#### **Environment Variables:**
```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Test Configuration
TEST_DURATION=300
TEST_CLIENT_INSTANCES=2
TEST_CONNECTIONS_PER_CLIENT=10
TEST_THREADS_PER_CLIENT=3

# Application Identity
APP_NAME=python-dev
INSTANCE_ID=  # Auto-generated random ID if not specified
VERSION=v1.0.0

# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Output
OUTPUT_FILE=test_results.json  # If specified, final summary goes to file; otherwise stdout
```

### Performance Tuning Examples

**Low Resource Testing:**
```bash
python main.py run \
  --workload-profile basic_rw \
  --duration 60 \
  --client-instances 1 \
  --connections-per-client 2 \
  --threads-per-client 1
```

**High Load Testing:**
```bash
python main.py run \
  --workload-profile high_throughput \
  --duration 300 \
  --client-instances 3 \
  --connections-per-client 15 \
  --threads-per-client 5
```

**Memory Usage Testing:**
```bash
python main.py run \
  --workload-profile list_operations \
  --duration 600 \
  --client-instances 2 \
  --connections-per-client 8 \
  --threads-per-client 3
```

### Final Test Summary Output

The application outputs a standardized final test summary at the end of each test run. This summary includes key metrics and connection statistics.

**Output to stdout (default):**
```bash
python main.py run \
  --workload-profile basic_rw \
  --duration 60
```

**Output to file:**
```bash
python main.py run \
  --workload-profile high_throughput \
  --duration 300 \
  --output-file results.json
```

**Example Final Summary Output:**
```json
{
  "app_name": "python-basic-rw",
  "instance_id": "python-basic-rw-a1b2c3d4",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "redis-py-5.0.1",
  "test_duration": "60.0s",
  "workload_name": "basic_rw",
  "total_commands_count": 1234567,
  "successful_commands_count": 1234565,
  "failed_commands_count": 2,
  "success_rate": "99.84%",
  "overall_throughput": 20576,
  "connection_attempts": 5,
  "connection_failures": 0,
  "connection_drops": 0,
  "connection_success_rate": "100.00%",
  "reconnection_count": 0,
  "avg_reconnection_duration_ms": 0,
  "run_start": 1703097600.123,
  "run_end": 1703097660.456,
  "min_latency_ms": 0.12,
  "max_latency_ms": 45.67,
  "median_latency_ms": 1.23,
  "p95_latency_ms": 3.45,
  "p99_latency_ms": 8.90,
  "avg_latency_ms": 1.56
}
```

## Manual Installation

### Prerequisites & Dependencies

1. Install dependencies:
```bash
make install-deps
# OR manually:
# pip install -r requirements.txt
```

2. Copy environment configuration (optional):
```bash
cp .env.example .env
# Edit .env with your Redis configuration
```

### Basic Usage

Test Redis connection:
```bash
make test-connection
# OR manually:
# python main.py test-connection
```

Run a basic load test:
```bash
python main.py run --client-instances 1 --connections-per-client 1 --threads-per-client 1 --workload-profile basic_rw
```

Use a workload profile:
```bash
python main.py run --workload-profile high_throughput --client-instances 2 --connections-per-client 5 --threads-per-client 4
```

Test Redis Cluster:
```bash
python main.py run --cluster --cluster-nodes "node1:7000,node2:7000,node3:7000"
```

## Workload Profiles

### Available Profiles

| Profile | Default Operations | Description |
|---------|-------------------|-------------|
| **`basic_rw`** | SET (40%), GET (50%), DEL (10%) | Basic read/write operations for general testing |
| **`high_throughput`** | SET (40%), GET (60%) | Optimized for maximum throughput with pipelining |
| **`list_operations`** | LPUSH (40%), LRANGE (40%), LPOP (20%) | List-based operations for queue-like workloads |
| **`pubsub_heavy`** | PUBLISH (70%), SUBSCRIBE (30%) | Publish/Subscribe operations for messaging patterns |
| **`transaction_heavy`** | SET, GET | Transaction-based operations using MULTI/EXEC |
| **`async_mixed`** | SET (30%), GET (40%), LPUSH (20%), LRANGE (10%) | Mixed async operations with pipelining |

### Profile Commands

List all profiles:
```bash
python main.py list-profiles
```

Describe a specific profile:
```bash
python main.py describe-profile high_throughput
```

### Custom Operation Weights

Override default operations and weights using escaped JSON format:

```bash
# Basic example with equal weights
python main.py run --workload-profile basic_rw \
  --operation-weights "{\"SET\": 0.2, \"GET\": 0.2}"

# High throughput with custom mix
python main.py run --workload-profile high_throughput \
  --operations SET,GET,INCR,HSET,ZADD \
  --operation-weights "{\"SET\": 0.3, \"GET\": 0.4, \"INCR\": 0.1, \"HSET\": 0.1, \"ZADD\": 0.1}"

# List operations with custom weights
python main.py run --workload-profile list_operations \
  --operation-weights "{\"LPUSH\": 0.5, \"RPUSH\": 0.2, \"LRANGE\": 0.2, \"LPOP\": 0.1}"
```

## Available Redis Commands

The application supports a comprehensive set of Redis commands across all major data types:

### String Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `SET` | Set key-value pair | Basic write operation |
| `GET` | Get value by key | Basic read operation |
| `INCR` | Increment integer value | Counter operations |
| `DECR` | Decrement integer value | Counter operations |
| `INCRBY` | Increment by specific amount | Custom increment |
| `DECRBY` | Decrement by specific amount | Custom decrement |
| `APPEND` | Append to string value | String concatenation |
| `STRLEN` | Get string length | String analysis |

### Key Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `DEL` | Delete keys | Cleanup operations |
| `EXISTS` | Check if key exists | Conditional logic |
| `EXPIRE` | Set key expiration | TTL management |
| `TTL` | Get time to live | Expiration monitoring |
| `TYPE` | Get key data type | Type checking |

### List Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `LPUSH` | Push to left of list | Queue operations |
| `RPUSH` | Push to right of list | Stack operations |
| `LPOP` | Pop from left of list | Queue processing |
| `RPOP` | Pop from right of list | Stack processing |
| `LRANGE` | Get range from list | Batch retrieval |
| `LLEN` | Get list length | Size monitoring |
| `LTRIM` | Trim list to range | List maintenance |

### Set Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `SADD` | Add members to set | Unique collections |
| `SREM` | Remove members from set | Set maintenance |
| `SMEMBERS` | Get all set members | Full set retrieval |
| `SCARD` | Get set cardinality | Set size monitoring |

### Hash Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `HSET` | Set hash field | Object storage |
| `HGET` | Get hash field | Field retrieval |
| `HDEL` | Delete hash fields | Field cleanup |
| `HGETALL` | Get all hash fields | Object retrieval |
| `HLEN` | Get hash field count | Object size monitoring |

### Sorted Set Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `ZADD` | Add scored members | Leaderboards, rankings |
| `ZREM` | Remove members | Ranking maintenance |
| `ZRANGE` | Get range by rank | Top-N queries |
| `ZCARD` | Get sorted set size | Size monitoring |
| `ZSCORE` | Get member score | Score retrieval |

### Pub/Sub Operations
| Command | Description | Example Usage |
|---------|-------------|---------------|
| `PUBLISH` | Publish message | Event broadcasting |
| `SUBSCRIBE` | Subscribe to channels | Event listening |

### Usage Examples

```bash
# String-heavy workload
python main.py run --operations SET,GET,INCR,APPEND \
  --operation-weights "{\"SET\": 0.4, \"GET\": 0.4, \"INCR\": 0.1, \"APPEND\": 0.1}"

# Mixed data types workload
python main.py run --operations SET,GET,LPUSH,SADD,HSET,ZADD \
  --operation-weights "{\"SET\": 0.2, \"GET\": 0.3, \"LPUSH\": 0.2, \"SADD\": 0.1, \"HSET\": 0.1, \"ZADD\": 0.1}"

# Key management focused
python main.py run --operations SET,GET,EXISTS,EXPIRE,TTL,DEL \
  --operation-weights "{\"SET\": 0.3, \"GET\": 0.3, \"EXISTS\": 0.1, \"EXPIRE\": 0.1, \"TTL\": 0.1, \"DEL\": 0.1}"
```

## Configuration

### Environment Variables

Key environment variables (see `.env.example` for complete list):

```bash
# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=mypassword

# Test Configuration
TEST_CLIENT_INSTANCES=4
TEST_CONNECTIONS_PER_CLIENT=10
TEST_THREADS_PER_CLIENT=8
TEST_TARGET_OPS_PER_SECOND=50000
```

### Command Line Options

```bash
python main.py run --help
```

Key options:
- `--client-instances`: Number of client instances
- `--connections-per-client`: Connections per client instance
- `--threads-per-client`: Threads per client instance
- `--target-ops-per-second`: Target throughput
- `--duration`: Test duration in seconds
- `--workload-profile`: Pre-defined workload profile

## High-Volume Testing

For 50K+ ops/sec, configure multiple client instances:

```bash
python main.py run \
  --client-instances 4 \
  --connections-per-client 5 \
  --threads-per-client 4 \
  --workload-profile high_throughput
```

**Performance Examples:**
- **Single thread**: 3K-33K ops/sec (depending on workload)
- **Multiple threads**: 47K+ ops/sec with pipeline workloads
- **Basic workloads**: ~3,500 ops/sec (SET/GET/DEL)
- **Pipeline workloads**: 15K-33K ops/sec (batched operations)

## Metrics & Monitoring

The application provides comprehensive metrics and monitoring capabilities:

- **Final test summary** output to stdout or JSON file with `--output-file`
- **Real-time statistics** during test execution
- **OpenTelemetry metrics** sent to external metrics stack (optional)
- **Comprehensive logging** with configurable levels

### Final Test Summary

```bash
# Print summary to stdout (default)
python main.py run --workload-profile basic_rw --duration 60

# Save summary to JSON file
python main.py run --workload-profile basic_rw --duration 60 --output-file results.json
```

Example output:
```json
{
  "app_name": "python-basic-rw",
  "instance_id": "python-basic-rw-a1b2c3d4",
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "version": "redis-py-5.0.1",
  "test_duration": "60.0s",
  "workload_name": "basic_rw",
  "total_commands_count": 1234567,
  "successful_commands_count": 1234565,
  "failed_commands_count": 2,
  "success_rate": "99.84%",
  "overall_throughput": 20576,
  "connection_attempts": 5,
  "connection_failures": 0,
  "connection_drops": 0,
  "connection_success_rate": "100.00%",
  "reconnection_count": 0,
  "avg_reconnection_duration_ms": 0,
  "run_start": 1703097600.123,
  "run_end": 1703097660.456,
  "min_latency_ms": 0.12,
  "max_latency_ms": 45.67,
  "median_latency_ms": 1.23,
  "p95_latency_ms": 3.45,
  "p99_latency_ms": 8.90,
  "avg_latency_ms": 1.56
}
```

## 📊 Metrics and Observability

This application sends metrics to an external **Redis Metrics Stack** using OpenTelemetry.

### Required Metrics Stack

You need the separate `redis-metrics-stack` repository running:

```bash
# Clone and start the metrics stack
git clone <redis-metrics-stack-repo>
cd redis-metrics-stack
make start
```

### Metrics Sent

The application automatically sends these standardized metrics:

- **`redis_operations_total`**: Counter of Redis operations
- **`redis_operation_duration`**: Histogram of operation latency
- **`redis_connections_total`**: Counter of connection attempts
- **`redis_reconnection_duration_ms`**: Histogram of reconnection time

### Configuration

Configure OpenTelemetry endpoint in `.env`:

```bash
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## ☁️ Production Deployment

**TODO: Complete production deployment documentation**

The application is designed for cloud deployment with:

- **✅ Kubernetes templates** (`k8s/` directory)
- **✅ Docker image** ready for deployment
- **✅ OpenTelemetry integration** for observability

**📋 TODO Items:**
- [ ] Complete Kubernetes manifests
- [ ] Helm chart implementation
- [ ] Production environment configuration
- [ ] Scaling and resource management

## 🧪 Testing

The application includes a comprehensive test suite for all workload implementations.

### Running Tests

**Quick test run:**
```bash
# Run all tests with default settings
python test_workloads.py

# Or use the test runner for better output
python run_tests.py
```

**Advanced test options:**
```bash
# Verbose output
python run_tests.py --verbose

# Quiet output
python run_tests.py --quiet

# Run specific test pattern
python run_tests.py --pattern "test_basic*"
```

### Test Coverage

The test suite covers:

- **BaseWorkload functionality** - Key/value generation, operation selection, threading safety
- **BasicWorkload operations** - SET, GET, DEL, INCR operations with error handling
- **ListWorkload operations** - LPUSH, RPUSH, LRANGE, LPOP, RPOP operations
- **PipelineWorkload** - Batch operations with individual metrics tracking
- **TransactionWorkload** - MULTI/EXEC transactions with proper cleanup
- **PubSubWorkload** - Publish/Subscribe with threading and message handling
- **WorkloadFactory** - Workload creation logic and type detection
- **Integration tests** - Real configuration profiles and concurrent execution
- **Edge cases** - Error conditions, empty configurations, invalid inputs

### Test Files

- `test_workloads.py` - Main test suite (50+ test cases)
- `run_tests.py` - Enhanced test runner with formatting and reporting

## Core Files

- `main.py` - Entry point and CLI interface
- `config.py` - Configuration management and workload profiles
- `redis_client.py` - Redis connection management with resilience
- `workloads.py` - Workload implementations
- `test_runner.py` - Main test execution engine
- `metrics.py` - Metrics collection and final test summaries
- `logger.py` - Logging configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template
- `Makefile` - Development and build commands
- `Dockerfile` - Container image definition

## Related Projects

- **`redis-metrics-stack`** - Observability infrastructure (separate repository)
  - OpenTelemetry Collector for metrics collection
  - Prometheus for metrics storage
  - Grafana dashboards for visualization
  - Redis database for testing
  - Complete monitoring stack for Redis applications

**Note**: This Redis test application is standalone and doesn't require the metrics stack to function. The metrics stack provides additional observability features for advanced monitoring and visualization.
