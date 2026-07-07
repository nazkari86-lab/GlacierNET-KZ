"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mountain, RotateCcw } from "lucide-react";
import HistoryTable from "@/components/HistoryTable";
import ErrorBoundary from "@/components/ErrorBoundary";
import { TableSkeleton } from "@/components/Skeletons";
import dynamic from "next/dynamic";
const MapView = dynamic(() => import("@/components/MapView"), { ssr: false });
import { fetchHistory, getStaticUrl, HistoryItem } from "@/lib/api";
import { useI18n } from "@/lib/I18nProvider";

export default function HistoryPage() {
  const { t } = useI18n();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [selected, setSelected] = useState<HistoryItem | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    fetchHistory().then(setItems).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <Link href="/" className="text-zinc-400 hover:text-zinc-600" aria-label={t("nav.back")}>
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Mountain className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <span className="font-bold">{t("history.title")}</span>
          <button
            onClick={load}
            className="ml-auto text-zinc-400 hover:text-zinc-600"
            aria-label={t("history.refresh")}
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        </div>
      </header>
      <main id="main-content" className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            {loading ? (
              <TableSkeleton />
            ) : (
              <HistoryTable items={items} onSelect={setSelected} />
            )}
          </section>
        </ErrorBoundary>

        {selected && (
          <section className="rounded-xl bg-white p-6 shadow-sm" aria-live="polite">
            <h2 className="mb-4 text-lg font-semibold">
              {selected.model_name} — {new Date(selected.created_at).toLocaleDateString()}
            </h2>
            {selected.area_km2 !== null && (
              <p className="mb-4 text-sm text-zinc-500">{t("history.area")}: {selected.area_km2.toFixed(2)} km²</p>
            )}
            {selected.thumbnail_path && (
              <div className="h-80 overflow-hidden rounded-xl">
                <MapView maskUrl={getStaticUrl(selected.thumbnail_path)} />
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
