# Redis Test App - Docker Setup

Simple Docker-based setup for running the Redis testing application with full monitoring capabilities.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available

### Run Everything
```bash
./setup.sh
```

That's it! The script will:
- Build the Redis test application
- Start Redis database
- Start monitoring services (Prometheus, Grafana, Jaeger)
- Run the test workload

## 📊 Access Points

After running `./setup.sh`, you can access:

- **Application Metrics**: http://localhost:8000/metrics
- **Grafana Dashboards**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger Tracing**: http://localhost:16686
- **Redis Database**: localhost:6379

## 🔧 Customization

### Change Test Workload
Edit `docker-compose.yml` and modify the command section:

```yaml
command: >
  python main.py
  --workload-profile basic_rw          # Change workload type
  --duration 1800                      # Change duration (seconds)
  --target-ops-per-second 500          # Change target throughput
```

Available workload profiles:
- `basic_rw` - Basic read/write operations
- `high_throughput` - High-performance testing
- `list_operations` - List-based operations
- `pubsub_test` - Pub/Sub testing
- `transaction_test` - Transaction testing

### Restart with New Configuration
```bash
docker-compose restart redis-test-app
```

## 📝 Management Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Just the test app
docker-compose logs -f redis-test-app

# Just Redis
docker-compose logs -f redis
```

### Check Status
```bash
docker-compose ps
```

### Stop Services
```bash
docker-compose down
```

### Complete Cleanup
```bash
# Stop services only
./cleanup.sh

# Stop and remove data
./cleanup.sh --remove-data

# Stop, remove data and images
./cleanup.sh --remove-data --remove-images
```

## 🎯 Use Cases

### Local Development
- Test Redis performance
- Debug connection issues
- Monitor application metrics
- Analyze traces

### Performance Testing
- Run long-duration tests
- Monitor memory usage
- Track performance over time
- Detect memory leaks

### Cloud Deployment
The same Docker setup can be deployed to:
- AWS ECS/EKS
- Google Cloud Run/GKE
- Azure Container Instances/AKS
- Any Docker-compatible platform

## 🔍 Monitoring

### Key Metrics Available
- **Operations per second** by operation type
- **Latency percentiles** (50th, 95th, 99th)
- **Error rates** and error types
- **Connection health** and reconnections
- **Memory and CPU usage**

### Grafana Dashboards
Pre-configured dashboards show:
- Redis operation performance
- Application health
- Error tracking
- Resource utilization

### Distributed Tracing
Jaeger provides detailed traces for:
- Individual Redis operations
- Connection management
- Error propagation
- Performance bottlenecks

## 🛠️ Troubleshooting

### Services Won't Start
```bash
# Check Docker is running
docker info

# Check logs for errors
docker-compose logs

# Restart everything
./cleanup.sh && ./setup.sh
```

### High Resource Usage
- Reduce test duration or throughput
- Adjust metrics retention in Prometheus
- Scale down monitoring services if needed

### Port Conflicts
If ports are already in use, modify `docker-compose.yml`:
- Change `8000:8000` to `8001:8000` for metrics
- Change `3000:3000` to `3001:3000` for Grafana
- etc.

## 📚 Next Steps

1. **Run the setup**: `./setup.sh`
2. **Open Grafana**: http://localhost:3000
3. **Monitor your tests**: Watch the dashboards
4. **Customize workloads**: Edit docker-compose.yml
5. **Deploy to cloud**: Use the same configuration

The application is designed for both short-term testing and long-term monitoring to detect performance degradations and memory leaks across different Redis versions.
