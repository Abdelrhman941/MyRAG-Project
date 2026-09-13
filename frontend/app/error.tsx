'use client';

import { AppErrorScreen } from '@/components/layout/app-error-screen';

export default function ErrorPage({ reset }: { reset: () => void }) {
  return <AppErrorScreen reset={reset} />;
}
