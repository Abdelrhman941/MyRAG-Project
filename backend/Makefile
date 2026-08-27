SHELL := /bin/bash
.ONESHELL:
.PHONY: sync run clean quality

# -----------------------------------------------
sync:
	uv lock && uv sync
# -----------------------------------------------
run:
	uv run uvicorn app.main:app --host 0.0.0.0
# -----------------------------------------------
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage
# -----------------------------------------------
quality:
	@echo "==> Ruff format"
	@uv run ruff format .
	@echo "==> Ruff lint"
	@if ! uv run ruff check .; then \
		echo "==> Applying safe autofix..."; \
		uv run ruff check --fix . || true; \
		uv run ruff format .; \
		echo "==> Re-checking..."; \
		if ! uv run ruff check .; then \
			echo ""; \
			echo "Some issues need --unsafe-fixes or a manual edit (not auto-fixed)."; \
			read -p "Continue anyway? [y/N] " ans; \
			case "$$ans" in \
				y|Y) echo "==> Continuing...";; \
				*) echo "==> Aborted."; exit 1;; \
			esac; \
		else \
			echo "==> All lint issues resolved."; \
		fi; \
	fi
	@echo "==> Mypy"
	@uv run mypy app/ || { \
		echo ""; \
		echo "mypy found type issues above — need a manual code fix."; \
		read -p "Continue to tests anyway? [y/N] " ans; \
		case "$$ans" in \
			y|Y) echo "==> Continuing despite type errors...";; \
			*) echo "==> Aborted. Fix the errors above, then re-run 'make quality'."; exit 1;; \
		esac; \
	}
	@echo "==> Tests"
	@uv run pytest -v
# -----------------------------------------------
