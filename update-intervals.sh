#!/bin/bash

# Script to update all interval configurations based on .env.docker values

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo "🔄 Updating Interval Configurations"
echo "=================================="

# Check if .env.docker exists
if [ ! -f ".env.docker" ]; then
    echo "❌ .env.docker file not found"
    exit 1
fi

# Extract intervals from .env.docker
PROMETHEUS_SCRAPE=$(grep "PROMETHEUS_SCRAPE_INTERVAL=" .env.docker | cut -d'=' -f2)
GRAFANA_REFRESH=$(grep "GRAFANA_REFRESH_INTERVAL=" .env.docker | cut -d'=' -f2)

print_status "Reading intervals from .env.docker..."
echo "   • Prometheus Scrape: $PROMETHEUS_SCRAPE"
echo "   • Grafana Refresh: $GRAFANA_REFRESH"

# Update Prometheus configuration
print_status "Updating Prometheus configuration..."
sed -i.bak "s/scrape_interval: [0-9]*s/scrape_interval: $PROMETHEUS_SCRAPE/g" observability/prometheus.yml
sed -i.bak "s/evaluation_interval: [0-9]*s/evaluation_interval: $PROMETHEUS_SCRAPE/g" observability/prometheus.yml
print_success "Prometheus configuration updated"

# Update OpenTelemetry Collector configuration
print_status "Updating OpenTelemetry Collector configuration..."
sed -i.bak "s/scrape_interval: [0-9]*s/scrape_interval: $PROMETHEUS_SCRAPE/g" observability/otel-collector-config.yml
print_success "OpenTelemetry Collector configuration updated"

# Update Grafana dashboard
print_status "Updating Grafana dashboard configuration..."
sed -i.bak "s/\"refresh\": \"[0-9]*s\"/\"refresh\": \"$GRAFANA_REFRESH\"/g" observability/grafana/dashboards/redis-test-dashboard.json
print_success "Grafana dashboard configuration updated"

# Clean up backup files
rm -f observability/prometheus.yml.bak
rm -f observability/otel-collector-config.yml.bak
rm -f observability/grafana/dashboards/redis-test-dashboard.json.bak

echo ""
print_success "All configurations updated successfully!"
echo ""
echo "🔄 To apply changes:"
echo "   docker-compose restart otel-collector prometheus grafana"
echo ""
echo "📊 Or restart everything:"
echo "   docker-compose down && ./setup.sh"
