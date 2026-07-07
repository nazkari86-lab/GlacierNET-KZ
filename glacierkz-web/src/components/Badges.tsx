"use client";

import React from "react";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info" | "purple";
  size?: "sm" | "md";
  dot?: boolean;
}

const variantStyles = {
  default: "bg-gray-100 text-gray-700",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
  info: "bg-blue-100 text-blue-700",
  purple: "bg-purple-100 text-purple-700",
};

const dotColors = {
  default: "bg-gray-400",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
  info: "bg-blue-500",
  purple: "bg-purple-500",
};

export function Badge({ children, variant = "default", size = "sm", dot }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full font-medium ${size === "sm" ? "px-2 py-0.5 text-xs" : "px-3 py-1 text-sm"} ${variantStyles[variant]}`}>
      {dot && <span className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]}`} />}
      {children}
    </span>
  );
}

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && <div className="text-4xl mb-4 text-gray-300">{icon}</div>}
      <h3 className="text-lg font-medium text-gray-900 mb-1">{title}</h3>
      {description && <p className="text-sm text-gray-500 max-w-sm mb-4">{description}</p>}
      {action}
    </div>
  );
}

interface StatusBadgeProps {
  status: "healthy" | "degraded" | "unhealthy" | "unknown";
  label?: string;
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = {
    healthy: { variant: "success" as const, text: "Healthy" },
    degraded: { variant: "warning" as const, text: "Degraded" },
    unhealthy: { variant: "error" as const, text: "Unhealthy" },
    unknown: { variant: "default" as const, text: "Unknown" },
  };
  const c = config[status];
  return <Badge variant={c.variant} dot>{label || c.text}</Badge>;
}
