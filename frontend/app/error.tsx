'use client';

import { AppErrorScreen } from '@/components/app-error-screen';

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <AppErrorScreen reset={reset} />;
}
