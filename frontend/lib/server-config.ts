import { getBackendUrl } from './backend-url';
import type { AppConfig } from './config';

export async function fetchAppConfig(): Promise<AppConfig | null> {
  try {
    const res = await fetch(`${getBackendUrl()}/api/v1/system/config`, {
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      console.warn('Failed to fetch app config:', res.status);
      return null;
    }

    return res.json();
  } catch (error) {
    console.error('Error fetching app config:', error);
    return null;
  }
}
