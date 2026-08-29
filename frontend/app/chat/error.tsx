'use client';

import { AppErrorScreen } from '@/components/app-error-screen';

export default function ChatErrorPage({
  reset,
}: { reset: () => void }) {
  return <AppErrorScreen reset={reset} />;
}
