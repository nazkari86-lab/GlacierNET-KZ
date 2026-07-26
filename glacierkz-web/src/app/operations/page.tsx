"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  ClipboardCheck,
  Database,
  Download,
  FileCheck2,
  MapPin,
  RefreshCw,
  Satellite,
  Save,
  ShieldCheck,
  WifiOff,
} from "lucide-react";
import {
  createFieldReport,
  fetchOperationsDemo,
  fetchOperationsOverview,
  type FieldReportInput,
  type OperationsOverview,
} from "@/lib/api";
import { useI18n } from "@/lib/I18nProvider";

const copy = {
  en: {
    title: "Cryosphere Operations",
    subtitle:
      "Decide what to observe next, document field work, and keep an auditable evidence trail.",
    demo: "Synthetic shadow-mode demo — no operational or hazard claim",
    safety: "Priorities rank observations. They are not failure probabilities or official warnings.",
    inbox: "Observation inbox",
    queue: "Next Best Observation",
    tasks: "Inspection tasks",
    cases: "Evidence cases",
    assets: "Monitored objects",
    audit: "Audit chain",
    save: "Save offline draft",
    saved: "Draft saved on this device",
    export: "Export audit snapshot",
    refresh: "Refresh",
    field: "Field inspection draft",
    observer: "Observer",
    water: "Water level, m",
    notes: "Notes",
    signature: "Signature",
    task: "Assigned task",
    empty: "No operational records yet.",
    back: "Back to home",
  },
  ru: {
    title: "Cryosphere Operations",
    subtitle:
      "Определяйте следующее наблюдение, фиксируйте полевые работы и сохраняйте аудируемую цепочку доказательств.",
    demo: "Синтетическая shadow-mode демонстрация — без operational или hazard claims",
    safety:
      "Приоритеты ранжируют наблюдения. Это не вероятность прорыва и не официальное предупреждение.",
    inbox: "Входящие наблюдения",
    queue: "Следующее лучшее наблюдение",
    tasks: "Задачи осмотра",
    cases: "Evidence cases",
    assets: "Объекты мониторинга",
    audit: "Цепочка аудита",
    save: "Сохранить offline-черновик",
    saved: "Черновик сохранён на этом устройстве",
    export: "Экспортировать audit snapshot",
    refresh: "Обновить",
    field: "Черновик полевого осмотра",
    observer: "Специалист",
    water: "Уровень воды, м",
    notes: "Комментарии",
    signature: "Подпись",
    task: "Назначенная задача",
    empty: "Операционных записей пока нет.",
    back: "На главную",
  },
  kk: {
    title: "Cryosphere Operations",
    subtitle:
      "Келесі бақылауды таңдаңыз, далалық жұмысты тіркеңіз және аудиттелетін дәлелдер тізбегін сақтаңыз.",
    demo: "Синтетикалық shadow-mode демо — операциялық немесе қауіп туралы мәлімдеме емес",
    safety:
      "Басымдықтар бақылауларды реттейді. Олар бұзылу ықтималдығы немесе ресми ескерту емес.",
    inbox: "Бақылаулар кірісі",
    queue: "Келесі ең пайдалы бақылау",
    tasks: "Тексеру тапсырмалары",
    cases: "Дәлел істері",
    assets: "Бақыланатын нысандар",
    audit: "Аудит тізбегі",
    save: "Offline нобайды сақтау",
    saved: "Нобай осы құрылғыда сақталды",
    export: "Audit snapshot жүктеу",
    refresh: "Жаңарту",
    field: "Далалық тексеру нобайы",
    observer: "Маман",
    water: "Су деңгейі, м",
    notes: "Ескертпелер",
    signature: "Қолтаңба",
    task: "Тағайындалған тапсырма",
    empty: "Операциялық жазбалар әлі жоқ.",
    back: "Басты бетке",
  },
};

