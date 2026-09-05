'use client';

import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function AppErrorScreen({ reset }: { reset: () => void }) {
  const router = useRouter();

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-6 text-foreground">
      <section className="w-full max-w-md rounded-3xl border border-border bg-card p-8 text-center shadow-2xl shadow-black/10 animate-in fade-in zoom-in-95 duration-500">
        <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <AlertCircle className="size-6" />
        </div>
        <h1 className="mt-5 text-xl font-semibold">We couldn’t load this page</h1>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Check that the RAG server is running, then try again.
        </p>
        <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            <RefreshCw className="size-4" />
            Try again
          </button>
          <button
            type="button"
            onClick={() => router.replace('/')}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-muted"
          >
            <ArrowLeft className="size-4" />
            Back to chats
          </button>
        </div>
      </section>
    </main>
  );
}
