"use client";

import Link from "next/link";
import {
  Mountain,
  LayoutDashboard,
  FlaskConical,
  BookOpen,
  Bot,
  HeartPulse,
  Monitor,
  ExternalLink,
} from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";

const SERVICES = [
  { href: "/dashboard", key: "hub.dashboard", icon: LayoutDashboard, external: false },
  { href: "/predict", key: "hub.predict", icon: Mountain, external: false },
  { href: "/demo", key: "hub.demo", icon: FlaskConical, external: true },
  { href: "/docs", key: "hub.api", icon: BookOpen, external: true },
  { href: "/mcp/tools", key: "hub.mcp", icon: Bot, external: true },
  { href: "/legacy", key: "hub.legacy", icon: Monitor, external: true },
  { href: "/health", key: "hub.health", icon: HeartPulse, external: true },
] as const;

export default function HubPage() {
  const { t } = useI18n();

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-blue-50">
      <div className="mx-auto max-w-4xl px-4 py-12">
        <div className="mb-10 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-4 py-1 text-sm font-medium text-blue-800">
            <Mountain className="h-4 w-4" />
            GlacierNET-KZ
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">{t("hub.title")}</h1>
          <p className="mt-3 text-slate-600">{t("hub.subtitle")}</p>
          <p className="mt-2 font-mono text-sm text-blue-700">http://localhost:8080</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {SERVICES.map(({ href, key, icon: Icon, external }) => (
            <Link
              key={href}
              href={href}
              target={external ? "_blank" : undefined}
              rel={external ? "noopener noreferrer" : undefined}
              className="group flex items-start gap-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <div className="rounded-lg bg-blue-50 p-3 text-blue-600 group-hover:bg-blue-100">
                <Icon className="h-6 w-6" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="font-semibold text-slate-900">{t(key)}</h2>
                  {external && <ExternalLink className="h-3.5 w-3.5 text-slate-400" />}
                </div>
                <p className="mt-1 text-sm text-slate-500">{t(`${key}.desc`)}</p>
                <p className="mt-2 font-mono text-xs text-slate-400">{href}</p>
              </div>
            </Link>
          ))}
        </div>

        <div className="mt-10 rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          <h3 className="font-semibold text-slate-900">{t("hub.stack")}</h3>
          <ul className="mt-3 space-y-1 font-mono text-xs">
            <li>gateway :8080 → web + api + demo</li>
            <li>redis (internal) · tensorflow · fastapi · next.js · gradio</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
