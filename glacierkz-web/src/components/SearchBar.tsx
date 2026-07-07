"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Search, X, ArrowRight } from "lucide-react";

interface SearchSuggestion {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  category?: string;
}

interface SearchBarProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (value: string) => void;
  onSuggestionClick?: (suggestion: SearchSuggestion) => void;
  suggestions?: SearchSuggestion[];
  showCommandHint?: boolean;
  autofocus?: boolean;
  debounceMs?: number;
  size?: "sm" | "md" | "lg";
  className?: string;
  compact?: boolean;
}

export default function SearchBar({
  placeholder = "Search...",
  value: controlledValue,
  onChange,
  onSearch,
  onSuggestionClick,
  suggestions = [],
  showCommandHint = true,
  autofocus = false,
  debounceMs = 300,
  size = "md",
  className,
  compact = false,
}: SearchBarProps) {
  const [internalValue, setInternalValue] = useState(controlledValue || "");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  const value = controlledValue !== undefined ? controlledValue : internalValue;

  const filteredSuggestions = suggestions.filter((s) => {
    if (!value) return true;
    const q = value.toLowerCase();
    return (
      s.label.toLowerCase().includes(q) ||
      s.description?.toLowerCase().includes(q) ||
      s.category?.toLowerCase().includes(q)
    );
  });

  const groupedSuggestions = filteredSuggestions.reduce(
    (acc, s) => {
      const cat = s.category || "Results";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(s);
      return acc;
    },
    {} as Record<string, SearchSuggestion[]>
  );

  const handleChange = useCallback(
    (val: string) => {
      if (controlledValue === undefined) setInternalValue(val);
      onChange?.(val);
      setShowSuggestions(true);
      setHighlightedIndex(-1);

      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        onSearch?.(val);
      }, debounceMs);
    },
    [controlledValue, onChange, onSearch, debounceMs]
  );

  const handleClear = useCallback(() => {
    handleChange("");
    inputRef.current?.focus();
  }, [handleChange]);

  const handleSuggestionClick = useCallback(
    (suggestion: SearchSuggestion) => {
      handleChange(suggestion.label);
      setShowSuggestions(false);
      onSuggestionClick?.(suggestion);
    },
    [handleChange, onSuggestionClick]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        setShowSuggestions(false);
        inputRef.current?.blur();
      }
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex((i) => Math.min(i + 1, filteredSuggestions.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex((i) => Math.max(i - 1, -1));
      }
      if (e.key === "Enter") {
        if (highlightedIndex >= 0 && filteredSuggestions[highlightedIndex]) {
          handleSuggestionClick(filteredSuggestions[highlightedIndex]);
        } else {
          onSearch?.(value);
          setShowSuggestions(false);
        }
      }
    },
    [filteredSuggestions, highlightedIndex, handleSuggestionClick, onSearch, value]
  );

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (autofocus) inputRef.current?.focus();
  }, [autofocus]);

  const sizeClasses = {
    sm: "pl-8 pr-8 py-1.5 text-xs",
    md: "pl-9 pr-9 py-2 text-sm",
    lg: "pl-10 pr-10 py-2.5 text-base",
  };

  const iconSize = size === "lg" ? "w-4 h-4" : "w-3.5 h-3.5";

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="relative">
        <Search className={cn("absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400", iconSize)} />
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowSuggestions(true)}
          placeholder={placeholder}
          className={cn(
            "w-full border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all",
            sizeClasses[size],
            compact && "rounded-md"
          )}
        />
        {value && (
          <button
            onClick={handleClear}
            className={cn(
              "absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-gray-100 text-gray-400",
              iconSize === "w-4 h-4" ? "right-3" : "right-2"
            )}
          >
            <X className={iconSize} />
          </button>
        )}
        {!value && showCommandHint && (
          <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5 text-[10px] text-gray-400">
            <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[9px]">⌘</kbd>
            <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[9px]">K</kbd>
          </div>
        )}
      </div>

      {showSuggestions && filteredSuggestions.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto">
          {Object.entries(groupedSuggestions).map(([category, items]) => (
            <div key={category}>
              <div className="px-3 py-1.5 text-[10px] font-medium text-gray-400 uppercase tracking-wider bg-gray-50">
                {category}
              </div>
              {items.map((suggestion) => {
                const globalIndex = filteredSuggestions.indexOf(suggestion);
                return (
                  <button
                    key={suggestion.id}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className={cn(
                      "flex items-center gap-3 w-full px-3 py-2 text-left text-sm hover:bg-gray-50 transition-colors",
                      highlightedIndex === globalIndex && "bg-gray-50"
                    )}
                  >
                    {suggestion.icon && (
                      <span className="text-gray-400">{suggestion.icon}</span>
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-gray-700 truncate block">{suggestion.label}</span>
                      {suggestion.description && (
                        <span className="text-[11px] text-gray-400 truncate block">{suggestion.description}</span>
                      )}
                    </div>
                    <ArrowRight className="w-3 h-3 text-gray-300 opacity-0 group-hover:opacity-100" />
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export type { SearchBarProps, SearchSuggestion };
