"use client";

import { createContext, useContext, ReactNode } from "react";

export type AppConfig = {
  max_file_size_mb: number;
  max_files_per_request: number;
  accepted_extensions: string[];
  app_name: string;
  app_version: string;
} | null;

const ConfigContext = createContext<AppConfig>(null);

export function ConfigProvider({
  config,
  children,
}: {
  config: AppConfig;
  children: ReactNode;
}) {
  return (
    <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>
  );
}

export function useConfig() {
  return useContext(ConfigContext);
}
