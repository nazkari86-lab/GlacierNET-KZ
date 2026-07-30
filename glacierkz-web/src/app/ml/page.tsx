"use client";

import dynamic from "next/dynamic";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Database,
  Download,
  Layers3,
  Loader2,
  MapPinned,
  Radar,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import {
  analyzeMlGlacier,
  fetchGlaciers,
  fetchMlCase,
  fetchMlReadiness,
  verifyMlTrainingDataset,
  type GlacierRecord,
  type MlEvidenceCase,
  type MlReadiness,
  type MlTrainingPipelineCheck,
} from "@/lib/api";
import { apiUrl } from "@/lib/utils";

const MlEvidenceMap = dynamic(() => import("@/components/MlEvidenceMap"), { ssr: false });
const TUYUKSU = "RGI2000-v7.0-G-13-33843";

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`;
}

function metricTone(priority: number) {
  if (priority >= 70) return "border-rose-200 bg-rose-50 text-rose-900";
  if (priority >= 45) return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-emerald-200 bg-emerald-50 text-emerald-900";
}

export default function MlWorkspacePage() {
  const [readiness, setReadiness] = useState<MlReadiness | null>(null);
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [selectedId, setSelectedId] = useState(TUYUKSU);
  const [year, setYear] = useState(2024);
  const [modelName, setModelName] = useState("temporal_s2_terrain_s1");
  const [useTta, setUseTta] = useState(true);
  const [evidence, setEvidence] = useState<MlEvidenceCase | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [verifyingPipeline, setVerifyingPipeline] = useState(false);
  const [pipelineCheck, setPipelineCheck] = useState<MlTrainingPipelineCheck | null>(null);
  const [pipelineError, setPipelineError] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const requestedRgi = query.get("rgi");
    const requestedYear = Number(query.get("year"));
    const requestedCase = query.get("case");
    Promise.all([fetchMlReadiness(), fetchGlaciers("", false, 1000)])
      .then(async ([ready, registry]) => {
        setReadiness(ready);
        setGlaciers(registry.glaciers);
        const initialRgi = requestedRgi && registry.glaciers.some((item) => item.rgi_id === requestedRgi)
          ? requestedRgi
          : registry.glaciers.some((item) => item.rgi_id === TUYUKSU)
            ? TUYUKSU
            : registry.glaciers[0]?.rgi_id ?? "";
        setSelectedId(initialRgi);
        const available = ready.years.filter((item) => item.compatible_models.length);
        const initialYear = available.some((item) => item.year === requestedYear)
          ? requestedYear
          : available.at(-1)?.year ?? 2024;
        setYear(initialYear);
        setModelName(
          ready.years.find((item) => item.year === initialYear)?.recommended_model
            ?? ready.recommended_model
            ?? "temporal_s2_terrain"
        );
        if (requestedCase) setEvidence(await fetchMlCase(requestedCase));
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "ML workspace could not be loaded"))
      .finally(() => setLoading(false));
  }, []);

  const selected = useMemo(
    () => glaciers.find((glacier) => glacier.rgi_id === selectedId) ?? null,
    [glaciers, selectedId]
  );
  const trainingDataset = readiness?.training_dataset;
  const priorityReviewCases = useMemo(() => {
    const seen = new Set<string>();
    return (trainingDataset?.review_queue ?? []).filter((item) => {
      if (seen.has(item.glacier_id)) return false;
      seen.add(item.glacier_id);
      return true;
    }).slice(0, 4);
  }, [trainingDataset]);
  const selectedDatasetSplit = selectedId ? trainingDataset?.membership[selectedId] : undefined;
  const yearStatus = readiness?.years.find((item) => item.year === year);
  const compatibleModels = readiness?.models.filter(
    (model) => yearStatus?.compatible_models.includes(model.name)
  ) ?? [];
  const currentModel = readiness?.models.find((model) => model.name === modelName) ?? compatibleModels[0];

  const selectYear = (nextYear: number) => {
    setYear(nextYear);
    const recommended = readiness?.years.find((item) => item.year === nextYear)?.recommended_model;
    if (recommended) setModelName(recommended);
    setEvidence(null);
  };

  const verifyPipeline = async (refresh = false) => {
    setVerifyingPipeline(true);
    setPipelineError("");
    try {
      setPipelineCheck(await verifyMlTrainingDataset(refresh));
    } catch (cause) {
      setPipelineError(cause instanceof Error ? cause.message : "Weighted pipeline check failed");
    } finally {
      setVerifyingPipeline(false);
    }
  };

  const openReviewCase = (glacierId: string, reviewYear: number) => {
    if (glaciers.some((item) => item.rgi_id === glacierId)) setSelectedId(glacierId);
    selectYear(reviewYear);
    document.getElementById("observation-target")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const run = async (refresh = false) => {
    if (!selectedId || !modelName) return;
    setRunning(true);
    setError("");
    try {
      const result = await analyzeMlGlacier(selectedId, {
        year,
        model_name: modelName,
        use_tta: useTta,
        context_m: 400,
        refresh,
      });
      setEvidence(result);
      const url = new URL(window.location.href);
      url.searchParams.set("rgi", selectedId);
      url.searchParams.set("year", String(year));
      url.searchParams.set("case", result.case_id);
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Inference failed");
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center gap-3 bg-slate-950 text-white">
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
        Loading the verified ML stack…
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[#f4f7fb] text-slate-950">
      <header className="border-b border-slate-800 bg-slate-950 text-white">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <Link href="/" aria-label="Back" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white">
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div className="rounded-xl bg-cyan-400/10 p-2 text-cyan-300"><BrainCircuit className="h-6 w-6" /></div>
            <div>
              <p className="font-semibold tracking-tight">GlacierNET-KZ · ML Workspace</p>
              <p className="text-xs text-slate-400">Real glacier · real year · traceable model evidence</p>
            </div>
          </div>
          <div className="flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1.5 text-xs font-medium text-emerald-300">
            <CheckCircle2 className="h-4 w-4" />
            {readiness?.status === "ready" ? "Verified local stack ready" : "ML stack blocked"}
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-[1500px] space-y-5 px-4 py-6 sm:px-6">
        <section className="overflow-hidden rounded-3xl bg-slate-950 text-white shadow-xl">
          <div className="grid gap-8 px-6 py-8 lg:grid-cols-[1.3fr_0.7fr] lg:px-10">
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.18em] text-cyan-300">
                <Sparkles className="h-4 w-4" /> Main intelligence layer
              </p>
              <h1 className="mt-4 max-w-4xl text-3xl font-bold tracking-tight sm:text-5xl">
                От спутникового композита до проверяемой границы конкретного ледника.
              </h1>
              <p className="mt-4 max-w-3xl text-base leading-7 text-slate-300">
                Система сама вырезает выбранный объект, совмещает Sentinel‑2, рельеф и SAR,
                запускает temporal holdout модель и показывает, где результат надёжен, а где его нужно проверить.
              </p>
            </div>
            <div className="grid gap-3 self-end text-sm sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-slate-400">Best measured hard Dice</p>
                <p className="mt-2 text-3xl font-bold text-cyan-300">
                  {currentModel?.benchmark.hard_dice ? currentModel.benchmark.hard_dice.toFixed(3) : "—"}
                </p>
                <p className="mt-1 text-xs text-slate-500">2024 temporal holdout · silver labels</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-slate-400">Physical local years</p>
                <p className="mt-2 text-3xl font-bold text-white">
                  {readiness?.years.filter((item) => item.compatible_models.length).length ?? 0}
                </p>
                <p className="mt-1 text-xs text-slate-500">2016–2024 model-compatible</p>
              </div>
              <div className="rounded-2xl border border-violet-400/20 bg-violet-400/10 p-4">
                <p className="text-violet-200">External failure containment</p>
                <p className="mt-2 text-3xl font-bold text-violet-300">
                  {readiness?.generalisation_sentinel.paired_dice_delta
                    ? `+${readiness.generalisation_sentinel.paired_dice_delta.toFixed(3)}`
                    : "—"}
                </p>
                <p className="mt-1 text-xs text-violet-200/60">paired Dice · provisional safeguard</p>
              </div>
            </div>
          </div>
        </section>

        {error && (
          <div role="alert" className="flex gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
            <AlertTriangle className="h-5 w-5 shrink-0" />{error}
          </div>
        )}

        <section id="training-data" className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
            <div className="p-6 sm:p-8">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-700">Training evidence · integrated</p>
                  <h2 className="mt-2 text-2xl font-bold">Leakage-safe weighted annotations</h2>
                </div>
                <span className={`rounded-full px-3 py-1.5 text-xs font-semibold ${
                  trainingDataset?.status === "ready"
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-rose-100 text-rose-800"
                }`}>
                  {trainingDataset?.status === "ready" ? "Validated local dataset" : "Dataset blocked"}
                </span>
              </div>

              {trainingDataset?.status === "ready" ? (
                <>
                  <p className="mt-4 text-sm leading-6 text-slate-600">
                    Используются только high-provisional границы. Все годы одного ледника закреплены
                    за одним split, а спорные и недействительные пиксели получают пониженный вес.
                  </p>
                  <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      ["Patches", trainingDataset.patch_count ?? 0],
                      ["High tasks", trainingDataset.eligible_tasks ?? 0],
                      ["Coverage", `${((trainingDataset.minimum_geometry_coverage ?? 0) * 100).toFixed(0)}%`],
                      ["Review queue", trainingDataset.excluded_tasks?.total ?? 0],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-2xl bg-slate-50 p-3">
                        <p className="text-xs text-slate-500">{label}</p>
                        <p className="mt-1 text-xl font-bold">{value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5 grid grid-cols-3 gap-2">
                    {(["train", "val", "test"] as const).map((split) => {
                      const value = trainingDataset.splits[split];
                      return (
                        <div key={split} className="rounded-2xl border border-slate-200 p-3">
                          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{split}</p>
                          <p className="mt-1 text-2xl font-bold">{value?.patch_count ?? 0}</p>
                          <p className="text-xs text-slate-500">{value?.glacier_count ?? 0} glaciers · 2022–2024</p>
                        </div>
                      );
                    })}
                  </div>
                  {trainingDataset.spatial_evaluation?.status === "completed_provisional_not_gold" && (
                    <div className="mt-5 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-bold text-emerald-950">Completed glacier-disjoint training run</p>
                          <p className="mt-1 text-xs leading-5 text-emerald-900">
                            Validation selected the threshold; the untouched test contains{" "}
                            {trainingDataset.spatial_evaluation.glacier_counts?.test ?? 0} different glaciers.
                          </p>
                        </div>
                        <span className="rounded-full bg-white px-3 py-1 text-xs font-bold text-emerald-800">
                          {trainingDataset.spatial_evaluation.epochs_completed}/
                          {trainingDataset.spatial_evaluation.epochs_requested} epochs · early stop
                        </span>
                      </div>
                      <dl className="mt-4 grid gap-2 sm:grid-cols-3">
                        <div className="rounded-xl bg-white p-3">
                          <dt className="text-xs text-slate-500">Test hard Dice</dt>
                          <dd className="mt-1 text-xl font-bold text-slate-950">
                            {trainingDataset.spatial_evaluation.candidate_test?.hard_dice?.toFixed(3) ?? "—"}
                          </dd>
                        </div>
                        <div className="rounded-xl bg-white p-3">
                          <dt className="text-xs text-slate-500">Test hard IoU</dt>
                          <dd className="mt-1 text-xl font-bold text-slate-950">
                            {trainingDataset.spatial_evaluation.candidate_test?.hard_iou?.toFixed(3) ?? "—"}
                          </dd>
                        </div>
                        <div className="rounded-xl bg-white p-3">
                          <dt className="text-xs text-slate-500">IoU vs frozen baseline</dt>
                          <dd className="mt-1 text-xl font-bold text-emerald-700">
                            +{trainingDataset.spatial_evaluation.candidate_minus_baseline_hard_iou?.toFixed(3) ?? "—"}
                          </dd>
                        </div>
                      </dl>
                      <p className="mt-3 text-xs leading-5 text-emerald-950">
                        Internal provisional evidence only: two test glaciers are insufficient for a claim-grade
                        confidence interval or external-regional accuracy.
                      </p>
                    </div>
                  )}
                  <div className="mt-5 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
                    <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                    <p>
                      Это сильный development dataset, но не независимый gold benchmark.
                      Medium/low разметки не подмешиваются в обучение и остаются в очереди проверки.
                    </p>
                  </div>
                  {!!priorityReviewCases.length && (
                    <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-50">
                      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold">
                        Highest-priority annotation reviews
                      </summary>
                      <div className="space-y-2 border-t border-slate-200 p-3">
                        {priorityReviewCases.map((item) => (
                          <button
                            key={`${item.glacier_id}-${item.year}`}
                            type="button"
                            onClick={() => openReviewCase(item.glacier_id, item.year)}
                            className="flex w-full items-start justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 text-left hover:border-cyan-400 hover:bg-cyan-50"
                          >
                            <span>
                              <strong className="block text-xs text-slate-900">
                                {item.glacier_id.split("-").at(-1)} · {item.year}
                              </strong>
                              <span className="mt-1 block text-xs leading-5 text-slate-500">{item.next_action}</span>
                            </span>
                            <span className="rounded-full bg-rose-100 px-2 py-1 text-xs font-bold text-rose-800">
                              {item.review_priority}
                            </span>
                          </button>
                        ))}
                      </div>
                    </details>
                  )}
                  <a
                    href={apiUrl(trainingDataset.manifest_url)}
                    className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 px-4 text-sm font-semibold hover:border-cyan-500 hover:bg-cyan-50"
                  >
                    <Download className="h-4 w-4" /> Open dataset manifest
                  </a>
                  {trainingDataset.training_command && (
                    <details className="mt-4 rounded-2xl border border-slate-200 bg-slate-950 text-white">
                      <summary className="cursor-pointer px-4 py-3 text-sm font-semibold text-cyan-300">
                        Real weighted training command
                      </summary>
                      <code className="block overflow-x-auto border-t border-white/10 px-4 py-3 text-xs leading-6 text-slate-300">
                        {trainingDataset.training_command}
                      </code>
                    </details>
                  )}
                  <div className="mt-4 rounded-2xl border border-cyan-200 bg-cyan-50 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-bold text-cyan-950">Real weighted TensorFlow check</p>
                        <p className="mt-1 text-xs leading-5 text-cyan-900">
                          Executes one bounded optimization batch. It verifies the pipeline, not model accuracy.
                        </p>
                      </div>
                      <button
                        type="button"
                        disabled={verifyingPipeline}
                        onClick={() => verifyPipeline(Boolean(pipelineCheck))}
                        className="inline-flex min-h-10 items-center gap-2 rounded-xl bg-cyan-700 px-4 text-sm font-semibold text-white hover:bg-cyan-800 disabled:opacity-60"
                      >
                        {verifyingPipeline
                          ? <><Loader2 className="h-4 w-4 animate-spin" /> Running real batch…</>
                          : pipelineCheck
                            ? <><RefreshCw className="h-4 w-4" /> Re-run real batch</>
                            : <><ShieldCheck className="h-4 w-4" /> Verify weighted pipeline</>}
                      </button>
                    </div>
                    {pipelineError && <p role="alert" className="mt-3 text-xs font-medium text-rose-800">{pipelineError}</p>}
                    {pipelineCheck && (
                      <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
                        <div className="rounded-xl bg-white p-3">
                          <span className="text-slate-500">Status</span>
                          <strong className="mt-1 block text-emerald-700">Verified {pipelineCheck.cache.hit ? "· cache" : "· fresh"}</strong>
                        </div>
                        <div className="rounded-xl bg-white p-3">
                          <span className="text-slate-500">Runtime</span>
                          <strong className="mt-1 block">{pipelineCheck.runtime.duration_seconds.toFixed(2)} s · TF {pipelineCheck.runtime.tensorflow}</strong>
                        </div>
                        <div className="rounded-xl bg-white p-3">
                          <span className="text-slate-500">Weighted batch</span>
                          <strong className="mt-1 block">{pipelineCheck.batch.features.join("×")}</strong>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <div role="alert" className="mt-5 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
                  {trainingDataset?.reason ?? "Training dataset is not available in this deployment."}
                </div>
              )}
            </div>
            <div className="self-start border-t border-slate-200 bg-slate-950 p-3 lg:border-l lg:border-t-0">
              {trainingDataset?.preview_url ? (
                <a href={apiUrl(trainingDataset.preview_url)} target="_blank" rel="noreferrer" className="block">
                  {/* Fixed local API artifact; no user-controlled URL is accepted here. */}
                  <Image
                    src={apiUrl(trainingDataset.preview_url)}
                    alt="Sentinel-2 patches, provisional glacier outlines, and pixel reliability maps for train, validation, and test"
                    width={2040}
                    height={2040}
                    sizes="(min-width: 1024px) 55vw, 100vw"
                    priority
                    unoptimized
                    className="max-h-[720px] w-full rounded-2xl object-contain"
                  />
                </a>
              ) : (
                <div className="grid h-full min-h-[340px] place-items-center text-sm text-slate-400">QA preview unavailable</div>
              )}
            </div>
          </div>
        </section>

        <section id="observation-target" className="grid scroll-mt-4 gap-5 xl:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="h-fit space-y-4 rounded-3xl border border-slate-200 bg-white p-5 shadow-sm xl:sticky xl:top-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">1 · Observation target</p>
              <label className="mt-3 block text-sm font-semibold" htmlFor="ml-glacier">Glacier</label>
              <select
                id="ml-glacier"
                value={selectedId}
                onChange={(event) => { setSelectedId(event.target.value); setEvidence(null); }}
                className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm"
              >
                {glaciers.map((glacier) => (
                  <option key={glacier.rgi_id} value={glacier.rgi_id}>
                    {glacier.name_ru} · {glacier.rgi_area_km2.toFixed(2)} km²
                  </option>
                ))}
              </select>
              {selected && (
                <div className="mt-3 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-600">
                  <strong className="text-slate-900">{selected.rgi_id}</strong><br />
                  {selected.centroid.latitude.toFixed(5)}, {selected.centroid.longitude.toFixed(5)}
                  <br />RGI area: {selected.rgi_area_km2.toFixed(4)} km²
                  <div className={`mt-2 rounded-lg px-2 py-1.5 font-semibold ${
                    selectedDatasetSplit
                      ? "bg-cyan-100 text-cyan-900"
                      : "bg-slate-200 text-slate-700"
                  }`}>
                    {selectedDatasetSplit
                      ? `Training dataset role: ${selectedDatasetSplit.toUpperCase()}`
                      : "Not used as provisional training truth"}
                  </div>
                </div>
              )}
            </div>

            <div className="border-t border-slate-100 pt-4">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">2 · Local year</p>
              <div className="mt-3 grid grid-cols-3 gap-2">
                {readiness?.years.filter((item) => item.compatible_models.length).map((item) => (
                  <button
                    key={item.year}
                    type="button"
                    onClick={() => selectYear(item.year)}
                    className={`rounded-xl border px-2 py-2 text-sm font-semibold ${
                      year === item.year
                        ? "border-cyan-600 bg-cyan-50 text-cyan-900"
                        : "border-slate-200 hover:border-cyan-300"
                    }`}
                  >
                    {item.year}
                  </button>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                <span className="rounded-full bg-blue-50 px-2 py-1 text-[11px] text-blue-800">Sentinel‑2</span>
                <span className="rounded-full bg-amber-50 px-2 py-1 text-[11px] text-amber-800">Terrain</span>
                {yearStatus?.sentinel1 && <span className="rounded-full bg-violet-50 px-2 py-1 text-[11px] text-violet-800">Sentinel‑1 SAR</span>}
              </div>
            </div>

            <div className="border-t border-slate-100 pt-4">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">3 · Model contract</p>
              <select
                value={modelName}
                onChange={(event) => { setModelName(event.target.value); setEvidence(null); }}
                className="mt-3 w-full rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm"
              >
                {compatibleModels.map((model) => (
                  <option key={model.name} value={model.name}>{model.display_name}</option>
                ))}
              </select>
              <label className="mt-3 flex items-center justify-between rounded-xl border border-slate-200 p-3 text-sm">
                <span><strong>Flip TTA ×4</strong><br /><span className="text-xs text-slate-500">Measured validation gain</span></span>
                <input type="checkbox" checked={useTta} onChange={(event) => setUseTta(event.target.checked)} />
              </label>
            </div>

            <button
              type="button"
              disabled={running || !selectedId || !modelName}
              onClick={() => run(false)}
              className="flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl bg-cyan-600 px-4 font-bold text-white shadow-lg shadow-cyan-600/20 hover:bg-cyan-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {running ? <><Loader2 className="h-5 w-5 animate-spin" /> Running geospatial ML…</> : <><Radar className="h-5 w-5" /> Analyze glacier</>}
            </button>
            {running && <p className="text-center text-xs leading-5 text-slate-500">Cold inference is usually 20–40 s. Repeated cases use the verified cache.</p>}
          </aside>

          <div className="min-w-0 space-y-5">
            {!evidence ? (
              <section className="grid min-h-[610px] place-items-center rounded-3xl border border-dashed border-slate-300 bg-white p-8 text-center">
                <div className="max-w-xl">
                  <div className="mx-auto grid h-20 w-20 place-items-center rounded-3xl bg-cyan-50 text-cyan-700"><Layers3 className="h-10 w-10" /></div>
                  <h2 className="mt-5 text-2xl font-bold">Один запуск — полный доказательный ML-кейс</h2>
                  <p className="mt-3 leading-7 text-slate-600">
                    На карте появятся RGI и новая ML‑граница. Отдельные слои вероятности и entropy
                    покажут не только ответ модели, но и где именно ей нельзя слепо доверять.
                  </p>
                  <div className="mt-6 grid gap-3 text-left sm:grid-cols-3">
                    {[
                      ["01", "Geographic crop", "Только выбранный ледник и контекст"],
                      ["02", "16-channel inference", "S2 + indices + terrain + SAR"],
                      ["03", "Evidence package", "Hash, метрики, слои и ограничения"],
                    ].map(([number, title, body]) => (
                      <div key={number} className="rounded-2xl border border-slate-200 p-4">
                        <span className="text-xs font-bold text-cyan-700">{number}</span>
                        <p className="mt-2 font-semibold">{title}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-500">{body}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            ) : (
              <>
                <section className="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3 px-3 py-3">
                    <div>
                      <p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-700">Model evidence map</p>
                      <h2 className="mt-1 text-xl font-bold">{evidence.glacier.name_ru} · {evidence.year}</h2>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="rounded-full bg-slate-100 px-3 py-1.5 text-xs text-slate-600">
                        {evidence.cache.hit ? "Verified cache" : `${evidence.inference.duration_seconds.toFixed(1)} s inference`}
                      </span>
                      <button type="button" onClick={() => run(true)} disabled={running} className="rounded-lg border border-slate-200 p-2 hover:bg-slate-50" aria-label="Rerun inference">
                        <RefreshCw className={`h-4 w-4 ${running ? "animate-spin" : ""}`} />
                      </button>
                    </div>
                  </div>
                  <MlEvidenceMap evidence={evidence} />
                </section>

                <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-xs text-slate-500">ML area · selected component</p>
                    <p className="mt-2 text-2xl font-bold">{evidence.metrics.predicted_area_km2.toFixed(4)} km²</p>
                    <p className="mt-1 text-xs text-slate-500">{evidence.metrics.area_delta_percent?.toFixed(2)}% vs rasterized RGI</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-xs text-slate-500">RGI agreement · not accuracy</p>
                    <p className="mt-2 text-2xl font-bold">{percent(evidence.metrics.rgi_overlap_iou)}</p>
                    <p className="mt-1 text-xs text-slate-500">Intersection over union</p>
                  </div>
                  <div className="rounded-2xl border border-slate-200 bg-white p-4">
                    <p className="text-xs text-slate-500">Uncertain review zone</p>
                    <p className="mt-2 text-2xl font-bold">{percent(evidence.metrics.uncertain_fraction_in_review_zone)}</p>
                    <p className="mt-1 text-xs text-slate-500">Entropy &gt; 0.65 nats</p>
                  </div>
                  <div className={`rounded-2xl border p-4 ${metricTone(evidence.metrics.review_priority_0_100)}`}>
                    <p className="text-xs opacity-70">Review priority</p>
                    <p className="mt-2 text-2xl font-bold">{evidence.metrics.review_priority_0_100}/100</p>
                    <p className="mt-1 text-xs opacity-70">Disagreement + uncertainty</p>
                  </div>
                  <div className="rounded-2xl border border-violet-200 bg-violet-50 p-4 text-violet-950">
                    <p className="text-xs text-violet-700">Generalisation Sentinel area</p>
                    <p className="mt-2 text-2xl font-bold">{evidence.metrics.inventory_guided_area_km2.toFixed(4)} km²</p>
                    <p className="mt-1 text-xs text-violet-700">{evidence.metrics.inventory_guided_area_delta_percent?.toFixed(2)}% vs RGI · safeguard</p>
                  </div>
                </section>

                <section className="rounded-3xl border border-violet-200 bg-violet-50 p-5 text-violet-950">
                  <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-700">Generalisation Sentinel</p><h2 className="mt-1 font-bold">Physics-constrained candidate for this exact glacier</h2></div><span className="rounded-full bg-white px-3 py-1 text-xs font-bold">NDSI ≥ {evidence.inventory_guided_decoder.config.ndsi_threshold} · {evidence.inventory_guided_decoder.config.support_buffer_m} m support</span></div>
                  <p className="mt-3 text-sm leading-6">{evidence.inventory_guided_decoder.circular_validation_warning}</p>
                </section>

                <section className="grid gap-5 lg:grid-cols-[1fr_0.9fr]">
                  <div className="rounded-3xl border border-slate-200 bg-white p-6">
                    <div className="flex items-start gap-3">
                      <MapPinned className="mt-0.5 h-5 w-5 text-cyan-700" />
                      <div>
                        <h2 className="font-bold">Что сделать с этим результатом</h2>
                        <p className="mt-2 text-sm leading-6 text-slate-600">{evidence.review.next_action}</p>
                      </div>
                    </div>
                    <Link
                      href={evidence.review.risk_twin_url}
                      className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white hover:bg-slate-800"
                    >
                      Open same case in Risk Twin <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                  <div className="rounded-3xl border border-slate-200 bg-white p-6">
                    <h2 className="flex items-center gap-2 font-bold"><Database className="h-5 w-5 text-cyan-700" /> Evidence package</h2>
                    <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                      {[
                        ["Mask GeoTIFF", "selected_mask_url"],
                        ["Safeguarded mask", "inventory_guided_mask_url"],
                        ["Probability", "probability_url"],
                        ["Entropy", "entropy_url"],
                        ["Boundary GeoJSON", "boundary_url"],
                        ["Audit manifest", "manifest_url"],
                      ].map(([label, key]) => evidence.artifacts[key] && (
                        <a key={key} href={apiUrl(evidence.artifacts[key] ?? "")} className="flex items-center justify-between rounded-xl border border-slate-200 px-3 py-2.5 hover:border-cyan-400 hover:bg-cyan-50">
                          {label}<Download className="h-3.5 w-3.5" />
                        </a>
                      ))}
                    </div>
                  </div>
                </section>

                <section className="grid gap-4 rounded-3xl border border-slate-200 bg-white p-6 lg:grid-cols-2">
                  <div>
                    <h2 className="flex items-center gap-2 font-bold text-emerald-800"><ShieldCheck className="h-5 w-5" /> What this case supports</h2>
                    <ul className="mt-3 space-y-2 text-sm text-slate-600">
                      {evidence.claims_allowed.map((claim) => <li key={claim} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{claim}</li>)}
                    </ul>
                  </div>
                  <div>
                    <h2 className="flex items-center gap-2 font-bold text-amber-900"><AlertTriangle className="h-5 w-5" /> What still needs validation</h2>
                    <ul className="mt-3 space-y-2 text-sm text-slate-600">
                      {evidence.claims_not_allowed.map((claim) => <li key={claim} className="flex gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />{claim}</li>)}
                    </ul>
                  </div>
                  <div className="border-t border-slate-100 pt-4 text-xs leading-5 text-slate-500 lg:col-span-2">
                    <div className="flex flex-wrap gap-x-6 gap-y-1">
                      <span className="flex items-center gap-1"><Clock3 className="h-3.5 w-3.5" />{evidence.inference.variant} · threshold {evidence.inference.decision_threshold}</span>
                      <span>{evidence.inference.window_shape.join("×")} px · {evidence.inference.feature_schema.length} channels</span>
                      <span className="font-mono">crop sha256 {evidence.source.source_crop_sha256.slice(0, 16)}…</span>
                    </div>
                  </div>
                </section>
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
