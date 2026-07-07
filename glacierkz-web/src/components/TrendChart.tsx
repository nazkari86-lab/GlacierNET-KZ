"use client";

import { useEffect, useState } from "react";
import { TrendResult } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface TrendChartProps {
  data: TrendResult;
}

export default function TrendChart({ data }: TrendChartProps) {
  const [isMounted, setIsMounted] = useState(false);
  useEffect(() => setIsMounted(true), []);

  const combined = [
    ...data.data.map((d) => ({ year: d.year, "Actual (km²)": d.area_km2, "Forecast (km²)": null })),
    ...data.forecast.map((d) => ({ year: d.year, "Actual (km²)": null, "Forecast (km²)": d.area_km2 })),
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-zinc-200 p-4 min-w-0">
        {isMounted ? (
          <ResponsiveContainer width="100%" height={300} minWidth={1} minHeight={1}>
            <LineChart data={combined}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis unit=" km²" />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="Actual (km²)" stroke="#2563eb" strokeWidth={2} dot={{ r: 4 }} connectNulls />
              <Line
                type="monotone"
                dataKey="Forecast (km²)"
                stroke="#dc2626"
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={{ r: 4 }}
                connectNulls
              />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-[300px] w-full rounded bg-zinc-50" />
        )}
      </div>
      <div className="grid grid-cols-3 gap-4 text-sm">
        <div className="rounded-lg bg-zinc-50 p-3 text-center">
          <p className="text-zinc-500">Loss Rate</p>
          <p className="text-lg font-bold text-red-600">{data.loss_rate_km2_per_year.toFixed(3)} km²/yr</p>
        </div>
        <div className="rounded-lg bg-zinc-50 p-3 text-center">
          <p className="text-zinc-500">Total Loss</p>
          <p className="text-lg font-bold text-red-600">{data.total_loss_percent.toFixed(1)}%</p>
        </div>
        <div className="rounded-lg bg-zinc-50 p-3 text-center">
          <p className="text-zinc-500">R² Fit</p>
          <p className="text-lg font-bold text-blue-600">{data.r_squared.toFixed(3)}</p>
        </div>
      </div>
    </div>
  );
}
