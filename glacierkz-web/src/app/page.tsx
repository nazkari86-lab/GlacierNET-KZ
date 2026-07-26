"use client";

import Link from "next/link";
import { Mountain, FileText, Network, CalendarRange, MapPinned, ClipboardCheck } from "lucide-react";
import GlacierHero from "@/components/GlacierHero";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useI18n } from "@/lib/I18nProvider";

const NAV_ITEMS = [
  { href: "/operations", key: "nav.operations" as const, icon: ClipboardCheck },
  { href: "/hub", key: "nav.hub" as const, icon: Network },
  { href: "/explore", key: "nav.explore" as const, icon: CalendarRange },
  { href: "/glaciers", key: "nav.glaciers" as const, icon: MapPinned },
  { href: "/reports", key: "nav.reports" as const, icon: FileText },
];

const PRIMARY_ACTIONS = [
  { href: "/operations", key: "home.action_operations" as const, desc: "home.action_operations_desc" as const, icon: ClipboardCheck },
  { href: "/explore", key: "home.action_years" as const, desc: "home.action_years_desc" as const, icon: CalendarRange },
  { href: "/glaciers", key: "home.action_glacier" as const, desc: "home.action_glacier_desc" as const, icon: MapPinned },
  { href: "/reports", key: "home.action_report" as const, desc: "home.action_report_desc" as const, icon: FileText },
];

export default function HomePage() {
  const { t } = useI18n();

  return (
    <div className="flex min-h-screen flex-col">
      <GlacierHero />

      <header className="border-b border-zinc-200">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
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
        <div className="grid w-full max-w-4xl gap-4 text-left sm:grid-cols-2">
          {PRIMARY_ACTIONS.map(({ href, key, desc, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-start gap-4 rounded-xl border border-zinc-200 bg-white p-5 transition-all hover:border-blue-300 hover:shadow-md"
            >
              <span className="rounded-lg bg-blue-50 p-3"><Icon className="h-6 w-6 text-blue-600" aria-hidden="true" /></span>
              <span>
                <span className="block font-semibold">{t(key)}</span>
                <span className="mt-1 block text-sm text-zinc-500">{t(desc)}</span>
              </span>
            </Link>
          ))}
        </div>
        <Link href="/hub" className="mt-8 text-sm text-blue-600 hover:underline">{t("home.all_tools")}</Link>
      </main>
    </div>
  );
}
