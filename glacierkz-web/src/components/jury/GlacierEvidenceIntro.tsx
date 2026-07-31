type GlacierEvidenceIntroProps = {
  comparableYears: number | null;
  scannedLakes: number | null;
  selectedPriority: number | null;
};

function factValue(value: number | null, fallback = "—") {
  return value === null || !Number.isFinite(value) ? fallback : value.toLocaleString("ru-RU");
}

/**
 * A small, decorative glacier scene with facts duplicated in HTML below it.
 * The SVG itself is hidden from assistive technology; the adjacent list is the
 * accessible source of the same information.
 */
export default function GlacierEvidenceIntro({
  comparableYears,
  scannedLakes,
  selectedPriority,
}: GlacierEvidenceIntroProps) {
  return <section aria-label="Анимация ледника и ключевые факты" className="jury-glacier-intro mt-6 overflow-hidden rounded-2xl border border-cyan-200/20 bg-cyan-950/30">
    <div className="relative h-44 overflow-hidden sm:h-52">
      <svg viewBox="0 0 560 250" preserveAspectRatio="xMidYMid slice" className="h-full w-full" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="jury-sky" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#082f49" />
            <stop offset="0.55" stopColor="#164e63" />
            <stop offset="1" stopColor="#0f172a" />
          </linearGradient>
          <linearGradient id="jury-ice" x1="0" y1="0" x2="0.8" y2="1">
            <stop offset="0" stopColor="#dff9ff" />
            <stop offset="0.45" stopColor="#67e8f9" />
            <stop offset="1" stopColor="#0891b2" />
          </linearGradient>
          <linearGradient id="jury-ridge" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#475569" />
            <stop offset="1" stopColor="#0f172a" />
          </linearGradient>
          <filter id="jury-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <rect width="560" height="250" fill="url(#jury-sky)" />
        <path d="M0 160 77 78l59 61 65-103 76 112 55-68 93 102 52-56 83 59v65H0Z" fill="url(#jury-ridge)" opacity="0.9" />
        <path d="m94 190 77-84 41 50 58-93 62 96 41-45 86 89H94Z" fill="#334155" opacity="0.94" />
        <path className="jury-glacier-ice" d="m190 164 39-36 39 17 35-36 56 59-23 42-73 1-49-18-45 12Z" fill="url(#jury-ice)" filter="url(#jury-glow)" />
        <path className="jury-glacier-flow jury-glacier-flow-one" d="M215 171c34-5 69 13 105 3" fill="none" stroke="#ecfeff" strokeWidth="3" strokeLinecap="round" />
        <path className="jury-glacier-flow jury-glacier-flow-two" d="M225 184c34-2 52 14 90 6" fill="none" stroke="#a5f3fc" strokeWidth="2" strokeLinecap="round" />
        <path d="M0 215c72-14 117 8 182-4 80-15 125 18 197 1 73-17 123 6 181-3v41H0Z" fill="#0e7490" opacity="0.48" />
        <path className="jury-glacier-water" d="M0 229c63-11 107 7 173-3 70-11 122 10 183-1 73-13 136 7 204-2" fill="none" stroke="#67e8f9" strokeWidth="2" opacity="0.75" />
        {[40, 91, 136, 182, 241, 307, 352, 412, 467, 521].map((cx, index) => <circle key={cx} className={`jury-glacier-snow jury-glacier-snow-${index % 3}`} cx={cx} cy={18 + (index % 4) * 24} r={index % 2 === 0 ? 2 : 1.25} fill="#e0f2fe" />)}
        <circle className="jury-glacier-beacon" cx="356" cy="185" r="5" fill="#fbbf24" />
        <circle className="jury-glacier-beacon-ring" cx="356" cy="185" r="11" fill="none" stroke="#fde68a" strokeWidth="1.5" />
      </svg>
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between p-4 text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-100/90">
        <span>Локальный криосферный архив</span><span className="rounded-full border border-cyan-100/20 bg-slate-950/35 px-2 py-1">live evidence</span>
      </div>
      <div className="pointer-events-none absolute bottom-3 right-4 flex items-center gap-2 rounded-lg bg-slate-950/75 px-2.5 py-1.5 text-[11px] font-semibold text-white backdrop-blur-sm"><span className="h-2 w-2 rounded-full bg-amber-300" />объект для следующей проверки</div>
    </div>
    <dl className="grid border-t border-cyan-200/15 bg-slate-950/65 sm:grid-cols-3">
      <div className="jury-glacier-fact jury-glacier-fact-one p-3.5"><dt className="text-[11px] font-bold uppercase tracking-wide text-cyan-100">Временной ряд</dt><dd className="mt-1 text-xl font-bold text-white">{factValue(comparableYears)} <span className="text-sm font-medium text-slate-300">сопоставимых лет</span></dd></div>
      <div className="jury-glacier-fact jury-glacier-fact-two border-t border-cyan-200/15 p-3.5 sm:border-l sm:border-t-0"><dt className="text-[11px] font-bold uppercase tracking-wide text-cyan-100">Реальный scan</dt><dd className="mt-1 text-xl font-bold text-white">{factValue(scannedLakes)} <span className="text-sm font-medium text-slate-300">озёр в инвентаре</span></dd></div>
      <div className="jury-glacier-fact jury-glacier-fact-three border-t border-cyan-200/15 p-3.5 sm:border-l sm:border-t-0"><dt className="text-[11px] font-bold uppercase tracking-wide text-cyan-100">Выбранный кейс</dt><dd className="mt-1 text-xl font-bold text-white">{factValue(selectedPriority)}<span className="text-sm font-medium text-slate-300">/100 приоритет проверки</span></dd></div>
    </dl>
    <p className="border-t border-cyan-200/15 bg-slate-950/85 px-3.5 py-2 text-xs leading-5 text-slate-300">Анимация показывает связь «ледник → водный объект → очередь проверки»; балл не является прогнозом прорыва или опасности.</p>
  </section>;
}
