"use client";

import { useMemo, useState } from "react";
import type { ClaimEvidenceStatus, EvidenceArtifact, ScientificEvidence } from "@/lib/api";

type Filter = "all" | ClaimEvidenceStatus;

const statusMeta: Record<ClaimEvidenceStatus, { label: string; className: string }> = {
  supported_silver: { label: "Supported · silver", className: "bg-cyan-100 text-cyan-950" },
  supported_provisional: { label: "Provisional", className: "bg-amber-100 text-amber-950" },
  refuted_for_current_model: { label: "Refuted for current model", className: "bg-rose-100 text-rose-950" },
  blocked_external_evidence: { label: "Blocked pending external evidence", className: "bg-slate-200 text-slate-800" },
};

function titleForMetric(metric: string): string {
  return metric.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(4);
}

function ArtifactList({ artifacts }: { artifacts: EvidenceArtifact[] }) {
  return <ul className="mt-3 space-y-2 text-xs">
    {artifacts.map((artifact) => <li key={artifact.path} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
      <p className="break-all font-mono text-slate-800">{artifact.path}</p>
      <p className="mt-1 text-slate-500">{artifact.exists ? `SHA-256 ${artifact.sha256?.slice(0, 16)}…` : "Artifact unavailable — not used as evidence."}</p>
    </li>)}
  </ul>;
}

export default function ScientificEvidenceCockpit({ science }: { science: ScientificEvidence }) {
  const [filter, setFilter] = useState<Filter>("all");
  const claims = useMemo(() => filter === "all" ? science.claim_registry : science.claim_registry.filter((claim) => claim.status === filter), [filter, science.claim_registry]);
  const temporal = science.temporal_holdout;
  const paired = science.paired_glacier_diagnostic;

  return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Scientific Evidence Cockpit</p><h2 className="mt-1 text-xl font-bold text-slate-950">Scientific Evidence Cockpit: что измерено — и где наука заканчивается</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">Все показатели ниже прочитаны из локальных артефактов. Статус, область применимости и запреты на расширение вывода показаны рядом с числом.</p></div><span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700">{science.schema}</span></div>

    <div className="mt-5 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
      <article className="rounded-xl border border-cyan-100 bg-cyan-50 p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div><p className="text-xs font-bold uppercase tracking-wide text-cyan-800">Temporal holdout</p><h3 className="mt-1 font-semibold text-cyan-950">{temporal.evaluation_protocol}</h3></div><span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-cyan-900">{temporal.label_quality_tier} labels</span></div><p className="mt-2 text-sm text-cyan-950">{temporal.generalisation_scope} · {temporal.label_provenance}</p><dl className="mt-4 grid grid-cols-3 gap-2 text-sm"><div className="rounded-lg bg-white p-3"><dt className="text-xs text-slate-500">Train</dt><dd className="mt-1 font-bold">{temporal.splits.train_years[0]}–{temporal.splits.train_years.at(-1)}</dd></div><div className="rounded-lg bg-white p-3"><dt className="text-xs text-slate-500">Validation</dt><dd className="mt-1 font-bold">{temporal.splits.validation_years.join(", ")}</dd></div><div className="rounded-lg bg-white p-3"><dt className="text-xs text-slate-500">Untouched test</dt><dd className="mt-1 font-bold">{temporal.splits.test_years.join(", ")}</dd></div></dl><div className="mt-4 grid gap-2 sm:grid-cols-2">{Object.entries(temporal.hard_metrics).filter(([, value]) => typeof value === "number").map(([metric, value]) => <div key={metric} className="rounded-lg border border-cyan-100 bg-white px-3 py-2"><p className="text-xs text-slate-500">{titleForMetric(metric)}</p><p className="mt-1 font-mono text-lg font-bold text-slate-950">{formatValue(Number(value))}</p></div>)}</div><p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-950"><strong>Glacier-level CI unavailable.</strong> {temporal.glacier_level_ci_status}. {temporal.boundary_metrics_status}</p></article>

      <article className="rounded-xl border border-amber-200 bg-amber-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-amber-800">Paired glacier diagnostic</p><h3 className="mt-1 font-semibold text-amber-950">Post-hoc, non-independent diagnostic</h3><p className="mt-2 text-sm text-amber-950">{paired.cohort_selection.n_glaciers} paired glaciers · {paired.label_quality_tier}</p><div className="mt-4 space-y-2">{Object.entries(paired.metrics).map(([metric, result]) => <div key={metric} className="rounded-lg border border-amber-100 bg-white p-3"><div className="flex items-baseline justify-between gap-2"><p className="font-medium text-slate-950">{titleForMetric(metric)}</p><p className="font-mono font-bold text-slate-950">{result.estimate >= 0 ? "+" : ""}{formatValue(result.estimate)}</p></div><p className="mt-1 text-xs text-slate-600">{Math.round(result.confidence * 100)}% bootstrap interval {formatValue(result.ci_lower)}…{formatValue(result.ci_upper)} · n={result.n_glaciers}</p></div>)}</div><p className="mt-4 text-xs leading-5 text-amber-950">Не разрешено: {paired.claims_not_allowed.join(", ")}.</p></article>
    </div>

    <article className="mt-4 min-w-0 rounded-xl border border-slate-200 p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-bold uppercase tracking-wide text-slate-600">Claim registry explorer</p><h3 className="mt-1 font-semibold text-slate-950">Каждое утверждение связано с файлом и границей</h3><p className="mt-1 text-xs text-slate-600">{science.claim_policy}</p></div><div className="flex max-w-full flex-wrap gap-2">{(["all", ...Object.keys(statusMeta)] as Filter[]).map((status) => <button key={status} type="button" onClick={() => setFilter(status)} aria-pressed={filter === status} className={`max-w-full rounded-full px-3 py-1.5 text-xs font-semibold ${filter === status ? "bg-slate-950 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`}>{status === "all" ? "All" : statusMeta[status].label}</button>)}</div></div><div className="mt-4 grid min-w-0 gap-3 lg:grid-cols-2">{claims.map((claim) => <details key={claim.id} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4"><summary className="cursor-pointer list-none"><div className="flex min-w-0 flex-wrap items-start justify-between gap-3"><p className="min-w-0 flex-1 break-words font-semibold text-slate-950">{claim.id} · {claim.claim}</p><span className={`max-w-full rounded-full px-2 py-1 text-center text-[11px] font-bold ${statusMeta[claim.status].className}`}>{statusMeta[claim.status].label}</span></div><p className="mt-2 break-words text-sm text-slate-600">{claim.scope}</p></summary><ArtifactList artifacts={claim.artifacts} /></details>)}</div></article>

    <article className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-rose-800">External generalisation gate</p><h3 className="mt-1 font-semibold text-rose-950">{science.external_generalisation.test_region}: {science.external_generalisation.status === "blocked_external_evidence" ? "blocked" : "evidence available"}</h3><p className="mt-2 text-sm text-rose-950">Required label tier: {science.external_generalisation.label_quality_tier_required}. {science.external_generalisation.blocked_reason}</p><ArtifactList artifacts={[science.external_generalisation.artifact]} /></article>
  </section>;
}
