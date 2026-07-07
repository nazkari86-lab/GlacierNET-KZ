'use client';

import React from 'react';
import type { ModelInfo } from '@/lib/api';
import { cn } from '@/lib/utils';

interface ModelSelectorProps {
  selectedModel: string;
  onSelect: (model: string) => void;
  models: ModelInfo[];
}

type Complexity = 'Low' | 'Medium' | 'High';

const COMPLEXITY_STYLE: Record<Complexity, string> = {
  Low: 'bg-emerald-100 text-emerald-700',
  Medium: 'bg-amber-100 text-amber-700',
  High: 'bg-red-100 text-red-700',
};

const USE_CASE: Record<string, string> = {
  unet: 'General-purpose segmentation',
  attention_unet: 'High-accuracy with attention gates',
  ndsi: 'Fast threshold-based classification',
  random_forest: 'Interpretable pixel classification',
  ensemble: 'Combined prediction for robustness',
};

const COMPLEXITY_MAP: Record<string, Complexity> = {
  unet: 'Medium',
  attention_unet: 'High',
  ndsi: 'Low',
  random_forest: 'Medium',
  ensemble: 'High',
};

const MODEL_ICON: Record<string, string> = {
  unet: '🔵',
  attention_unet: '🟣',
  ndsi: '🟢',
  random_forest: '🟠',
  ensemble: '🔴',
};

export default function ModelSelector({ selectedModel, onSelect, models }: ModelSelectorProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3" role="radiogroup" aria-label="Model selection">
      {models.map((model) => {
        const isSelected = selectedModel === model.name;
        const complexity = COMPLEXITY_MAP[model.name] ?? 'Medium';
        const useCase = USE_CASE[model.name] ?? model.description;

        return (
          <button
            key={model.name}
            role="radio"
            aria-checked={isSelected}
            aria-label={`${model.display_name} — ${complexity} complexity — ${useCase}`}
            onClick={() => onSelect(model.name)}
            className={cn(
              'group relative rounded-xl border-2 p-4 text-left transition-all',
              isSelected
                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200 shadow-sm'
                : 'border-zinc-200 hover:border-zinc-300 hover:shadow-sm',
            )}
          >
            {isSelected && (
              <div className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-blue-500">
                <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}

            <div className="flex items-start gap-3">
              <span className="text-xl" aria-hidden="true">
                {MODEL_ICON[model.name] ?? '⚪'}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-zinc-900">{model.display_name}</div>
                <div className="mt-1 text-xs text-zinc-500 line-clamp-2">{useCase}</div>
              </div>
            </div>

            <div className="mt-3 flex items-center gap-2">
              <span
                className={cn('inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold', COMPLEXITY_STYLE[complexity])}
              >
                {complexity}
              </span>
              {model.supports_tta && (
                <span className="inline-block rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-600">
                  TTA
                </span>
              )}
              {model.supports_crf && (
                <span className="inline-block rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-medium text-zinc-600">
                  CRF
                </span>
              )}
            </div>

            <div className="mt-2 text-[10px] text-zinc-400 capitalize">{model.name.replace('_', ' ')}</div>
          </button>
        );
      })}
    </div>
  );
}
