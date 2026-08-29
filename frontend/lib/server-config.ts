import { getBackendUrl } from './backend-url';
import type { AppConfig } from './config';

export async function fetchAppConfig(): Promise<AppConfig> {
  try {
    const res = await fetch(`${getBackendUrl()}/api/v1/system/config`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
