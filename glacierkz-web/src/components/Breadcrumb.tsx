"use client";

import { cn } from "@/lib/utils";
import { ChevronRight, Home } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  href?: string;
  onClick?: () => void;
  icon?: React.ReactNode;
  active?: boolean;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  separator?: React.ReactNode;
  showHome?: boolean;
  onHomeClick?: () => void;
  className?: string;
  size?: "sm" | "md";
}

export default function Breadcrumb({
  items,
  separator = <ChevronRight className="w-3.5 h-3.5 text-gray-400" />,
  showHome = true,
  onHomeClick,
  className,
  size = "sm",
}: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={cn("flex items-center", className)}>
      <ol className="flex items-center gap-1">
        {showHome && (
          <li className="flex items-center">
            <button
              onClick={onHomeClick}
              className={cn(
                "flex items-center text-gray-500 hover:text-gray-700 transition-colors",
                size === "sm" ? "text-xs" : "text-sm"
              )}
            >
              <Home className="w-3.5 h-3.5" />
            </button>
            {items.length > 0 && <span className="mx-1">{separator}</span>}
          </li>
        )}
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <li key={i} className="flex items-center">
              {item.icon && <span className="mr-1">{item.icon}</span>}
              {item.href || item.onClick ? (
                <button
                  onClick={item.onClick}
                  className={cn(
                    "hover:text-gray-700 transition-colors",
                    size === "sm" ? "text-xs" : "text-sm",
                    isLast ? "text-gray-900 font-medium" : "text-gray-500"
                  )}
                >
                  {item.label}
                </button>
              ) : (
                <span
                  className={cn(
                    size === "sm" ? "text-xs" : "text-sm",
                    isLast ? "text-gray-900 font-medium" : "text-gray-500"
                  )}
                >
                  {item.label}
                </span>
              )}
              {!isLast && <span className="mx-1">{separator}</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

interface BreadcrumbWithBackProps {
  title: string;
  backLabel?: string;
  onBack?: () => void;
  actions?: React.ReactNode;
  className?: string;
}

export function BreadcrumbWithBack({
  title,
  onBack,
  actions,
  className,
}: BreadcrumbWithBackProps) {
  return (
    <div className={cn("flex items-center justify-between mb-4", className)}>
      <div className="flex items-center gap-3">
        {onBack && (
          <button
            onClick={onBack}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <ChevronRight className="w-5 h-5 rotate-180" />
          </button>
        )}
        <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export type { BreadcrumbProps, BreadcrumbItem, BreadcrumbWithBackProps };
