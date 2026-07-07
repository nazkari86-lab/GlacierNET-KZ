"use client";

import React, { useState, useEffect } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

const typeStyles: Record<ToastType, { bg: string; border: string; icon: string }> = {
  success: { bg: "bg-emerald-50", border: "border-emerald-200", icon: "✓" },
  error: { bg: "bg-red-50", border: "border-red-200", icon: "✕" },
  warning: { bg: "bg-amber-50", border: "border-amber-200", icon: "⚠" },
  info: { bg: "bg-blue-50", border: "border-blue-200", icon: "ℹ" },
};

let toastId = 0;
let listeners: ((toast: Toast) => void)[] = [];

export function showToast(type: ToastType, title: string, message?: string, duration = 5000) {
  const toast: Toast = { id: `t${++toastId}`, type, title, message, duration };
  listeners.forEach((l) => l(toast));
}

export const toast = {
  success: (title: string, msg?: string) => showToast("success", title, msg),
  error: (title: string, msg?: string) => showToast("error", title, msg),
  warning: (title: string, msg?: string) => showToast("warning", title, msg),
  info: (title: string, msg?: string) => showToast("info", title, msg),
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const listener = (t: Toast) => {
      setToasts((prev) => [...prev, t]);
      if (t.duration) {
        setTimeout(() => {
          setToasts((prev) => prev.filter((x) => x.id !== t.id));
        }, t.duration);
      }
    };
    listeners.push(listener);
    return () => {
      listeners = listeners.filter((l) => l !== listener);
    };
  }, []);

  const dismiss = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <div className="fixed bottom-4 right-4 z-[100] space-y-2 max-w-sm">
      {toasts.map((t) => {
        const style = typeStyles[t.type];
        return (
          <div
            key={t.id}
            className={`${style.bg} ${style.border} border rounded-xl p-4 shadow-lg animate-in slide-in-from-right duration-300`}
          >
            <div className="flex items-start gap-3">
              <span className="text-lg">{style.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900">{t.title}</p>
                {t.message && <p className="text-xs text-gray-600 mt-0.5">{t.message}</p>}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                className="text-gray-400 hover:text-gray-600 text-xs"
              >
                ✕
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
