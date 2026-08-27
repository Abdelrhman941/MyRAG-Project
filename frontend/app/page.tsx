'use client';

import { bootstrapSessionAction } from '@/lib/api';
import { useEffect, useRef } from 'react';

export default function SplashPage() {
  const called = useRef(false);

  useEffect(() => {
    if (!called.current) {
      called.current = true;
      bootstrapSessionAction();
    }
  }, []);

  return (
    <div className="flex h-screen w-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4 animate-in fade-in duration-700">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold text-2xl">
          R
        </div>
        <div className="text-muted-foreground text-sm font-medium tracking-widest uppercase">
          Initializing
        </div>
      </div>
    </div>
  );
}
