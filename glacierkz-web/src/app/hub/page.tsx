"use client";

import Link from "next/link";
import {
  Mountain,
  BrainCircuit,
  HeartPulse,
  MapPinned,
  ClipboardCheck,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";

const SERVICES = [
  {
    href: "/ml",
    key: "hub.ml",
    icon: BrainCircuit,
  },
  {
    href: "/risk-twin",
    key: "hub.risk",
    icon: HeartPulse,
  },
  {
    href: "/operations",
    key: "hub.operations",
    icon: ClipboardCheck,
  },
  {
    href: "/analysis",
    key: "hub.analysis",
    icon: MessageSquareText,
  },
  {
    href: "/jury",
    key: "hub.jury",
    icon: ShieldCheck,
  },
  {
    href: "/glaciers",
    key: "hub.glaciers",
    icon: MapPinned,
  },
] as const;

const SECONDARY_LINKS = [
  ["/explore", "hub.explore"],
  ["/predict", "hub.predict"],
  ["/pilot", "hub.pilot"],
  ["/dashboard", "hub.dashboard"],
  ["/reports", "reports.title"],
] as const;

export default function HubPage() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-blue-50">
      <main id="main-content" className="mx-auto max-w-4xl px-4 py-12">
        <div className="mb-10 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-4 py-1 text-sm font-medium text-blue-800">
            <Mountain className="h-4 w-4" />
            GlacierNET-KZ
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">{t("hub.title")}</h1>
          <p className="mt-3 text-slate-600">{t("hub.subtitle")}</p>
          <p className="mt-2 text-sm text-blue-700">Web workspace. API endpoints are configured through NEXT_PUBLIC_API_URL.</p>
        </div>

        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">{t("hub.primary_eyebrow")}</p>
            <h2 className="mt-1 text-xl font-bold text-slate-950">{t("hub.primary_title")}</h2>
          </div>
          <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800 sm:inline">
            {t("hub.real_artifacts")}
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {SERVICES.map(({ href, key, icon: Icon }, index) => (
            <Link
              key={href}
              href={href}
              className="group flex items-start gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <div className="relative rounded-lg bg-blue-50 p-3 text-blue-600 group-hover:bg-blue-100">
                <Icon className="h-6 w-6" />
                <span className="absolute -right-2 -top-2 grid h-5 w-5 place-items-center rounded-full bg-slate-950 text-[10px] font-bold text-white">
                  {index + 1}
                </span>
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-slate-900">{t(key)}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-600">{t(`${key}.desc`)}</p>
                <p className="mt-2 font-mono text-xs text-slate-400">{href}</p>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-10 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          <h3 className="font-semibold text-slate-900">{t("hub.supporting")}</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">
            {t("hub.supporting.desc")}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {SECONDARY_LINKS.map(([href, key]) => (
              <Link key={href} href={href} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 hover:border-blue-300 hover:text-blue-800">
                {t(key)}
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
