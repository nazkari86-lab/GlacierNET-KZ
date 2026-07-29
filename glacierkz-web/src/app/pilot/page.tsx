import Link from "next/link";
import { ArrowRight, CheckCircle2, ClipboardCheck, FileSearch, MapPinned, ShieldAlert, UsersRound } from "lucide-react";

const stages = [
  { icon: MapPinned, title: "1. Выбрать границу пилота", body: "Один бассейн или группа ледников, ответственный владелец и конкретный вопрос: что проверить в этом сезоне?", href: "/risk-twin", cta: "Открыть карту screening" },
  { icon: FileSearch, title: "2. Собрать доказательства", body: "Инвентарные контуры, годовые слои, полевые фото/измерения и источник каждого значения. Неподтверждённые пробелы остаются видимыми.", href: "/operations#monitor", cta: "Открыть Operations" },
  { icon: ClipboardCheck, title: "3. Принять и сохранить решение", body: "Сформировать Evidence Case: что наблюдалось, что неизвестно, какой следующий шаг утверждён и кто его проверит.", href: "/operations#reports", cta: "Открыть отчёты" },
];

const deliverables = [
  "Очередь объектов для проверки с координатами, источником и ограничениями.",
  "Case Action Plan: спутниковые данные, полевая проверка, решение и научный экспорт.",
  "Воспроизводимый JSON-пакет evidence case и цепочка аудита.",
  "Явное abstain-состояние, если данных недостаточно для вывода.",
];

export default function PilotPage() {
  return <main id="main" className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:px-6"><div className="mx-auto max-w-6xl space-y-6">
    <header className="overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-cyan-950 to-blue-950 p-7 text-white shadow-[0_26px_70px_-38px_rgba(8,47,73,0.9)] sm:p-10">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-200">Pilot readiness</p>
      <h1 className="mt-3 max-w-4xl text-3xl font-bold tracking-tight sm:text-5xl">Запустить проверяемый мониторинг — за один пилотный цикл.</h1>
      <p className="mt-4 max-w-3xl text-base leading-7 text-slate-200">GlacierNET-KZ не заменяет эксперта и не выдаёт официальные предупреждения. Он даёт команде единый маршрут от локального наблюдения к человеческому решению с понятной областью применимости.</p>
      <div className="mt-6 flex flex-wrap gap-3"><Link href="/risk-twin" className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-cyan-300 px-4 py-2 text-sm font-bold text-slate-950 transition hover:bg-cyan-200">Начать с реального case <ArrowRight className="h-4 w-4" /></Link><Link href="/jury" className="inline-flex min-h-11 items-center rounded-xl border border-white/25 px-4 py-2 text-sm font-semibold transition hover:bg-white/10">Проверить границы доказательств</Link></div>
    </header>

    <section aria-labelledby="pilot-flow" className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7"><div className="flex items-start gap-3"><UsersRound className="mt-1 h-6 w-6 text-cyan-700" /><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-800">Рабочий контур</p><h2 id="pilot-flow" className="mt-1 text-2xl font-bold">Три шага без ложной автоматизации</h2></div></div><div className="mt-6 grid gap-4 lg:grid-cols-3">{stages.map(({ icon: Icon, title, body, href, cta }) => <article key={title} className="flex min-w-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5"><Icon className="h-7 w-7 text-cyan-700" /><h3 className="mt-4 text-lg font-bold">{title}</h3><p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{body}</p><Link href={href} className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-cyan-800 hover:text-cyan-950">{cta} <ArrowRight className="h-4 w-4" /></Link></article>)}</div></section>

    <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]"><article className="rounded-3xl border border-emerald-100 bg-emerald-50 p-6"><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">Результат пилота</p><h2 className="mt-2 text-2xl font-bold text-emerald-950">Не “карта риска”, а доказуемая очередь действий.</h2><ul className="mt-5 space-y-3">{deliverables.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-emerald-950"><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />{item}</li>)}</ul></article><aside className="rounded-3xl border border-amber-200 bg-amber-50 p-6"><ShieldAlert className="h-7 w-7 text-amber-700" /><h2 className="mt-4 text-xl font-bold text-amber-950">Что требуется от партнёра</h2><ul className="mt-3 space-y-2 text-sm leading-6 text-amber-900"><li>• владелец решения и полевой контакт;</li><li>• граница пилота и приоритетные объекты;</li><li>• разрешённые источники наблюдений;</li><li>• правило: кто подтверждает и закрывает кейс.</li></ul><p className="mt-4 border-t border-amber-200 pt-4 text-xs leading-5 text-amber-800">Без этих входов система остаётся исследовательским screening-инструментом и честно не заявляет операционную готовность.</p></aside></section>

    <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">До масштабирования</p><h2 className="mt-2 text-2xl font-bold">Четыре контрольные точки качества</h2><div className="mt-5 grid gap-3 md:grid-cols-2">{[["Данные", "Все входы имеют источник, дату, геометрию и ограничения."],["Наука", "Экспертная двойная разметка и внешний регион не подменяются локальными метриками."],["Операции", "Человек утверждает каждую инспекцию и решение; автоматического тревожного сигнала нет."],["Аудит", "Каждый финальный case можно экспортировать и повторно проверить."]].map(([title, body]) => <article key={title} className="rounded-2xl border border-slate-200 p-4"><h3 className="font-bold">{title}</h3><p className="mt-1 text-sm leading-6 text-slate-600">{body}</p></article>)}</div></section>
  </div></main>;
}
