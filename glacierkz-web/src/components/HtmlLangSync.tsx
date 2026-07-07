"use client";

import { useEffect } from "react";
import { useI18n } from "@/lib/I18nProvider";

/** Syncs document.documentElement.lang with the active locale. */
export default function HtmlLangSync() {
  const { locale } = useI18n();

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  return null;
}
