import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#171717] px-6 text-neutral-100">
      <section className="w-full max-w-md rounded-3xl border border-white/10 bg-[#202020] p-8 text-center shadow-2xl shadow-black/20 animate-in fade-in zoom-in-95 duration-500">
        <p className="text-sm font-medium tracking-[0.2em] text-neutral-500">404</p>
        <h1 className="mt-3 text-2xl font-semibold">Chat not found</h1>
        <p className="mt-2 text-sm leading-6 text-neutral-400">
          This chat may have been deleted or the link is no longer valid.
        </p>
        <Link
          href="/"
          className="mt-7 inline-flex rounded-lg bg-neutral-100 px-4 py-2.5 text-sm font-medium text-neutral-900 transition-colors hover:bg-white"
        >
          Back to chats
        </Link>
      </section>
    </main>
  );
}
