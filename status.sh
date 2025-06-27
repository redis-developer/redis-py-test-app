#!/bin/bash

# Redis Test App Status Script
# Shows the current status of all services

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

print_status() {
    if [ "$2" = "UP" ]; then
        echo -e "${GREEN}✅ $1${NC}"
    elif [ "$2" = "DOWN" ]; then
        echo -e "${RED}❌ $1${NC}"
    else
        echo -e "${YELLOW}⚠️  $1${NC}"
    fi
}

print_header "Redis Test App Status"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_status "Docker is not running" "DOWN"
    exit 1
fi

# Check container status
echo ""
echo "📦 Container Status:"
docker-compose ps

echo ""
echo "🔍 Service Health:"

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_status "Redis Database" "UP"
else
    print_status "Redis Database" "DOWN"
fi

# Check Redis Test App
if docker-compose ps redis-test-app | grep -q "Up"; then
    print_status "Redis Test App" "UP"
else
    print_status "Redis Test App" "DOWN"
fi

# Check Prometheus
if curl -s http://localhost:9090/-/ready > /dev/null 2>&1; then
    print_status "Prometheus" "UP"
else
    print_status "Prometheus" "DOWN"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
    print_status "Grafana" "UP"
else
    print_status "Grafana" "DOWN"
fi

# Check Jaeger
if curl -s http://localhost:16686/api/services > /dev/null 2>&1; then
    print_status "Jaeger" "UP"
else
    print_status "Jaeger" "DOWN"
fi

# Check OpenTelemetry Collector
if docker-compose ps otel-collector | grep -q "Up"; then
    print_status "OpenTelemetry Collector" "UP"
else
    print_status "OpenTelemetry Collector" "DOWN"
fi

# Check metrics endpoint
if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    print_status "Metrics Endpoint" "UP"
else
    print_status "Metrics Endpoint" "DOWN"
fi

echo ""
echo "🌐 Access URLs:"
echo "   • Grafana:    http://localhost:3000 (admin/admin)"
echo "   • Prometheus: http://localhost:9090"
echo "   • Jaeger:     http://localhost:16686"
echo "   • Metrics:    http://localhost:8000/metrics"

echo ""
echo "📊 Quick Stats:"

# Get some basic metrics if available
if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    # Try to get operation count
    TOTAL_OPS=$(curl -s http://localhost:8000/metrics | grep "redis_operations_total" | head -1 | awk '{print $2}' 2>/dev/null || echo "N/A")
    echo "   • Total Operations: $TOTAL_OPS"
    
    # Try to get active connections
    ACTIVE_CONN=$(curl -s http://localhost:8000/metrics | grep "redis_active_connections" | awk '{print $2}' 2>/dev/null || echo "N/A")
    echo "   • Active Connections: $ACTIVE_CONN"
else
    echo "   • Metrics not available"
fi

echo ""
echo "📝 Useful Commands:"
echo "   • View logs:     docker-compose logs -f"
echo "   • Restart app:   docker-compose restart redis-test-app"
echo "   • Stop all:      docker-compose down"
echo "   • Full cleanup:  ./cleanup.sh"
