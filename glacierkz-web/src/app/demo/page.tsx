import Link from "next/link";
import { ArrowRight, ShieldAlert, Sparkles } from "lucide-react";

const steps = [
  { href: "/explore", title: "1. Explore annual glacier evidence", text: "Inspect available annual layers, provenance and quality caveats." },
  { href: "/risk-twin", title: "2. Run an evidence-gap screening", text: "Select a real RGI boundary, add typed observations and receive an abstaining or evidence-priority result." },
  { href: "/operations", title: "3. Review on the operations map", text: "Compare annual screening layers with RGI inventory geometry and shadow-mode work queues." },
];

export default function DemoPage() {
  return <main id="main-content" className="min-h-screen bg-slate-50 px-4 py-12"><section className="mx-auto max-w-4xl"><div className="rounded-2xl bg-slate-950 p-8 text-white"><p className="inline-flex items-center gap-2 text-sm text-cyan-200"><Sparkles className="h-4 w-4" />Interactive walkthrough</p><h1 className="mt-3 text-3xl font-bold">GlacierNET-KZ research workflow</h1><p className="mt-3 max-w-2xl text-slate-200">This is a guided route through the live local product, not a fabricated prediction demo.</p><p className="mt-5 flex items-center gap-2 rounded-lg bg-amber-300/10 p-3 text-sm text-amber-100"><ShieldAlert className="h-4 w-4" />Risk Twin outputs are screening evidence only, never official warnings.</p></div><div className="mt-6 space-y-4">{steps.map((step) => <Link key={step.href} href={step.href} className="group flex items-center justify-between rounded-xl bg-white p-6 shadow-sm transition hover:ring-2 hover:ring-cyan-500"><div><h2 className="font-semibold">{step.title}</h2><p className="mt-1 text-sm text-slate-600">{step.text}</p></div><ArrowRight className="h-5 w-5 text-cyan-700 group-hover:translate-x-1" /></Link>)}</div></section></main>;
}
