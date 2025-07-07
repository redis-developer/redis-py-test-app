# Redis Test App - Development and Deployment Makefile
.PHONY: help dev-setup dev-start dev-stop dev-logs dev-test build push deploy clean

# Default target
help:
	@echo "Redis Test App - Available Commands:"
	@echo ""
	@echo "🚀 Development Commands:"
	@echo "  make dev-start     - Start complete development environment"
	@echo "  make dev-start-metrics-stack - Start metrics stack only"
	@echo "  make dev-stop      - Stop metrics stack"
	@echo "  make dev-logs      - Show metrics stack logs"
	@echo "  make dev-test      - Run Python app locally against metrics stack"
	@echo "  make dev-clean     - Clean up development environment"
	@echo ""
	@echo "🏗️  Build Commands:"
	@echo "  make build         - Build all Docker images"
	@echo "  make build-app     - Build only Python app images"
	@echo "  make build-metrics - Build only metrics stack images"
	@echo ""
	@echo "☁️  Deployment Commands:"
	@echo "  make push          - Push images to registry"
	@echo "  make deploy-dev    - Deploy to development environment"
	@echo "  make deploy-prod   - Deploy to production environment"
	@echo ""
	@echo "🧹 Cleanup Commands:"
	@echo "  make clean         - Clean up all containers and volumes"
	@echo "  make clean-images  - Remove all built images"

# Development Environment Variables
COMPOSE_FILE_DEV = docker-compose.dev.yml
COMPOSE_FILE_METRICS = docker-compose.metrics.yml
COMPOSE_FILE_FULL = docker-compose.yml

# Registry and deployment variables
REGISTRY ?= your-registry.com
IMAGE_TAG ?= latest
NAMESPACE ?= redis-test-app

#==============================================================================
# Development Commands
#==============================================================================

dev-start: dev-start-metrics-stack
	@echo "🚀 Development environment ready!"
	@echo ""
	@echo "📊 Grafana:    http://localhost:3000 (admin/admin) - Redis Test Dashboard"
	@echo "📈 Prometheus: http://localhost:9090"
	@echo "🔍 Jaeger:     http://localhost:16686"
	@echo "📡 Redis:      localhost:6379"
	@echo ""
	@echo "To run Python app locally:"
	@echo "  make dev-test"
	@echo "  ./venv/bin/python main.py run --workload-profile basic_rw --duration 60"

dev-start-metrics-stack:
	@echo "🚀 Starting metrics stack..."
	docker-compose -f $(COMPOSE_FILE_METRICS) up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 15
	@echo "✅ Metrics stack started"

dev-stop:
	@echo "🛑 Stopping metrics stack..."
	docker-compose -f $(COMPOSE_FILE_METRICS) down

dev-logs:
	docker-compose -f $(COMPOSE_FILE_METRICS) logs -f

dev-test:
	@echo "🧪 Running Python app locally (60 second test)..."
	@if [ ! -d "venv" ]; then make install-deps; fi
	./venv/bin/python main.py run --workload-profile basic_rw --duration 60 --host localhost

dev-clean: dev-stop
	@echo "🧹 Cleaning development environment..."
	docker-compose -f $(COMPOSE_FILE_METRICS) down -v
	docker system prune -f

#==============================================================================
# Build Commands  
#==============================================================================

build: build-metrics build-app

build-app:
	@echo "🏗️  Building Python app images..."
	docker-compose -f $(COMPOSE_FILE_FULL) build \
		redis-test-basic-rw \
		redis-test-high-throughput \
		redis-test-list-ops \
		redis-test-async-mixed

build-metrics:
	@echo "🏗️  Building metrics stack images..."
	docker-compose -f $(COMPOSE_FILE_METRICS) build

#==============================================================================
# Cloud Deployment Commands
#==============================================================================

push: build
	@echo "📤 Pushing images to registry..."
	docker tag redis-py-test-app-redis-test-basic-rw $(REGISTRY)/redis-test-basic-rw:$(IMAGE_TAG)
	docker tag redis-py-test-app-redis-test-high-throughput $(REGISTRY)/redis-test-high-throughput:$(IMAGE_TAG)
	docker tag redis-py-test-app-redis-test-list-ops $(REGISTRY)/redis-test-list-ops:$(IMAGE_TAG)
	docker tag redis-py-test-app-redis-test-async-mixed $(REGISTRY)/redis-test-async-mixed:$(IMAGE_TAG)
	
	docker push $(REGISTRY)/redis-test-basic-rw:$(IMAGE_TAG)
	docker push $(REGISTRY)/redis-test-high-throughput:$(IMAGE_TAG)
	docker push $(REGISTRY)/redis-test-list-ops:$(IMAGE_TAG)
	docker push $(REGISTRY)/redis-test-async-mixed:$(IMAGE_TAG)

deploy-dev:
	@echo "🚀 Deploying to development environment..."
	# This will be replaced with actual deployment commands (kubectl, helm, etc.)
	@echo "TODO: Implement development deployment"

deploy-prod:
	@echo "🚀 Deploying to production environment..."
	# This will be replaced with actual deployment commands
	@echo "TODO: Implement production deployment"

#==============================================================================
# Cleanup Commands
#==============================================================================

clean:
	@echo "🧹 Cleaning up all containers and volumes..."
	docker-compose -f $(COMPOSE_FILE_FULL) down -v
	docker-compose -f $(COMPOSE_FILE_METRICS) down -v
	docker system prune -f

clean-images:
	@echo "🧹 Removing built images..."
	docker rmi -f $$(docker images "redis-py-test-app*" -q) 2>/dev/null || true
	docker rmi -f $$(docker images "$(REGISTRY)/redis-test*" -q) 2>/dev/null || true

#==============================================================================
# Utility Commands
#==============================================================================

status:
	@echo "📊 Development Environment Status:"
	@docker-compose -f $(COMPOSE_FILE_METRICS) ps

install-deps:
	@echo "📦 Setting up Python virtual environment..."
	python3 -m venv venvacti
	@echo "📦 Installing Python dependencies..."
	./venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed in virtual environment"
	@echo "💡 To activate: source venv/bin/activate"

lint:
	@echo "🔍 Running code linting..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

test-local:
	@echo "🧪 Running local tests..."
	@if [ ! -d "venv" ]; then make install-deps; fi
	./venv/bin/python -m pytest tests/ -v

# Development shortcuts
dev: dev-start
stop: dev-stop
logs: dev-logs
test: dev-test
