# Redis Python Test App - Makefile
.PHONY: help install-python310 install-deps-venv test test-connection build clean

# Default target
help:
	@echo "Redis Python Test App - Available Commands:"
	@echo ""
	@echo "🚀 Development Commands:"
	@echo "  make install-python310  - Install Python 3.10 on Ubuntu/Debian systems"
	@echo "  make install-deps-venv - Create virtual environment and install dependencies"
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
	@echo "  • Python 3.10+ installed (required for redis>=7.1.0)"
	@echo "  • Run 'make install-python310' to install Python 3.10 on Ubuntu/Debian"
	@echo "  • Run 'make install-deps-venv' to set up virtual environment"
	@echo "  • Redis Metrics Stack must be running (separate repository)"
	@echo "  • Redis accessible at localhost:6379"
	@echo "  • OpenTelemetry Collector at localhost:4317"

# Application variables
APP_NAME ?= redis-py-test-app
IMAGE_TAG ?= latest

#==============================================================================
# Development Commands
#==============================================================================

install-python310: ## Install Python 3.10 on Ubuntu/Debian systems
	@echo "🐍 Installing Python 3.10..."
	@if command -v python3.10 >/dev/null 2>&1; then \
		echo "✓ Python 3.10 already installed"; \
		python3.10 --version; \
	else \
		echo "📦 Installing Python 3.10 and required packages..."; \
		sudo apt update; \
		sudo apt install -y python3.10 python3.10-venv python3.10-dev python3.10-distutils; \
		echo "✅ Python 3.10 installation complete"; \
		python3.10 --version; \
	fi

install-deps-venv: ## Create virtual environment and install dependencies
	@echo "📦 Setting up Python virtual environment..."
	@if [ ! -d "venv" ]; then \
		echo "🔧 Creating virtual environment with Python 3.10..."; \
		if command -v python3.10 >/dev/null 2>&1; then \
			python3.10 -m venv venv; \
		else \
			echo "❌ Python 3.10 not found. Run 'make install-python310' first."; \
			exit 1; \
		fi; \
	else \
		echo "✓ Virtual environment already exists"; \
	fi
	@echo "📦 Ensuring pip is available in virtual environment..."
	@if [ ! -f "./venv/bin/pip" ]; then \
		echo "🔧 Pip not found, bootstrapping pip in virtual environment..."; \
		./venv/bin/python -m ensurepip --upgrade || { \
			echo "❌ Failed to bootstrap pip. Recreating virtual environment..."; \
			rm -rf venv; \
			python3 -m venv venv --system-site-packages; \
			./venv/bin/python -m ensurepip --upgrade; \
		}; \
	fi
	@echo "📦 Installing dependencies in virtual environment..."
	@echo "🔧 Clearing pip cache (if supported)..."
	@./venv/bin/python -m pip cache purge 2>/dev/null || echo "ℹ️  Cache purge not supported, continuing..."
	./venv/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple/ --upgrade pip
	./venv/bin/python -m pip install --no-cache-dir --index-url https://pypi.org/simple/ -r requirements.txt
	@echo "✅ Virtual environment setup complete"
	@echo ""
	@echo "💡 To activate the virtual environment, run:"
	@echo "   source venv/bin/activate"

test-connection: ## Test Redis connection
	@echo "🔍 Testing Redis connection..."
	@if [ -d "venv" ]; then \
		./venv/bin/python main.py test-connection; \
	else \
		echo "❌ Virtual environment not found. Run 'make install-deps-venv' first."; \
		exit 1; \
	fi
	@echo "✅ Connection test complete"

test: ## Run basic test (60 seconds)
	@echo "🧪 Running basic test..."
	@if [ -d "venv" ]; then \
		./venv/bin/python main.py run --workload-profile basic_rw --duration 60; \
	else \
		echo "❌ Virtual environment not found. Run 'make install-deps-venv' first."; \
		exit 1; \
	fi
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
