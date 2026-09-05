'use client';

import { Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useReadiness } from '@/hooks/use-readiness';
import Image from 'next/image';

export function SplashScreen() {
  const { status } = useReadiness();
  const [text, setText] = useState('Initializing...');
  const [opacity, setOpacity] = useState(1);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    const timer1 = setTimeout(() => setText('Warming up BGE-M3 (takes a moment)...'), 500);
    const timer2 = setTimeout(() => setText('Connecting to Qdrant...'), 2500);

    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
    };
  }, []);

  useEffect(() => {
    if (status === 'ready') {
      const fadeTimer = setTimeout(() => setOpacity(0), 50);
      const hideTimer = setTimeout(() => setHidden(true), 1050); // Wait for fade out
      return () => {
        clearTimeout(fadeTimer);
        clearTimeout(hideTimer);
      };
    }
  }, [status]);

  if (hidden) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center bg-background text-foreground transition-opacity duration-1000"
      style={{ opacity }}
    >
      <div className="flex flex-col items-center gap-6">
        <div className="relative h-12 w-32">
          <Image
            src="/images/logos/nova-text.webp"
            alt="Nova Logo"
            fill
            className="object-contain dark:invert"
            priority
          />
        </div>
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground animate-pulse">{text}</p>
        </div>
      </div>
    </div>
  );
}
