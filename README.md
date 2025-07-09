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

You'll need the **Redis Metrics Stack** running to collect and visualize metrics:

```bash
# Clone and start the metrics stack (separate repository)
git clone <redis-metrics-stack-repo>
cd redis-metrics-stack
make start
```

### 🛠️ Local Development (Recommended)

**Fast iteration with external metrics stack:**

```bash
# Install dependencies
make install-deps

# Run tests repeatedly (fast iteration)
python main.py run --workload-profile basic_rw --duration 30
python main.py run --workload-profile high_throughput --duration 60
python main.py run --workload-profile basic_rw # unlimited test run
```

**Access your dashboards (from metrics stack):**
- **📊 Grafana**: http://localhost:3000 (admin/admin) - **Redis Test Dashboard**
- **📈 Prometheus**: http://localhost:9090 - Raw metrics

### 🐳 Docker Environment

**For testing containerized setup:**

```bash
# Build the application
make build

# Run with Docker (requires external metrics stack)
docker run --network redis-test-network \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317 \
  redis-py-test-app \
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
python main.py test-connection
```

### Access Services (from metrics stack)
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
# 60-second basic test
make test

# Test Redis connection
make test-connection
```

#### **Custom Test Examples:**

**Basic Read/Write Operations:**
```bash
# 30-second test
./venv/bin/python main.py run --workload-profile basic_rw --duration 30

# Unlimited duration (until Ctrl+C)
./venv/bin/python main.py run --workload-profile basic_rw
```

**High Throughput Testing:**
```bash
# 60-second high-load test
./venv/bin/python main.py run --workload-profile high_throughput --duration 60 --threads-per-client 4

# Unlimited high-load test (for sustained performance monitoring)
./venv/bin/python main.py run --workload-profile high_throughput --threads-per-client 4
```

**List Operations:**
```bash
# 45-second list operations test
./venv/bin/python main.py run --workload-profile list_operations --duration 45

# Unlimited list operations (for memory usage monitoring)
./venv/bin/python main.py run --workload-profile list_operations
```

**Async Mixed Workload:**
```bash
# 2-minute mixed workload test
./venv/bin/python main.py run --workload-profile async_mixed --duration 120

# Unlimited mixed workload (for long-term stability testing)
./venv/bin/python main.py run --workload-profile async_mixed
```

**Custom Configuration:**
```bash
# Multiple clients with custom threading
# Note: app-name will be concatenated with workload profile (python-dev-basic_rw)
./venv/bin/python main.py run \
  --workload-profile basic_rw \
  --duration 300 \
  --client-instances 2 \
  --connections-per-client 10 \
  --threads-per-client 3 \
  --app-name python-dev \
  --version test-v1
```

**Environment Variable Configuration:**
```bash
# Set via environment variables
export TEST_DURATION=180
export TEST_CLIENT_INSTANCES=3
export APP_NAME=python-custom
./venv/bin/python main.py run --workload-profile high_throughput
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
./venv/bin/python main.py run --workload-profile high_throughput &

# Monitor in real-time
echo "Monitor at: http://localhost:3000"
echo "Stop test with: kill %1"

# Or run in foreground and stop with Ctrl+C
./venv/bin/python main.py run --workload-profile basic_rw
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
```bash
--workload-profile PROFILE    # Workload type (required)
--duration SECONDS           # Test duration (default: unlimited)
--client-instances N         # Number of client pools (default: 1)
--connections-per-client N   # Connections per pool (default: 5)
--threads-per-client N       # Worker threads per pool (default: 2)
--app-name NAME             # Base application name (default: python)
--version VERSION           # Version label (default: dev)
--host HOST                 # Redis host (default: localhost)
--port PORT                 # Redis port (default: 6379)
--quiet                     # Minimal output
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
```

### Performance Tuning Examples

**Low Resource Testing:**
```bash
./venv/bin/python main.py run \
  --workload-profile basic_rw \
  --duration 60 \
  --client-instances 1 \
  --connections-per-client 2 \
  --threads-per-client 1
```

**High Load Testing:**
```bash
./venv/bin/python main.py run \
  --workload-profile high_throughput \
  --duration 300 \
  --client-instances 3 \
  --connections-per-client 15 \
  --threads-per-client 5
```

**Memory Usage Testing:**
```bash
./venv/bin/python main.py run \
  --workload-profile list_operations \
  --duration 600 \
  --client-instances 2 \
  --connections-per-client 8 \
  --threads-per-client 3
```

## Manual Installation

### Prerequisites & Dependencies

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment configuration (optional):
```bash
cp .env.example .env
# Edit .env with your Redis configuration
```

### Basic Usage

Test Redis connection:
```bash
python main.py test-connection
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

Available workload profiles with intuitive names:

- **`basic_rw`**: Basic read/write operations (SET, GET, DEL)
- **`high_throughput`**: Optimized for maximum throughput with pipelining
- **`list_operations`**: List-based operations (LPUSH, LRANGE, LPOP)
- **`pubsub_heavy`**: Publish/Subscribe operations
- **`transaction_heavy`**: Transaction-based operations (MULTI/EXEC)
- **`async_mixed`**: Mixed async operations with pipelining

List all profiles:
```bash
python main.py list-profiles
```

Describe a specific profile:
```bash
python main.py describe-profile high_throughput
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

- **Prometheus metrics** available at `http://localhost:8000/metrics`
- **Real-time statistics** during test execution
- **JSON export** for custom analysis with `--output-file`
- **Comprehensive logging** with configurable levels

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

## Core Files

- `main.py` - Entry point and CLI interface
- `config.py` - Configuration management and workload profiles
- `redis_client.py` - Redis connection management with resilience
- `workloads.py` - Workload implementations
- `test_runner.py` - Main test execution engine
- `metrics.py` - OpenTelemetry metrics collection
- `logger.py` - Logging configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template
- `Makefile` - Development and build commands
- `Dockerfile` - Container image definition
- `setup.sh` - Quick setup script

## Related Projects

- **`redis-metrics-stack`** - Observability infrastructure (separate repository)
  - OpenTelemetry Collector
  - Prometheus metrics storage
  - Grafana dashboards
  - Redis database for testing
