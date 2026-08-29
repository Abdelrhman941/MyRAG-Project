'use client';

import { useReadiness } from '@/hooks/use-readiness';
import { bootstrapSessionAction } from '@/lib/api';
import { useConfig } from '@/lib/config';
import { Check, Circle, Database, RefreshCw, TriangleAlert } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

type Step = {
  label: string;
  complete: boolean;
  active: boolean;
};

function StatusStep({ step }: { step: Step }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span
        className={`flex size-5 items-center justify-center rounded-full border ${
          step.complete
            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
            : step.active
              ? 'border-primary bg-primary text-primary-foreground'
              : 'border-border text-muted-foreground'
        }`}
      >
        {step.complete ? <Check className="size-3" /> : <Circle className="size-2 fill-current" />}
      </span>
      <span className={step.active || step.complete ? 'text-foreground' : 'text-muted-foreground'}>
        {step.label}
      </span>
    </div>
  );
}

export function SplashScreen() {
  const config = useConfig();
  const { status, detail, retry } = useReadiness();
  const [transitioning, setTransitioning] = useState(false);
  const bootstrapped = useRef(false);

  useEffect(() => {
    if (status !== 'ready' || bootstrapped.current) return;

    bootstrapped.current = true;
    setTransitioning(true);
    const timeout = window.setTimeout(() => {
      void bootstrapSessionAction();
    }, 350);

    return () => window.clearTimeout(timeout);
  }, [status]);

  const isError = status === 'error';
  const isQdrantStarting = status === 'qdrant_not_ready';
  const steps: Step[] = [
    {
      label: 'Connecting to server',
      complete: status !== 'connecting' && !isError,
      active: status === 'connecting',
    },
    {
      label: 'Loading AI model',
      complete: status === 'qdrant_not_ready' || status === 'ready',
      active: status === 'warming',
    },
    {
      label: 'Ready',
      complete: status === 'ready',
      active: isQdrantStarting,
    },
  ];

  return (
    <main
      className={`flex min-h-screen items-center justify-center bg-background px-6 text-foreground transition-opacity duration-500 ${
        transitioning ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <div className="w-full max-w-sm animate-in fade-in zoom-in-95 duration-700">
        <div className="rounded-3xl border border-border bg-card p-8 shadow-2xl shadow-black/10">
          <div className="mb-10 flex items-center gap-4">
            <div className="flex size-16 items-center justify-center rounded-2xl bg-primary text-3xl font-bold text-primary-foreground shadow-lg shadow-primary/10">
              R
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                {config?.app_name || 'RAG Assistant'}
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">Chat with your documents</p>
            </div>
          </div>

          {isError ? (
            <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-4">
              <div className="flex items-start gap-3">
                <TriangleAlert className="mt-0.5 size-5 shrink-0 text-destructive" />
                <div>
                  <p className="font-medium text-foreground">Unable to reach the server</p>
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
          ) : (
            <div className="space-y-4" aria-live="polite">
              {steps.map((step) => (
                <StatusStep key={step.label} step={step} />
              ))}
              {isQdrantStarting && (
                <div className="mt-5 flex items-center gap-2 rounded-xl border border-border bg-muted/50 px-3 py-2.5 text-sm text-muted-foreground animate-in fade-in duration-300">
                  <Database className="size-4" />
                  Search engine is starting…
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
