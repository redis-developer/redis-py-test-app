#!/bin/bash
# Development Environment Setup Script

set -e

echo "🚀 Setting up Redis Test App Development Environment"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Check if Python 3.11+ is available
if ! python3 --version | grep -E "3\.(11|12)" > /dev/null 2>&1; then
    echo "❌ Python 3.11+ is required. Please install it and try again."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create local environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating local environment configuration..."
    cp .env.local .env
    echo "✅ Created .env file from .env.local template"
else
    echo "ℹ️  .env file already exists, skipping creation"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Python dependencies installed"
else
    echo "❌ requirements.txt not found"
    exit 1
fi

# Start metrics stack
echo "🚀 Starting metrics stack..."
make dev-start-metrics-stack

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 15

# Test Redis connection
echo "🧪 Testing Redis connection..."
if python main.py test-connection --host localhost --port 6379; then
    echo "✅ Redis connection successful"
else
    echo "❌ Redis connection failed"
    exit 1
fi

# Run a quick test
echo "🧪 Running quick integration test..."
if python main.py run --workload-profile basic_rw --duration 10 --host localhost --quiet; then
    echo "✅ Integration test successful"
else
    echo "❌ Integration test failed"
    exit 1
fi

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "📊 Access your services:"
echo "  Grafana:    http://localhost:3000 (admin/admin)"
echo "  Prometheus: http://localhost:9090"
echo "  Jaeger:     http://localhost:16686"
echo "  Redis:      localhost:6379"
echo ""
echo "🧪 Run tests locally:"
echo "  python main.py run --workload-profile basic_rw --duration 60"
echo "  python main.py run --workload-profile high_throughput --duration 30"
echo ""
echo "📚 Available make commands:"
echo "  make help      - Show all available commands"
echo "  make dev-test  - Run a quick test"
echo "  make dev-logs  - Show metrics stack logs"
echo "  make dev-stop  - Stop metrics stack"
echo ""
