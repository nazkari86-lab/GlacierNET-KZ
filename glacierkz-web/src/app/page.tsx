"use client";

import Link from "next/link";
import { ArrowRight, BrainCircuit, ClipboardCheck, FileText, Map, Mountain, ShieldCheck } from "lucide-react";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useI18n } from "@/lib/I18nProvider";

const pageCopy = {
  en: {
    eyebrow: "Multimodal glacier intelligence",
    title: "Analyze a real glacier and see where the model can be trusted.",
    body: "Choose any local glacier and year. GlacierNET-KZ aligns Sentinel-2, terrain and SAR, delineates the glacier, maps uncertainty and passes the same evidence case into the Risk Twin.",
    primary: "Open ML Workspace",
    secondary: "View scientific evidence",
    safety: "Shadow-mode decision support. Not an official warning system.",
    map: "Active Cryosphere Risk Twin",
    mapText: "Trace glacier, lake, river and exposed assets through one evidence-led cascade.",
    audit: "Evidence trail",
    auditText: "Every decision is linked to data, limitations, and review.",
  },
  ru: {
    eyebrow: "Мультимодальный интеллект ледников",
    title: "Проанализируйте реальный ледник и увидьте, где модели можно доверять.",
    body: "Выберите любой локальный ледник и год. GlacierNET-KZ совмещает Sentinel‑2, рельеф и SAR, строит границу, показывает неопределённость и передаёт тот же доказательный кейс в Risk Twin.",
    primary: "Открыть ML Workspace",
    secondary: "Научные доказательства",
    safety: "Поддержка решений в shadow mode. Не официальная система предупреждений.",
    map: "Active Cryosphere Risk Twin",
    mapText: "Связывает ледник, озеро, реку и объекты воздействия в одну доказательную цепочку.",
    audit: "Цепочка доказательств",
    auditText: "Каждое решение связано с данными, ограничениями и проверкой.",
  },
  kk: {
    eyebrow: "Мұздықтардың мультимодалды интеллекті",
    title: "Нақты мұздықты талдап, модельге қай жерде сенуге болатынын көріңіз.",
    body: "Кез келген жергілікті мұздық пен жылды таңдаңыз. GlacierNET-KZ Sentinel‑2, жер бедері және SAR деректерін біріктіріп, шекара мен белгісіздікті көрсетеді және сол дәлелді Risk Twin жүйесіне береді.",
    primary: "ML Workspace ашу",
    secondary: "Ғылыми дәлелдер",
    safety: "Shadow mode шешімдерді қолдау. Ресми ескерту жүйесі емес.",
    map: "Active Cryosphere Risk Twin",
    mapText: "Мұздық, көл, өзен және әсер нысандарын бір дәлелдер тізбегіне біріктіреді.",
    audit: "Дәлелдер тізбегі",
    auditText: "Әр шешім дерекпен, шектеумен және тексерумен байланыстырылған.",
  },
};

export default function HomePage() {
  const { locale } = useI18n();
  const text = pageCopy[locale];

  return <div className="min-h-screen bg-slate-50 text-slate-950">
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight"><Mountain className="h-6 w-6 text-blue-700" />GlacierNET-KZ</Link>
        <div className="flex items-center gap-3"><Link className="hidden text-sm font-medium text-slate-600 hover:text-slate-950 sm:block" href="/jury">Jury evidence</Link><LanguageSwitcher /></div>
      </div>
    </header>
    <main id="main-content" className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:py-24">
      <section>
        <p className="text-sm font-semibold uppercase tracking-[0.16em] text-blue-800">{text.eyebrow}</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">{text.title}</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">{text.body}</p>
        <div className="mt-8 flex flex-wrap gap-3"><Link href="/ml" className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white hover:bg-blue-800">{text.primary}<ArrowRight className="h-4 w-4" /></Link><Link href="/jury" className="inline-flex min-h-12 items-center rounded-lg border border-slate-300 bg-white px-5 py-3 font-semibold hover:bg-slate-100">{text.secondary}</Link></div>
        <p className="mt-6 flex items-center gap-2 text-sm text-slate-600"><ShieldCheck className="h-4 w-4 text-blue-700" />{text.safety}</p>
      </section>
      <section aria-label="Product capabilities" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
        <Link href="/ml" className="rounded-2xl border border-cyan-200 bg-cyan-50 p-6 shadow-sm transition hover:border-cyan-400 hover:shadow-md"><BrainCircuit className="h-7 w-7 text-cyan-700" /><h2 className="mt-4 text-xl font-semibold">Glacier-first ML</h2><p className="mt-2 text-sm leading-6 text-slate-600">16-channel segmentation, probability, entropy and a downloadable audit manifest.</p></Link>
        <Link href="/risk-twin" className="rounded-2xl border border-blue-100 bg-white p-6 shadow-sm transition hover:border-blue-300 hover:shadow-md"><Map className="h-7 w-7 text-blue-700" /><h2 className="mt-4 text-xl font-semibold">{text.map}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{text.mapText}</p></Link>
        <Link href="/jury" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:border-blue-300 hover:shadow-md"><ClipboardCheck className="h-7 w-7 text-blue-700" /><h2 className="mt-4 text-xl font-semibold">{text.audit}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{text.auditText}</p></Link>
        <Link href="/analysis" className="sm:col-span-2 lg:col-span-1 inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-950 px-5 py-4 font-semibold text-white hover:bg-slate-800"><FileText className="h-5 w-5 text-blue-300" />Evidence-first AI analysis<ArrowRight className="ml-auto h-4 w-4" /></Link>
      </section>
    </main>
  </div>;
}
