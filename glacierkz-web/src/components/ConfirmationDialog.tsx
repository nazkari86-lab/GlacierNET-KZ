"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { AlertTriangle, Info, CheckCircle, X } from "lucide-react";

interface ConfirmationDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "warning" | "info" | "success";
  onConfirm?: () => void | Promise<void>;
  onCancel?: () => void;
  requireConfirmation?: boolean;
  confirmationText?: string;
  loading?: boolean;
  className?: string;
}

const VARIANT_CONFIG = {
  danger: {
    icon: AlertTriangle,
    iconBg: "bg-red-100",
    iconColor: "text-red-600",
    confirmBg: "bg-red-600 hover:bg-red-700",
  },
  warning: {
    icon: AlertTriangle,
    iconBg: "bg-amber-100",
    iconColor: "text-amber-600",
    confirmBg: "bg-amber-600 hover:bg-amber-700",
  },
  info: {
    icon: Info,
    iconBg: "bg-blue-100",
    iconColor: "text-blue-600",
    confirmBg: "bg-blue-600 hover:bg-blue-700",
  },
  success: {
    icon: CheckCircle,
    iconBg: "bg-green-100",
    iconColor: "text-green-600",
    confirmBg: "bg-green-600 hover:bg-green-700",
  },
};

export default function ConfirmationDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "danger",
  onConfirm,
  onCancel,
  requireConfirmation = false,
  confirmationText = "DELETE",
  loading = false,
  className,
}: ConfirmationDialogProps) {
  const [confirmInput, setConfirmInput] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  const config = VARIANT_CONFIG[variant];
  const Icon = config.icon;

  const isConfirmDisabled =
    loading || isProcessing || (requireConfirmation && confirmInput !== confirmationText);

  useEffect(() => {
    if (open) setConfirmInput("");
  }, [open]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open && onCancel) onCancel();
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open, onCancel]);

  const handleConfirm = useCallback(async () => {
    if (isConfirmDisabled) return;
    setIsProcessing(true);
    try {
      await onConfirm?.();
    } finally {
      setIsProcessing(false);
    }
  }, [onConfirm, isConfirmDisabled]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="fixed inset-0 bg-black/50" onClick={onCancel} />
      <div
        className={cn(
          "relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden",
          className
        )}
      >
        <button
          onClick={onCancel}
          className="absolute top-3 right-3 p-1 rounded-full hover:bg-gray-100 transition-colors"
          aria-label="Close"
        >
          <X className="w-4 h-4 text-gray-400" />
        </button>

        <div className="p-6">
          <div className="flex items-start gap-4">
            <div className={cn("w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0", config.iconBg)}>
              <Icon className={cn("w-5 h-5", config.iconColor)} />
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-gray-900">{title}</h3>
              <p className="text-sm text-gray-600 mt-1">{message}</p>
            </div>
          </div>

          {requireConfirmation && (
            <div className="mt-4 ml-14">
              <label className="text-xs text-gray-500">
                Type <span className="font-mono font-medium">{confirmationText}</span> to confirm
              </label>
              <input
                type="text"
                value={confirmInput}
                onChange={(e) => setConfirmInput(e.target.value)}
                className="mt-1 w-full px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-red-500 focus:border-red-500"
                placeholder={confirmationText}
                autoFocus
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-6 py-3 bg-gray-50 border-t border-gray-100">
          <button
            onClick={onCancel}
            disabled={loading || isProcessing}
            className="px-4 py-2 text-sm text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-40 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={handleConfirm}
            disabled={isConfirmDisabled}
            className={cn(
              "px-4 py-2 text-sm text-white rounded-lg disabled:opacity-40 transition-colors",
              config.confirmBg
            )}
          >
            {loading || isProcessing ? (
              <span className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </span>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

interface SimpleConfirmProps {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function SimpleConfirm({ open, title, message, onConfirm, onCancel }: SimpleConfirmProps) {
  return (
    <ConfirmationDialog
      open={open}
      title={title}
      message={message}
      confirmLabel="Yes"
      cancelLabel="No"
      variant="info"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />
  );
}

export type { ConfirmationDialogProps };
