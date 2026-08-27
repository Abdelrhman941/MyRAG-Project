.PHONY: back-up front-up back-down front-down down

# ------------------------------------------------------------------------------
# Run Commands (Auto-kill existing process on port before start)
# ------------------------------------------------------------------------------
back-up: back-down
	@echo "==> Starting Qdrant (via Docker)..."
	@-docker.exe compose up -d qdrant || docker compose up -d qdrant || echo "⚠ Could not start Qdrant automatically. Please ensure Docker is running."
	@echo "==> Backend starting..."
	@cd backend && $(MAKE) run

front-up: front-down
	@echo "==> Frontend starting..."
	@cd frontend && $(MAKE) run

# ------------------------------------------------------------------------------
# Stop Commands (Kill process using port 8000 for backend & 3000 for frontend)
# ------------------------------------------------------------------------------
back-down:
	@echo "==> Stopping Backend (Port 8000)..."
	@-fuser -k 8000/tcp > /dev/null 2>&1 || true

front-down:
	@echo "==> Stopping Frontend (Port 3000)..."
	@-fuser -k 3000/tcp > /dev/null 2>&1 || true

down: back-down front-down
