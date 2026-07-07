"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mountain, Loader2, Plus, X } from "lucide-react";
import TrendChart from "@/components/TrendChart";
import UploadZone from "@/components/UploadZone";
import ModelSelector from "@/components/ModelSelector";
import ErrorBoundary from "@/components/ErrorBoundary";
import { fetchModels, fetchTrend, predict, ModelInfo, TrendResult } from "@/lib/api";
import { useI18n } from "@/lib/I18nProvider";

export default function TrendPage() {
  const { t } = useI18n();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("unet");
  const [entries, setEntries] = useState<{ file: File | null; year: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TrendResult | null>(null);

  useEffect(() => {
    fetchModels().then((m) => {
      setModels(m);
      if (m.length > 0) setSelectedModel(m[0].name);
    });
  }, []);

  const addEntry = () => setEntries((prev) => [...prev, { file: null, year: new Date().getFullYear() }]);

  const removeEntry = (i: number) => setEntries((prev) => prev.filter((_, idx) => idx !== i));

  const updateEntry = (i: number, field: "file" | "year", value: File | number) => {
    setEntries((prev) => prev.map((e, idx) => (idx === i ? { ...e, [field]: value } : e)));
  };

  const handleAnalyze = async () => {
    const valid = entries.filter((e) => e.file);
    if (valid.length < 2) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const taskIds: string[] = [];
      const years: number[] = [];

      for (let i = 0; i < valid.length; i++) {
        const entry = valid[i];
        setProgress(`${i + 1}/${valid.length}`);
        const pred = await predict(entry.file!, selectedModel, false, false, undefined, entry.year);
        if (pred.status === "failed" || !pred.task_id) {
          throw new Error(pred.error || `Prediction failed for year ${entry.year}`);
        }
        taskIds.push(pred.task_id);
        years.push(entry.year);
      }

      setProgress("");
      const r = await fetchTrend(taskIds, years);
      setResult(r);
    } catch (e) {
      setError(String(e));
      console.error(e);
    } finally {
      setLoading(false);
      setProgress("");
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
          <span className="font-bold">{t("trend.title")}</span>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("predict.step2")}</h2>
            <ModelSelector models={models} selectedModel={selectedModel} onSelect={setSelectedModel} />
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t("trend.upload_by_year")}</h2>
              <button
                onClick={addEntry}
                className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                {t("trend.add_year")}
              </button>
            </div>
            <div className="space-y-4">
              {entries.map((entry, i) => (
                <div key={i} className="flex items-start gap-4 rounded-lg border border-zinc-200 p-4">
                  <div className="flex-1">
                    <UploadZone
                      onFileSelected={(f) => updateEntry(i, "file", f)}
                      disabled={loading}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <div>
                      <p className="mb-1 text-xs text-zinc-400">{t("trend.year")}</p>
                      <input
                        type="number"
                        value={entry.year}
                        onChange={(e) => updateEntry(i, "year", parseInt(e.target.value) || 2000)}
                        className="w-20 rounded-lg border border-zinc-300 px-2 py-1 text-sm"
                        min="1980"
                        max="2030"
                        aria-label={t("trend.year")}
                      />
                    </div>
                    <button
                      onClick={() => removeEntry(i)}
                      className="mt-5 rounded-lg p-1 text-zinc-400 hover:text-red-500"
                      aria-label={`Remove year ${entry.year}`}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
              {entries.length === 0 && (
                <p className="py-4 text-center text-sm text-zinc-400">
                  {t("trend.empty")}
                </p>
              )}
            </div>
          </section>
        </ErrorBoundary>

        {error && (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-600" role="alert">
            {error}
          </p>
        )}

        <button
          onClick={handleAnalyze}
          disabled={entries.filter((e) => e.file).length < 2 || loading || !selectedModel}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          aria-busy={loading}
        >
          {loading && <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />}
          {loading
            ? progress
              ? `${t("trend.analyzing")} (${progress})`
              : t("trend.analyzing")
            : t("trend.analyze")}
        </button>

        {result && (
          <section className="rounded-xl bg-white p-6 shadow-sm" role="status" aria-live="polite">
            <h2 className="mb-4 text-lg font-semibold">{t("trend.result")}</h2>
            <TrendChart data={result} />
          </section>
        )}
      </main>
    </div>
  );
}
