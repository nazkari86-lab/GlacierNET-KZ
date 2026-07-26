"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Bot,
  Download,
  Loader2,
  MapPin,
  Mountain,
  Search,
} from "lucide-react";
import {
  fetchGlaciers,
  fetchGlacierSeries,
  type GlacierRecord,
  type GlacierTimeSeries,
} from "@/lib/api";
import { apiUrl } from "@/lib/utils";
import { useI18n } from "@/lib/I18nProvider";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const GlacierBoundaryMap = dynamic(() => import("@/components/GlacierBoundaryMap"), { ssr: false });

export default function GlaciersPage() {
  const { t } = useI18n();
  const [glaciers, setGlaciers] = useState<GlacierRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedId, setSelectedId] = useState("");
  const [series, setSeries] = useState<GlacierTimeSeries | null>(null);
  const [search, setSearch] = useState("");
  const [namedOnly, setNamedOnly] = useState(true);
  const [method, setMethod] = useState("ndsi");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRegistry = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await fetchGlaciers(search, namedOnly, 1000);
      setGlaciers(result.glaciers);
      setTotal(result.total);
      if (!result.glaciers.some((item) => item.rgi_id === selectedId)) {
        setSelectedId(result.glaciers[0]?.rgi_id ?? "");
      }
    } catch (cause) {
      setError(String(cause));
    } finally {
      setLoading(false);
    }
  }, [namedOnly, search, selectedId]);

  useEffect(() => {
    loadRegistry();
    // Registry reloads only when its filters change; selectedId is handled inside.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [namedOnly]);

  useEffect(() => {
    if (!selectedId) {
      setSeries(null);
      return;
    }
    setLoading(true);
    fetchGlacierSeries(selectedId, method)
      .then(setSeries)
      .catch((cause) => setError(String(cause)))
      .finally(() => setLoading(false));
  }, [method, selectedId]);

  const selected = series?.glacier;

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3">
          <Link href="/" className="text-zinc-400 hover:text-zinc-700" aria-label={t("nav.back")}>
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Mountain className="h-5 w-5 text-blue-600" />
          <span className="font-bold">{t("glaciers.title")}</span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-7xl space-y-6 px-4 py-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t("glaciers.title")}</h1>
          <p className="mt-2 max-w-3xl text-zinc-600">{t("glaciers.subtitle")}</p>
        </div>

        {error && <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">{error}</p>}

        <section className="grid gap-6 lg:grid-cols-[340px_1fr]">
          <aside className="h-fit rounded-xl bg-white p-4 shadow-sm">
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                loadRegistry();
              }}
            >
              <label className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400" />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={t("glaciers.search")}
                  aria-label={t("glaciers.search")}
                  className="w-full rounded-lg border border-zinc-300 py-2 pl-9 pr-3 text-sm"
                />
              </label>
              <button className="rounded-lg bg-blue-600 px-3 text-white hover:bg-blue-700" aria-label={t("glaciers.search")}>
                <Search className="h-4 w-4" />
              </button>
            </form>
            <label className="mt-3 flex items-center gap-2 text-sm text-zinc-600">
              <input type="checkbox" checked={namedOnly} onChange={(event) => setNamedOnly(event.target.checked)} />
              {t("glaciers.named_only")}
            </label>
            <p className="mt-3 text-xs text-zinc-400">
              {total} {t("glaciers.results")}
            </p>
            <div className="mt-3 max-h-[620px] space-y-2 overflow-y-auto">
              {glaciers.map((glacier) => (
                <button
                  key={glacier.rgi_id}
                  onClick={() => setSelectedId(glacier.rgi_id)}
                  className={`w-full rounded-lg border p-3 text-left transition ${
                    glacier.rgi_id === selectedId
                      ? "border-blue-500 bg-blue-50"
                      : "border-zinc-200 hover:border-blue-300"
                  }`}
                >
                  <p className="font-medium text-zinc-900">{glacier.name_ru}</p>
                  <p className="mt-1 text-xs text-zinc-500">{glacier.rgi_area_km2.toFixed(3)} km²</p>
                  <p className="mt-1 truncate font-mono text-[10px] text-zinc-400">{glacier.rgi_id}</p>
                </button>
              ))}
            </div>
          </aside>

          <div className="space-y-6">
            {loading && !series && (
              <div className="flex min-h-80 items-center justify-center gap-2 rounded-xl bg-white text-zinc-500">
                <Loader2 className="h-5 w-5 animate-spin" />
                {t("glaciers.loading")}
              </div>
            )}

            {selected && series && (
              <>
                <section className="rounded-xl bg-white p-6 shadow-sm">
                  <div className="flex flex-col justify-between gap-4 sm:flex-row">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-2xl font-bold">{selected.name_ru}</h2>
                        {selected.wgms_reference && (
                          <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-medium text-emerald-800">
                            WGMS reference
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-zinc-500">{selected.name}</p>
                      <p className="mt-2 flex items-center gap-1 text-sm text-zinc-500">
                        <MapPin className="h-4 w-4" />
                        {selected.centroid.latitude.toFixed(5)}, {selected.centroid.longitude.toFixed(5)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/analysis?glacier=${encodeURIComponent(selected.rgi_id)}&method=${method}`}
                        className="inline-flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700"
                      >
                        <Bot className="h-4 w-4" /> {t("glaciers.ask_ai")}
                      </Link>
                      <a
                        href={apiUrl(`/api/glaciers/${encodeURIComponent(selected.rgi_id)}/report?method=${method}`)}
                        className="inline-flex items-center gap-2 rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium hover:bg-zinc-50"
                      >
                        <Download className="h-4 w-4" /> {t("glaciers.report")}
                      </a>
                    </div>
                  </div>

                  <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                    <div><p className="text-xs text-zinc-500">{t("glaciers.rgi_area")}</p><p className="text-2xl font-bold">{selected.rgi_area_km2.toFixed(3)} km²</p></div>
                    <div><p className="text-xs text-zinc-500">{t("glaciers.elevation")}</p><p className="text-2xl font-bold">{selected.elevation.mean_m.toFixed(0)} m</p></div>
                    <div><p className="text-xs text-zinc-500">{t("glaciers.slope")}</p><p className="text-2xl font-bold">{selected.slope_deg.toFixed(1)}°</p></div>
                    <div><p className="text-xs text-zinc-500">{t("glaciers.length")}</p><p className="text-2xl font-bold">{selected.maximum_length_m} m</p></div>
                  </div>
                </section>

                {selected.geometry && (
                  <section className="rounded-xl bg-white p-6 shadow-sm">
                    <h2 className="mb-4 text-lg font-semibold">{t("glaciers.map")}</h2>
                    <div className="h-96 overflow-hidden rounded-lg">
                      <GlacierBoundaryMap geometry={selected.geometry} name={selected.name_ru} />
                    </div>
                  </section>
                )}

                <section className="rounded-xl bg-white p-6 shadow-sm">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-lg font-semibold">{t("glaciers.timeseries")}</h2>
                      <p className="text-sm text-zinc-500">
                        {series.first_year}–{series.last_year} · {series.points.length} {t("glaciers.years")}
                      </p>
                    </div>
                    <select
                      value={method}
                      onChange={(event) => setMethod(event.target.value)}
                      className="rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm"
                      aria-label={t("glaciers.method")}
                    >
                      <option value="ndsi">NDSI · 16 years</option>
                      <option value="rf">Random Forest · physical artifacts only</option>
                      <option value="unet">U-Net · physical artifacts only</option>
                    </select>
                  </div>

                  <div className="h-80" data-testid="glacier-series-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={series.points}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e4e4e7" />
                        <XAxis dataKey="year" />
                        <YAxis unit=" km²" width={75} />
                        <Tooltip formatter={(value) => [`${Number(value).toFixed(4)} km²`, t("glaciers.area")]} />
                        <Line type="monotone" dataKey="area_km2" stroke="#2563eb" strokeWidth={2.5} dot={{ r: 3 }} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  <div className="mt-4 grid gap-4 sm:grid-cols-3">
                    <div><p className="text-xs text-zinc-500">{t("glaciers.change")}</p><p className="text-xl font-bold">{series.change_km2?.toFixed(4) ?? "—"} km²</p></div>
                    <div><p className="text-xs text-zinc-500">{t("glaciers.change_percent")}</p><p className="text-xl font-bold">{series.change_percent?.toFixed(2) ?? "—"}%</p></div>
                    <div><p className="text-xs text-zinc-500">WGMS</p><p className="text-xl font-bold">{series.wgms_points.length} {t("glaciers.points")}</p></div>
                  </div>
                </section>

                <section className="flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
                  <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                  <div><strong>{t("glaciers.boundary")}:</strong> {series.caveat}</div>
                </section>
              </>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
