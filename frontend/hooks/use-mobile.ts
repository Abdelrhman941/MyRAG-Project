import * as React from 'react';

const MOBILE_BREAKPOINT = 768;

function getMediaQuery() {
  return `(max-width: ${MOBILE_BREAKPOINT - 1}px)`;
}

function subscribeToMediaQuery(onStoreChange: () => void): () => void {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const mediaQuery = window.matchMedia(getMediaQuery());

  const handleChange = () => {
    onStoreChange();
  };

  mediaQuery.addEventListener('change', handleChange);

  return () => {
    mediaQuery.removeEventListener('change', handleChange);
  };
}

function getSnapshot(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }

  return window.matchMedia(getMediaQuery()).matches;
}

function getServerSnapshot(): boolean {
  return false;
}

export function useIsMobile(): boolean {
  return React.useSyncExternalStore(subscribeToMediaQuery, getSnapshot, getServerSnapshot);
}
