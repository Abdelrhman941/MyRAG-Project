# RAG Assistant Frontend

The frontend is a Next.js 16 App Router application for the RAG Assistant.
It renders session-scoped chat and document management, consumes streamed chat
responses, and displays backend readiness before starting a session.

## Development

Use pnpm from this directory:

```bash
pnpm install
pnpm dev
```

The app runs at `http://localhost:3000` by default.

## Configuration

| Variable | Used by | Purpose |
| --- | --- | --- |
| `BACKEND_API_URL` | Server Components, Server Actions, upload route | Private server-to-server backend origin. |
| `NEXT_PUBLIC_API_URL` | Browser SSE client | Public backend origin used for streamed answers. Also acts as a local fallback for server calls. |
| `NEXT_PUBLIC_APP_URL` | Metadata | Public frontend origin used for canonical metadata. |

For local development, the backend defaults to `http://127.0.0.1:8000` when
neither backend URL is configured.

## Project organization

- `app/` contains routes, layouts, loading, error, route-handler boundaries,
  and route-owned components in private `_components/` folders.
- `features/chat/` contains the stream hook and chat-specific UI.
- `features/documents/` contains the Zustand document cache, upload/delete hook,
  and document manager.
- `components/layout/` and `components/providers/` hold app-shell-only UI and
  root providers.
- `components/ui/` contains reusable Base UI/shadcn-style primitives only.
- `lib/` contains configuration, typed API access, shared types, and utilities.

## Verification

```bash
pnpm lint
pnpm exec tsc --noEmit
pnpm build
```
