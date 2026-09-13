'use client';

import { createContext, ReactNode, useContext } from 'react';

export type AppConfig = {
  max_file_size_mb: number;
  max_files_per_request: number;
  accepted_extensions: string[];
  app_name: string;
  app_version: string;
  max_question_length: number;
};

const ConfigContext = createContext<AppConfig | null>(null);
ConfigContext.displayName = 'AppConfigContext';

export function ConfigProvider({ config, children }: { config: AppConfig; children: ReactNode }) {
  return <ConfigContext.Provider value={config}>{children}</ConfigContext.Provider>;
}

export function useConfig() {
  const context = useContext(ConfigContext);
  if (context === null) {
    throw new Error('useConfig must be used within a ConfigProvider');
  }
  return context;
}
