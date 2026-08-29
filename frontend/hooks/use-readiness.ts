'use client';

import { getReadyStatusAction } from '@/lib/api';
import { useCallback, useEffect, useState } from 'react';

export type ReadinessStatus = 'connecting' | 'warming' | 'qdrant_not_ready' | 'ready' | 'error';

type ReadinessState = {
  status: ReadinessStatus;
  detail?: string;
};

function normalizeStatus(status: string): ReadinessStatus {
  if (status === 'ready' || status === 'warming' || status === 'qdrant_not_ready') {
    return status;
  }
  return 'error';
}

/** Polls the backend readiness endpoint until it becomes ready or reports an error. */
export function useReadiness() {
  const [state, setState] = useState<ReadinessState>({ status: 'connecting' });
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setState({ status: 'connecting' });
    setAttempt((current) => current + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;
    let checking = false;

    const checkReadiness = async () => {
      if (checking) return;
      checking = true;

      try {
        const result = await getReadyStatusAction();
        if (cancelled) return;

        const status = normalizeStatus(result.status);
        setState({ status, detail: result.detail });

        if (status === 'ready' || status === 'error') {
          clearInterval(interval);
        }
      } finally {
        checking = false;
      }
    };

    const interval = setInterval(() => void checkReadiness(), 2000);
    void checkReadiness();

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [attempt]);

  return { ...state, retry };
}
