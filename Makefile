SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.RECIPEPREFIX := >

.DEFAULT_GOAL := help

# ------------------------------------------------------------------------------
# Project Configuration
# ------------------------------------------------------------------------------

BACKEND_DIR := backend
FRONTEND_DIR := frontend

BACKEND_PORT := 8000
FRONTEND_PORT := 3000

# Prefer the native Docker CLI, with docker.exe as a WSL/Docker Desktop fallback.
DOCKER := $(shell \
	if command -v docker >/dev/null 2>&1; then \
		echo docker; \
	elif command -v docker.exe >/dev/null 2>&1; then \
		echo docker.exe; \
	else \
		echo docker; \
	fi \
)

# ------------------------------------------------------------------------------
# Phony Targets
# ------------------------------------------------------------------------------

.PHONY: \
	help \
	check-docker \
	infra-up \
	infra-down \
	back-up \
	back-down \
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

# ------------------------------------------------------------------------------
# Help
# ------------------------------------------------------------------------------

help:
> @printf '%s\n' \
> 	'Project commands:' \
> 	'' \
> 	'  Infrastructure' \
> 	'    make infra-up          Start Qdrant and Redis' \
> 	'    make infra-down        Stop Qdrant and Redis' \
> 	'' \
> 	'  Development' \
> 	'    make back-up           Start infrastructure + backend' \
> 	'    make back-down         Stop backend on port $(BACKEND_PORT)' \
> 	'    make front-up          Start frontend' \
> 	'    make front-down        Stop frontend on port $(FRONTEND_PORT)' \
> 	'    make down              Stop backend, frontend, and infrastructure' \
> 	'' \
> 	'  Dependencies' \
> 	'    make sync              Sync backend + frontend dependencies' \
> 	'    make backend-sync      Sync Python dependencies from uv.lock' \
> 	'    make backend-lock      Resolve/update uv.lock explicitly' \
> 	'    make frontend-sync     Install frontend dependencies from lockfile' \
> 	'' \
> 	'  Quality' \
> 	'    make backend-fix       Auto-fix Ruff issues and format backend' \
> 	'    make backend-quality   Ruff + format check + MyPy' \
> 	'    make frontend-lint     Run ESLint' \
> 	'    make frontend-typecheck Run TypeScript check' \
> 	'    make frontend-quality  ESLint + TypeScript check' \
> 	'    make quality           Backend + frontend quality checks' \
> 	'    make frontend-build    Production frontend build' \
> 	'    make build             Production frontend build' \
> 	'    make verify            Quality checks + frontend build' \
> 	'    make ci                Alias for verify' \
> 	'' \
> 	'  Cleanup' \
> 	'    make clean             Safe project-wide cache/build cleanup' \
> 	'' \
> 	'  Tests are intentionally excluded for now.'

# ------------------------------------------------------------------------------
# Infrastructure
# ------------------------------------------------------------------------------

check-docker:
> if ! command -v "$(DOCKER)" >/dev/null 2>&1; then
> 	echo "Error: Docker CLI was not found."
> 	echo "Make sure Docker/Docker Desktop is installed and available in PATH."
> 	exit 1
> fi

infra-up: check-docker
> echo "==> Starting Qdrant and Redis..."
> $(DOCKER) compose up -d qdrant redis
> echo "==> Infrastructure is running."

infra-down: check-docker
> echo "==> Stopping Qdrant and Redis..."
> $(DOCKER) compose stop qdrant redis
> echo "==> Infrastructure stopped."

# ------------------------------------------------------------------------------
# Backend Development
# ------------------------------------------------------------------------------

back-up: back-down infra-up
> echo "==> Starting backend on port $(BACKEND_PORT)..."
> cd $(BACKEND_DIR)
> uv run uvicorn app.main:app --host 0.0.0.0 --port $(BACKEND_PORT)

back-down:
> echo "==> Stopping backend on port $(BACKEND_PORT)..."
> if command -v fuser >/dev/null 2>&1; then
> 	fuser -k $(BACKEND_PORT)/tcp >/dev/null 2>&1 || true
> else
> 	echo "Warning: 'fuser' is not installed; backend process was not stopped automatically."
> fi

# ------------------------------------------------------------------------------
# Frontend Development
# ------------------------------------------------------------------------------

