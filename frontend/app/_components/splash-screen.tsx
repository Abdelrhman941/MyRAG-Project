'use client';

import { useReadiness } from '@/hooks/use-readiness';
import { bootstrapSessionAction } from '@/lib/api';
import { RefreshCw, TriangleAlert } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const MIN_SPLASH_DURATION_MS = 900;
const SPLASH_EXIT_DURATION_MS = 700;

export function SplashScreen() {
  const { status, detail, retry } = useReadiness();
  const [transitioning, setTransitioning] = useState(false);
  const bootstrapped = useRef(false);
  const mountedAt = useRef<number | null>(null);

  useEffect(() => {
    mountedAt.current = Date.now();
  }, []);

  useEffect(() => {
    if (status !== 'ready' || bootstrapped.current) return;

    let bootstrapTimeout: number | undefined;
    const splashStartedAt = mountedAt.current ?? Date.now();
    const remainingSplashTime = Math.max(
      0,
      MIN_SPLASH_DURATION_MS - (Date.now() - splashStartedAt)
    );
    const transitionTimeout = window.setTimeout(() => {
      bootstrapped.current = true;
      setTransitioning(true);
      bootstrapTimeout = window.setTimeout(() => {
        void bootstrapSessionAction();
      }, SPLASH_EXIT_DURATION_MS);
    }, remainingSplashTime);

    return () => {
      window.clearTimeout(transitionTimeout);
      if (bootstrapTimeout) window.clearTimeout(bootstrapTimeout);
    };
  }, [status]);

  const isError = status === 'error';
  return (
    <main className={`splash-screen ${transitioning ? 'splash-screen--exiting' : ''}`}>
      <div className="splash-loader" role="img" aria-label="Loading">
        <div className="splash-loader__cube" aria-hidden="true">
          {Array.from({ length: 6 }, (_, index) => (
            <span key={index} className={`splash-loader__face splash-loader__face--${index + 1}`} />
          ))}
        </div>
        <div className="splash-loader__particles" aria-hidden="true">
          {Array.from({ length: 8 }, (_, index) => (
            <span key={index} className="splash-loader__particle" />
          ))}
        </div>
      </div>

      {!isError && (
        <p
          key={status}
          className="mt-6 text-sm text-white/50 animate-in fade-in duration-500"
        >
          {status === 'warming' && 'Loading AI model — first boot can take a minute…'}
          {status === 'qdrant_not_ready' && 'Search engine is starting…'}
          {status === 'connecting' && 'Connecting to server…'}
          {status === 'ready' && 'Ready'}
        </p>
      )}

      {isError && (
        <div className="splash-error" role="alert">
          <div className="flex items-start gap-3">
            <TriangleAlert className="mt-0.5 size-5 shrink-0 text-destructive" />
            <div>
              <p className="font-medium text-white">Unable to reach the server</p>
              <p className="mt-1 text-sm leading-5 text-white/60">
                {detail || 'Please ensure the backend server is running.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={retry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-medium text-black transition-colors hover:bg-white/85"
          >
            <RefreshCw className="size-3.5" />
            Retry
          </button>
        </div>
      )}
    </main>
  );
}
