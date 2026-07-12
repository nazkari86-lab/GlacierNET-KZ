"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mountain, Loader2, Download } from "lucide-react";
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
  const [ndsiThreshold, setNdsiThreshold] = useState(0.4);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResult | null>(null);

  useEffect(() => {
    fetchModels().then((m) => {
      setModels(m);
      if (m.length > 0) setSelectedModel(m[0].name);
    });
  }, []);

  const handlePredict = async () => {
    if (!file) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await predict(file, selectedModel, useTta, useCrf, ndsiThreshold);
      setResult(r);
    } catch (e) {
      setResult({ task_id: "", status: "failed", error: String(e) });
    } finally {
      setLoading(false);
    }
  };

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
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step1")}</h2>
            <UploadZone onFileSelected={setFile} disabled={loading} />
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step2")}</h2>
            <ModelSelector models={models} selectedModel={selectedModel} onSelect={setSelectedModel} />
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step3")}</h2>
            <div className="flex flex-wrap gap-6">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={useTta}
                  onChange={(e) => setUseTta(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm">{t("predict.tta")}</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={useCrf}
                  onChange={(e) => setUseCrf(e.target.checked)}
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
            </div>
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
                {result.mask_path && (
                  <div className="h-96 overflow-hidden rounded-xl">
                    <MapView imageUrl={result.overlay_path && getStaticUrl(result.overlay_path)} maskUrl={getStaticUrl(result.mask_path)} />
                  </div>
                )}
                {result.task_id && (
                  <a
                    href={apiUrl(`/api/export/${result.task_id}?fmt=geotiff`)}
                    className="flex items-center gap-2 text-sm text-blue-600 hover:underline"
                  >
                    <Download className="h-4 w-4" aria-hidden="true" />
                    {t("predict.download")}
                  </a>
                )}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
