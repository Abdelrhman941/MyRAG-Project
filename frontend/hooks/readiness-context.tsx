'use client';

import { createContext, useContext } from 'react';
import { useReadiness, type ReadinessStatus } from './use-readiness';

type ReadinessContextValue = {
  status: ReadinessStatus;
  detail?: string;
  retry: () => void;
};

const ReadinessContext = createContext<ReadinessContextValue | null>(null);

/** Single poller — mount once in the root layout, share state across all consumers. */
export function ReadinessProvider({ children }: { children: React.ReactNode }) {
  const value = useReadiness();
  return <ReadinessContext.Provider value={value}>{children}</ReadinessContext.Provider>;
}

/** Read the shared readiness state. Must be used inside <ReadinessProvider>. */
export function useReadinessState(): ReadinessContextValue {
  const ctx = useContext(ReadinessContext);
  if (ctx === null) {
    throw new Error('useReadinessState must be used inside <ReadinessProvider>');
  }
  return ctx;
}
