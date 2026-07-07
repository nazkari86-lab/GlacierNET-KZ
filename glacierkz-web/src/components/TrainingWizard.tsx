'use client';

import React, { useState, useCallback } from 'react';
import type { ModelInfo } from '@/lib/api';

export interface DatasetInfo {
  id: string;
  name: string;
  year: number;
  size: number;
  bandCount: number;
}

export interface TrainConfig {
  datasetId: string;
  modelName: string;
  epochs: number;
  batchSize: number;
  learningRate: number;
  useTta: boolean;
  useCrf: boolean;
}

interface TrainingWizardProps {
  onComplete: (config: TrainConfig) => void;
  datasets: DatasetInfo[];
  models?: ModelInfo[];
}

const STEPS = [
  { id: 1, label: 'Dataset' },
  { id: 2, label: 'Model' },
  { id: 3, label: 'Params' },
  { id: 4, label: 'Review' },
] as const;

function StepIndicator({ current }: { current: number }) {
  return (
    <nav aria-label="Training wizard progress" className="flex items-center justify-center mb-8">
      <ol className="flex items-center gap-0">
        {STEPS.map((step, i) => {
          const isCompleted = current > step.id;
          const isCurrent = current === step.id;
          return (
            <li key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-9 w-9 items-center justify-center rounded-full border-2 text-sm font-semibold transition-colors ${
                    isCompleted
                      ? 'border-emerald-500 bg-emerald-500 text-white'
                      : isCurrent
                        ? 'border-blue-500 bg-blue-500 text-white'
                        : 'border-zinc-300 bg-white text-zinc-500'
                  }`}
                  aria-current={isCurrent ? 'step' : undefined}
                >
                  {isCompleted ? (
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    step.id
                  )}
                </div>
                <span
                  className={`mt-1.5 text-xs font-medium ${
                    isCurrent ? 'text-blue-600' : isCompleted ? 'text-emerald-600' : 'text-zinc-400'
                  }`}
                >
                  {step.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`mx-2 h-0.5 w-12 sm:w-16 ${
                    current > step.id ? 'bg-emerald-500' : 'bg-zinc-200'
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export default function TrainingWizard({ onComplete, datasets }: TrainingWizardProps) {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState<TrainConfig>({
    datasetId: datasets[0]?.id ?? '',
    modelName: 'unet',
    epochs: 100,
    batchSize: 8,
    learningRate: 1e-4,
    useTta: false,
    useCrf: false,
  });

  const selectedDataset = datasets.find((d) => d.id === config.datasetId);

  const canNext = useCallback(() => {
    if (step === 1) return !!config.datasetId;
    if (step === 2) return !!config.modelName;
    if (step === 3) return config.epochs > 0 && config.batchSize > 0 && config.learningRate > 0;
    return true;
  }, [step, config]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && canNext()) {
        if (step < 4) {
          e.preventDefault();
          setStep(step + 1);
        } else {
          e.preventDefault();
          onComplete(config);
        }
      }
      if (e.key === 'Backspace' && step > 1) {
        e.preventDefault();
        setStep(step - 1);
      }
    },
    [step, canNext, config, onComplete]
  );

  return (
    <div
      className="mx-auto max-w-2xl rounded-2xl bg-white p-6 shadow-lg ring-1 ring-zinc-200"
      role="wizard"
      aria-label="Training configuration wizard"
      onKeyDown={handleKeyDown}
    >
      <StepIndicator current={step} />

      {step === 1 && (
        <fieldset aria-label="Dataset selection">
          <legend className="text-lg font-semibold text-zinc-900">Select a Dataset</legend>
          <p className="mt-1 text-sm text-zinc-500">Choose the training data for your model.</p>
          <div className="mt-4 space-y-2">
            {datasets.length === 0 && (
              <p className="rounded-lg bg-zinc-50 p-4 text-sm text-zinc-400">No datasets available.</p>
            )}
            {datasets.map((ds) => (
              <button
                key={ds.id}
                role="radio"
                aria-checked={config.datasetId === ds.id}
                onClick={() => setConfig({ ...config, datasetId: ds.id })}
                className={`w-full rounded-xl border-2 p-4 text-left transition-all ${
                  config.datasetId === ds.id
                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-200'
                    : 'border-zinc-200 hover:border-zinc-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-semibold text-zinc-900">{ds.name}</div>
                    <div className="mt-0.5 text-xs text-zinc-500">
                      Year {ds.year} &middot; {ds.bandCount} bands &middot; {formatBytes(ds.size)}
                    </div>
                  </div>
                  {config.datasetId === ds.id && (
                    <div className="h-5 w-5 rounded-full bg-blue-500 flex items-center justify-center">
                      <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {step === 2 && (
        <fieldset aria-label="Model selection">
          <legend className="text-lg font-semibold text-zinc-900">Select a Model</legend>
          <p className="mt-1 text-sm text-zinc-500">Pick the architecture for training.</p>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {['unet', 'attention_unet', 'random_forest', 'ndsi', 'ensemble'].map((m) => (
              <button
                key={m}
                role="radio"
                aria-checked={config.modelName === m}
                onClick={() => setConfig({ ...config, modelName: m })}
                className={`rounded-xl border-2 p-3 text-left transition-all ${
                  config.modelName === m
                    ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-200'
                    : 'border-zinc-200 hover:border-zinc-300'
                }`}
              >
                <div className="text-sm font-semibold text-zinc-900 capitalize">
                  {m.replace('_', ' ')}
                </div>
              </button>
            ))}
          </div>
        </fieldset>
      )}

      {step === 3 && (
        <fieldset aria-label="Training parameters">
          <legend className="text-lg font-semibold text-zinc-900">Training Parameters</legend>
          <div className="mt-4 space-y-4">
            <div>
              <label htmlFor="wiz-epochs" className="block text-sm font-medium text-zinc-700">Epochs</label>
              <input
                id="wiz-epochs"
                type="number"
                min={1}
                max={1000}
                value={config.epochs}
                onChange={(e) => setConfig({ ...config, epochs: Number(e.target.value) })}
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label htmlFor="wiz-batch" className="block text-sm font-medium text-zinc-700">Batch Size</label>
              <input
                id="wiz-batch"
                type="number"
                min={1}
                max={256}
                value={config.batchSize}
                onChange={(e) => setConfig({ ...config, batchSize: Number(e.target.value) })}
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label htmlFor="wiz-lr" className="block text-sm font-medium text-zinc-700">Learning Rate</label>
              <input
                id="wiz-lr"
                type="number"
                step={0.0001}
                min={0.00001}
                value={config.learningRate}
                onChange={(e) => setConfig({ ...config, learningRate: Number(e.target.value) })}
                className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm text-zinc-700">
                <input
                  type="checkbox"
                  checked={config.useTta}
                  onChange={(e) => setConfig({ ...config, useTta: e.target.checked })}
                  className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
                />
                Test-time augmentation
              </label>
              <label className="flex items-center gap-2 text-sm text-zinc-700">
                <input
                  type="checkbox"
                  checked={config.useCrf}
                  onChange={(e) => setConfig({ ...config, useCrf: e.target.checked })}
                  className="h-4 w-4 rounded border-zinc-300 text-blue-600 focus:ring-blue-500"
                />
                CRF post-processing
              </label>
            </div>
          </div>
        </fieldset>
      )}

      {step === 4 && (
        <div aria-label="Review and start">
          <h2 className="text-lg font-semibold text-zinc-900">Review Configuration</h2>
          <div className="mt-4 rounded-xl bg-zinc-50 p-4 space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-zinc-500">Dataset</span>
              <span className="font-medium text-zinc-900">{selectedDataset?.name ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Model</span>
              <span className="font-medium text-zinc-900 capitalize">{config.modelName.replace('_', ' ')}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Epochs</span>
              <span className="font-medium text-zinc-900">{config.epochs}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Batch Size</span>
              <span className="font-medium text-zinc-900">{config.batchSize}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Learning Rate</span>
              <span className="font-medium text-zinc-900">{config.learningRate}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">TTA / CRF</span>
              <span className="font-medium text-zinc-900">
                {config.useTta ? 'Yes' : 'No'} / {config.useCrf ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
        </div>
      )}

      <div className="mt-8 flex items-center justify-between" role="group" aria-label="Wizard navigation">
        <button
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
          className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-700 transition-colors hover:bg-zinc-50 disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Go to previous step"
        >
          Back
        </button>
        {step < 4 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={!canNext()}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
            aria-label="Go to next step"
          >
            Next
          </button>
        ) : (
          <button
            onClick={() => onComplete(config)}
            className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-700"
            aria-label="Start training"
          >
            Start Training
          </button>
        )}
      </div>
    </div>
  );
}
