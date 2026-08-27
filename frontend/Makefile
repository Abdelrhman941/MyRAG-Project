.PONY: install run build

# -----------------------------------------------
install:
	pnpm install
# -----------------------------------------------
run:
  pnpm format
	pnpm dev
# -----------------------------------------------
build:
  pnpm format
	pnpm tsc --noEmit
	pnpm eslint .
	pnpm build
