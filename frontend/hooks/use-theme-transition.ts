'use client';

import type { AppTheme } from '@/components/providers/theme-provider';
import { useTheme } from 'next-themes';
import { useCallback, useState } from 'react';

type ViewTransitionDocument = Document & {
  startViewTransition?: (updateCallback: () => void) => { finished: Promise<void> };
};

const toAppTheme = (theme: string | undefined): AppTheme => (theme === 'light' ? 'light' : 'dark');

/** Changes the theme with a smooth View Transition when supported by the browser. */
export function useThemeTransition() {
  const { resolvedTheme, setTheme } = useTheme();
  const [isTransitioning, setIsTransitioning] = useState(false);
  const theme = toAppTheme(resolvedTheme);

  const setAppTheme = useCallback(
    (nextTheme: AppTheme) => {
      if (nextTheme === theme || isTransitioning) return;

      const updateTheme = () => setTheme(nextTheme);
      const supportsReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const documentWithTransitions = document as ViewTransitionDocument;

      if (supportsReducedMotion || !documentWithTransitions.startViewTransition) {
        updateTheme();
        return;
      }

      setIsTransitioning(true);
      let transition: { finished: Promise<void> };
      try {
        transition = documentWithTransitions.startViewTransition(updateTheme);
      } catch {
        setIsTransitioning(false);
        updateTheme();
        return;
      }
      void transition.finished.catch(() => undefined).finally(() => setIsTransitioning(false));
    },
    [isTransitioning, setTheme, theme]
  );

  const toggleTheme = useCallback(
    () => setAppTheme(theme === 'dark' ? 'light' : 'dark'),
    [setAppTheme, theme]
  );

  return { theme, setTheme: setAppTheme, toggleTheme, isTransitioning };
}
