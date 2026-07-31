"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, CircleDashed, ClipboardCheck, Copy, Download, FileSearch, LockKeyhole, MapPin, Satellite, ShieldCheck, Upload, UsersRound } from "lucide-react";
import { createRiskTwinHandoff, type GlacierRecord, type RiskTwinSpatialContext } from "@/lib/api";
import type { EvidenceMapObject } from "@/lib/riskTwinEvidence";
import { buildCaseActionPlan, buildSelectedObjectAdvice, type ActionAudience } from "@/lib/caseActionPlan";

type Candidate = RiskTwinSpatialContext["screening_candidates"][number];

const AUDIENCES: Array<{ id: ActionAudience; label: string; icon: typeof Satellite }> = [
  { id: "satellite", label: "Снимки", icon: Satellite },
  { id: "field", label: "Поле", icon: MapPin },
  { id: "decision", label: "Решение", icon: UsersRound },
  { id: "research", label: "Наука", icon: FileSearch },
];

interface CaseActionPlanProps {
  glacier: GlacierRecord | null;
  candidate: Candidate | null;
  object: EvidenceMapObject | null;
  year: number;
}

function Guardrails({ items }: { items: string[] }) {
  return (
    <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-center gap-2 font-bold text-amber-950"><ShieldCheck className="h-4 w-4" />Границы утверждений</div>
      <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-950">{items.map((item) => <li key={item}>• {item}</li>)}</ul>
    </div>
  );
}

const GATE_STYLE = {
  observed: { label: "Наблюдаемый факт", icon: CheckCircle2, className: "border-emerald-200 bg-emerald-50 text-emerald-950" },
  verify: { label: "Нужно подтвердить", icon: CircleDashed, className: "border-cyan-200 bg-cyan-50 text-cyan-950" },
  blocked: { label: "Пока не оценивается", icon: LockKeyhole, className: "border-amber-200 bg-amber-50 text-amber-950" },
} as const;

