"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { ArrowLeft, Mountain, Loader2, Download, FlaskConical, ArrowRight } from "lucide-react";
import UploadZone from "@/components/UploadZone";
import ModelSelector from "@/components/ModelSelector";
import ErrorBoundary from "@/components/ErrorBoundary";
import dynamic from "next/dynamic";
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });
import { fetchModels, predict, getStaticUrl, ModelInfo, PredictResult } from "@/lib/api";
import { apiUrl, cn } from "@/lib/utils";
import { useI18n } from "@/lib/I18nProvider";

export default function PredictPage() {
  const { t } = useI18n();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [useTta, setUseTta] = useState(false);
  const [useCrf, setUseCrf] = useState(false);
  const [year, setYear] = useState(2024);
  const [ndsiThreshold, setNdsiThreshold] = useState(0.4);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResult | null>(null);

  useEffect(() => {
    fetchModels().then((m) => {
      setModels(m);
      if (m.length > 0) {
        setSelectedModel(m[0].name);
        setUseTta(Boolean(m[0].supports_tta));
      }
    });
  }, []);

  const handlePredict = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const selected = models.find((model) => model.name === selectedModel);
      const r = await predict(
        file,
        selectedModel,
        useTta,
        useCrf,
        ndsiThreshold,
        selected?.channel_count === 16 ? year : undefined,
      );
      setResult(r);
    } catch (e) {
      setResult({ task_id: "", status: "failed", error: String(e) });
    } finally {
      setLoading(false);
    }
  };
  const selectedSpec = models.find((model) => model.name === selectedModel);

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <Link href="/" className="text-zinc-400 hover:text-zinc-600" aria-label={t("nav.back")}>
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Mountain className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <span className="font-bold">{t("predict.title")}</span>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">{t("predict.title")}</h1>
        <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="flex items-center gap-2 font-semibold text-emerald-950">
                <FlaskConical className="h-5 w-5" aria-hidden="true" />
                {t("predict.try_example_title")}
              </h2>
              <p className="mt-1 max-w-3xl text-sm text-emerald-900">{t("predict.try_example_desc")}</p>
            </div>
            <Link
              href="/ml"
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
            >
              {t("predict.try_example_button")}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </section>
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step1")}</h2>
            <UploadZone onFileSelected={setFile} disabled={loading} />
            <p className="mt-3 text-sm text-zinc-500">{t("predict.upload_hint")}</p>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step2")}</h2>
            <ModelSelector
              models={models}
              selectedModel={selectedModel}
              onSelect={(name) => {
                const next = models.find((model) => model.name === name);
                setSelectedModel(name);
                setUseTta(Boolean(next?.supports_tta));
                setUseCrf(false);
              }}
            />
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step3")}</h2>
            <div className="flex flex-wrap gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={useTta}
                  onChange={(e) => setUseTta(e.target.checked)}
                  disabled={!selectedSpec?.supports_tta}
                  className="rounded"
                />
                <span className="text-sm">{t("predict.tta")}</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={useCrf}
                  onChange={(e) => setUseCrf(e.target.checked)}
                  disabled={!selectedSpec?.supports_crf}
                  className="rounded"
                />
                <span className="text-sm">{t("predict.crf")}</span>
              </label>
              {selectedModel === "ndsi" && (
                <label className="flex items-center gap-2">
                  <span className="text-sm">{t("predict.ndsi_threshold")}</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={ndsiThreshold}
                    onChange={(e) => setNdsiThreshold(parseFloat(e.target.value))}
                    className="w-24"
                    aria-label={t("predict.ndsi_threshold")}
                  />
                  <span className="text-sm font-mono">{ndsiThreshold}</span>
                </label>
              )}
              {selectedSpec?.channel_count === 16 && (
                <label className="flex items-center gap-2">
                  <span className="text-sm">Observation year</span>
                  <select
                    value={year}
                    onChange={(event) => setYear(Number(event.target.value))}
                    className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm"
                    aria-label="Observation year for Sentinel-1 composite"
                  >
                    {Array.from({ length: 8 }, (_, index) => 2024 - index).map((value) => (
                      <option key={value} value={value}>{value}</option>
                    ))}
                  </select>
                </label>
              )}
            </div>
            {selectedSpec?.feature_schema && (
              <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-3 text-xs text-zinc-600">
                <div className="font-semibold text-zinc-800">
                  Exact input contract · {selectedSpec.channel_count} channels · {selectedSpec.evidence_tier}
                </div>
                <div className="mt-1">{selectedSpec.feature_schema.join(" · ")}</div>
              </div>
            )}
          </section>
        </ErrorBoundary>

        <button
          onClick={handlePredict}
          disabled={!file || loading}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl py-3 text-white transition-colors",
            loading ? "bg-blue-400" : "bg-blue-600 hover:bg-blue-700",
            (!file || loading) && "cursor-not-allowed"
          )}
          aria-busy={loading}
        >
          {loading && <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />}
          {loading ? t("predict.processing") : t("predict.run")}
        </button>

        {result && (
          <section className="rounded-xl bg-white p-6 shadow-sm" role="status" aria-live="polite">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.result")}</h2>
            {result.status === "failed" ? (
              <p className="text-red-600">{t("predict.error")}: {result.error}</p>
            ) : (
              <div className="space-y-4">
                {result.area_km2 !== undefined && (
                  <div className="rounded-lg bg-blue-50 p-4 text-center">
                    <p className="text-sm text-blue-600">{t("predict.area")}</p>
                    <p className="text-3xl font-bold text-blue-700">{result.area_km2.toFixed(2)} km²</p>
                  </div>
                )}
                {(result.decision_threshold !== undefined || result.uncertain_pixel_fraction !== undefined) && (
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-lg border border-zinc-200 p-3">
                      <div className="text-xs text-zinc-500">Inference</div>
                      <div className="mt-1 font-semibold">{result.inference_variant ?? "single_pass"}</div>
                    </div>
                    <div className="rounded-lg border border-zinc-200 p-3">
                      <div className="text-xs text-zinc-500">Decision threshold</div>
                      <div className="mt-1 font-semibold">{result.decision_threshold?.toFixed(2) ?? "—"}</div>
                    </div>
                    <div className="rounded-lg border border-zinc-200 p-3">
                      <div className="text-xs text-zinc-500">High-entropy pixels</div>
                      <div className="mt-1 font-semibold">
                        {result.uncertain_pixel_fraction !== undefined
                          ? `${(result.uncertain_pixel_fraction * 100).toFixed(1)}%`
                          : "—"}
                      </div>
                    </div>
                  </div>
                )}
                {result.mask_path && (
                  <div className="h-96 overflow-hidden rounded-xl">
                    <MapView imageUrl={result.overlay_path && getStaticUrl(result.overlay_path)} maskUrl={getStaticUrl(result.mask_path)} />
                  </div>
                )}
                {result.task_id && (
                  <div className="flex flex-wrap gap-4">
                    <a
                      href={result.geotiff_path ? getStaticUrl(result.geotiff_path) : apiUrl(`/api/export/${result.task_id}?fmt=geotiff`)}
                      className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
                    >
                      <Download className="h-4 w-4" aria-hidden="true" />
                      {t("predict.download")}
                    </a>
                    {result.probability_geotiff_path && (
                      <a href={getStaticUrl(result.probability_geotiff_path)} className="text-sm text-blue-600 hover:underline">
                        Probability GeoTIFF
                      </a>
                    )}
                    {result.entropy_geotiff_path && (
                      <a href={getStaticUrl(result.entropy_geotiff_path)} className="text-sm text-blue-600 hover:underline">
                        Entropy GeoTIFF
                      </a>
                    )}
                  </div>
                )}
                {(result.probability_path || result.entropy_path) && (
                  <div className="grid gap-4 sm:grid-cols-2">
                    {result.probability_path && (
                      <figure className="overflow-hidden rounded-xl border border-zinc-200">
                        <Image
                          src={getStaticUrl(result.probability_path)}
                          alt="Glacier probability map"
                          width={768}
                          height={768}
                          unoptimized
                          className="h-auto w-full"
                        />
                        <figcaption className="p-3 text-xs text-zinc-600">Per-pixel glacier probability</figcaption>
                      </figure>
                    )}
                    {result.entropy_path && (
                      <figure className="overflow-hidden rounded-xl border border-zinc-200">
                        <Image
                          src={getStaticUrl(result.entropy_path)}
                          alt="Predictive entropy map"
                          width={768}
                          height={768}
                          unoptimized
                          className="h-auto w-full"
                        />
                        <figcaption className="p-3 text-xs text-zinc-600">Predictive entropy · brighter means review first</figcaption>
                      </figure>
                    )}
                  </div>
                )}
                {result.warnings && result.warnings.length > 0 && (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                    <div className="font-semibold">Evidence limits</div>
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {result.warnings.map((warning) => <li key={warning}>{warning}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
