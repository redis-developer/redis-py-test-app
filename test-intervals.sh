#!/bin/bash

# Test script to verify all intervals are properly configured and synchronized

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "$(printf '=%.0s' {1..50})"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_header "Testing Interval Configuration Synchronization"

# Check if .env.docker exists
if [ ! -f ".env.docker" ]; then
    echo "❌ .env.docker file not found"
    exit 1
fi

# Extract intervals from .env.docker
METRICS_INTERVAL=$(grep "METRICS_INTERVAL=" .env.docker | cut -d'=' -f2)
PROMETHEUS_SCRAPE=$(grep "PROMETHEUS_SCRAPE_INTERVAL=" .env.docker | cut -d'=' -f2)
OTEL_EXPORT=$(grep "OTEL_EXPORT_INTERVAL=" .env.docker | cut -d'=' -f2)
GRAFANA_REFRESH=$(grep "GRAFANA_REFRESH_INTERVAL=" .env.docker | cut -d'=' -f2)

echo ""
echo "📊 Current Interval Configuration:"
echo "   • App Metrics Interval:      ${METRICS_INTERVAL}s"
echo "   • Prometheus Scrape:         ${PROMETHEUS_SCRAPE}"
echo "   • OpenTelemetry Export:      ${OTEL_EXPORT}ms"
echo "   • Grafana Refresh:           ${GRAFANA_REFRESH}"

echo ""
print_header "Synchronization Check"

# Convert all to seconds for comparison
METRICS_SEC=$METRICS_INTERVAL
PROMETHEUS_SEC=$(echo $PROMETHEUS_SCRAPE | sed 's/s$//')
OTEL_SEC=$((OTEL_EXPORT / 1000))
GRAFANA_SEC=$(echo $GRAFANA_REFRESH | sed 's/s$//')

echo ""
echo "🔄 Converted to seconds for comparison:"
echo "   • App Metrics:     ${METRICS_SEC}s"
echo "   • Prometheus:      ${PROMETHEUS_SEC}s"
echo "   • OpenTelemetry:   ${OTEL_SEC}s"
echo "   • Grafana:         ${GRAFANA_SEC}s"

echo ""
# Check if all intervals are synchronized
if [ "$METRICS_SEC" = "$PROMETHEUS_SEC" ] && [ "$PROMETHEUS_SEC" = "$OTEL_SEC" ] && [ "$OTEL_SEC" = "$GRAFANA_SEC" ]; then
    print_success "All intervals are synchronized at ${METRICS_SEC} seconds"
else
    print_warning "Intervals are not synchronized - this may cause inconsistent data collection"
fi

echo ""
print_header "Recommendations"

if [ "$METRICS_SEC" -lt 5 ]; then
    print_warning "Intervals less than 5 seconds may cause high overhead"
elif [ "$METRICS_SEC" -gt 30 ]; then
    print_warning "Intervals greater than 30 seconds may miss short-term issues"
else
    print_success "Interval timing looks good for most use cases"
fi

echo ""
echo "💡 To change intervals:"
echo "   1. Edit .env.docker"
echo "   2. Keep all intervals synchronized"
echo "   3. Restart: docker-compose restart"
echo ""
echo "📖 Format examples:"
echo "   • METRICS_INTERVAL=10 (seconds)"
echo "   • PROMETHEUS_SCRAPE_INTERVAL=10s"
echo "   • OTEL_EXPORT_INTERVAL=10000 (milliseconds)"
echo "   • GRAFANA_REFRESH_INTERVAL=10s"
