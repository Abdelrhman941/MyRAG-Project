import { AppConfig } from "./config";

export async function fetchAppConfig(): Promise<AppConfig> {
  try {
    const res = await fetch("http://localhost:8000/api/v1/system/config", {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
