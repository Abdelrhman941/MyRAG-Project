.PHONY: install run build

# -----------------------------------------------
install:
	pnpm install
# -----------------------------------------------
run:
	pnpm dev
# -----------------------------------------------
build:
	pnpm tsc --noEmit
	pnpm eslint .
	pnpm build
