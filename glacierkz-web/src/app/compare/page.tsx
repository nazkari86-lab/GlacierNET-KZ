"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mountain, Loader2 } from "lucide-react";
import UploadZone from "@/components/UploadZone";
import SplitView from "@/components/SplitView";
import ErrorBoundary from "@/components/ErrorBoundary";
import { fetchModels, compareModels, ModelInfo, CompareResult } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useI18n } from "@/lib/I18nProvider";

export default function ComparePage() {
  const { t } = useI18n();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [useTta, setUseTta] = useState(false);
  const [useCrf, setUseCrf] = useState(false);
  const [year, setYear] = useState(2024);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResult | null>(null);

  useEffect(() => {
    fetchModels().then(setModels);
  }, []);

  const toggleModel = (name: string) => {
    setSelectedModels((prev) =>
      prev.includes(name) ? prev.filter((m) => m !== name) : [...prev, name]
    );
  };

  const handleCompare = async () => {
    if (!file || selectedModels.length < 2) return;
    setLoading(true);
    setResult(null);
    try {
      const needsSar = selectedModels.some((name) => models.find((model) => model.name === name)?.channel_count === 16);
      const r = await compareModels(file, selectedModels, useTta, useCrf, needsSar ? year : undefined);
      setResult(r);
    } catch (e) {
      console.error(e);
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
          <h1 className="font-bold">{t("compare.title")}</h1>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("compare.step1")}</h2>
            <UploadZone onFileSelected={setFile} disabled={loading} />
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("compare.step2")}</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3" role="group" aria-label="Model selection">
              {models.map((m) => (
                <button
                  key={m.name}
                  onClick={() => toggleModel(m.name)}
                  className={cn(
                    "rounded-xl border-2 p-3 text-left text-sm transition-all",
                    selectedModels.includes(m.name)
                      ? "border-blue-500 bg-blue-50"
                      : "border-zinc-200 hover:border-zinc-300"
                  )}
                  aria-pressed={selectedModels.includes(m.name)}
                >
                  {m.display_name}
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("compare.step3")}</h2>
            <div className="flex flex-wrap gap-6">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={useTta} onChange={(e) => setUseTta(e.target.checked)} className="rounded" />
                <span className="text-sm">{t("compare.tta")}</span>
              </label>
              {selectedModels.some((name) => models.find((model) => model.name === name)?.channel_count === 16) && (
                <label className="flex items-center gap-2">
                  <span className="text-sm">Observation year</span>
                  <select value={year} onChange={(event) => setYear(Number(event.target.value))} className="rounded border px-2 py-1 text-sm">
                    {Array.from({ length: 8 }, (_, index) => 2024 - index).map((value) => (
                      <option key={value} value={value}>{value}</option>
                    ))}
                  </select>
                </label>
              )}
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={useCrf} onChange={(e) => setUseCrf(e.target.checked)} className="rounded" />
                <span className="text-sm">{t("compare.crf")}</span>
              </label>
            </div>
          </section>
        </ErrorBoundary>

        <button
          onClick={handleCompare}
          disabled={!file || selectedModels.length < 2 || loading}
          className={cn(
            "flex w-full items-center justify-center gap-2 rounded-xl py-3 text-white transition-colors",
            loading ? "bg-blue-400" : "bg-blue-600 hover:bg-blue-700",
            "disabled:cursor-not-allowed"
          )}
          aria-busy={loading}
        >
          {loading && <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />}
          {loading ? t("predict.processing") : t("compare.run")}
        </button>

        {result && (
          <section className="rounded-xl bg-white p-6 shadow-sm" role="status" aria-live="polite">
            <h2 className="mb-4 text-lg font-semibold">{t("compare.results")}</h2>
            <SplitView segments={result.segments} imageUrl={file ? URL.createObjectURL(file) : undefined} />
            {result.failures && result.failures.length > 0 && (
              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                {result.failures.map((failure) => (
                  <div key={failure.model_name}><strong>{failure.model_name}:</strong> {failure.error}</div>
                ))}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
