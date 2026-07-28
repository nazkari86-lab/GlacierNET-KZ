"use client";

import { useEffect, useMemo, useState } from "react";
import type { EvidenceMapObject } from "@/lib/riskTwinEvidence";

type MapMode = "evidence" | "route" | "people";

interface EvidenceRouteRibbonProps {
  objects: EvidenceMapObject[];
  mode: MapMode;
}

const routeKinds: Array<{ kind: EvidenceMapObject["kind"]; label: string; status: string }> = [
  { kind: "glacier", label: "Ледник", status: "инвентарь" },
  { kind: "lake", label: "Озеро", status: "контекст" },
  { kind: "river", label: "Русло", status: "справочный слой" },
  { kind: "asset", label: "Объект рядом", status: "планировочный контекст" },
];

export default function EvidenceRouteRibbon({ objects, mode }: EvidenceRouteRibbonProps) {
  const [reducedMotion, setReducedMotion] = useState(true);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReducedMotion(query.matches);
    sync();
    query.addEventListener?.("change", sync);
    return () => query.removeEventListener?.("change", sync);
  }, []);

  const route = useMemo(() => routeKinds.flatMap((step) => {
    const object = objects.find((item) => item.kind === step.kind);
    return object ? [{ ...step, object }] : [];
  }), [objects]);

  if (route.length === 0) return null;
  const animated = mode === "route" && !reducedMotion;
  return (
    <section aria-label="Evidence route" className="rounded-2xl border border-cyan-100 bg-gradient-to-r from-cyan-50 via-white to-blue-50 p-3 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-cyan-800">Evidence route</p><h3 className="text-sm font-bold text-slate-950">Связи, которые можно проверить на карте</h3></div><span className="rounded-full bg-amber-100 px-2 py-1 text-[10px] font-bold text-amber-900">Не прогноз</span></div>
      <ol className="mt-3 flex items-stretch gap-1 overflow-x-auto pb-1">
        {route.map((step, index) => <li key={step.object.id} className="flex min-w-[146px] items-center gap-1"><div className="flex-1 rounded-xl border border-slate-200 bg-white p-2.5"><p className="text-[10px] font-bold uppercase tracking-wide text-cyan-800">{step.label}</p><p className="mt-1 truncate text-xs font-semibold text-slate-900" title={step.object.name}>{step.object.name}</p><p className="mt-1 text-[10px] text-slate-500">{step.status}</p></div>{index < route.length - 1 && <span className={`risk-twin-route-particle px-1 text-lg text-cyan-700 ${animated ? "animate-pulse" : ""}`} data-route-motion={animated ? "enabled" : undefined} aria-hidden="true">→</span>}</li>)}
      </ol>
      <p className="mt-2 text-xs leading-5 text-slate-600">Карта показывает пространственный контекст; это не модель затопления или последствий.</p>
    </section>
  );
}
