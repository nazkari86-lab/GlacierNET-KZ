// GlacierNET-KZ Training Page
"use client";

import { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  Square,
  RotateCcw,
  Settings,
  Cpu,
  Clock,
  Target,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import { useI18n } from "@/lib/I18nProvider";
import { StatCard } from "@/components/StatCard";
import { LineChart } from "@/components/Charts";
import { Modal } from "@/components/Modal";
import { toast, ToastContainer } from "@/components/Toast";
import { Tabs, TabPanel } from "@/components/TabsAccordion";
import {
  fetchDatasets,
  getTrainingLogs,
  getTrainingStatus,
  pauseTrainingRun,
  startTraining,
  stopTrainingRun,
} from "@/lib/api";

type TrainingStatus = "idle" | "running" | "paused" | "stopped";

interface Hyperparams {
  learningRate: number;
  batchSize: number;
  epochs: number;
  optimizer: string;
  model: string;
  augmentation: boolean;
  tta: boolean;
}

interface LogLine {
  time: string;
  text: string;
  type: "info" | "success" | "warning" | "error";
}

function formatTime(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0 ? `${h}h ${m}m ${sec}s` : `${m}m ${sec}s`;
}

const DEFAULT_DATASET_ID = "ds-zailiysky-2020";

export default function TrainingPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<TrainingStatus>("idle");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [datasetId, setDatasetId] = useState(DEFAULT_DATASET_ID);
  const [currentEpoch, setCurrentEpoch] = useState(0);
  const [totalEpochs, setTotalEpochs] = useState(100);
  const [bestLoss, setBestLoss] = useState(0);
  const [lr, setLr] = useState(1e-4);
  const [elapsed, setElapsed] = useState(0);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [lossData, setLossData] = useState<{ label: string; values: number[] }[]>([]);
  const [iouData, setIouData] = useState<{ label: string; values: number[] }[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState("logs");
  const logRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number | null>(null);

  const [hyperparams, setHyperparams] = useState<Hyperparams>({
    learningRate: 1e-4,
    batchSize: 8,
    epochs: 100,
    optimizer: "adam",
    model: "unet",
    augmentation: true,
    tta: false,
  });

  useEffect(() => {
    fetchDatasets()
      .then((res) => {
        if (res.datasets.length > 0) {
          setDatasetId(res.datasets[0].id);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  useEffect(() => {
    if (!taskId || status === "idle" || status === "stopped") return;

    const poll = async () => {
      try {
        const s = await getTrainingStatus(taskId);
        const logLines = await getTrainingLogs(taskId);
        setCurrentEpoch(s.epoch);
        setTotalEpochs(s.total_epochs);
        setBestLoss(s.best_metric);
        setLogs(logLines as LogLine[]);

        if (s.metrics.loss !== undefined) {
          setLossData((prev) => {
            const next = [...prev, { label: String(s.epoch), values: [s.metrics.loss, s.metrics.val_loss || s.metrics.loss] }];
            return next.slice(-20);
          });
          setIouData((prev) => {
            const iou = s.metrics.iou || 0;
            return [...prev, { label: String(s.epoch), values: [iou, iou * 0.98] }].slice(-20);
          });
        }

        if (startTimeRef.current) {
          setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
        }

        if (["completed", "stopped", "failed"].includes(s.status)) {
          setStatus(s.status === "completed" ? "idle" : "stopped");
          if (s.status === "completed") {
            toast.success(t("training.complete_title"), t("training.complete_msg", { epochs: s.total_epochs }));
          }
        } else if (s.status === "paused") {
          setStatus("paused");
        } else {
          setStatus("running");
        }
      } catch {
        /* ignore transient poll errors */
      }
    };

    poll();
    const interval = setInterval(poll, 1500);
    return () => clearInterval(interval);
  }, [taskId, status, t]);

  const startTrainingHandler = async () => {
    if (status === "running") return;
    try {
      setTotalEpochs(hyperparams.epochs);
      setLr(hyperparams.learningRate);
      startTimeRef.current = Date.now();
      const result = await startTraining({
        dataset_id: datasetId,
        model_name: hyperparams.model,
        epochs: hyperparams.epochs,
        batch_size: hyperparams.batchSize,
        learning_rate: hyperparams.learningRate,
        optimizer: hyperparams.optimizer,
      });
      setTaskId(result.task_id);
      setStatus("running");
      setLossData([]);
      setIouData([]);
      toast.success(t("training.started_title"), t("training.started_msg"));
    } catch {
      toast.error(t("training.failed_start"));
    }
  };

  const pauseTrainingHandler = async () => {
    if (!taskId || status !== "running") return;
    try {
      await pauseTrainingRun(taskId);
      setStatus("paused");
      toast.warning(t("training.paused"));
    } catch {
      toast.error(t("training.failed_pause"));
    }
  };

  const stopTrainingHandler = async () => {
    if (!taskId || status === "idle") return;
    try {
      await stopTrainingRun(taskId);
      setStatus("stopped");
      toast.error(t("training.stopped"));
    } catch {
      toast.error(t("training.failed_stop"));
    }
  };

  const resetTraining = () => {
    setStatus("idle");
    setTaskId(null);
    setCurrentEpoch(0);
    setBestLoss(0);
    setElapsed(0);
    setLr(1e-4);
    setLogs([]);
    setLossData([]);
    setIouData([]);
    startTimeRef.current = null;
  };

  const eta = status === "running" && currentEpoch < totalEpochs
    ? formatTime(Math.round(((totalEpochs - currentEpoch) * elapsed) / Math.max(currentEpoch, 1)))
    : "--:--:--";

  const logTypeColors: Record<string, string> = {
    info: "text-blue-400",
    success: "text-emerald-400",
    warning: "text-amber-400",
    error: "text-red-400",
  };

  return (
    <div className="min-h-screen bg-zinc-50">
      <ToastContainer />
      <header className="w-full border-b bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{t("training.title")}</h1>
              <p className="mt-1 text-sm text-gray-500">{t("training.subtitle")}</p>
            </div>
            <button
              onClick={() => setShowSettings(true)}
              className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              aria-label="Training settings"
            >
              <Settings className="h-4 w-4" />
              {t("training.configuration")}
            </button>
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        {/* Training Status */}
        <section aria-label="Training status">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label={t("training.epoch")}
              value={`${currentEpoch} / ${totalEpochs}`}
              icon={<Cpu className="h-5 w-5" />}
              color="blue"
            />
            <StatCard
              label={t("training.best_loss")}
              value={bestLoss > 0 ? bestLoss.toFixed(4) : "--"}
              icon={<Target className="h-5 w-5" />}
              color="green"
            />
            <StatCard
              label={t("training.learning_rate_label")}
              value={lr.toExponential(1)}
              icon={<TrendingUp className="h-5 w-5" />}
              color="purple"
            />
            <StatCard
              label={t("training.time_elapsed")}
              value={formatTime(elapsed)}
              icon={<Clock className="h-5 w-5" />}
              color="yellow"
            />
          </div>
        </section>

        {/* Training Progress */}
        <section className="rounded-xl border border-gray-200 bg-white p-6" aria-label={t("training.progress")}>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-700">{t("training.progress")}</h2>
            <span className="text-xs text-gray-500">{t("training.eta")}: {eta}</span>
          </div>
          <div className="w-full overflow-hidden rounded-full bg-gray-200">
            <div
              className="rounded-full bg-blue-600 py-1.5 text-center text-xs font-medium text-white transition-all duration-500"
              style={{ width: `${totalEpochs > 0 ? (currentEpoch / totalEpochs) * 100 : 0}%` }}
              role="progressbar"
              aria-valuenow={currentEpoch}
              aria-valuemin={0}
              aria-valuemax={totalEpochs}
            >
              {totalEpochs > 0 ? ((currentEpoch / totalEpochs) * 100).toFixed(1) : 0}%
            </div>
          </div>
          <p className="mt-2 text-center text-xs text-gray-500">
            {currentEpoch} / {totalEpochs} {t("training.epochs")}
          </p>
        </section>

        {/* Training Charts */}
        <section aria-label="Training charts">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="mb-4 text-sm font-semibold text-gray-700">{t("training.loss")} over {t("training.epochs")}</h3>
              <LineChart
                data={lossData}
                series={[
                  { name: `Train ${t("training.loss")}`, color: "#3b82f6" },
                  { name: `Val ${t("training.loss")}`, color: "#f59e0b" },
                ]}
                height={220}
              />
            </div>
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h3 className="mb-4 text-sm font-semibold text-gray-700">{t("training.iou_over_epochs")}</h3>
              <LineChart
                data={iouData}
                series={[
                  { name: t("training.train_iou"), color: "#10b981" },
                  { name: t("training.val_iou"), color: "#8b5cf6" },
                ]}
                height={220}
              />
            </div>
          </div>
        </section>

        {/* Hyperparameters & Log */}
        <section aria-label="Training details">
          <Tabs
            tabs={[
              { key: "logs", label: t("training.history") },
              { key: "hyperparams", label: t("training.hyperparameters") },
            ]}
            active={activeTab}
            onChange={setActiveTab}
          />

          <TabPanel active={activeTab} tab="logs">
            <div
              ref={logRef}
              className="mt-2 max-h-80 overflow-y-auto rounded-xl border border-gray-800 bg-gray-900 p-4 font-mono text-xs leading-relaxed"
              role="log"
              aria-live="polite"
            >
              {logs.length === 0 && (
                <p className="text-gray-500">{t("training.no_logs")}</p>
              )}
              {logs.map((line, i) => (
                <div key={i} className="flex gap-2">
                  <span className="text-gray-600">[{line.time}]</span>
                  <span className={logTypeColors[line.type]}>{line.text}</span>
                </div>
              ))}
            </div>
          </TabPanel>

          <TabPanel active={activeTab} tab="hyperparams">
            <div className="mt-2 grid grid-cols-1 gap-4 rounded-xl border border-gray-200 bg-white p-6 sm:grid-cols-2 lg:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.learning_rate")}</label>
                <input
                  type="number"
                  step="0.00001"
                  value={hyperparams.learningRate}
                  onChange={(e) => setHyperparams({ ...hyperparams, learningRate: parseFloat(e.target.value) || 1e-4 })}
                  disabled={status === "running"}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:opacity-50"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.batch_size")}</label>
                <input
                  type="number"
                  value={hyperparams.batchSize}
                  onChange={(e) => setHyperparams({ ...hyperparams, batchSize: parseInt(e.target.value) || 8 })}
                  disabled={status === "running"}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:opacity-50"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.epochs")}</label>
                <input
                  type="number"
                  value={hyperparams.epochs}
                  onChange={(e) => setHyperparams({ ...hyperparams, epochs: parseInt(e.target.value) || 100 })}
                  disabled={status === "running"}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:opacity-50"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.optimizer")}</label>
                <select
                  value={hyperparams.optimizer}
                  onChange={(e) => setHyperparams({ ...hyperparams, optimizer: e.target.value })}
                  disabled={status === "running"}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:opacity-50"
                >
                  <option value="adam">Adam</option>
                  <option value="adamw">AdamW</option>
                  <option value="sgd">SGD</option>
                  <option value="rmsprop">RMSprop</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.model")}</label>
                <select
                  value={hyperparams.model}
                  onChange={(e) => setHyperparams({ ...hyperparams, model: e.target.value })}
                  disabled={status === "running"}
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:opacity-50"
                >
                  <option value="unet">U-Net</option>
                  <option value="attention_unet">Attention U-Net</option>
                  <option value="unet_plus_plus">U-Net++</option>
                  <option value="deeplabv3plus">DeepLabV3+</option>
                </select>
              </div>
              <div className="flex items-end gap-6">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={hyperparams.augmentation}
                    onChange={(e) => setHyperparams({ ...hyperparams, augmentation: e.target.checked })}
                    disabled={status === "running"}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">{t("training.augmentation")}</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={hyperparams.tta}
                    onChange={(e) => setHyperparams({ ...hyperparams, tta: e.target.checked })}
                    disabled={status === "running"}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm text-gray-700">TTA</span>
                </label>
              </div>
            </div>
          </TabPanel>
        </section>

        {/* Control Buttons */}
        <section className="flex flex-wrap items-center gap-3" aria-label="Training controls">
          <button
            onClick={startTrainingHandler}
            disabled={status === "running"}
            className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium text-white transition-colors ${
              status === "running"
                ? "cursor-not-allowed bg-blue-400"
                : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            <Play className="h-4 w-4" />
            {t("training.start")}
          </button>
          <button
            onClick={pauseTrainingHandler}
            disabled={status !== "running"}
            className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors ${
              status === "running"
                ? "bg-amber-500 text-white hover:bg-amber-600"
                : "cursor-not-allowed bg-gray-200 text-gray-400"
            }`}
          >
            <Pause className="h-4 w-4" />
            {t("training.pause")}
          </button>
          <button
            onClick={stopTrainingHandler}
            disabled={status === "idle"}
            className={`flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium transition-colors ${
              status !== "idle"
                ? "bg-red-600 text-white hover:bg-red-700"
                : "cursor-not-allowed bg-gray-200 text-gray-400"
            }`}
          >
            <Square className="h-4 w-4" />
            {t("training.stop")}
          </button>
          <button
            onClick={resetTraining}
            disabled={status === "running"}
            className={`flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition-colors ${
              status === "running"
                ? "cursor-not-allowed border-gray-200 text-gray-300"
                : "border-gray-300 text-gray-700 hover:bg-gray-50"
            }`}
          >
            <RotateCcw className="h-4 w-4" />
            {t("training.reset")}
          </button>
          {status === "paused" && (
            <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-700">
              <AlertTriangle className="h-4 w-4" />
              {t("training.paused_banner")}
            </div>
          )}
        </section>
      </main>

      {/* Settings Modal */}
      <Modal open={showSettings} onClose={() => setShowSettings(false)} title={t("training.configuration")} size="lg">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">{t("training.settings_desc")}</p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.gpu_device")}</label>
              <select className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <option>CUDA:0 (NVIDIA RTX 4090)</option>
                <option>CUDA:1 (NVIDIA RTX 4090)</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.num_workers")}</label>
              <input type="number" defaultValue={4} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.precision")}</label>
              <select className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <option>fp32</option>
                <option>fp16 (mixed)</option>
                <option>bf16</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">{t("training.checkpoint_dir")}</label>
              <input type="text" defaultValue="checkpoints/" className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
}
