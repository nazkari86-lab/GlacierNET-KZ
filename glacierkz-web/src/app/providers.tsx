"use client";

import { type ReactNode, useEffect } from "react";
import { initLeafletIcons } from "@/lib/leaflet-setup";
import { I18nProvider, useI18n } from "@/lib/I18nProvider";
import ErrorBoundary from "@/components/ErrorBoundary";
import HtmlLangSync from "@/components/HtmlLangSync";

function SkipToContentLink() {
  const { t } = useI18n();
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[9999] focus:rounded-lg focus:bg-blue-600 focus:px-4 focus:py-2 focus:text-white focus:shadow-lg"
    >
      {t("nav.skip")}
    </a>
  );
}

export default function ClientProviders({ children }: { children: ReactNode }) {
  useEffect(() => {
    initLeafletIcons();
  }, []);

  return (
    <I18nProvider>
      <HtmlLangSync />
      <ErrorBoundary>
        <SkipToContentLink />
        {children}
      </ErrorBoundary>
    </I18nProvider>
  );
}
