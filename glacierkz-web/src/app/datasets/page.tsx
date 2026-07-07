// GlacierNET-KZ Datasets Page
"use client";

import { useState, useMemo, useEffect, useCallback } from "react";
import {
  Folder,
  Upload,
  Download,
  CheckCircle,
  AlertTriangle,
  HardDrive,
  FileText,
} from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";
import { StatCard } from "@/components/StatCard";
import { DataTable, type ColumnDef } from "@/components/DataTable";
import { Modal } from "@/components/Modal";
import { toast, ToastContainer } from "@/components/Toast";
import { cn } from "@/lib/utils";
import { fetchDatasets, fetchDataCoverage, type DatasetInfo, type DataCoverage } from "@/lib/api";

type DatasetStatus = "validated" | "pending" | "processing";

interface GlacierDataset {
  id: string;
  name: string;
  source: "Sentinel-2" | "Landsat";
  year: number;
  bands: number;
  patchCount: number;
  sizeMb: number;
  status: DatasetStatus;
}

const STATUS_CONFIG: Record<DatasetStatus, { label: string; style: string; icon: React.ReactNode }> = {
  validated: { label: "Validated", style: "bg-emerald-50 text-emerald-700", icon: <CheckCircle className="h-3.5 w-3.5" /> },
  pending: { label: "Pending", style: "bg-amber-50 text-amber-700", icon: <AlertTriangle className="h-3.5 w-3.5" /> },
  processing: { label: "Processing", style: "bg-blue-50 text-blue-700", icon: <AlertTriangle className="h-3.5 w-3.5" /> },
};

function mapApiStatus(status: string): DatasetStatus {
  if (status === "ready") return "validated";
  if (status === "uploading") return "processing";
  return "pending";
}

function mapDataset(ds: DatasetInfo): GlacierDataset {
  const isLandsat = ds.name.toLowerCase().includes("landsat");
  const yearMatch = ds.name.match(/(20\d{2})/);
  return {
    id: ds.id,
    name: ds.name,
    source: isLandsat ? "Landsat" : "Sentinel-2",
    year: yearMatch ? parseInt(yearMatch[1], 10) : parseInt(ds.date_range, 10) || 2020,
    bands: isLandsat ? 11 : 13,
    patchCount: ds.num_samples,
    sizeMb: ds.size_mb,
    status: mapApiStatus(ds.status),
  };
}

