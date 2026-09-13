# ------------------------------------------------------------------------------
# Shell configuration
# ------------------------------------------------------------------------------
SHELL := /bin/bash

# Run each target as a single script instead of separate commands
.ONESHELL:

# Strict options: -e (exit on any error), -u (exit on undefined variable),
# -o pipefail (exit if any pipe command fails)
.SHELLFLAGS := -eu -o pipefail -c

# Suppress printing of commands themselves, only messages
.SILENT:

# Default target when user runs make alone
.DEFAULT_GOAL := help


# ==============================================================================
# Project directories and variables
# ==============================================================================
BACKEND_DIR := backend
FRONTEND_DIR := frontend
CACHE_DIRS := .ruff_cache .mypy_cache .pytest_cache

# Ports
BACKEND_PORT := 8000
FRONTEND_PORT := 3000

# Runtime directory for PID files
RUN_DIR := .run
BACKEND_PID_FILE := $(RUN_DIR)/backend.pid
WORKER_PID_FILE := $(RUN_DIR)/worker.pid

# Docker command
DOCKER := docker


# ==============================================================================
# Phony targets (not files)
# ==============================================================================
.PHONY: \
	help \
	check-docker \
	infra-up \
	infra-down \
	db-migrate \
	back-up \
	back-down \
	worker-up \
	worker-down \
	front-up \
	front-down \
	down \
	sync \
	backend-sync \
	backend-lock \
	frontend-sync \
	backend-fix \
	backend-quality \
	frontend-lint \
	frontend-typecheck \
	frontend-quality \
	frontend-build \
	quality \
	build \
	verify \
	ci \
	clean


# ==============================================================================
# Help target - displays available commands
# ==============================================================================
help:
	echo "Available commands:"
	echo
	echo "Infrastructure:"
	echo "  make infra-up            Start Qdrant and Redis"
	echo "  make infra-down          Stop Qdrant and Redis"
	echo
	echo "Database:"
	echo "  make db-migrate          Apply Alembic migrations"
	echo
	echo "Backend:"
	echo "  make back-up             Start Qdrant + Redis + migrations + API + ARQ worker"
	echo "  make back-down           Stop API + ARQ worker"
	echo "  make worker-up           Start ARQ ingestion worker only"
	echo "  make worker-down         Stop ARQ ingestion worker"
	echo
	echo "Frontend:"
	echo "  make front-up            Start frontend"
	echo "  make front-down          Stop frontend"
	echo
	echo "Combined:"
	echo "  make down                Stop frontend, backend and infrastructure"
	echo
	echo "Dependencies:"
	echo "  make sync                Sync backend and frontend dependencies"
	echo "  make backend-sync        Sync backend dependencies"
	echo "  make backend-lock        Update backend lockfile"
	echo "  make frontend-sync       Sync frontend dependencies"
	echo
	echo "Quality:"
	echo "  make backend-fix         Run backend Ruff fix + format"
	echo "  make backend-quality     Run backend Ruff + format + mypy"
	echo "  make frontend-lint       Run frontend lint"
	echo "  make frontend-typecheck  Run frontend TypeScript checks"
	echo "  make frontend-quality    Run frontend lint + typecheck"
	echo "  make quality             Run backend + frontend quality checks"
	echo
	echo "Build:"
	echo "  make frontend-build      Build frontend"
	echo "  make build               Build production artifacts"
	echo
	echo "Verification:"
	echo "  make verify              Run available verification checks"
	echo "  make ci                  Run CI-equivalent checks"
	echo
	echo "Cleanup:"
	echo "  make clean               Remove generated local artifacts"
	echo
	echo "Tests are intentionally excluded for now."


# ==============================================================================
# Docker check - ensures Docker is installed and running
# ==============================================================================
check-docker:
	command -v $(DOCKER) >/dev/null 2>&1 || {
		echo "Error: Docker is not installed or not available in PATH."
		exit 1
	}

	$(DOCKER) info >/dev/null 2>&1 || {
		echo "Error: Docker daemon is not running."
		exit 1
	}


# ==============================================================================
# Infrastructure (Qdrant + Redis)
# ==============================================================================
infra-up: check-docker
	echo "==> Starting Qdrant and Redis..."
	$(DOCKER) compose up -d qdrant redis
	echo "==> Infrastructure is running."


infra-down: check-docker
	echo "==> Stopping Qdrant and Redis..."
	$(DOCKER) compose stop qdrant redis
	echo "==> Infrastructure stopped."


# ==============================================================================
# Database migrations
# ==============================================================================
db-migrate:
	echo "==> Applying database migrations..."
	cd "$(BACKEND_DIR)"
	uv run alembic upgrade head
	echo "==> Database is up to date."


# ==============================================================================
# Backend services (API + ARQ worker)
# ==============================================================================

# Stop API and worker using PID files + kill anything on the port
back-down:
	echo "==> Stopping backend API and ARQ worker..."

	if [ -f "$(BACKEND_PID_FILE)" ]; then
		PID=$$(cat "$(BACKEND_PID_FILE)")
		if kill -0 "$$PID" 2>/dev/null; then
			kill "$$PID" 2>/dev/null || true
		fi
	fi

	if [ -f "$(WORKER_PID_FILE)" ]; then
		PID=$$(cat "$(WORKER_PID_FILE)")
		if kill -0 "$$PID" 2>/dev/null; then
			kill "$$PID" 2>/dev/null || true
		fi
	fi

	rm -f "$(BACKEND_PID_FILE)" "$(WORKER_PID_FILE)"

	# If fuser is available, kill any process on the backend port
	if command -v fuser >/dev/null 2>&1; then
		fuser -k $(BACKEND_PORT)/tcp >/dev/null 2>&1 || true
	fi

	echo "==> Backend stopped."


