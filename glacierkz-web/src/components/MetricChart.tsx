'use client';

import React, { useState, useMemo, useRef, useCallback } from 'react';

export interface ChartDataPoint {
  x: number;
  y: number;
}

export interface ChartDataset {
  label: string;
  data: ChartDataPoint[];
  color: string;
}

interface MetricChartProps {
  data: ChartDataPoint[];
  title: string;
  xLabel?: string;
  yLabel?: string;
  datasets?: ChartDataset[];
}

const PADDING = { top: 24, right: 16, bottom: 32, left: 48 };

function niceRange(min: number, max: number, ticks = 5): [number, number, number[]] {
  if (min === max) { min -= 1; max += 1; }
  const range = max - min;
  const roughStep = range / ticks;
  const mag = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const norm = roughStep / mag;
  const step = norm < 1.5 ? mag : norm < 3 ? 2 * mag : norm < 7 ? 5 * mag : 10 * mag;
  const niceMin = Math.floor(min / step) * step;
  const niceMax = Math.ceil(max / step) * step;
  const ticksArr: number[] = [];
  for (let v = niceMin; v <= niceMax + step * 0.01; v += step) {
    ticksArr.push(parseFloat(v.toFixed(10)));
  }
  return [niceMin, niceMax, ticksArr];
}

export default function MetricChart({ data, title, xLabel, yLabel, datasets }: MetricChartProps) {
  const [tooltip, setTooltip] = useState<{ x: number; y: number; dx: number; dy: number; label?: string } | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const allPoints = useMemo(() => {
    const pts = [...data];
    datasets?.forEach((ds) => pts.push(...ds.data));
    return pts;
  }, [data, datasets]);

  const xValues = allPoints.map((p) => p.x);
  const yValues = allPoints.map((p) => p.y);
  const [xMin, xMax, xTicks] = niceRange(Math.min(...xValues), Math.max(...xValues), 6);
  const [yMin, yMax, yTicks] = niceRange(Math.min(...yValues), Math.max(...yValues), 5);

  const width = 600;
  const height = 300;
  const plotW = width - PADDING.left - PADDING.right;
  const plotH = height - PADDING.top - PADDING.bottom;

  const toSvgX = useCallback((v: number) => PADDING.left + ((v - xMin) / (xMax - xMin)) * plotW, [xMin, xMax, plotW]);
  const toSvgY = useCallback((v: number) => PADDING.top + plotH - ((v - yMin) / (yMax - yMin)) * plotH, [yMin, yMax, plotH]);

  const makePath = (points: ChartDataPoint[]) =>
    points.map((p, i) => `${i === 0 ? 'M' : 'L'}${toSvgX(p.x).toFixed(2)},${toSvgY(p.y).toFixed(2)}`).join(' ');

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const scaleX = width / rect.width;
      const scaleY = height / rect.height;
      const svgX = (e.clientX - rect.left) * scaleX;
      const svgY = (e.clientY - rect.top) * scaleY;

      const dx = xMin + ((svgX - PADDING.left) / plotW) * (xMax - xMin);
      const dy = yMin + ((PADDING.top + plotH - svgY) / plotH) * (yMax - yMin);

      setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top, dx, dy });
    },
    [xMin, xMax, yMin, yMax, plotW, plotH, width, height],
  );

  return (
    <div className="w-full rounded-xl border border-zinc-200 bg-white p-4" aria-label={`Chart: ${title}`}>
      <h3 className="mb-3 text-sm font-semibold text-zinc-800">{title}</h3>

      <div className="relative w-full" style={{ aspectRatio: `${width} / ${height}` }}>
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="h-full w-full"
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setTooltip(null)}
          role="img"
          aria-label={`${title} line chart`}
        >
          {/* Grid lines */}
          {yTicks.map((tick) => (
            <g key={`y-${tick}`}>
              <line
                x1={PADDING.left}
                y1={toSvgY(tick)}
                x2={PADDING.left + plotW}
                y2={toSvgY(tick)}
                stroke="#f4f4f5"
                strokeWidth="1"
              />
              <text
                x={PADDING.left - 8}
                y={toSvgY(tick) + 3}
                textAnchor="end"
                className="fill-zinc-400"
                fontSize="10"
              >
                {tick}
              </text>
            </g>
          ))}

          {xTicks.map((tick) => (
            <g key={`x-${tick}`}>
              <line
                x1={toSvgX(tick)}
                y1={PADDING.top}
                x2={toSvgX(tick)}
                y2={PADDING.top + plotH}
                stroke="#f4f4f5"
                strokeWidth="1"
              />
              <text
                x={toSvgX(tick)}
                y={PADDING.top + plotH + 16}
                textAnchor="middle"
                className="fill-zinc-400"
                fontSize="10"
              >
                {tick}
              </text>
            </g>
          ))}

          {/* Axes */}
          <line
            x1={PADDING.left}
            y1={PADDING.top}
            x2={PADDING.left}
            y2={PADDING.top + plotH}
            stroke="#d4d4d8"
            strokeWidth="1"
          />
          <line
            x1={PADDING.left}
            y1={PADDING.top + plotH}
            x2={PADDING.left + plotW}
            y2={PADDING.top + plotH}
            stroke="#d4d4d8"
            strokeWidth="1"
          />

          {/* Default dataset line */}
          {data.length > 1 && (
            <path d={makePath(data)} fill="none" stroke="#3b82f6" strokeWidth="2" strokeLinejoin="round" />
          )}

          {/* Additional datasets */}
          {datasets?.map((ds) =>
            ds.data.length > 1 ? (
              <path
                key={ds.label}
                d={makePath(ds.data)}
                fill="none"
                stroke={ds.color}
                strokeWidth="2"
                strokeLinejoin="round"
              />
            ) : null,
          )}

          {/* Data point dots */}
          {data.map((p, i) => (
            <circle
              key={`d-${i}`}
              cx={toSvgX(p.x)}
              cy={toSvgY(p.y)}
              r="3"
              fill="#3b82f6"
              className="opacity-0 hover:opacity-100 transition-opacity"
            />
          ))}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="pointer-events-none absolute z-10 rounded-lg bg-zinc-900 px-3 py-1.5 text-xs text-white shadow-lg"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
          >
            x: {tooltip.dx.toFixed(2)}, y: {tooltip.dy.toFixed(2)}
          </div>
        )}
      </div>

      {/* Labels */}
      <div className="mt-1 flex items-center justify-between px-1">
        {xLabel && <span className="text-[10px] text-zinc-400">{xLabel}</span>}
        {yLabel && <span className="text-[10px] text-zinc-400">{yLabel}</span>}
      </div>

      {/* Legend */}
      {datasets && datasets.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3 justify-center">
          {data.length > 0 && (
            <div className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full bg-blue-500" />
              <span className="text-[10px] text-zinc-500">Primary</span>
            </div>
          )}
          {datasets.map((ds) => (
            <div key={ds.label} className="flex items-center gap-1.5">
              <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: ds.color }} />
              <span className="text-[10px] text-zinc-500">{ds.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