export default function DatasetsPage() {
  const { t } = useI18n();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [datasets, setDatasets] = useState<GlacierDataset[]>([]);
  const [coverage, setCoverage] = useState<DataCoverage | null>(null);
  const [loading, setLoading] = useState(true);

  const loadDatasets = useCallback(async () => {
    try {
      const [res, cov] = await Promise.all([fetchDatasets(), fetchDataCoverage()]);
      setDatasets(res.datasets.map(mapDataset));
      setCoverage(cov);
    } catch {
      toast.error("Failed to load datasets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  const stats = useMemo(() => {
    const totalPatches = datasets.reduce((s, d) => s + d.patchCount, 0);
    const totalSizeMb = datasets.reduce((s, d) => s + d.sizeMb, 0);
    const avgPatchSize = datasets.length > 0 ? (totalSizeMb / datasets.length).toFixed(0) : "0";
    return {
      totalDatasets: datasets.length,
      totalPatches: totalPatches.toLocaleString(),
      avgPatchSize: `${avgPatchSize} MB`,
      storageUsed: `${(totalSizeMb / 1024).toFixed(1)} GB`,
    };
  }, [datasets]);

  const handleExport = () => {
    toast.success("Report exported", "Dataset report has been generated.");
  };

  const columns: ColumnDef<GlacierDataset>[] = [
    {
      key: "name",
      header: t("datasets.dataset_name"),
      sortable: true,
      accessor: (row) => (
        <span className="flex items-center gap-2 font-medium text-gray-900">
          <Folder className="h-4 w-4 text-gray-400 shrink-0" aria-hidden="true" />
          {row.name}
        </span>
      ),
    },
    {
      key: "source",
      header: t("datasets.source"),
      sortable: true,
      width: "120px",
      accessor: (row) => (
        <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
          {row.source}
        </span>
      ),
    },
    {
      key: "year",
      header: t("datasets.year"),
      sortable: true,
      width: "80px",
      align: "center",
      accessor: (row) => <span className="text-gray-500 tabular-nums">{row.year}</span>,
    },
    {
      key: "bands",
      header: t("datasets.bands"),
      sortable: true,
      width: "80px",
      align: "center",
      accessor: (row) => <span className="text-gray-500 tabular-nums">{row.bands}</span>,
    },
    {
      key: "patchCount",
      header: t("datasets.patch_count"),
      sortable: true,
      width: "100px",
      align: "right",
      accessor: (row) => <span className="text-gray-500 tabular-nums">{row.patchCount.toLocaleString()}</span>,
    },
    {
      key: "sizeMb",
      header: t("datasets.size"),
      sortable: true,
      width: "100px",
      align: "right",
      accessor: (row) => <span className="text-gray-500 tabular-nums">{row.sizeMb} MB</span>,
    },
    {
      key: "status",
      header: t("datasets.status"),
      sortable: true,
      width: "130px",
      accessor: (row) => {
        const cfg = STATUS_CONFIG[row.status];
        return (
          <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium", cfg.style)}>
            {cfg.icon}
            {t(`datasets.status_${row.status}`)}
          </span>
        );
      },
    },
  ];

  return (
    <div className="min-h-screen bg-zinc-50">
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <div className="flex items-center gap-2">
              <Folder className="h-5 w-5 text-blue-600" aria-hidden="true" />
              <h1 className="text-xl font-bold text-gray-900">{t("datasets.title")}</h1>
            </div>
            <p className="mt-1 text-sm text-gray-500">{t("datasets.subtitle")}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setUploadOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              aria-label={t("datasets.upload")}
            >
              <Upload className="h-4 w-4" aria-hidden="true" />
              {t("datasets.upload")}
            </button>
            <button
              onClick={handleExport}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              aria-label={t("datasets.export_report")}
            >
              <Download className="h-4 w-4" aria-hidden="true" />
              {t("datasets.export_report")}
            </button>
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        <section aria-label="Dataset statistics" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label={t("datasets.total_datasets")} value={stats.totalDatasets} icon={<HardDrive className="h-5 w-5" />} color="blue" />
          <StatCard label={t("datasets.total_patches")} value={stats.totalPatches} icon={<Folder className="h-5 w-5" />} color="green" />
          <StatCard label={t("datasets.avg_patch_size")} value={stats.avgPatchSize} icon={<FileText className="h-5 w-5" />} color="purple" />
          <StatCard label={t("datasets.storage_used")} value={stats.storageUsed} icon={<HardDrive className="h-5 w-5" />} color="red" />
        </section>

        {coverage && coverage.missing_predictions.length > 0 && (
          <section
            aria-label="Data coverage"
            className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          >
            <p className="font-medium">Inference pending for years: {coverage.missing_predictions.join(", ")}</p>
            <p className="mt-1 text-xs text-amber-800">
              Raw GeoTIFFs: Sentinel-2 {coverage.raw_sentinel2.length} yrs · Landsat {coverage.raw_landsat.length} yrs ·
              Predictions {coverage.predictions.length} yrs
            </p>
          </section>
        )}

        <section aria-label="Glacier datasets table">
          {loading ? (
            <div className="rounded-xl border border-gray-200 bg-white p-12 text-center text-sm text-gray-500">
              Loading datasets…
            </div>
          ) : (
            <DataTable
              data={datasets}
              columns={columns}
              sortable
              pagination
              pageSize={8}
              emptyMessage="No datasets found."
            />
          )}
        </section>
      </main>

      <Modal open={uploadOpen} onClose={() => setUploadOpen(false)} title={t("datasets.upload")} size="md">
        <div className="space-y-4 p-2">
          <p className="text-sm text-gray-500">Select a dataset archive to upload for preprocessing.</p>
          <div className="rounded-lg border-2 border-dashed border-gray-200 p-8 text-center">
            <Upload className="mx-auto h-8 w-8 text-gray-400" aria-hidden="true" />
            <p className="mt-2 text-sm text-gray-500">Drag and drop or click to browse</p>
          </div>
        </div>
      </Modal>

      <ToastContainer />
    </div>
  );
}
