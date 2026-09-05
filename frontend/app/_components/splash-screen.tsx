'use client';

import { useReadiness } from '@/hooks/use-readiness';
import { bootstrapSessionAction } from '@/lib/api';
import { RefreshCw, TriangleAlert } from 'lucide-react';
import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';

const MIN_SPLASH_DURATION_MS = 900;
const SPLASH_EXIT_DURATION_MS = 300;

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
      <div className="flex flex-col items-center animate-in fade-in duration-[400ms] motion-reduce:animate-none">
        <Image
          src="/images/logos/nova.webp"
          alt="Nova Logo"
          width={64}
          height={64}
          className="h-16 w-auto object-contain"
          priority
        />

        <div className="mt-8 h-[2px] w-40 overflow-hidden rounded-full bg-white/10">
          <div
            className={`h-full bg-white/60 transition-all ${
              status === 'ready'
                ? 'w-full'
                : 'w-full animate-indeterminate motion-reduce:animate-none'
            }`}
          />
        </div>

        {!isError && (
          <p
            key={status}
            className="mt-4 text-[13px] text-white/40 animate-in fade-in duration-500 motion-reduce:animate-none"
          >
            {status === 'warming' && 'Loading AI model — first boot can take a minute…'}
            {status === 'qdrant_not_ready' && 'Search engine is starting…'}
            {status === 'connecting' && 'Connecting to server…'}
            {status === 'ready' && 'Ready'}
          </p>
        )}
      </div>

      {isError && (
        <div className="mt-8 w-full max-w-[22rem] rounded-xl border border-border bg-card p-4 text-card-foreground shadow-sm" role="alert">
          <div className="flex items-start gap-3">
            <TriangleAlert className="mt-0.5 size-5 shrink-0 text-destructive" />
            <div>
              <p className="font-medium">Unable to reach the server</p>
              <p className="mt-1 text-sm leading-5 text-muted-foreground">
                {detail || 'Please ensure the backend server is running.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={retry}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <RefreshCw className="size-3.5" />
            Retry
          </button>
        </div>
      )}
    </main>
  );
}
