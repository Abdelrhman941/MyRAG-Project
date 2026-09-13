const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';

/** Returns the backend origin that is safe to expose to browser-side SSE requests. */
export function getPublicBackendUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_BACKEND_URL;
}