front-up: front-down
> echo "==> Starting frontend..."
> cd $(FRONTEND_DIR)
> pnpm dev

front-down:
> echo "==> Stopping frontend on port $(FRONTEND_PORT)..."
> if command -v fuser >/dev/null 2>&1; then
> 	fuser -k $(FRONTEND_PORT)/tcp >/dev/null 2>&1 || true
> else
> 	echo "Warning: 'fuser' is not installed; frontend process was not stopped automatically."
> fi

# ------------------------------------------------------------------------------
# Stop Everything
# ------------------------------------------------------------------------------

down: back-down front-down infra-down
> echo "==> Application and infrastructure stopped."

# ------------------------------------------------------------------------------
# Dependencies
# ------------------------------------------------------------------------------

backend-sync:
> echo "==> Syncing backend dependencies..."
> cd $(BACKEND_DIR)
> uv sync --locked

backend-lock:
> echo "==> Resolving/updating uv.lock..."
> cd $(BACKEND_DIR)
> uv lock

frontend-sync:
> echo "==> Installing frontend dependencies..."
> cd $(FRONTEND_DIR)
> pnpm install --frozen-lockfile

sync: backend-sync frontend-sync
> echo "==> All project dependencies are synchronized."

# ------------------------------------------------------------------------------
# Backend Quality
# ------------------------------------------------------------------------------

backend-fix:
> echo "==> Fixing backend with Ruff..."
> cd $(BACKEND_DIR)
> uv run ruff check . --fix
> uv run ruff format .
> echo "==> Backend auto-fix completed."

backend-quality:
> echo "==> Backend: Ruff"
> cd $(BACKEND_DIR)
> uv run ruff check .

> echo "==> Backend: Ruff format check"
> uv run ruff format --check .

> echo "==> Backend: MyPy"
> uv run mypy app/

# ------------------------------------------------------------------------------
# Frontend Quality
# ------------------------------------------------------------------------------

frontend-lint:
> echo "==> Frontend: ESLint"
> cd $(FRONTEND_DIR)
> pnpm lint

frontend-typecheck:
> echo "==> Frontend: TypeScript"
> cd $(FRONTEND_DIR)
> pnpm exec tsc --noEmit

frontend-quality: frontend-lint frontend-typecheck
> echo "==> Frontend quality checks passed."

# ------------------------------------------------------------------------------
# Combined Quality
# ------------------------------------------------------------------------------

quality: backend-quality frontend-quality
> echo "==> All quality checks passed."

# ------------------------------------------------------------------------------
# Build / Verification
# ------------------------------------------------------------------------------

frontend-build:
> echo "==> Frontend: production build"
> cd $(FRONTEND_DIR)
> pnpm build

build: frontend-build

verify: quality build
> echo "==> Verification passed."

ci: verify

# ------------------------------------------------------------------------------
# Safe Cleanup
#
# Removes generated/cache/build artifacts across the entire repository.
#
# Intentionally preserves:
#   - .git/
#   - node_modules/
#   - .venv/
#   - backend/data/
#   - SQLite databases
#   - uploaded documents
#   - source files
# ------------------------------------------------------------------------------

clean:
> echo "==> Cleaning project-wide generated files and caches..."

> find . \
> 	-path './.git' -prune -o \
> 	-path '*/node_modules' -prune -o \
> 	-path '*/.venv' -prune -o \
> 	-type d \
> 	\( \
> 		-name "__pycache__" \
> 		-o -name ".pytest_cache" \
> 		-o -name ".ruff_cache" \
> 		-o -name ".mypy_cache" \
> 		-o -name ".next" \
> 		-o -name "out" \
> 		-o -name "coverage" \
> 	\) \
> 	-print -exec rm -rf {} +

> find . \
> 	-path './.git' -prune -o \
> 	-path '*/node_modules' -prune -o \
> 	-path '*/.venv' -prune -o \
> 	-type f \
> 	\( \
> 		-name "*.pyc" \
> 		-o -name "*.pyo" \
> 		-o -name "*.coverage" \
> 		-o -name "*.tsbuildinfo" \
> 	\) \
> 	-print -exec rm -f {} +

> echo "==> Project cleanup completed."