# Start infrastructure + migrations + API + worker
back-up: back-down infra-up db-migrate
	mkdir -p "$(RUN_DIR)"

	echo "==> Starting backend API and ARQ worker..."
	echo

	# Cleanup function executed on Ctrl+C or process termination
	cleanup() {
		echo
		echo "==> Stopping backend processes..."

		if [ -n "$${BACKEND_PID:-}" ] && kill -0 "$$BACKEND_PID" 2>/dev/null; then
			kill "$$BACKEND_PID" 2>/dev/null || true
		fi

		if [ -n "$${WORKER_PID:-}" ] && kill -0 "$$WORKER_PID" 2>/dev/null; then
			kill "$$WORKER_PID" 2>/dev/null || true
		fi

		wait "$${BACKEND_PID:-}" 2>/dev/null || true
		wait "$${WORKER_PID:-}" 2>/dev/null || true

		rm -f "$(BACKEND_PID_FILE)" "$(WORKER_PID_FILE)"

		echo "==> Backend processes stopped."
	}

	# Bind cleanup to exit events
	trap cleanup INT TERM EXIT

	cd "$(BACKEND_DIR)"

	echo "==> Starting FastAPI..."
	uv run uvicorn app.main:app \
		--host 0.0.0.0 \
		--port $(BACKEND_PORT) &

	BACKEND_PID=$$!
	echo "$$BACKEND_PID" > "../$(BACKEND_PID_FILE)"

	echo "==> Starting ARQ worker..."
	uv run arq app.workers.ingestion.WorkerSettings &

	WORKER_PID=$$!
	echo "$$WORKER_PID" > "../$(WORKER_PID_FILE)"

	echo
	echo "==> API PID: $$BACKEND_PID"
	echo "==> Worker PID: $$WORKER_PID"
	echo
	echo "==> Backend API: http://localhost:$(BACKEND_PORT)"
	echo "==> ARQ worker is running"
	echo "==> Press Ctrl+C to stop API and worker."
	echo

	# Wait for the first process to finish
	wait -n "$$BACKEND_PID" "$$WORKER_PID"


# Start ARQ worker only
worker-up: infra-up db-migrate
	mkdir -p "$(RUN_DIR)"
	echo "==> Starting ARQ ingestion worker..."
	cd "$(BACKEND_DIR)"
	uv run arq app.workers.ingestion.WorkerSettings


# Stop ARQ worker
worker-down:
	echo "==> Stopping ARQ ingestion worker..."

	if [ -f "$(WORKER_PID_FILE)" ]; then
		PID=$$(cat "$(WORKER_PID_FILE)")

		if kill -0 "$$PID" 2>/dev/null; then
			kill "$$PID" 2>/dev/null || true
		fi

		rm -f "$(WORKER_PID_FILE)"
	fi

	echo "==> ARQ worker stopped."


# ==============================================================================
# Frontend services
# ==============================================================================
front-up:
	echo "==> Starting frontend on port $(FRONTEND_PORT)..."
	cd "$(FRONTEND_DIR)"
	pnpm dev --port $(FRONTEND_PORT)


front-down:
	echo "==> Stopping frontend..."

	if command -v fuser >/dev/null 2>&1; then
		fuser -k $(FRONTEND_PORT)/tcp >/dev/null 2>&1 || true
	fi

	echo "==> Frontend stopped."


# ==============================================================================
# Combined stop
# ==============================================================================
down: front-down back-down infra-down
	echo "==> All local services stopped."


# ==============================================================================
# Dependency management
# ==============================================================================
sync: backend-sync frontend-sync


backend-sync:
	echo "==> Syncing backend dependencies..."
	cd "$(BACKEND_DIR)"
	uv sync --locked


backend-lock:
	echo "==> Updating backend lockfile..."
	cd "$(BACKEND_DIR)"
	uv lock


frontend-sync:
	echo "==> Syncing frontend dependencies..."
	cd "$(FRONTEND_DIR)"
	pnpm install --frozen-lockfile


# ==============================================================================
# Code quality
# ==============================================================================
backend-fix:
	echo "==> Fixing backend lint and formatting..."
	cd "$(BACKEND_DIR)"
	uv run ruff check app --fix
	uv run ruff format app


backend-quality:
	echo "==> Checking backend quality..."
	cd "$(BACKEND_DIR)"
	uv run ruff check app
	uv run ruff format --check app
	uv run mypy app


frontend-lint:
	echo "==> Running frontend lint..."
	cd "$(FRONTEND_DIR)"
	pnpm lint


frontend-typecheck:
	echo "==> Running frontend typecheck..."
	cd "$(FRONTEND_DIR)"
	pnpm exec tsc --noEmit


frontend-quality: frontend-lint frontend-typecheck


quality: backend-quality frontend-quality


# ==============================================================================
# Build
# ==============================================================================
frontend-build:
	echo "==> Building frontend..."
	cd "$(FRONTEND_DIR)"
	pnpm build


build: frontend-build
	echo "==> Production build completed."


# ==============================================================================
# Verification and CI
# ==============================================================================
verify: quality
	echo "==> Verification checks completed."


ci: quality frontend-build
	echo "==> CI-equivalent checks completed."


# ==============================================================================
# Cleanup
# ==============================================================================
clean:
	echo "==> Cleaning generated local artifacts..."
	rm -rf "$(RUN_DIR)"
	rm -rf "$(FRONTEND_DIR)/.next"
	# Remove caches from root, backend, and frontend
	rm -rf $(CACHE_DIRS) \
	       $(addprefix $(BACKEND_DIR)/,$(CACHE_DIRS)) \
	       $(addprefix $(FRONTEND_DIR)/,$(CACHE_DIRS))
	echo "==> Clean complete."
