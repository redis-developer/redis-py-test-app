# Redis Test App Observability Stack

This document describes the complete observability setup for the Redis testing application, including metrics, tracing, and dashboards.

## 🏗️ Architecture

The observability stack includes:

- **Redis Test App** - Python application with OpenTelemetry instrumentation
- **Redis** - Target database for testing
- **OpenTelemetry Collector** - Metrics and traces aggregation
- **Prometheus** - Metrics storage and querying
- **Grafana** - Dashboards and visualization
- **Jaeger** - Distributed tracing

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- At least 4GB RAM available for containers

### Start the Stack
```bash
./start-observability-stack.sh
```

### Access Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **App Metrics**: http://localhost:8000/metrics

## 📊 Metrics Available

### Redis Operation Metrics
- `redis_operations_total` - Total operations by type and status
- `redis_operation_duration_seconds` - Operation latency histograms
- `redis_connections_total` - Connection attempts and failures
- `redis_active_connections` - Current active connections
- `redis_reconnection_duration_seconds` - Reconnection timing

### Application Metrics
- Memory usage and CPU utilization
- Thread pool statistics
- Error rates and types
- Throughput measurements

## 🔍 Tracing

OpenTelemetry provides distributed tracing for:
- Redis operations (GET, SET, etc.)
- Connection management
- Workload execution
- Error propagation

## 📈 Grafana Dashboards

### Pre-configured Dashboards
1. **Redis Test App Dashboard** - Main performance overview
   - Operations rate and latency
   - Error rates
   - Connection health
   - Memory and CPU usage

### Custom Dashboards
You can create additional dashboards using the Prometheus datasource.

## 🔧 Configuration

### Environment Variables
Key configuration options in `.env`:

```bash
# OpenTelemetry
OTEL_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_SERVICE_NAME=redis-py-test-app

# Metrics
METRICS_ENABLED=true
METRICS_PORT=8000
```

### Workload Configuration
Modify `docker-compose.yml` to change test parameters:

```yaml
command: >
  python main.py
  --workload-profile high_throughput
  --duration 3600
  --target-ops-per-second 1000
```

## 🎯 Use Cases

### Local Development
- Real-time performance monitoring
- Debugging connection issues
- Workload optimization
- Memory leak detection

### Cloud Deployment
The same stack can be deployed to cloud platforms:

1. **AWS**: ECS/EKS with CloudWatch integration
2. **GCP**: GKE with Cloud Monitoring
3. **Azure**: AKS with Azure Monitor

### Long-term Testing
For continuous performance monitoring:

1. Deploy to cloud with persistent storage
2. Configure alerting rules
3. Set up automated reporting
4. Monitor for performance degradation

## 🛠️ Troubleshooting

### Common Issues

**Services not starting:**
```bash
docker-compose logs <service-name>
```

**Metrics not appearing:**
- Check OpenTelemetry Collector logs
- Verify endpoint configuration
- Ensure network connectivity

**High memory usage:**
- Adjust metrics retention
- Reduce scrape intervals
- Limit trace sampling

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# Restart specific service
docker-compose restart redis-test-app

# Scale test app instances
docker-compose up --scale redis-test-app=3

# Clean up everything
docker-compose down -v
```

## 📝 Extending the Stack

### Adding New Metrics
1. Modify `metrics.py` to add new instruments
2. Update Grafana dashboards
3. Configure alerting rules

### Custom Exporters
Add new exporters to OpenTelemetry Collector:
- InfluxDB for time-series data
- Elasticsearch for log aggregation
- Custom webhooks for notifications

### Performance Tuning
- Adjust batch sizes in OTel Collector
- Configure appropriate retention policies
- Optimize dashboard queries

## 🔒 Security Considerations

For production deployment:
- Use proper authentication
- Configure TLS/SSL
- Implement network policies
- Regular security updates

## 📚 References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Design](https://grafana.com/docs/grafana/latest/dashboards/)
- [Jaeger Deployment](https://www.jaegertracing.io/docs/deployment/)
