#!/bin/bash

# Redis Test App Observability Stack Startup Script

set -e

echo "🚀 Starting Redis Test App Observability Stack..."

# Create logs directory
mkdir -p logs

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Build and start the stack
echo "📦 Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Redis
if docker-compose exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is ready"
else
    echo "❌ Redis is not responding"
fi

# Check if Prometheus is accessible
if curl -s http://localhost:9090/-/ready > /dev/null; then
    echo "✅ Prometheus is ready"
else
    echo "❌ Prometheus is not ready"
fi

# Check if Grafana is accessible
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✅ Grafana is ready"
else
    echo "❌ Grafana is not ready"
fi

# Check if Jaeger is accessible
if curl -s http://localhost:16686/api/services > /dev/null; then
    echo "✅ Jaeger is ready"
else
    echo "❌ Jaeger is not ready"
fi

echo ""
echo "🎉 Observability Stack is running!"
echo ""
echo "📊 Access your dashboards:"
echo "   • Grafana:    http://localhost:3000 (admin/admin)"
echo "   • Prometheus: http://localhost:9090"
echo "   • Jaeger:     http://localhost:16686"
echo "   • App Metrics: http://localhost:8000/metrics"
echo ""
echo "📝 View logs:"
echo "   docker-compose logs -f redis-test-app"
echo ""
echo "🛑 Stop the stack:"
echo "   docker-compose down"
echo ""
echo "🔄 Restart the test app with different workload:"
echo "   docker-compose restart redis-test-app"
