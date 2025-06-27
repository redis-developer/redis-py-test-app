#!/bin/bash

# Redis Test App Cleanup Script
# Stops all services and optionally removes data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

echo "🧹 Redis Test App Cleanup"
echo "========================="

# Parse command line arguments
REMOVE_DATA=false
REMOVE_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --remove-data)
            REMOVE_DATA=true
            shift
            ;;
        --remove-images)
            REMOVE_IMAGES=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --remove-data    Remove persistent data volumes"
            echo "  --remove-images  Remove Docker images"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            print_warning "Unknown option: $1"
            shift
            ;;
    esac
done

# Stop and remove containers
print_status "Stopping and removing containers..."
docker-compose down --remove-orphans

if [ $? -eq 0 ]; then
    print_success "Containers stopped and removed"
else
    print_warning "Some containers may not have stopped cleanly"
fi

# Remove data volumes if requested
if [ "$REMOVE_DATA" = true ]; then
    print_status "Removing data volumes..."
    docker-compose down -v
    print_success "Data volumes removed"
fi

# Remove Docker images if requested
if [ "$REMOVE_IMAGES" = true ]; then
    print_status "Removing Docker images..."
    
    # Remove the built image
    docker rmi redis-py-test-app_redis-test-app 2>/dev/null || true
    
    # Remove unused images
    docker image prune -f
    
    print_success "Docker images cleaned up"
fi

# Clean up local files
print_status "Cleaning up local files..."
rm -rf logs/* 2>/dev/null || true
print_success "Local cleanup complete"

echo ""
print_success "Cleanup completed!"
echo ""
echo "To restart the application, run: ./setup.sh"
