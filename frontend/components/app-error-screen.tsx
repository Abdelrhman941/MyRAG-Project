'use client';

import { AlertCircle, ArrowLeft, RefreshCw } from 'lucide-react';
import Link from 'next/link';

export function AppErrorScreen({ reset }: { reset: () => void }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#171717] px-6 text-neutral-100">
      <section className="w-full max-w-md rounded-3xl border border-white/10 bg-[#202020] p-8 text-center shadow-2xl shadow-black/20 animate-in fade-in zoom-in-95 duration-500">
        <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-red-400/10 text-red-300">
          <AlertCircle className="size-6" />
        </div>
        <h1 className="mt-5 text-xl font-semibold">We couldn’t load this page</h1>
        <p className="mt-2 text-sm leading-6 text-neutral-400">
          Check that the RAG server is running, then try again.
        </p>
        <div className="mt-7 flex flex-col justify-center gap-3 sm:flex-row">
          <button
            type="button"
            onClick={reset}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-neutral-100 px-4 py-2.5 text-sm font-medium text-neutral-900 transition-colors hover:bg-white"
          >
            <RefreshCw className="size-4" />
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-white/10 px-4 py-2.5 text-sm font-medium text-neutral-200 transition-colors hover:bg-white/5"
          >
            <ArrowLeft className="size-4" />
            Back to chats
          </Link>
        </div>
      </section>
    </main>
  );
}
