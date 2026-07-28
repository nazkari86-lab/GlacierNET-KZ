"use client";

import type { EvidenceIssue, EvidenceMapObject } from "@/lib/riskTwinEvidence";

interface EvidenceInspectorProps {
  object: EvidenceMapObject | null;
  issue: EvidenceIssue | null;
}

export default function EvidenceInspector({ object, issue }: EvidenceInspectorProps) {
  if (!object && !issue) {
    return <section aria-label="Evidence inspector" className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">Выберите объект или проблему на карте.</section>;
  }

  const title = object?.name ?? issue?.title ?? "Evidence item";
  const visibleFact = object?.visibleFact ?? "Пробел данных определён по типизированным требованиям текущей оценки.";
  const allowedClaim = object?.allowedClaim ?? "Можно показать, какое решение блокируется этим пробелом.";
  const prohibitedClaims = Array.from(new Set([
    object?.prohibitedClaim,
    issue?.blockedClaim,
    !object && !issue ? "Нельзя выходить за пределы доступного источника." : undefined,
  ].filter((claim): claim is string => Boolean(claim))));
  const nextAction = issue?.nextAction ?? "Выберите проблему из очереди, чтобы увидеть следующий способ проверки.";

  return (
    <section aria-label="Evidence inspector" className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-cyan-700">Evidence inspector</p>
      <h3 role="status" aria-live="polite" className="mt-1 text-base font-bold text-slate-950">{title}</h3>
      {object && <p className="mt-1 text-xs text-slate-500">{object.source} · {object.temporalCoverage}</p>}
      <div className="mt-4 space-y-3 text-sm">
        <div><h4 className="font-semibold text-slate-900">Что видно</h4><p className="mt-1 leading-5 text-slate-700">{visibleFact}</p></div>
        <div><h4 className="font-semibold text-emerald-900">Что можно утверждать</h4><p className="mt-1 leading-5 text-emerald-800">{allowedClaim}</p></div>
        <div><h4 className="font-semibold text-amber-950">Чего утверждать нельзя</h4><ul className="mt-1 space-y-1 leading-5 text-amber-900">{prohibitedClaims.map((claim) => <li key={claim}>• {claim}</li>)}</ul></div>
        <div><h4 className="font-semibold text-cyan-950">Следующая проверка</h4><p className="mt-1 leading-5 text-cyan-900">{nextAction}</p></div>
      </div>
      {object && <dl className="mt-4 grid gap-2 border-t border-slate-100 pt-3 text-xs sm:grid-cols-2">
        {object.inspectorFacts.map((fact) => <div key={fact.label} className="rounded-lg bg-slate-50 px-2.5 py-2"><dt className="font-medium text-slate-500">{fact.label}</dt><dd className="mt-0.5 break-words font-semibold text-slate-800">{fact.value}</dd></div>)}
      </dl>}
    </section>
  );
}
