#!/bin/bash

# Show current configuration for Redis Test App

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

print_config() {
    echo -e "${GREEN}$1:${NC} $2"
}

print_header "Redis Test App Configuration"

echo ""
echo "📁 Configuration Sources:"
echo "   • .env.docker (default values)"
echo "   • docker-compose.yml (Docker overrides)"
echo "   • Environment variables (runtime overrides)"

echo ""
print_header "Current Configuration from .env.docker"

if [ -f ".env.docker" ]; then
    echo ""
    echo "🔧 Redis Connection:"
    grep "REDIS_" .env.docker | while read line; do
        key=$(echo $line | cut -d'=' -f1)
        value=$(echo $line | cut -d'=' -f2)
        print_config "$key" "$value"
    done

    echo ""
    echo "🎯 Test Configuration:"
    grep "TEST_" .env.docker | while read line; do
        key=$(echo $line | cut -d'=' -f1)
        value=$(echo $line | cut -d'=' -f2)
        print_config "$key" "$value"
    done

    echo ""
    echo "📊 Metrics Configuration:"
    grep "METRICS_\|PROMETHEUS_\|GRAFANA_" .env.docker | while read line; do
        key=$(echo $line | cut -d'=' -f1)
        value=$(echo $line | cut -d'=' -f2)
        print_config "$key" "$value"
    done

    echo ""
    echo "🔍 OpenTelemetry Configuration:"
    grep "OTEL_" .env.docker | while read line; do
        key=$(echo $line | cut -d'=' -f1)
        value=$(echo $line | cut -d'=' -f2)
        print_config "$key" "$value"
    done

    echo ""
    echo "📝 Logging Configuration:"
    grep "LOG_" .env.docker | while read line; do
        key=$(echo $line | cut -d'=' -f1)
        value=$(echo $line | cut -d'=' -f2)
        print_config "$key" "$value"
    done
else
    echo "❌ .env.docker file not found"
fi

echo ""
print_header "Configuration Notes"
echo ""
echo "✅ All configuration comes from .env.docker"
echo "🐳 No Docker-specific overrides needed"
echo "🔗 Container names resolve automatically in Docker network"
echo ""
echo "⏱️  Synchronized Intervals:"
echo "   • METRICS_INTERVAL: App console reporting (seconds)"
echo "   • PROMETHEUS_SCRAPE_INTERVAL: Prometheus scraping (e.g., 5s)"
echo "   • OTEL_EXPORT_INTERVAL: OpenTelemetry export (milliseconds)"
echo "   • GRAFANA_REFRESH_INTERVAL: Dashboard refresh (e.g., 5s)"

echo ""
print_header "How to Customize"
echo ""
echo "1. 📝 Edit .env.docker for default values"
echo "2. 🔄 Restart: docker-compose restart redis-test-app"
echo "3. 🌍 Override with environment variables:"
echo "   TEST_DURATION=7200 docker-compose up redis-test-app"
echo ""
echo "🎯 Available Workload Profiles:"
echo "   • basic_rw - Basic read/write operations"
echo "   • high_throughput - High-performance testing"
echo "   • list_operations - List-based operations"
echo "   • pubsub_test - Pub/Sub testing"
echo "   • transaction_test - Transaction testing"