export default function CaseActionPlan({ glacier, candidate, object, year }: CaseActionPlanProps) {
  const [audience, setAudience] = useState<ActionAudience>("satellite");
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [handoffMessage, setHandoffMessage] = useState("");
  const [operationsUrl, setOperationsUrl] = useState("");
  const plan = useMemo(() => glacier && candidate ? buildCaseActionPlan(glacier, candidate, year) : null, [candidate, glacier, year]);
  const objectAdvice = useMemo(() => !plan && object ? buildSelectedObjectAdvice(object, year) : null, [object, plan, year]);

  if (!plan && !objectAdvice) {
    return (
      <section id="case-action-plan" aria-label="Case Action Plan" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-700">Case Action Plan</p>
        <h2 className="mt-1 text-xl font-bold">Выберите объект на карте или в очереди</h2>
        <p className="mt-2 text-sm text-slate-600">Для выбранного объекта здесь появится конкретный первый шаг, измеренные факты и условие, которое не позволяет делать неподтверждённые выводы.</p>
      </section>
    );
  }

  if (!plan && objectAdvice) {
    return (
      <section id="case-action-plan" aria-label="Case Action Plan" className="overflow-hidden rounded-3xl border border-cyan-200 bg-gradient-to-br from-cyan-50 via-white to-blue-50 shadow-[0_20px_50px_-32px_rgba(8,145,178,0.45)]">
        <div className="border-b border-cyan-100 bg-slate-950 p-5 text-white">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-200">Selected object guidance</p>
          <h2 className="mt-1 text-xl font-bold">{objectAdvice.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-5 text-slate-300">{objectAdvice.rationale}</p>
        </div>
        <div className="p-5">
          <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-4">
            <p className="text-xs font-bold uppercase tracking-wide text-cyan-900">Сделайте сейчас</p>
            <h3 className="mt-1 font-bold text-slate-950">{objectAdvice.nextStep.title}</h3>
            <p className="mt-2 text-sm leading-6 text-slate-700">{objectAdvice.nextStep.instruction}</p>
            <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
              <p className="rounded-lg bg-white p-2.5 text-emerald-950"><strong>Готово, когда:</strong> {objectAdvice.nextStep.acceptance}</p>
              <p className="rounded-lg bg-amber-50 p-2.5 text-amber-950"><strong>Стоп-условие:</strong> {objectAdvice.nextStep.blockedClaim}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{objectAdvice.facts.map((fact) => <div key={fact.label} className="rounded-xl border border-cyan-100 bg-white p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-cyan-800">{fact.label}</p><p className="mt-1 text-sm font-bold text-slate-900">{fact.value}</p></div>)}</div>
          <a href="#evidence-ledger" className="mt-4 inline-flex min-h-10 items-center rounded-xl bg-cyan-700 px-3 text-sm font-bold text-white transition hover:bg-cyan-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700">Перейти к журналу доказательств</a>
          <Guardrails items={objectAdvice.guardrails} />
        </div>
      </section>
    );
  }

  // The two early returns above cover every no-plan state. Keep the explicit
  // guard so TypeScript also preserves that fact inside the export callbacks.
  if (!plan) return null;

  const priorityComponents = candidate?.priority_components;
  const priorityDrivers: Array<[string, number]> = priorityComponents
    ? ([
        ["Изменение площади", priorityComponents.area_change],
        ["Размер озера", priorityComponents.lake_size],
        ["Близость к RGI", priorityComponents.rgi_proximity],
        ["Нет надёжного прошлого match", priorityComponents.no_reliable_previous_match],
      ] as Array<[string, number]>).filter(([, value]) => value > 0)
    : [];

  const copy = async () => {
    try {
      await navigator.clipboard?.writeText(plan.summary);
    } catch {
      // Some local or embedded browsers deny clipboard permission. The brief
      // remains visible and exportable; never let that permission block the plan.
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };
  const download = () => {
    const blob = new Blob([JSON.stringify(plan, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `glaciernet-case-${plan.caseId.replaceAll(/[^a-zA-Z0-9._-]/g, "_")}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const saveToOperations = async () => {
    if (!glacier || !candidate) return;
    setSaving(true);
    setHandoffMessage("");
    try {
      const result = await createRiskTwinHandoff({
        rgi_id: glacier.rgi_id,
        glacier_name: glacier.name_ru || glacier.name,
        lake_id: candidate.lake_id,
        inventory_year: candidate.inventory_year,
        previous_inventory_year: candidate.previous_inventory_year,
        latitude: candidate.latitude,
        longitude: candidate.longitude,
        area_current_m2: candidate.area_current_m2,
        area_previous_m2: candidate.area_previous_m2,
        area_change_percent: candidate.area_change_percent,
        geometric_match_distance_m: candidate.geometric_match_distance_m,
        distance_to_rgi_boundary_m: candidate.distance_to_rgi_boundary_m,
        observation_priority_0_100: candidate.observation_priority_0_100,
        flags: candidate.flags,
        action_summary: plan.summary,
      });
      setOperationsUrl(result.operations_url);
      setHandoffMessage(result.status === "created" ? "Кейс, наблюдение и задача инспекции сохранены в Operations." : "Этот кейс уже был сохранён; открыт существующий рабочий кейс.");
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Не удалось сохранить кейс.";
      setHandoffMessage(detail.includes("403") ? "Для сохранения войдите в проект под ролью analyst или admin. Карта и экспорт остаются доступны без входа." : detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section id="case-action-plan" aria-label="Case Action Plan" className="overflow-hidden rounded-3xl border border-cyan-200 bg-gradient-to-br from-cyan-50 via-white to-blue-50 shadow-[0_20px_50px_-32px_rgba(8,145,178,0.45)]">
      <div className="border-b border-cyan-100 bg-slate-950 p-5 text-white">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-200">Case Action Plan</p>
            <h2 className="mt-1 text-xl font-bold">Что сделать с этим объектом сейчас</h2>
            <p className="mt-2 max-w-3xl text-sm leading-5 text-slate-300">{plan.summary}</p>
          </div>
          <ClipboardCheck className="h-8 w-8 shrink-0 text-cyan-300" />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" onClick={() => void copy()} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-white/20 px-3 text-xs font-bold hover:bg-white/10"><Copy className="h-3.5 w-3.5" />{copied ? "Скопировано" : "Скопировать brief"}</button>
          <button type="button" onClick={download} className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-cyan-300 px-3 text-xs font-bold text-slate-950 hover:bg-cyan-200"><Download className="h-3.5 w-3.5" />Скачать JSON</button>
          <button type="button" onClick={() => void saveToOperations()} disabled={saving} className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-cyan-200 bg-cyan-700 px-3 text-xs font-bold text-white hover:bg-cyan-600 disabled:cursor-not-allowed disabled:opacity-60"><Upload className="h-3.5 w-3.5" />{saving ? "Сохраняем…" : "Сохранить в Operations"}</button>
        </div>
      </div>
      <div className="p-5">
        <div className="rounded-2xl border border-cyan-300 bg-cyan-50 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-900">Сначала сделайте</p>
          <h3 className="mt-1 text-lg font-bold text-slate-950">{plan.focus.headline}</h3>
          <ul className="mt-3 space-y-2 text-sm leading-5 text-slate-700">{plan.focus.reasons.map((reason) => <li key={reason} className="flex gap-2"><span className="font-bold text-cyan-800">•</span><span>{reason}</span></li>)}</ul>
          <p className="mt-3 rounded-xl bg-white p-3 text-xs text-emerald-950"><strong>Результат первого шага:</strong> {plan.focus.nextStep.acceptance}</p>
          <a href="#evidence-ledger" className="mt-3 inline-flex min-h-10 items-center rounded-xl bg-cyan-700 px-3 text-sm font-bold text-white transition hover:bg-cyan-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-700">Перейти к журналу доказательств</a>
        </div>
        <section aria-labelledby="case-decision-gates" className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-600">Decision gates</p><h3 id="case-decision-gates" className="mt-1 text-base font-bold text-slate-950">Что этот объект позволяет утверждать сейчас</h3></div><p className="text-xs text-slate-600">Статусы — не уровни опасности</p></div>
          <ul className="mt-3 grid gap-2 lg:grid-cols-2" aria-label="Статус доказательств кейса">{plan.decisionGates.map((gate) => { const meta = GATE_STYLE[gate.status]; const Icon = meta.icon; return <li key={gate.label} className={`rounded-xl border p-3 ${meta.className}`}><p className="flex items-center gap-1.5 text-xs font-bold"><Icon aria-hidden="true" className="h-3.5 w-3.5" />{meta.label}</p><h4 className="mt-1 text-sm font-bold">{gate.label}</h4><p className="mt-1 text-xs leading-5">{gate.detail}</p></li>; })}</ul>
        </section>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{plan.facts.map((fact) => <div key={fact.label} className="rounded-xl border border-cyan-100 bg-white p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-cyan-800">{fact.label}</p><p className="mt-1 text-sm font-bold text-slate-900">{fact.value}</p></div>)}</div>
        {priorityComponents && <section aria-labelledby="case-priority-breakdown" className="mt-4 rounded-2xl border border-cyan-200 bg-cyan-50 p-4"><div className="flex flex-wrap items-baseline justify-between gap-2"><div><p className="text-xs font-bold uppercase tracking-[0.14em] text-cyan-900">Проверяемая формула очереди</p><h3 id="case-priority-breakdown" className="mt-1 text-base font-bold text-slate-950">Почему этому объекту назначен приоритет {candidate?.observation_priority_0_100.toFixed(0)}/100</h3></div><span className="text-xs font-semibold text-cyan-900">Сбор доказательств ≠ риск</span></div><div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{priorityDrivers.map(([label, value]) => <div key={label} className="rounded-xl bg-white p-3 text-sm"><p className="text-xs font-medium text-slate-600">{label}</p><p className="mt-1 font-bold text-slate-950">+{value.toFixed(0)} баллов</p></div>)}</div><p className="mt-3 text-xs leading-5 text-cyan-950">Базовый балл: {priorityComponents.base_follow_up.toFixed(0)}. Сумма до ограничения: {priorityComponents.total_before_cap.toFixed(0)}; итог ограничен шкалой 0–100. Это прозрачная очередность проверки инвентарных данных, не вероятность прорыва и не оценка последствий.</p></section>}
        <p className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm"><MapPin className="h-3.5 w-3.5 text-cyan-700" />{plan.coordinates}</p>
        <div className="mt-5 flex flex-wrap gap-2" role="tablist" aria-label="Роль пользователя">
          {AUDIENCES.map((item) => {
            const Icon = item.icon;
            return <button key={item.id} type="button" role="tab" aria-selected={audience === item.id} onClick={() => setAudience(item.id)} className={`inline-flex min-h-10 items-center gap-2 rounded-xl border px-3 text-sm font-bold ${audience === item.id ? "border-cyan-700 bg-cyan-700 text-white" : "border-slate-300 bg-white text-slate-700 hover:bg-cyan-50"}`}><Icon className="h-4 w-4" />{item.label}</button>;
          })}
        </div>
        <ol className="mt-4 space-y-3">{plan.actions[audience].map((step, index) => <li key={step.id} className="rounded-2xl border border-slate-200 bg-white p-4"><p className="text-xs font-bold text-cyan-800">ШАГ {index + 1}</p><h3 className="mt-1 font-bold text-slate-950">{step.title}</h3><p className="mt-2 text-sm leading-6 text-slate-700">{step.instruction}</p><div className="mt-3 grid gap-2 text-xs sm:grid-cols-2"><p className="rounded-lg bg-emerald-50 p-2.5 text-emerald-950"><strong>Готово, когда:</strong> {step.acceptance}</p><p className="rounded-lg bg-amber-50 p-2.5 text-amber-950"><strong>Стоп-условие:</strong> {step.blockedClaim}</p></div></li>)}</ol>
        <Guardrails items={plan.guardrails} />
        {handoffMessage && <p role="status" aria-live="polite" className="mt-4 rounded-xl border border-cyan-200 bg-cyan-50 p-3 text-sm font-medium text-cyan-950">{handoffMessage} {operationsUrl && <a href={operationsUrl} className="ml-1 underline underline-offset-2">Открыть Operations.</a>}</p>}
      </div>
    </section>
  );
}
