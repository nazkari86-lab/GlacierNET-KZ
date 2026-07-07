"use client";

import { useI18n } from "@/lib/I18nProvider";
import { cn } from "@/lib/utils";
import type { Locale } from "@/lib/i18n";

const LOCALE_OPTIONS: { value: Locale; label: string }[] = [
  { value: "en", label: "EN" },
  { value: "ru", label: "RU" },
  { value: "kk", label: "KK" },
];

export default function LanguageSwitcher() {
  const { locale, setLocale } = useI18n();

  return (
    <div className="flex gap-1" role="radiogroup" aria-label="Language selection">
      {LOCALE_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          role="radio"
          aria-checked={locale === opt.value}
          onClick={() => setLocale(opt.value)}
          className={cn(
            "rounded-md px-2 py-0.5 text-xs font-medium transition-colors",
            locale === opt.value
              ? "bg-blue-600 text-white"
              : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700"
          )}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
