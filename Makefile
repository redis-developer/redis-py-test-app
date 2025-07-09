# Redis Python Test App - Makefile
.PHONY: help install-deps test test-connection build clean

# Default target
help:
	@echo "Redis Python Test App - Available Commands:"
	@echo ""
	@echo "🚀 Development Commands:"
	@echo "  make install-deps  - Install Python dependencies"
	@echo "  make test          - Run basic test (60 seconds)"
	@echo "  make test-connection - Test Redis connection"
	@echo ""
	@echo "🏗️  Build Commands:"
	@echo "  make build         - Build Docker image"
	@echo ""
	@echo "🧹 Cleanup Commands:"
	@echo "  make clean         - Clean up Python cache and virtual environment"
	@echo ""
	@echo "📋 Prerequisites:"
	@echo "  • Redis Metrics Stack must be running (separate repository)"
	@echo "  • Redis accessible at localhost:6379"
	@echo "  • OpenTelemetry Collector at localhost:4317"

# Application variables
APP_NAME ?= redis-py-test-app
IMAGE_TAG ?= latest

#==============================================================================
# Development Commands
#==============================================================================

install-deps: ## Install Python dependencies
	@echo "📦 Installing Python dependencies..."
	python3 -m pip install --upgrade pip
	python3 -m pip install -r requirements.txt
	@echo "✅ Dependencies installed"

test-connection: ## Test Redis connection
	@echo "🔍 Testing Redis connection..."
	python3 main.py test-connection
	@echo "✅ Connection test complete"

test: ## Run basic test (60 seconds)
	@echo "🧪 Running basic test..."
	python3 main.py run --workload-profile basic_rw --duration 60
	@echo "✅ Test complete"
#==============================================================================
# Build Commands
#==============================================================================

build: ## Build Docker image
	@echo "🏗️  Building Python app image..."
	docker build -t $(APP_NAME):$(IMAGE_TAG) .
	@echo "✅ Build complete"

#==============================================================================
# Cleanup Commands
#==============================================================================

clean: ## Clean up Python cache and virtual environment
	@echo "🧹 Cleaning up Python environment..."
	rm -rf __pycache__/
	rm -rf *.pyc
	rm -rf .pytest_cache/
	rm -rf venv/
	@echo "✅ Cleanup complete"
