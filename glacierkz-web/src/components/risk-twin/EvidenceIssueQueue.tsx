"use client";

import type { EvidenceIssue } from "@/lib/riskTwinEvidence";

interface EvidenceIssueQueueProps {
  issues: EvidenceIssue[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const impactLabel: Record<EvidenceIssue["decisionImpact"], string> = { high: "высокое", medium: "среднее", low: "низкое" };
const impactClass: Record<EvidenceIssue["decisionImpact"], string> = {
  high: "border-red-200 bg-red-50 text-red-900",
  medium: "border-amber-200 bg-amber-50 text-amber-950",
  low: "border-cyan-200 bg-cyan-50 text-cyan-950",
};
const impactOrder: Record<EvidenceIssue["decisionImpact"], number> = { high: 0, medium: 1, low: 2 };

export default function EvidenceIssueQueue({ issues, selectedId, onSelect }: EvidenceIssueQueueProps) {
  const orderedIssues = [...issues].sort((left, right) => impactOrder[left.decisionImpact] - impactOrder[right.decisionImpact]);
  return (
    <section aria-labelledby="evidence-issue-queue-title" className="rounded-2xl border border-slate-700 bg-slate-950 p-4 text-white shadow-sm">
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-cyan-200">Очередь проверок</p>
      <h2 id="evidence-issue-queue-title" className="mt-1 text-lg font-bold">Что может изменить решение</h2>
      {orderedIssues.length === 0 ? <p className="mt-3 rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3 text-sm text-emerald-100">Все обязательные переменные представлены в текущем ledger. Сохраняйте проверку происхождения данных.</p> : (
        <ol className="mt-3 space-y-2">
          {orderedIssues.map((issue) => <li key={issue.id}>
            <button type="button" aria-pressed={issue.id === selectedId} onClick={() => onSelect(issue.id)} className={`w-full rounded-xl border p-3 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-200 ${impactClass[issue.decisionImpact]} ${issue.id === selectedId ? "ring-2 ring-cyan-300 ring-offset-2 ring-offset-slate-950" : "hover:-translate-y-0.5"}`}>
              <span className="text-[10px] font-bold uppercase tracking-wider">Влияние на решение: {impactLabel[issue.decisionImpact]}</span>
              <strong className="mt-1 block text-sm">{issue.title}</strong>
              <span className="mt-1 block text-xs leading-5 opacity-90">{issue.rationale}</span>
              <span className="mt-2 block border-t border-current/15 pt-2 text-xs font-semibold">Следующее действие: {issue.nextAction}</span>
            </button>
          </li>)}
        </ol>
      )}
    </section>
  );
}
