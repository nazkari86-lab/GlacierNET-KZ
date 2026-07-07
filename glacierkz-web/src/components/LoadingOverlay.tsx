'use client';

import React, { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';

interface LoadingOverlayProps {
  loading: boolean;
  message?: string;
  subtext?: string;
}

export default function LoadingOverlay({ loading, message = 'Loading…', subtext }: LoadingOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!loading) return;
    const el = overlayRef.current;
    if (!el) return;
    el.focus();
    const trap = (e: KeyboardEvent) => {
      if (e.key === 'Tab') e.preventDefault();
    };
    el.addEventListener('keydown', trap);
    return () => el.removeEventListener('keydown', trap);
  }, [loading]);

  if (!loading) return null;

  return (
    <div
      ref={overlayRef}
      role="dialog"
      aria-modal="true"
      aria-label={message}
      tabIndex={-1}
      className={cn(
        'fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm transition-opacity duration-300',
      )}
    >
      <div className="relative h-12 w-12">
        <div className="absolute inset-0 rounded-full border-4 border-zinc-200" />
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-blue-600" />
      </div>

      <p className="mt-4 text-sm font-semibold text-zinc-800">{message}</p>
      {subtext && <p className="mt-1 text-xs text-zinc-500">{subtext}</p>}
    </div>
  );
}
