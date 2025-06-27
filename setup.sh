#!/bin/bash

# Redis Test App Setup Script
# Builds Docker image and runs the complete testing environment

set -e

echo "🚀 Redis Test App Setup"
echo "======================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check if Docker is installed and running
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_success "Prerequisites check passed"

# Create necessary directories
print_status "Creating directories..."
mkdir -p logs
mkdir -p data
print_success "Directories created"

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down --remove-orphans > /dev/null 2>&1 || true

# Build the application
print_status "Building Redis test application..."
docker-compose build --no-cache

if [ $? -eq 0 ]; then
    print_success "Application built successfully"
else
    print_error "Failed to build application"
    exit 1
fi

# Start the services
print_status "Starting services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 15

# Check service health
print_status "Checking service health..."

# Check Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is ready"
else
    print_warning "Redis is not responding yet"
fi

# Check if the test app is running
if docker-compose ps redis-test-app | grep -q "Up"; then
    print_success "Redis test app is running"
else
    print_warning "Redis test app may not be running properly"
fi

# Check if metrics endpoint is accessible
sleep 5
if curl -s http://localhost:8000/metrics > /dev/null 2>&1; then
    print_success "Metrics endpoint is accessible"
else
    print_warning "Metrics endpoint is not ready yet"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📊 Services running:"
echo "   • Redis Database:  localhost:6379"
echo "   • Test Application: Running workload"
echo "   • Metrics:         http://localhost:8000/metrics"
echo "   • Prometheus:      http://localhost:9090"
echo "   • Grafana:         http://localhost:3000 (admin/admin)"
echo "   • Jaeger:          http://localhost:16686"
echo ""
echo "📝 Useful commands:"
echo "   • View logs:       docker-compose logs -f"
echo "   • View app logs:   docker-compose logs -f redis-test-app"
echo "   • Stop services:   docker-compose down"
echo "   • Restart app:     docker-compose restart redis-test-app"
echo ""
echo "🔧 Customize workload:"
echo "   • View config:     ./show-config.sh"
echo "   • Edit config:     nano .env.docker"
echo "   • Restart app:     docker-compose restart redis-test-app"
echo ""

# Show current status
print_status "Current container status:"
docker-compose ps

echo ""
print_success "Redis Test App is ready for testing!"
