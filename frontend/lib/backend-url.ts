import { getPublicBackendUrl } from './public-backend-url';

/** Returns the backend origin for server-rendered requests and route handlers. */
export function getBackendUrl(): string {
  return process.env.BACKEND_API_URL || getPublicBackendUrl();
}
