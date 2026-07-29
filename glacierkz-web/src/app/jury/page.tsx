"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, FileCheck2, ShieldCheck, Workflow } from "lucide-react";
import { fetchJuryEvidence, type JuryEvidence } from "@/lib/api";
import { riskTwinHref } from "@/lib/evidenceCase";
import ScientificEvidenceCockpit from "@/components/ScientificEvidenceCockpit";

const JURY_CASE_HREF = riskTwinHref({
  rgiId: "RGI2000-v7.0-G-13-33843",
  year: 2024,
  sourceScope: "local_inventory",
});

export default function JuryPage() {
  const [evidence, setEvidence] = useState<JuryEvidence | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { fetchJuryEvidence().then(setEvidence).catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load jury evidence")); }, []);
  return <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900"><div className="mx-auto max-w-6xl space-y-6">
    <header className="rounded-2xl bg-slate-950 p-7 text-white"><p className="text-xs font-semibold uppercase tracking-widest text-cyan-200">Jury evidence pack</p><h1 className="mt-2 text-3xl font-bold">Что GlacierNET-KZ может доказать сейчас</h1><p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300">Не рекламный экран: все утверждения привязаны к локальным артефактам, а ограничения и отрицательные результаты показаны рядом.</p><div className="mt-5 flex flex-wrap gap-3"><Link href={JURY_CASE_HREF} className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950">Открыть проверяемый Risk Twin case <ArrowRight className="ml-1 inline h-4 w-4" /></Link><Link href="/analysis" className="rounded-lg border border-white/25 px-4 py-2 text-sm">Открыть AI Evidence</Link></div></header>
    {error && <p role="alert" className="rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
    {!evidence ? <p className="rounded-xl bg-white p-6 shadow-sm">Загрузка проверяемых артефактов…</p> : <>
      <section className="grid gap-4 md:grid-cols-3"><article className="rounded-xl bg-white p-5 shadow-sm"><FileCheck2 className="h-6 w-6 text-emerald-700" /><p className="mt-3 text-2xl font-bold">{evidence.release_checks.local_package_complete ? "Complete" : "Incomplete"}</p><p className="mt-1 text-sm text-slate-600">Локальный release package: {evidence.release_checks.required_artifact_count} обязательных артефактов.</p></article><article className="rounded-xl bg-white p-5 shadow-sm"><ShieldCheck className="h-6 w-6 text-cyan-700" /><p className="mt-3 text-2xl font-bold">{evidence.claim_status_counts.supported_silver ?? 0}</p><p className="mt-1 text-sm text-slate-600">Поддержанных silver-утверждений с ограниченной областью применимости.</p></article><article className="rounded-xl bg-white p-5 shadow-sm"><AlertTriangle className="h-6 w-6 text-amber-700" /><p className="mt-3 text-2xl font-bold">{evidence.blocked_until_external_work.length}</p><p className="mt-1 text-sm text-slate-600">Утверждений честно заблокировано до внешней валидации.</p></article></section>
      <section className="min-w-0 rounded-xl bg-white p-6 shadow-sm"><h2 className="text-lg font-semibold">Подтверждено локальными артефактами</h2><div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2">{evidence.supported_now.map((item) => <article key={item.title} className="min-w-0 rounded-xl border border-emerald-100 bg-emerald-50 p-4"><h3 className="break-words font-semibold text-emerald-950">{item.title}</h3><pre className="mt-2 max-w-full overflow-auto text-xs text-emerald-900">{JSON.stringify(item.value, null, 2)}</pre><p className="mt-2 break-words text-xs text-emerald-800">Scope: {item.scope}</p></article>)}</div></section>
      <section className="rounded-xl border border-amber-200 bg-amber-50 p-6"><h2 className="text-lg font-semibold text-amber-950">Важный отрицательный результат</h2><p className="mt-2 text-sm text-amber-900">{evidence.honest_negative_result.meaning}</p><div className="mt-4 grid gap-3 sm:grid-cols-2"><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">External stress-test Dice</p><p className="mt-1 text-xl font-bold">{evidence.honest_negative_result.hard_dice.estimate.toFixed(3)}</p><p className="text-xs text-slate-600">95% CI {evidence.honest_negative_result.hard_dice.ci_lower.toFixed(3)}–{evidence.honest_negative_result.hard_dice.ci_upper.toFixed(3)}</p></div><div className="rounded-lg bg-white p-3"><p className="text-xs text-slate-500">Area error</p><p className="mt-1 text-xl font-bold">{evidence.honest_negative_result.area_error_percent.estimate.toFixed(0)}%</p><p className="text-xs text-slate-600">Внешняя генерализация пока не доказана.</p></div></div></section>
      <ScientificEvidenceCockpit science={evidence.scientific_evidence} />
      <section className="rounded-xl border border-blue-100 bg-blue-50 p-6"><h2 className="text-lg font-semibold text-blue-950">Что ещё нельзя заявлять</h2><ul className="mt-3 space-y-3">{evidence.blocked_until_external_work.map((item) => <li key={item.id} className="rounded-lg bg-white p-3 text-sm"><strong>{item.claim}</strong><span className="mt-1 block text-slate-600">{item.scope}</span></li>)}</ul></section>
      <section className="rounded-xl border border-violet-100 bg-violet-50 p-6"><div className="flex items-start gap-3"><Workflow className="mt-0.5 h-5 w-5 text-violet-700" /><div><h2 className="text-lg font-semibold text-violet-950">Готовность автоматического контура</h2><p className="mt-1 text-sm text-violet-900">Создан machine-assisted pack: {evidence.automation_readiness.machine_assisted_label_pack.tasks} задач, {evidence.automation_readiness.machine_assisted_label_pack.glaciers} ледников, годы {evidence.automation_readiness.machine_assisted_label_pack.years.join(", ")}. Он помогает с QA и подготовкой разметки, но не является экспертной истиной.</p></div></div><ul className="mt-4 grid gap-2 md:grid-cols-2">{evidence.automation_readiness.claims.map((item) => <li key={item.id} className="rounded-lg bg-white p-3 text-sm"><span className={item.automated_input_ready ? "font-semibold text-emerald-700" : "font-semibold text-amber-700"}>{item.automated_input_ready ? "Готово к автоматической обработке" : "Ожидает внешние данные"}</span><p className="mt-1 font-medium text-slate-900">{item.claim}</p><p className="mt-1 text-xs text-slate-600">{item.status}</p></li>)}</ul></section>
    </>}
  </div></main>;
}
