"use client";

import React from "react";

interface TabsProps {
  tabs: { key: string; label: string; icon?: React.ReactNode; count?: number }[];
  active: string;
  onChange: (key: string) => void;
  className?: string;
}

export function Tabs({ tabs, active, onChange, className = "" }: TabsProps) {
  return (
    <div className={`flex gap-1 border-b border-gray-200 ${className}`}>
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
            active === tab.key
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          {tab.icon}
          {tab.label}
          {tab.count !== undefined && (
            <span className={`text-xs px-1.5 py-0.5 rounded-full ${active === tab.key ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-500"}`}>
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

interface TabPanelProps {
  active: string;
  tab: string;
  children: React.ReactNode;
}

export function TabPanel({ active, tab, children }: TabPanelProps) {
  if (active !== tab) return null;
  return <div className="py-4">{children}</div>;
}

interface AccordionProps {
  items: { key: string; title: string; content: React.ReactNode; icon?: React.ReactNode }[];
  defaultOpen?: string[];
}

export function Accordion({ items, defaultOpen = [] }: AccordionProps) {
  const [open, setOpen] = React.useState<Set<string>>(new Set(defaultOpen));
  const toggle = (key: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className="space-y-1">
      {items.map((item) => (
        <div key={item.key} className="border border-gray-200 rounded-xl overflow-hidden">
          <button
            onClick={() => toggle(item.key)}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium text-left hover:bg-gray-50 transition-colors"
          >
            {item.icon}
            <span className="flex-1">{item.title}</span>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${open.has(item.key) ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {open.has(item.key) && (
            <div className="px-4 pb-4 text-sm text-gray-600 border-t border-gray-100">
              {item.content}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
