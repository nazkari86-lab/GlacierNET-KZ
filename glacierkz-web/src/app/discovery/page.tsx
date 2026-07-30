"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Beaker,
  Database,
  GitCompareArrows,
  MapPinned,
  ShieldAlert,
} from "lucide-react";

import DiscoveryPassportPanel from "@/components/DiscoveryPassportPanel";
import {
  fetchCryoGenesisDiscoveries,
  fetchCryoGenesisPassport,
  fetchGlacier,
  fetchGlacierSeries,
  type GlacierRecord,
  type GlacierTimeSeries,
} from "@/lib/api";
import type {
  CryoGenesisDiscoverySummary,
  CryoGenesisTwinMatch,
  DiscoveryPassport,
} from "@/lib/cryogenesis";

const CryoGenesisMap = dynamic(
  () => import("@/components/CryoGenesisMap"),
  { ssr: false },
);

export default function DiscoveryPage() {
  const [discoveries, setDiscoveries] = useState<
    CryoGenesisDiscoverySummary[]
  >([]);
  const [passport, setPassport] = useState<DiscoveryPassport | null>(null);
  const [selectedRgiId, setSelectedRgiId] = useState("");
  const [geometries, setGeometries] = useState<Record<string, GlacierRecord>>(
    {},
  );
  const [series, setSeries] = useState<Record<string, GlacierTimeSeries>>({});
  const [sourceErrors, setSourceErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCryoGenesisDiscoveries()
      .then((payload) => {
        setDiscoveries(payload.items);
        setSelectedRgiId(payload.items[0]?.target_rgi_id ?? "");
        if (payload.status !== "ready") {
          setError("No validated physical discovery cohort is available.");
        }
      })
      .catch((cause) =>
        setError(
          cause instanceof Error
            ? cause.message
            : "CryoGenesis API is unavailable.",
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedRgiId) {
      setPassport(null);
      return;
    }
    setError("");
    fetchCryoGenesisPassport(selectedRgiId)
      .then(setPassport)
      .catch((cause) =>
        setError(
          cause instanceof Error
            ? cause.message
            : "Exact passport lookup failed.",
        ),
      );
  }, [selectedRgiId]);

  useEffect(() => {
    if (!passport) return;
    const ids = [
      passport.target_rgi_id,
      ...passport.match.twins.map((item) => item.rgi_id),
    ];
    setGeometries({});
    setSeries({});
    setSourceErrors({});
    Promise.allSettled(
      ids.map(async (rgiId) => {
        const [glacier, timeSeries] = await Promise.all([
          fetchGlacier(rgiId),
          fetchGlacierSeries(rgiId),
        ]);
        return { rgiId, glacier, timeSeries };
      }),
    ).then((results) => {
      const nextGeometries: Record<string, GlacierRecord> = {};
      const nextSeries: Record<string, GlacierTimeSeries> = {};
      const nextErrors: Record<string, string> = {};
      results.forEach((result, index) => {
        const rgiId = ids[index];
        if (result.status === "fulfilled") {
          nextGeometries[rgiId] = result.value.glacier;
          nextSeries[rgiId] = result.value.timeSeries;
        } else {
          nextErrors[rgiId] =
            result.reason instanceof Error
              ? result.reason.message
              : "Exact geometry or time series unavailable.";
        }
      });
      setGeometries(nextGeometries);
      setSeries(nextSeries);
      setSourceErrors(nextErrors);
    });
  }, [passport]);

  const target = passport ? geometries[passport.target_rgi_id] ?? null : null;
  const twins = useMemo(
    () =>
      passport?.match.twins.flatMap((match) => {
        const glacier = geometries[match.rgi_id];
        return glacier ? [{ glacier, match }] : [];
      }) ?? [],
    [geometries, passport],
  );
  const selectedMapId =
    selectedRgiId && geometries[selectedRgiId]
      ? selectedRgiId
      : passport?.target_rgi_id ?? "";
  const selectMapObject = useCallback((rgiId: string) => {
    const element = document.getElementById(`object-${rgiId}`);
    element?.focus();
  }, []);

  const trajectoryIds = passport
    ? [
        passport.target_rgi_id,
        ...(passport.match.twins[0]
          ? [passport.match.twins[0].rgi_id]
          : []),
      ]
    : [];

  return (
    <main
      id="main-content"
      className="min-h-screen bg-[radial-gradient(circle_at_top_left,_#cffafe_0,_transparent_28rem),linear-gradient(#f8fafc,#eef2ff)] px-4 py-8 text-slate-950"
    >
      <div className="mx-auto max-w-[1500px] space-y-6">
        <header className="rounded-3xl border border-white/80 bg-white/90 p-6 shadow-sm backdrop-blur lg:p-8">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <Link
              href="/hub"
              className="inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-blue-800"
            >
              <ArrowLeft className="h-4 w-4" />
              Project hub
            </Link>
            <span className="rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-bold text-violet-800">
              Release 1 · retrospective evidence
            </span>
          </div>
          <div className="mt-6 max-w-5xl">
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-800">
              CryoGenesis X
            </p>
            <h1 className="mt-2 text-4xl font-bold tracking-tight sm:text-5xl">
              CryoGenesis: which similar glaciers diverged—and where should
              science look next?
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-slate-600">
              Every target is compared with physical, pre-outcome matched
              glaciers. The workspace exposes the distance, mapped-area
              difference, uncertainty boundary, source hashes, and reasons to
              abstain.
            </p>
          </div>
        </header>

        {error && (
          <div
            role="alert"
            className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950"
          >
            {error}
          </div>
        )}

        <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
          <aside className="rounded-3xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="flex items-center gap-3 px-2 py-2">
              <Beaker className="h-5 w-5 text-violet-700" />
              <div>
                <h2 className="font-semibold">Discovery queue</h2>
                <p className="text-xs text-slate-500">
                  {discoveries.length} validated passports
                </p>
              </div>
            </div>
            <div className="mt-3 max-h-[760px] space-y-2 overflow-y-auto pr-1">
              {loading && (
                <p className="p-3 text-sm text-slate-500">
                  Loading physical cohort…
                </p>
              )}
              {!loading && discoveries.length === 0 && (
                <p className="rounded-xl bg-slate-50 p-3 text-sm text-slate-600">
                  No synthetic fallback is shown. Build or mount a validated
                  cohort first.
                </p>
              )}
              {discoveries.map((item, index) => (
                <button
                  key={item.target_rgi_id}
                  type="button"
                  onClick={() => setSelectedRgiId(item.target_rgi_id)}
                  className={`w-full rounded-2xl border p-4 text-left transition ${
                    selectedRgiId === item.target_rgi_id
                      ? "border-cyan-400 bg-cyan-50 shadow-sm"
                      : "border-slate-200 hover:border-violet-300"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-500">
                      #{index + 1}
                    </span>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-bold uppercase tracking-wide">
                      {item.match_status.replaceAll("_", " ")}
                    </span>
                  </div>
                  <p className="mt-3 break-all font-mono text-xs font-bold">
                    {item.target_rgi_id}
                  </p>
                  <p className="mt-2 text-sm font-semibold text-violet-800">
                    {item.surprise_class.replaceAll("_", " ")}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.twin_count} comparators · divergence{" "}
                    {item.raw_divergence !== null
                      ? `${(item.raw_divergence * 100).toFixed(2)}%`
                      : "abstained"}
                  </p>
                </button>
              ))}
            </div>
          </aside>

          <div className="min-w-0 space-y-6">
            {passport && (
              <>
                <section className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,.65fr)]">
                  <div className="rounded-3xl border border-slate-200 bg-white p-3 shadow-sm">
                    <CryoGenesisMap
                      target={target}
                      twins={twins}
                      selectedRgiId={selectedMapId}
                      onSelect={selectMapObject}
                    />
                  </div>
                  <div className="space-y-4">
                    <EvidenceCard
                      icon={<Database className="h-5 w-5" />}
                      title="Supporting evidence"
                      body={`${passport.match.twins.length} pre-outcome comparators passed the frozen split, feature support, and distance checks. ${passport.provenance.length} source assets are content-addressed.`}
                      tone="cyan"
                    />
                    <EvidenceCard
                      icon={<GitCompareArrows className="h-5 w-5" />}
                      title="Contradicting / sensitivity evidence"
                      body={
                        passport.divergence
                          ? `Removing one twin moves the comparator between ${(passport.divergence.leave_one_out_range[0] * 100).toFixed(2)}% and ${(passport.divergence.leave_one_out_range[1] * 100).toFixed(2)}%.`
                          : "Comparison did not meet the minimum support needed to estimate divergence."
                      }
                      tone="violet"
                    />
                    <EvidenceCard
                      icon={<ShieldAlert className="h-5 w-5" />}
                      title="Missing evidence"
                      body="Mechanism-specific velocity, debris, lake-contact and field evidence remain unscored in Release 1. The result cannot identify cause or operational risk."
                      tone="amber"
                    />
                  </div>
                </section>

                <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                  <div className="flex items-center gap-3">
                    <MapPinned className="h-5 w-5 text-cyan-700" />
                    <div>
                      <h2 className="font-semibold">
                        Exact objects and matching diagnostics
                      </h2>
                      <p className="text-sm text-slate-500">
                        This table remains usable without the map or tile
                        network.
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[720px] text-left text-sm">
                      <thead className="border-b text-xs uppercase tracking-wide text-slate-500">
                        <tr>
                          <th className="px-3 py-3">Role</th>
                          <th className="px-3 py-3">RGI ID</th>
                          <th className="px-3 py-3">Distance</th>
                          <th className="px-3 py-3">Weight</th>
                          <th className="px-3 py-3">Exact local source</th>
                        </tr>
                      </thead>
                      <tbody>
                        <ObjectRow
                          rgiId={passport.target_rgi_id}
                          role="Target"
                          loaded={Boolean(geometries[passport.target_rgi_id])}
                          error={sourceErrors[passport.target_rgi_id]}
                        />
                        {passport.match.twins.map((match) => (
                          <ObjectRow
                            key={match.rgi_id}
                            rgiId={match.rgi_id}
                            role="Twin"
                            match={match}
                            loaded={Boolean(geometries[match.rgi_id])}
                            error={sourceErrors[match.rgi_id]}
                          />
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <TrajectoryChart
                  series={trajectoryIds.flatMap((id) =>
                    series[id] ? [series[id]] : [],
                  )}
                />
                <ComponentDistanceTable passport={passport} />
                <DiscoveryPassportPanel passport={passport} />
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

function EvidenceCard({
  icon,
  title,
  body,
  tone,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  tone: "cyan" | "violet" | "amber";
}) {
  const styles = {
    cyan: "border-cyan-200 bg-cyan-50 text-cyan-950",
    violet: "border-violet-200 bg-violet-50 text-violet-950",
    amber: "border-amber-200 bg-amber-50 text-amber-950",
  }[tone];
  return (
    <section className={`rounded-3xl border p-5 ${styles}`}>
      <div className="flex items-center gap-2 font-semibold">
        {icon}
        <h2>{title}</h2>
      </div>
      <p className="mt-3 text-sm leading-6">{body}</p>
    </section>
  );
}

function ObjectRow({
  rgiId,
  role,
  match,
  loaded,
  error,
}: {
  rgiId: string;
  role: string;
  match?: CryoGenesisTwinMatch;
  loaded: boolean;
  error?: string;
}) {
  return (
    <tr
      id={`object-${rgiId}`}
      tabIndex={-1}
      className="border-b border-slate-100 focus:bg-cyan-50 focus:outline-none"
    >
      <td className="px-3 py-3 font-semibold">{role}</td>
      <td className="px-3 py-3 font-mono text-xs">{rgiId}</td>
      <td className="px-3 py-3 tabular-nums">
        {match?.total_distance.toFixed(3) ?? "—"}
      </td>
      <td className="px-3 py-3 tabular-nums">
        {match ? `${(match.weight * 100).toFixed(1)}%` : "—"}
      </td>
      <td className="px-3 py-3">
        <span className={loaded ? "text-emerald-700" : "text-amber-800"}>
          {loaded ? "RGI geometry + annual series" : error ?? "Loading…"}
        </span>
      </td>
    </tr>
  );
}

function ComponentDistanceTable({
  passport,
}: {
  passport: DiscoveryPassport;
}) {
  const features = Array.from(
    new Set(
      passport.match.twins.flatMap((twin) =>
        Object.keys(twin.component_distances),
      ),
    ),
  ).sort();
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">
        Why each comparator was selected
      </h2>
      <p className="mt-1 text-sm text-slate-500">
        Lower robust-scaled component distance means greater pre-outcome
        similarity.
      </p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[700px] text-sm">
          <thead>
            <tr className="border-b text-left text-xs uppercase text-slate-500">
              <th className="p-3">Twin</th>
              {features.map((feature) => (
                <th key={feature} className="p-3">
                  {feature.replaceAll("_", " ")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {passport.match.twins.map((twin) => (
              <tr key={twin.rgi_id} className="border-b border-slate-100">
                <td className="p-3 font-mono text-xs">{twin.rgi_id}</td>
                {features.map((feature) => (
                  <td key={feature} className="p-3 tabular-nums">
                    {twin.component_distances[feature]?.toFixed(3) ?? "—"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function TrajectoryChart({ series }: { series: GlacierTimeSeries[] }) {
  const points = series.flatMap((item) => item.points);
  if (!points.length) {
    return (
      <section className="rounded-3xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
        Exact annual trajectories are unavailable; no chart is fabricated.
      </section>
    );
  }
  const years = points.map((point) => point.year);
  const areas = points.map((point) => point.area_km2);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const minArea = Math.min(...areas);
  const maxArea = Math.max(...areas);
  const x = (year: number) =>
    36 + ((year - minYear) / Math.max(maxYear - minYear, 1)) * 728;
  const y = (area: number) =>
    32 + (1 - (area - minArea) / Math.max(maxArea - minArea, 1e-9)) * 208;
  const colors = ["#0891b2", "#7c3aed"];
  return (
    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Observed annual trajectories</h2>
      <p className="mt-1 text-sm text-slate-500">
        Existing exact glacier series; not a fitted forecast.
      </p>
      <svg
        viewBox="0 0 800 280"
        className="mt-4 h-auto w-full"
        role="img"
        aria-label="Mapped glacier area trajectories"
      >
        <line x1="36" y1="240" x2="764" y2="240" stroke="#cbd5e1" />
        <line x1="36" y1="32" x2="36" y2="240" stroke="#cbd5e1" />
        {series.map((item, index) => {
          const path = item.points
            .map(
              (point, pointIndex) =>
                `${pointIndex ? "L" : "M"} ${x(point.year)} ${y(point.area_km2)}`,
            )
            .join(" ");
          return (
            <g key={item.glacier.rgi_id}>
              <path
                d={path}
                fill="none"
                stroke={colors[index] ?? "#334155"}
                strokeWidth="4"
                strokeLinecap="round"
              />
              {item.points.map((point) => (
                <circle
                  key={point.year}
                  cx={x(point.year)}
                  cy={y(point.area_km2)}
                  r="4"
                  fill={colors[index] ?? "#334155"}
                >
                  <title>
                    {item.glacier.rgi_id}: {point.year}, {point.area_km2} km²
                  </title>
                </circle>
              ))}
            </g>
          );
        })}
        <text x="36" y="262" fontSize="12" fill="#64748b">
          {minYear}
        </text>
        <text x="740" y="262" fontSize="12" fill="#64748b">
          {maxYear}
        </text>
      </svg>
      <div className="mt-3 flex flex-wrap gap-4 text-xs">
        {series.map((item, index) => (
          <span key={item.glacier.rgi_id} className="flex items-center gap-2">
            <i
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: colors[index] ?? "#334155" }}
            />
            <span className="font-mono">{item.glacier.rgi_id}</span>
          </span>
        ))}
      </div>
    </section>
  );
}
