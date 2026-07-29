import { AlertTriangle, CheckCircle2, Fingerprint, Scale } from "lucide-react";

import type { DiscoveryPassport } from "@/lib/cryogenesis";

function title(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function percent(value: number | null | undefined) {
  return value === null || value === undefined
    ? "Not measured"
    : `${(value * 100).toFixed(2)}%`;
}

export default function DiscoveryPassportPanel({
  passport,
}: {
  passport: DiscoveryPassport;
}) {
  return (
    <section
      aria-labelledby="passport-heading"
      className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm"
    >
      <div className="border-b border-slate-200 bg-slate-950 p-6 text-white">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-300">
              Verified Discovery Passport
            </p>
            <h2 id="passport-heading" className="mt-2 text-2xl font-semibold">
              {title(passport.surprise_class)}
            </h2>
            <p className="mt-2 font-mono text-xs text-slate-300">
              {passport.target_rgi_id} · {passport.cohort_id}
            </p>
          </div>
          <span className="rounded-full border border-cyan-400/40 bg-cyan-300/10 px-3 py-1 text-xs font-bold text-cyan-200">
            {title(passport.claim_tier)}
          </span>
        </div>
        {passport.divergence && (
          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <Metric
              label="Target change"
              value={percent(passport.divergence.target_outcome)}
            />
            <Metric
              label="Twin comparator"
              value={percent(passport.divergence.comparator_outcome)}
            />
            <Metric
              label="Measured divergence"
              value={percent(passport.divergence.raw_divergence)}
            />
          </div>
        )}
      </div>

      <div className="grid gap-4 p-6 lg:grid-cols-2">
        <ClaimBlock
          title="What this evidence supports"
          icon={<CheckCircle2 className="h-5 w-5" />}
          items={passport.claims_allowed}
          tone="emerald"
        />
        <ClaimBlock
          title="What it must not claim"
          icon={<AlertTriangle className="h-5 w-5" />}
          items={passport.claims_not_allowed}
          tone="amber"
        />
      </div>

      <div className="border-t border-slate-100 px-6 py-5">
        <div className="flex items-start gap-3">
          <Scale className="mt-0.5 h-5 w-5 shrink-0 text-violet-700" />
          <div>
            <h3 className="font-semibold text-slate-950">
              Retrospective, not causal
            </h3>
            <p className="mt-1 text-sm leading-6 text-slate-600">
              Twins are auditable matched comparators. Difference from them is
              a discovery candidate, not proof that a mechanism caused the
              observed mapped-area change.
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 bg-slate-50 px-6 py-4 font-mono text-[11px] text-slate-500">
        <Fingerprint className="h-4 w-4" />
        <span>SHA-256</span>
        <span className="break-all">{passport.payload_sha256}</span>
        {passport.download_url && (
          <a
            href={passport.download_url}
            download
            className="ml-auto font-sans font-bold text-blue-700 underline"
          >
            Download JSON
          </a>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
    </div>
  );
}

function ClaimBlock({
  title,
  icon,
  items,
  tone,
}: {
  title: string;
  icon: React.ReactNode;
  items: string[];
  tone: "emerald" | "amber";
}) {
  const styles =
    tone === "emerald"
      ? "border-emerald-200 bg-emerald-50 text-emerald-950"
      : "border-amber-200 bg-amber-50 text-amber-950";
  return (
    <div className={`rounded-2xl border p-4 ${styles}`}>
      <div className="flex items-center gap-2 font-semibold">
        {icon}
        <h3>{title}</h3>
      </div>
      <ul className="mt-3 space-y-2 text-sm">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span aria-hidden>•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

