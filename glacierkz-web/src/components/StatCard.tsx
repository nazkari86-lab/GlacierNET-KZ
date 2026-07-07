"use client";

import React from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  trendValue?: string;
  color?: "blue" | "green" | "red" | "yellow" | "purple" | "emerald" | "amber" | "violet";
  loading?: boolean;
}

const colorMap: Record<string, string> = {
  blue: "bg-blue-50 text-blue-600 border-blue-200",
  green: "bg-emerald-50 text-emerald-600 border-emerald-200",
  red: "bg-red-50 text-red-600 border-red-200",
  yellow: "bg-amber-50 text-amber-600 border-amber-200",
  purple: "bg-purple-50 text-purple-600 border-purple-200",
  emerald: "bg-emerald-50 text-emerald-600 border-emerald-200",
  amber: "bg-amber-50 text-amber-600 border-amber-200",
  violet: "bg-violet-50 text-violet-600 border-violet-200",
};

const trendIcons = {
  up: "↑",
  down: "↓",
  neutral: "→",
};

export function StatCard({ label, value, icon, trend, trendValue, color = "blue", loading }: StatCardProps) {
  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white p-6 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-24 mb-3" />
        <div className="h-8 bg-gray-200 rounded w-16" />
      </div>
    );
  }
  return (
    <div className={`rounded-xl border p-6 transition-all hover:shadow-md ${colorMap[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium opacity-75">{label}</span>
        {icon && <span className="text-lg">{icon}</span>}
      </div>
      <div className="text-2xl font-bold">{value}</div>
      {trend && trendValue && (
        <div className={`text-xs mt-1 ${trend === "up" ? "text-emerald-600" : trend === "down" ? "text-red-600" : "text-gray-500"}`}>
          {trendIcons[trend]} {trendValue}
        </div>
      )}
    </div>
  );
}

interface ProgressCardProps {
  label: string;
  progress: number;
  max?: number;
  color?: string;
  showPercentage?: boolean;
}

export function ProgressCard({ label, progress, max = 100, color = "#3b82f6", showPercentage = true }: ProgressCardProps) {
  const pct = Math.min(100, Math.max(0, (progress / max) * 100));
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        {showPercentage && <span className="text-sm text-gray-500">{pct.toFixed(1)}%</span>}
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className="h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

interface DashboardGridProps {
  children: React.ReactNode;
  cols?: 2 | 3 | 4;
}

export function DashboardGrid({ children, cols = 4 }: DashboardGridProps) {
  const gridCols = {
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
    4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4",
  };
  return (
    <div className={`grid ${gridCols[cols]} gap-4`}>
      {children}
    </div>
  );
}
