"use client";

import React from "react";

interface FormFieldProps {
  label: string;
  name: string;
  type?: "text" | "number" | "email" | "password" | "textarea" | "select" | "file" | "date" | "range";
  value?: string | number;
  onChange?: (value: string) => void;
  placeholder?: string;
  error?: string;
  helpText?: string;
  required?: boolean;
  disabled?: boolean;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
  rows?: number;
  accept?: string;
  className?: string;
}

export function FormField({
  label,
  name,
  type = "text",
  value,
  onChange,
  placeholder,
  error,
  helpText,
  required,
  disabled,
  options,
  min,
  max,
  step,
  rows = 3,
  accept,
  className = "",
}: FormFieldProps) {
  const baseClass = `w-full rounded-lg border px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
    error
      ? "border-red-300 bg-red-50"
      : "border-gray-300 bg-white hover:border-gray-400"
  } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`;

  const renderInput = () => {
    switch (type) {
      case "textarea":
        return (
          <textarea
            id={name}
            name={name}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            rows={rows}
            className={`${baseClass} resize-y`}
          />
        );
      case "select":
        return (
          <select
            id={name}
            name={name}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            disabled={disabled}
            className={baseClass}
          >
            <option value="">Select...</option>
            {options?.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );
      case "file":
        return (
          <input
            id={name}
            name={name}
            type="file"
            onChange={(e) => onChange?.(e.target.files?.[0]?.name || "")}
            disabled={disabled}
            accept={accept}
            className={baseClass}
          />
        );
      case "range":
        return (
          <div className="flex items-center gap-3">
            <input
              id={name}
              name={name}
              type="range"
              value={value}
              onChange={(e) => onChange?.(e.target.value)}
              disabled={disabled}
              min={min}
              max={max}
              step={step}
              className="flex-1 accent-blue-500"
            />
            <span className="text-sm text-gray-600 w-12 text-right">{value}</span>
          </div>
        );
      default:
        return (
          <input
            id={name}
            name={name}
            type={type}
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            placeholder={placeholder}
            disabled={disabled}
            min={min}
            max={max}
            step={step}
            className={baseClass}
          />
        );
    }
  };

  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-gray-700">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {renderInput()}
      {error && <p className="text-xs text-red-500">{error}</p>}
      {helpText && !error && <p className="text-xs text-gray-400">{helpText}</p>}
    </div>
  );
}

interface FormProps {
  children: React.ReactNode;
  onSubmit?: (data: Record<string, FormDataEntryValue>) => void;
  className?: string;
}

export function Form({ children, onSubmit, className = "" }: FormProps) {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const data: Record<string, FormDataEntryValue> = {};
    const formData = new FormData(form);
    formData.forEach((val, key) => {
      data[key] = val;
    });
    onSubmit?.(data);
  };

  return (
    <form onSubmit={handleSubmit} className={`space-y-4 ${className}`}>
      {children}
    </form>
  );
}
