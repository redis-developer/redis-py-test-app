# Redis Load Testing Application

A comprehensive Redis load testing tool designed to simulate high-volume operations for testing client resilience during database upgrades. Built with Python and redis-py, this application can generate 50K+ operations per second with comprehensive observability.

## Features

- **50K+ ops/sec capability** through multi-threaded architecture
- **Standalone & Cluster Redis** support with TLS/SSL
- **Intuitive workload profiles** with descriptive names
- **Comprehensive observability** with Prometheus metrics
- **Environment variable configuration** with python-dotenv
- **Connection resilience** with auto-reconnect and retry logic
- **CLI interface** with extensive configuration options

## 🚀 Quick Start (Docker - Recommended)

**The fastest way to get everything running with full monitoring:**

```bash
./setup.sh
```

This single command will:
- Build the Redis test application
- Start Redis database
- Launch complete monitoring stack (Prometheus, Grafana, Jaeger)
- Begin running performance tests

**Access your dashboards:**
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **Metrics**: http://localhost:8000/metrics

**Management commands:**
```bash
./status.sh    # Check if everything is running
./cleanup.sh   # Stop and clean up everything
```

📖 **For detailed Docker setup**: See [DOCKER_SETUP.md](DOCKER_SETUP.md)

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

## Core Files

- `main.py` - Entry point and CLI interface
- `config.py` - Configuration management and workload profiles
- `redis_client.py` - Redis connection management with resilience
- `workloads.py` - Workload implementations
- `test_runner.py` - Main test execution engine
- `metrics.py` - Metrics collection and reporting
- `logger.py` - Logging configuration
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variables template
