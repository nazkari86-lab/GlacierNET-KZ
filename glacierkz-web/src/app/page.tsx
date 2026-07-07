"use client";

import Link from "next/link";
import { Mountain, GitCompareArrows, TrendingUp, Clock, Bot, BarChart3, Database, Cog, FileText, Settings, Network } from "lucide-react";
import GlacierHero from "@/components/GlacierHero";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useI18n } from "@/lib/I18nProvider";

const NAV_ITEMS = [
  { href: "/hub", key: "nav.hub" as const, icon: Network },
  { href: "/dashboard", key: "nav.dashboard" as const, icon: BarChart3 },
  { href: "/predict", key: "nav.predict" as const, icon: Mountain },
  { href: "/compare", key: "nav.compare" as const, icon: GitCompareArrows },
  { href: "/trend", key: "nav.trend" as const, icon: TrendingUp },
  { href: "/datasets", key: "nav.datasets" as const, icon: Database },
  { href: "/training", key: "nav.training" as const, icon: Cog },
  { href: "/reports", key: "nav.reports" as const, icon: FileText },
  { href: "/history", key: "nav.history" as const, icon: Clock },
  { href: "/analysis", key: "nav.analysis" as const, icon: Bot },
  { href: "/settings", key: "nav.settings" as const, icon: Settings },
];

export default function HomePage() {
  const { t } = useI18n();

  return (
    <div className="flex min-h-screen flex-col">
      <GlacierHero />

      <header className="border-b border-zinc-200">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <Link href="/" className="flex items-center gap-2">
            <Mountain className="h-6 w-6 text-blue-600" />
            <span className="text-lg font-bold">{t("home.title")}</span>
          </Link>
          <div className="flex items-center gap-4">
            <nav className="flex gap-6" aria-label="Main navigation">
              {NAV_ITEMS.map(({ href, key, icon: Icon }) => (
                <Link
                  key={href}
                  href={href}
                  className="flex items-center gap-1.5 text-sm text-zinc-600 transition-colors hover:text-zinc-900"
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {t(key)}
                </Link>
              ))}
            </nav>
            <LanguageSwitcher />
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto flex max-w-5xl flex-1 flex-col items-center justify-center px-4 py-24 text-center">
        <Mountain className="mb-6 h-16 w-16 text-blue-600" aria-hidden="true" />
        <h1 className="mb-4 text-4xl font-bold tracking-tight">{t("home.title")}</h1>
        <p className="mb-8 max-w-lg text-lg text-zinc-500">
          {t("home.description")}
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {NAV_ITEMS.map(({ href, key, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex flex-col items-center gap-2 rounded-xl border border-zinc-200 p-5 transition-all hover:border-blue-300 hover:shadow-sm"
            >
              <Icon className="h-6 w-6 text-blue-600" aria-hidden="true" />
              <span className="text-sm font-medium">{t(key)}</span>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
