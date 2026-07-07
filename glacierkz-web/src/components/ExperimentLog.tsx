'use client';

import React, { useState, useMemo, useRef, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

export interface LogEntry {
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'success';
  message: string;
}

type LogLevel = LogEntry['level'];

interface ExperimentLogProps {
  logs: LogEntry[];
  filter?: LogLevel;
}

const LEVEL_STYLE: Record<LogLevel, { bg: string; text: string; icon: string }> = {
  info: { bg: 'bg-blue-50', text: 'text-blue-700', icon: 'ℹ' },
  warning: { bg: 'bg-amber-50', text: 'text-amber-700', icon: '⚠' },
  error: { bg: 'bg-red-50', text: 'text-red-700', icon: '✕' },
  success: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: '✓' },
};

const ALL_LEVELS: LogLevel[] = ['info', 'warning', 'error', 'success'];

export default function ExperimentLog({ logs, filter }: ExperimentLogProps) {
  const [activeFilter, setActiveFilter] = useState<LogLevel | undefined>(filter);
  const [search, setSearch] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    let result = logs;
    if (activeFilter) result = result.filter((l) => l.level === activeFilter);
    if (search) {
      const q = search.toLowerCase();
      result = result.filter((l) => l.message.toLowerCase().includes(q));
    }
    return result;
  }, [logs, activeFilter, search]);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filtered, autoScroll]);

  const handleExport = useCallback(() => {
    const text = filtered
      .map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`)
      .join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `experiment-log-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [filtered]);

  const levelCounts = useMemo(() => {
    const counts: Record<LogLevel, number> = { info: 0, warning: 0, error: 0, success: 0 };
    logs.forEach((l) => counts[l.level]++);
    return counts;
  }, [logs]);

  return (
    <div className="flex flex-col rounded-xl border border-zinc-200 bg-white overflow-hidden" aria-label="Experiment log viewer">
      <div className="flex flex-wrap items-center gap-3 border-b border-zinc-200 px-4 py-3">
        <div className="flex gap-1" role="tablist" aria-label="Filter by level">
          <button
            role="tab"
            aria-selected={!activeFilter}
            onClick={() => setActiveFilter(undefined)}
            className={cn(
              'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
              !activeFilter ? 'bg-zinc-800 text-white' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200',
            )}
          >
            All ({logs.length})
          </button>
          {ALL_LEVELS.map((level) => (
            <button
              key={level}
              role="tab"
              aria-selected={activeFilter === level}
              onClick={() => setActiveFilter(level)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium transition-colors',
                activeFilter === level
                  ? `${LEVEL_STYLE[level].bg} ${LEVEL_STYLE[level].text}`
                  : 'bg-zinc-100 text-zinc-500 hover:bg-zinc-200',
              )}
            >
              {level.charAt(0).toUpperCase() + level.slice(1)} ({levelCounts[level]})
            </button>
          ))}
        </div>

        <div className="relative ml-auto">
          <svg
            className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search logs…"
            aria-label="Search log messages"
            className="w-44 rounded-lg border border-zinc-300 bg-zinc-50 py-1.5 pl-8 pr-3 text-xs text-zinc-700 placeholder:text-zinc-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>

        <label className="flex items-center gap-1.5 text-xs text-zinc-500">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="h-3.5 w-3.5 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
          />
          Auto-scroll
        </label>

        <button
          onClick={handleExport}
          className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-700 transition-colors hover:bg-zinc-50"
          aria-label="Export log entries"
        >
          Export
        </button>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto font-mono text-xs leading-relaxed"
        style={{ maxHeight: 400 }}
        role="log"
        aria-live="polite"
      >
        {filtered.length === 0 && (
          <div className="flex h-32 items-center justify-center text-zinc-400">No log entries</div>
        )}
        {filtered.map((log, i) => {
          const style = LEVEL_STYLE[log.level];
          return (
            <div
              key={i}
              className={cn(
                'flex items-start gap-3 border-b border-zinc-100 px-4 py-2 transition-colors hover:bg-zinc-50',
                style.bg,
              )}
            >
              <span className="shrink-0 text-[10px] text-zinc-400 pt-0.5 w-20 tabular-nums">
                {log.timestamp}
              </span>
              <span className={cn('shrink-0 text-[10px] font-bold uppercase w-16', style.text)}>
                {style.icon} {log.level}
              </span>
              <span className="flex-1 text-zinc-700 break-words">{log.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