function percentage(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function downloadJson(name: string, value: unknown): void {
  const blob = new Blob([JSON.stringify(value, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

export default function OperationsPage() {
  const { locale } = useI18n();
  const text = copy[locale];
  const [data, setData] = useState<OperationsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [observer, setObserver] = useState("");
  const [waterLevel, setWaterLevel] = useState("");
  const [notes, setNotes] = useState("");
  const [signature, setSignature] = useState("");

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const live = await fetchOperationsOverview();
      const next =
        (live.counts.assets ?? 0) > 0 ? live : await fetchOperationsDemo();
      setData(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Operations API unavailable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const assetsById = useMemo(
    () => Object.fromEntries((data?.assets ?? []).map((asset) => [asset.id, asset])),
    [data]
  );
  const selectedTask = data?.inspection_tasks[0];
  const selectedAsset = selectedTask ? assetsById[selectedTask.asset_id] : undefined;

  const saveOffline = () => {
    if (!selectedTask || !selectedAsset) return;
    const draft: FieldReportInput = {
      task_id: selectedTask.id,
      asset_id: selectedAsset.id,
      observer,
      observed_at: new Date().toISOString(),
      latitude: selectedAsset.latitude,
      longitude: selectedAsset.longitude,
      measurements: { water_level_m: waterLevel ? Number(waterLevel) : null },
      checklist: { location_verified: true, shadow_mode: true },
      notes,
      attachment_manifest: [],
      signature,
      sync_status: "offline_draft",
    };
    localStorage.setItem("glaciernet-operations-field-draft", JSON.stringify(draft));
    setSaved(true);
  };

  const syncDraft = async () => {
    if (data?.demo_only) return;
    const raw = localStorage.getItem("glaciernet-operations-field-draft");
    if (!raw) return;
    const draft = JSON.parse(raw) as FieldReportInput;
    await createFieldReport({ ...draft, sync_status: "synced" });
    localStorage.removeItem("glaciernet-operations-field-draft");
    setSaved(false);
    await load();
  };

  return (
    <div className="min-h-screen bg-[#f3f7f5] text-slate-950">
      <header className="border-b border-emerald-950/10 bg-[#0d2923] text-white">
        <div className="mx-auto max-w-7xl px-4 py-5 sm:px-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <Link
                href="/"
                className="mb-3 inline-flex items-center gap-2 text-sm text-emerald-100 hover:text-white"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                {text.back}
              </Link>
              <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                {text.title}
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-emerald-50/80 sm:text-base">
                {text.subtitle}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void load()}
                className="inline-flex items-center gap-2 rounded-lg border border-white/20 px-3 py-2 text-sm hover:bg-white/10"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {text.refresh}
              </button>
              <button
                type="button"
                disabled={!data}
                onClick={() =>
                  data &&
                  downloadJson("glaciernet-operations-audit-snapshot.json", {
                    schema: "glaciernet-kz.operations-ui-snapshot.v1",
                    exported_at: new Date().toISOString(),
                    data,
                  })
                }
                className="inline-flex items-center gap-2 rounded-lg bg-[#c7f36b] px-3 py-2 text-sm font-semibold text-[#173126] hover:bg-[#d5fa87] disabled:opacity-50"
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                {text.export}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6">
        {data?.demo_only && (
          <div className="flex items-start gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
            <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">{text.demo}</p>
              <p className="mt-1">{text.safety}</p>
            </div>
          </div>
        )}

        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-red-800">
            {error}
          </div>
        )}

        <section aria-label="Operations summary" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <SummaryCard icon={Database} label={text.assets} value={data?.counts.assets ?? 0} />
          <SummaryCard icon={Satellite} label={text.inbox} value={data?.counts.observations ?? 0} />
          <SummaryCard
            icon={ClipboardCheck}
            label={text.tasks}
            value={data?.counts.inspection_tasks ?? 0}
          />
          <SummaryCard icon={FileCheck2} label={text.cases} value={data?.counts.evidence_cases ?? 0} />
        </section>

        {loading ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-500">
            {text.refresh}…
          </div>
        ) : (
          <div className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
            <div className="space-y-6">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                      {text.inbox}
                    </p>
                    <h2 className="mt-1 text-xl font-semibold">{text.queue}</h2>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-800">
                    {data?.observation_queue.length ?? 0} candidates
                  </span>
                </div>
                <div className="space-y-3">
                  {(data?.observation_queue ?? []).map((candidate, index) => {
                    const asset = assetsById[candidate.asset_id];
                    return (
                      <article
                        key={candidate.id}
                        className="grid gap-4 rounded-xl border border-slate-200 p-4 md:grid-cols-[auto_1fr_auto]"
                      >
                        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#173126] font-semibold text-white">
                          {index + 1}
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="font-semibold">{asset?.name ?? candidate.asset_id}</h3>
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-900">
                              {candidate.status}
                            </span>
                            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                              {candidate.evidence_tier}
                            </span>
                          </div>
                          <p className="mt-2 text-sm text-slate-600">{candidate.rationale}</p>
                          <p className="mt-2 font-mono text-xs text-emerald-800">
                            {candidate.next_action.replaceAll("_", " ")}
                          </p>
                        </div>
                        <div className="min-w-28 text-right">
                          <p className="text-2xl font-semibold">
                            {percentage(candidate.priority_score)}
                          </p>
                          <p className="text-xs text-slate-500">observation priority</p>
                          <p className="mt-2 text-xs text-slate-500">
                            shift: {candidate.domain_shift_status.replaceAll("_", " ")}
                          </p>
                        </div>
                      </article>
                    );
                  })}
                  {!data?.observation_queue.length && (
                    <p className="rounded-xl bg-slate-50 p-6 text-center text-slate-500">
                      {text.empty}
                    </p>
                  )}
                </div>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-semibold">{text.tasks}</h2>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {(data?.inspection_tasks ?? []).map((task) => (
                    <article key={task.id} className="rounded-xl bg-[#eef5f0] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm font-semibold">
                          {assetsById[task.asset_id]?.name ?? task.asset_id}
                        </span>
                        <span className="rounded-full bg-white px-2 py-1 text-xs">
                          {task.status}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-slate-600">{task.rationale}</p>
                      <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
                        <span>{task.action_type.replaceAll("_", " ")}</span>
                        <strong className="text-slate-900">{percentage(task.priority_score)}</strong>
                      </div>
                    </article>
                  ))}
                </div>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-semibold">{text.assets}</h2>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {(data?.assets ?? []).map((asset) => (
                    <article key={asset.id} className="rounded-xl border border-slate-200 p-4">
                      <div className="flex items-start gap-3">
                        <MapPin className="mt-0.5 h-5 w-5 text-emerald-700" aria-hidden="true" />
                        <div>
                          <h3 className="font-semibold">{asset.name}</h3>
                          <p className="mt-1 text-sm text-slate-500">
                            {asset.asset_type.replaceAll("_", " ")} · {asset.status}
                          </p>
                          <p className="mt-2 text-xs text-slate-500">
                            {asset.latitude.toFixed(3)}, {asset.longitude.toFixed(3)}
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            </div>

            <aside className="space-y-6">
              <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2">
                  <WifiOff className="h-5 w-5 text-emerald-700" aria-hidden="true" />
                  <h2 className="text-lg font-semibold">{text.field}</h2>
                </div>
                <p className="mt-2 text-sm text-slate-500">
                  Offline-first draft. Synchronisation requires an analyst account and a persisted task.
                </p>
                <div className="mt-5 space-y-4">
                  <label className="block text-sm font-medium">
                    {text.task}
                    <input
                      readOnly
                      value={selectedTask?.id ?? ""}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-slate-50 px-3 py-2 text-sm"
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    {text.observer}
                    <input
                      value={observer}
                      onChange={(event) => setObserver(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    {text.water}
                    <input
                      type="number"
                      inputMode="decimal"
                      value={waterLevel}
                      onChange={(event) => setWaterLevel(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    {text.notes}
                    <textarea
                      rows={4}
                      value={notes}
                      onChange={(event) => setNotes(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                    />
                  </label>
                  <label className="block text-sm font-medium">
                    {text.signature}
                    <input
                      value={signature}
                      onChange={(event) => setSignature(event.target.value)}
                      className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-100"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={saveOffline}
                    disabled={!selectedTask || !observer || !signature}
                    className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#173126] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#24483b] disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <Save className="h-4 w-4" aria-hidden="true" />
                    {text.save}
                  </button>
                  {saved && (
                    <div className="flex items-center gap-2 text-sm text-emerald-700">
                      <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                      {text.saved}
                    </div>
                  )}
                  {!data?.demo_only && saved && (
                    <button
                      type="button"
                      onClick={() => void syncDraft()}
                      className="w-full rounded-lg border border-emerald-700 px-4 py-2 text-sm font-semibold text-emerald-800"
                    >
                      Synchronise signed report
                    </button>
                  )}
                </div>
              </section>

              <section className="rounded-2xl bg-[#173126] p-5 text-white shadow-sm">
                <h2 className="text-lg font-semibold">{text.audit}</h2>
                <div className="mt-4 flex items-center gap-3">
                  <ShieldCheck className="h-8 w-8 text-[#c7f36b]" aria-hidden="true" />
                  <div>
                    <p className="font-semibold">
                      {data?.audit_chain.valid ? "SHA-256 chain valid" : "Chain unavailable"}
                    </p>
                    <p className="text-sm text-emerald-50/70">
                      {data?.audit_chain.events ?? 0} append-only events
                    </p>
                  </div>
                </div>
                <p className="mt-4 break-all font-mono text-[10px] text-emerald-100/70">
                  {data?.audit_chain.head_sha256 ?? "No persistent audit head in demo preview"}
                </p>
              </section>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}

function SummaryCard({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Database;
  label: string;
  value: number;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <span className="text-sm text-slate-500">{label}</span>
        <Icon className="h-5 w-5 text-emerald-700" aria-hidden="true" />
      </div>
      <p className="mt-3 text-3xl font-semibold">{value}</p>
    </div>
  );
}
