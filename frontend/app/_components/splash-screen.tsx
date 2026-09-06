'use client';

import { Loader2, RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';

import { useReadiness, type ReadinessStatus } from '@/hooks/use-readiness';

const STATUS_MESSAGES: Record<ReadinessStatus, string> = {
  connecting: 'Connecting to the RAG server...',
  warming: 'Warming up BGE-M3 (takes a moment)...',
  qdrant_not_ready: 'Connecting to Qdrant...',
  ready: 'Ready',
  error: 'Unable to connect to the RAG server.',
};

export function SplashScreen() {
  const { status, retry } = useReadiness();
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    if (status !== 'ready') return;

    const timer = setTimeout(() => setHidden(true), 300);

    return () => clearTimeout(timer);
  }, [status]);

  if (hidden) return null;

  const isError = status === 'error';
  const isReady = status === 'ready';

  return (
    <div
      className={`fixed inset-0 z-100 flex items-center justify-center bg-background text-foreground transition-opacity duration-300 ${
        isReady ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <div className="flex flex-col items-center gap-5 text-center">
        <Loader2
          className={`size-8 text-muted-foreground ${
            isReady || isError ? 'animate-none' : 'animate-spin'
          }`}
        />

        <div className="flex flex-col items-center gap-2">
          <p className="text-sm text-muted-foreground">{STATUS_MESSAGES[status]}</p>

          {isError && (
            <button
              type="button"
              onClick={retry}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted"
            >
              <RefreshCw className="size-4" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
