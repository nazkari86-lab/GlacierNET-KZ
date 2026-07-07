"use client";

/* eslint-disable @next/next/no-img-element -- segmentation overlays can be dynamic API/blob URLs. */

import { CompareSegment } from "@/lib/api";

interface SplitViewProps {
  segments: CompareSegment[];
  imageUrl?: string;
}

export default function SplitView({ segments, imageUrl }: SplitViewProps) {
  const MODEL_COLORS = ["#2563eb", "#7c3aed", "#059669", "#ea580c", "#dc2626"];

  return (
    <div className="space-y-4">
      {segments.map((seg, i) => (
        <div key={seg.model_name} className="rounded-xl border border-zinc-200 p-4">
          <div className="mb-2 flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: MODEL_COLORS[i % MODEL_COLORS.length] }} />
            <span className="font-semibold">{seg.model_name}</span>
            <span className="ml-auto text-sm text-zinc-500">{seg.area_km2.toFixed(2)} km²</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {imageUrl && (
              <div>
                <p className="mb-1 text-xs text-zinc-400">Original</p>
                <img src={imageUrl} alt="Original" className="w-full rounded-lg" />
              </div>
            )}
            <div>
              <p className="mb-1 text-xs text-zinc-400">Segmentation</p>
              <img
                src={seg.overlay_path || seg.mask_path}
                alt={seg.model_name}
                className="w-full rounded-lg"
              />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
