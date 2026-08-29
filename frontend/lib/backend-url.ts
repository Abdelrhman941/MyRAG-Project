/**
 * Returns the backend origin for server-rendered requests and route handlers.
 * `BACKEND_API_URL` keeps the server-to-server address private; the public
 * variable remains available for the browser SSE client.
 */
export function getBackendUrl(): string {
  return process.env.BACKEND_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
}
