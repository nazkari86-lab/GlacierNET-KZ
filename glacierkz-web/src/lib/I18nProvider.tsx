"use client";

import { createContext, useContext, useCallback, useSyncExternalStore, type ReactNode } from "react";
import { type Locale, type TranslationKey, translations } from "@/lib/i18n";

export const LOCALE_STORAGE_KEY = "glacierkz-locale";

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

let localeListeners: Array<() => void> = [];

function readStoredLocale(): Locale {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored === "en" || stored === "ru" || stored === "kk") return stored;
  const browser = navigator.language.slice(0, 2);
  if (browser === "ru" || browser === "kk") return browser;
  return "en";
}

function subscribeLocale(callback: () => void) {
  localeListeners.push(callback);
  return () => {
    localeListeners = localeListeners.filter((l) => l !== callback);
  };
}

function notifyLocaleListeners() {
  localeListeners.forEach((l) => l());
}

function getLocaleSnapshot(): Locale {
  return readStoredLocale();
}

function getLocaleServerSnapshot(): Locale {
  return "en";
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const locale = useSyncExternalStore(subscribeLocale, getLocaleSnapshot, getLocaleServerSnapshot);

  const setLocale = useCallback((next: Locale) => {
    localStorage.setItem(LOCALE_STORAGE_KEY, next);
    notifyLocaleListeners();
  }, []);

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>): string => {
      const localeTranslations = translations[locale] as Record<string, string>;
      let text = localeTranslations[key] ?? translations.en[key] ?? key;
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          text = text.replace(`{${k}}`, String(v));
        }
      }
      return text;
    },
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within <I18nProvider>");
  return ctx;
}

// Keep for tests that import LOCALE_STORAGE_KEY only
export function _resetLocaleListeners() {
  localeListeners = [];
}
