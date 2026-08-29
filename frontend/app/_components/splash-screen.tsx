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
            ? 'border-emerald-400/40 bg-emerald-400/15 text-emerald-300'
            : step.active
              ? 'border-neutral-400 bg-neutral-100 text-neutral-900'
              : 'border-neutral-700 text-neutral-600'
        }`}
      >
        {step.complete ? <Check className="size-3" /> : <Circle className="size-2 fill-current" />}
      </span>
      <span className={step.active || step.complete ? 'text-neutral-100' : 'text-neutral-500'}>
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
      className={`flex min-h-screen items-center justify-center bg-[#171717] px-6 text-neutral-100 transition-opacity duration-500 ${
        transitioning ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <div className="w-full max-w-sm animate-in fade-in zoom-in-95 duration-700">
        <div className="rounded-3xl border border-white/10 bg-[#202020] p-8 shadow-2xl shadow-black/20">
          <div className="mb-10 flex items-center gap-4">
            <div className="flex size-16 items-center justify-center rounded-2xl bg-neutral-100 text-3xl font-bold text-neutral-900 shadow-lg shadow-white/5">
              R
            </div>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">
                {config?.app_name || 'RAG Assistant'}
              </h1>
              <p className="mt-1 text-sm text-neutral-400">Chat with your documents</p>
            </div>
          </div>

          {isError ? (
            <div className="rounded-2xl border border-red-400/20 bg-red-400/10 p-4">
              <div className="flex items-start gap-3">
                <TriangleAlert className="mt-0.5 size-5 shrink-0 text-red-300" />
                <div>
                  <p className="font-medium text-red-100">Unable to reach the server</p>
                  <p className="mt-1 text-sm leading-5 text-red-200/70">
                    {detail || 'Please ensure the backend server is running.'}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={retry}
                className="mt-4 inline-flex items-center gap-2 rounded-lg bg-red-100 px-3 py-2 text-sm font-medium text-red-950 transition-colors hover:bg-white"
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
                <div className="mt-5 flex items-center gap-2 rounded-xl border border-white/8 bg-white/4 px-3 py-2.5 text-sm text-neutral-300 animate-in fade-in duration-300">
                  <Database className="size-4 text-neutral-400" />
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
