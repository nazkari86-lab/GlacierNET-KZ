"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, MessageSquare, Loader2, Bot, RefreshCw, Key, Wrench, Play, Check, Search, Sparkles } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchAnalysisModels, fetchProviderModels, analyzeWithLLM, LLMProviderInfo, LLMModelInfo, LLMAnalyzeResponse, fetchMCPTools, callMCPTool, MCPTool, MCPToolCallResult, fetchYears, compareLocalYears, fetchGlacierSeries, fetchTrendEvidence, TrendEvidence } from "@/lib/api";
import ErrorBoundary from "@/components/ErrorBoundary";
import { useI18n } from "@/lib/I18nProvider";
import { riskTwinHref } from "@/lib/evidenceCase";

const QUICK_PROMPT_VALUES = [
  { label: "Описать ледник", mode: "describe" as const, prompt: "Опиши состояние ледников по данным спутниковой сегментации. Выдели ключевые зоны таяния." },
  { label: "Тренд таяния", mode: "trend" as const, prompt: "Проанализируй многолетний тренд изменения площади ледников. Укажи скорость потери льда и аномальные годы." },
  { label: "Сравнить модели", mode: "compare" as const, prompt: "Сравни результаты разных моделей сегментации. Какая модель точнее выделяет границы ледника?" },
];

const PRESENTATION_TOOL_NAMES = ["get_project_stats", "list_local_years", "search_glaciers", "list_datasets"];

function toolDefaults(tool: MCPTool): Record<string, unknown> {
  const read = (props: Record<string, unknown>): Record<string, unknown> => Object.fromEntries(
    Object.entries(props).flatMap(([key, value]) => {
      const property = value as { default?: unknown; properties?: Record<string, unknown>; type?: string };
      if (property.default !== undefined) return [[key, property.default]];
      if (property.type === "object" && property.properties) {
        const nested = read(property.properties);
        return Object.keys(nested).length ? [[key, nested]] : [];
      }
      return [];
    })
  );
  return tool.inputSchema?.properties ? read(tool.inputSchema.properties as Record<string, unknown>) : {};
}

function toolGroup(name: string): string {
  if (/(local_year|glacier|dataset|project_stats|time_series)/.test(name)) return "Verified local evidence";
  if (/(model|experiment|benchmark|training|loss|scheduler|augmentation)/.test(name)) return "Models and experiments";
  if (/(predict|anomal|spectral|uncertainty|ensemble|postprocess|satellite)/.test(name)) return "Research processing";
  return "Advanced research";
}

function EvidenceTrendCard({ evidence, loading, error }: { evidence: TrendEvidence | null; loading: boolean; error: string }) {
  if (loading) return <section className="rounded-xl bg-white p-6 shadow-sm"><div className="flex items-center gap-2 text-zinc-500"><Loader2 className="h-4 w-4 animate-spin" />Загрузка проверяемого временного ряда…</div></section>;
  if (error) return <section className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">График доказательств недоступен: {error}</section>;
  if (!evidence) return null;
  const summary = evidence.exploratory_linear_trend;
  const anomalousYears = new Set(evidence.flagged_temporal_anomalies.map((item) => item.year));
  const chartData = evidence.points.map((point) => ({ ...point, marker: anomalousYears.has(point.year) ? point.area_km2 : undefined }));
  return <section className="min-w-0 rounded-xl border border-blue-100 bg-white p-6 shadow-sm">
    <div className="flex min-w-0 flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-wide text-blue-700">Evidence-first analysis</p><h2 className="mt-1 text-lg font-semibold">Проверяемый ряд площади</h2><p className="mt-1 text-sm text-zinc-500">График строится локально из <code className="break-all rounded bg-zinc-100 px-1">{evidence.primary_table}</code>; Groq не рисует и не вычисляет эти значения.</p></div><span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-800">Exploratory · не экспертная валидация</span></div>
    {summary && <div className="mt-4 grid gap-3 sm:grid-cols-4"><div className="rounded-lg bg-zinc-50 p-3"><p className="text-xs text-zinc-500">Наблюдения</p><p className="mt-1 text-lg font-semibold">{summary.n_observations}</p></div><div className="rounded-lg bg-zinc-50 p-3"><p className="text-xs text-zinc-500">Наклон ряда</p><p className="mt-1 text-lg font-semibold">{summary.slope_km2_per_year} км²/год</p></div><div className="rounded-lg bg-zinc-50 p-3"><p className="text-xs text-zinc-500">Прибл. 95% интервал</p><p className="mt-1 text-sm font-semibold">{summary.slope_interval_95_approx[0]}…{summary.slope_interval_95_approx[1]}</p></div><div className="rounded-lg bg-zinc-50 p-3"><p className="text-xs text-zinc-500">R² линейной модели</p><p className="mt-1 text-lg font-semibold">{summary.r_squared}</p></div></div>}
    <div className="mt-5 h-72 min-w-0" role="img" aria-label="График площади ледников по локальным годам"><ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1} initialDimension={{ width: 320, height: 288 }}><AreaChart data={chartData} margin={{ top: 12, right: 16, bottom: 0, left: 0 }}><defs><linearGradient id="evidence-area" x1="0" x2="0" y1="0" y2="1"><stop offset="5%" stopColor="#2563eb" stopOpacity={0.22}/><stop offset="95%" stopColor="#2563eb" stopOpacity={0}/></linearGradient></defs><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="year" tick={{ fontSize: 12 }} /><YAxis tick={{ fontSize: 12 }} width={70} label={{ value: "км²", angle: -90, position: "insideLeft" }} /><Tooltip formatter={(value) => { const numeric = typeof value === "number" ? value : Number(value ?? 0); return [`${numeric.toFixed(2)} км²`, "Площадь"] as [string, string]; }} labelFormatter={(label) => `Год ${label}`} contentStyle={{ borderRadius: 10 }} /><Area type="monotone" dataKey="area_km2" stroke="#2563eb" fill="url(#evidence-area)" strokeWidth={2} /><Line type="monotone" dataKey="marker" stroke="#dc2626" strokeWidth={0} dot={{ r: 5, fill: "#dc2626" }} activeDot={false} /></AreaChart></ResponsiveContainer></div>
    <div className="mt-4 grid gap-3 lg:grid-cols-2"><div className="rounded-lg border border-zinc-200 p-3"><p className="text-sm font-semibold">Отмеченные годы качества</p>{evidence.flagged_temporal_anomalies.length ? <ul className="mt-2 space-y-1 text-xs text-zinc-600">{evidence.flagged_temporal_anomalies.map((item) => <li key={item.year}><span className="font-semibold text-amber-700">{item.year} · {item.status}</span> — {item.reason}</li>)}</ul> : <p className="mt-2 text-xs text-zinc-500">Нет автоматических флагов.</p>}</div><div className="rounded-lg border border-zinc-200 p-3"><p className="text-sm font-semibold">Научные ограничения</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-zinc-600">{evidence.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></div>
  </section>;
}

export default function AnalysisPage() {
  const { t } = useI18n();
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [selectedProvider] = useState("groq");
  const [selectedModel, setSelectedModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<"describe" | "trend" | "compare">("describe");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LLMAnalyzeResponse | null>(null);
  const [error, setError] = useState("");
  const [dynamicModels, setDynamicModels] = useState<LLMModelInfo[] | null>(null);
  const [modelLoadError, setModelLoadError] = useState("");
  const [modelLoading, setModelLoading] = useState(false);
  const [trendEvidence, setTrendEvidence] = useState<TrendEvidence | null>(null);
  const [trendEvidenceLoading, setTrendEvidenceLoading] = useState(true);
  const [trendEvidenceError, setTrendEvidenceError] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // MCP Tools state
  const [mcpTools, setMcpTools] = useState<MCPTool[]>([]);
  const [mcpLoading, setMcpLoading] = useState(false);
  const [mcpCatalogError, setMcpCatalogError] = useState("");
  const [mcpResults, setMcpResults] = useState<Record<string, MCPToolCallResult>>({});
  const [mcpContext, setMcpContext] = useState<string[]>([]);
  const [mcpQuery, setMcpQuery] = useState("");
  const [presentationLoading, setPresentationLoading] = useState(false);
  const [linkedRiskTwinHref, setLinkedRiskTwinHref] = useState(() => riskTwinHref({
    rgiId: "RGI2000-v7.0-G-13-33843",
    year: 2024,
    sourceScope: "annual_screening",
  }));

  useEffect(() => {
    fetchAnalysisModels().then((p) => {
      setProviders(p);
    });
  }, []);

  useEffect(() => {
    fetchTrendEvidence().then(setTrendEvidence).catch((cause) => setTrendEvidenceError(cause instanceof Error ? cause.message : "Не удалось загрузить данные")).finally(() => setTrendEvidenceLoading(false));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const year = Number(params.get("year"));
    const fromYear = Number(params.get("from"));
    const toYear = Number(params.get("to"));
    const glacierId = params.get("glacier");
    const glacierMethod = params.get("method") || "ndsi";
    const caseYear = Number.isInteger(year) && year >= 1900 && year <= 2100 ? year : 2024;
    setLinkedRiskTwinHref(riskTwinHref({
      rgiId: glacierId || "RGI2000-v7.0-G-13-33843",
      year: caseYear,
      sourceScope: glacierId ? "local_inventory" : "annual_screening",
    }));

    if (year) {
      fetchYears()
        .then((records) => records.find((record) => record.year === year))
        .then((record) => {
          if (!record) return;
          setMcpContext([`inspect_local_year: ${JSON.stringify(record, null, 2)}`]);
          setPrompt(
            `Проанализируй локальные проверенные данные GlacierNET-KZ за ${year} год. ` +
            "Объясни площадь, качество, доступные методы и ограничения. Не делай выводов за пределами переданного контекста."
          );
          setMode("describe");
        })
        .catch((cause) => setError(String(cause)));
    } else if (fromYear && toYear) {
      compareLocalYears(fromYear, toYear)
        .then((record) => {
          setMcpContext([`compare_local_years: ${JSON.stringify(record, null, 2)}`]);
          setPrompt(
            `Проанализируй проверенное сравнение GlacierNET-KZ ${fromYear}–${toYear}. ` +
            "Объясни изменение площади, строгую сравнимость и все предупреждения. Не добавляй внешние числа."
          );
          setMode("trend");
        })
        .catch((cause) => setError(String(cause)));
    } else if (glacierId) {
      fetchGlacierSeries(glacierId, glacierMethod)
        .then((record) => {
          setMcpContext([`inspect_glacier_timeseries: ${JSON.stringify(record, null, 2)}`]);
          setPrompt(
            `Разбери проверенную карточку ледника ${record.glacier.name_ru} (${glacierId}). ` +
            "Опиши RGI-характеристики, временной ряд, изменение, WGMS-контекст и ограничения. " +
            "Не интерпретируй площадь как объём воды и не добавляй внешние числа."
          );
          setMode("trend");
        })
        .catch((cause) => setError(String(cause)));
    }
  }, []);

  const loadGroqModels = useCallback(async () => {
    if (!apiKey.trim()) return;
    setModelLoading(true);
    setModelLoadError("");
    try {
      const models = await fetchProviderModels("groq", apiKey.trim());
      if (!models.length) throw new Error("Groq accepted the request but returned no available chat models.");
      setDynamicModels(models);
    } catch (cause) {
      setDynamicModels(null);
      setModelLoadError(cause instanceof Error ? cause.message : "Could not load Groq models");
    } finally {
      setModelLoading(false);
    }
  }, [apiKey]);

  // Fetch models after a short pause; the button below also lets a presenter
  // explicitly verify a key and inspect the resulting model list.
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    if (!apiKey.trim()) {
      setDynamicModels(null);
      setModelLoadError("");
      return;
    }

    debounceRef.current = setTimeout(() => { void loadGroqModels(); }, 800);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [apiKey, loadGroqModels]);

  const currentProvider = providers.find((p) => p.provider === selectedProvider);

  const filteredModels = useMemo(() => {
    if (!currentProvider) return [];
    const models = dynamicModels || currentProvider.models;
    return models;
  }, [currentProvider, dynamicModels]);

  useEffect(() => {
    if (filteredModels.length > 0) {
      setSelectedModel(filteredModels[0].id);
    }
  }, [filteredModels]);

  // Load MCP tools on mount
  useEffect(() => {
    setMcpLoading(true);
    setMcpCatalogError("");
    fetchMCPTools()
      .then(setMcpTools)
      .catch((cause) => setMcpCatalogError(cause instanceof Error ? cause.message : "MCP catalog unavailable"))
      .finally(() => setMcpLoading(false));
  }, []);

  const handleMCPTool = useCallback(async (tool: MCPTool) => {
    const args = toolDefaults(tool);
    
    // Check for required args missing defaults
    const required = (tool.inputSchema?.required as string[]) || [];
    const missing = required.filter((r) => !(r in args));
    if (missing.length > 0) {
      // Prompt user for missing required args
      const prompted: Record<string, unknown> = {};
      for (const field of missing) {
        const val = window.prompt(`Введите значение для "${field}" инструмента ${tool.name}:`);
        if (val === null) return; // user cancelled
        prompted[field] = val;
      }
      Object.assign(args, prompted);
    }
    
    setMcpResults((prev) => ({ ...prev, [tool.name]: { status: "loading", data: null, error: null } }));
    
    try {
      const result = await callMCPTool(tool.name, args);
      setMcpResults((prev) => ({ ...prev, [tool.name]: result }));
      
      if (result.status === "success" && result.data) {
        const summary = `${tool.name}: ${JSON.stringify(result.data, null, 2).slice(0, 500)}`;
        setMcpContext((prev) => [...prev, summary]);
      }
    } catch (e) {
      setMcpResults((prev) => ({
        ...prev,
        [tool.name]: { status: "error", data: null, error: String(e) },
      }));
    }
  }, []);

  const loadPresentationContext = useCallback(async () => {
    const tools = mcpTools.filter((tool) => PRESENTATION_TOOL_NAMES.includes(tool.name));
    if (!tools.length) return;
    setPresentationLoading(true);
    setMcpResults((previous) => ({ ...previous, ...Object.fromEntries(tools.map((tool) => [tool.name, { status: "loading", data: null, error: null } as MCPToolCallResult])) }));
    try {
      const settled = await Promise.all(tools.map(async (tool) => [tool, await callMCPTool(tool.name, toolDefaults(tool))] as const));
      const successful = settled.filter(([, response]) => response.status === "success" && response.data);
      setMcpResults((previous) => ({ ...previous, ...Object.fromEntries(settled.map(([tool, response]) => [tool.name, response])) }));
      setMcpContext((previous) => [
        ...successful.map(([tool, response]) => `${tool.name}: ${JSON.stringify(response.data, null, 2).slice(0, 1000)}`),
        ...previous.filter((entry) => !PRESENTATION_TOOL_NAMES.some((name) => entry.startsWith(`${name}:`))),
      ]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Presentation context could not be prepared");
    } finally {
      setPresentationLoading(false);
    }
  }, [mcpTools]);

  useEffect(() => {
    if (mcpTools.length) void loadPresentationContext();
  }, [mcpTools.length, loadPresentationContext]);

  const groupedTools = useMemo(() => {
    const query = mcpQuery.trim().toLowerCase();
    return mcpTools
      .filter((tool) => !query || `${tool.name} ${tool.description}`.toLowerCase().includes(query))
      .reduce<Record<string, MCPTool[]>>((groups, tool) => {
        const group = toolGroup(tool.name);
        (groups[group] ||= []).push(tool);
        return groups;
      }, {});
  }, [mcpTools, mcpQuery]);

  const handleAnalyze = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult(null);
    setError("");
    try {
      const contextStr = mcpContext.length > 0
        ? `\n\nДанные из базы проекта:\n${mcpContext.join("\n")}`
        : undefined;
      
      const r = await analyzeWithLLM({
        prompt: prompt.trim(),
        provider: selectedProvider,
        model: selectedModel,
        mode,
        api_key: apiKey || undefined,
        context: contextStr,
      });
      if (r.content.startsWith("\u274c") || r.content.includes("\u0412\u0441\u0435 LLM-\u043f\u0440\u043e\u0432\u0430\u0439\u0434\u0435\u0440\u044b \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b")) {
        setError(r.content);
      } else {
        setResult(r);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [prompt, selectedProvider, selectedModel, mode, apiKey, mcpContext]);

  return (
    <div className="min-h-screen bg-zinc-50">
      <a href="#main" aria-label="Skip to main content" className="sr-only rounded-lg bg-zinc-950 px-4 py-3 text-sm font-semibold text-white focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[1000]">Перейти к анализу</a>
      <header className="border-b bg-white">
        <nav aria-label="Analysis navigation" className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <Link href="/" className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-lg text-zinc-500 hover:bg-zinc-100 hover:text-zinc-700" aria-label={t("nav.back")}>
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Bot className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <span className="font-bold">{t("analysis.title")}</span>
          <Link href={linkedRiskTwinHref} className="ml-auto inline-flex min-h-11 max-w-full items-center rounded-lg border border-blue-200 px-3 py-2 text-center text-xs font-semibold text-blue-800 hover:bg-blue-50">Открыть связанный Risk Twin case</Link>
        </nav>
      </header>

      <main id="main" className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <h1 className="sr-only">AI analysis</h1>
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">AI analysis</h2>
            <div className="flex flex-wrap gap-4">
              <div className="flex-1 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-sm"><span className="text-xs text-orange-700">Provider</span><p className="font-semibold text-orange-950">Groq</p></div>
              {currentProvider && (
                <div className="flex-[2]">
                  <label className="mb-1 block text-xs text-zinc-400">{t("analysis.model")} ({filteredModels.length})</label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                    aria-label={t("analysis.model")}
                  >
                    {filteredModels.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name || m.id} {m.free ? "\ud83c\udf81" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            {currentProvider?.needs_key && (
              <div className="mt-4">
                <label className="mb-1 flex items-center gap-1 text-xs text-zinc-400">
                  <Key className="h-3 w-3" aria-hidden="true" />
                  {t("analysis.api_key")}
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="gsk_..."
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                  aria-label={t("analysis.api_key")}
                />
                <div className="mt-2 flex flex-wrap items-center gap-3"><button type="button" onClick={() => void loadGroqModels()} disabled={!apiKey.trim() || modelLoading} className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-orange-300 px-3 py-2 text-xs font-semibold text-orange-800 hover:bg-orange-50 disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${modelLoading ? "animate-spin" : ""}`} />{modelLoading ? "Checking Groq…" : "Check key and load models"}</button><p className="text-xs text-zinc-500">The key is sent only to Groq for this request and is not saved in the browser or project files.</p></div>
                {modelLoadError && <p role="alert" aria-live="assertive" className="mt-2 rounded-lg border border-red-200 bg-red-50 p-2 text-xs text-red-800">Groq key check failed: {modelLoadError}</p>}
              </div>
            )}
          </section>

          <EvidenceTrendCard evidence={trendEvidence} loading={trendEvidenceLoading} error={trendEvidenceError} />

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("analysis.quick_prompts")}</h2>
            <div className="flex flex-wrap gap-2">
              {QUICK_PROMPT_VALUES.map((q) => (
                <button
                  key={q.label}
                  onClick={() => {
                    setPrompt(q.prompt);
                    setMode(q.mode);
                  }}
                  className="min-h-11 rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:text-blue-600"
                >
                  {q.label}
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <Wrench className="h-5 w-5 text-zinc-500" aria-hidden="true" />
              <h2 className="text-lg font-semibold">Контекст проекта для AI</h2>
            </div>
            <p className="mb-4 text-sm text-zinc-500">Безопасный контекст презентации загружается автоматически. Обучение, инференс и экспериментальные команды не запускаются автоматически.</p>
            
            {mcpLoading ? (
              <div className="flex items-center gap-2 text-zinc-400">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Загрузка инструментов...
              </div>
            ) : mcpCatalogError ? (
              <p role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">Каталог MCP недоступен: {mcpCatalogError}</p>
            ) : mcpTools.length === 0 ? (
              <p className="text-sm text-zinc-400">Нет доступных MCP инструментов</p>
            ) : (
              <>
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div><p className="flex items-center gap-2 text-sm font-semibold text-blue-950"><Sparkles className="h-4 w-4" />Контекст презентации</p><p className="mt-1 text-xs text-blue-800">Статус проекта · локальные годы · RGI-реестр · доступные datasets</p></div>
                    <button onClick={() => void loadPresentationContext()} disabled={presentationLoading} className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-blue-700 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-800 disabled:opacity-50"><RefreshCw className={`h-3.5 w-3.5 ${presentationLoading ? "animate-spin" : ""}`} />{presentationLoading ? "Подготовка…" : "Обновить контекст"}</button>
                  </div>
                </div>
                <details className="mt-4 rounded-lg border border-zinc-200 p-3">
                  <summary className="cursor-pointer text-sm font-medium text-zinc-700">Каталог MCP-инструментов ({mcpTools.length})</summary>
                  <div className="relative mt-3"><label htmlFor="analysis-mcp-search" className="sr-only">Найти MCP инструмент</label><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-zinc-400" /><input id="analysis-mcp-search" value={mcpQuery} onChange={(event) => setMcpQuery(event.target.value)} placeholder="Найти инструмент" className="w-full rounded-lg border border-zinc-300 py-2 pl-9 pr-3 text-sm" /></div>
                  <div className="mt-3 space-y-4">{Object.entries(groupedTools).map(([group, tools]) => <div key={group}><h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">{group}</h3><div className="flex flex-wrap gap-2">{tools.map((tool) => {
                    const toolResult = mcpResults[tool.name]; const isLoaded = toolResult?.status === "success"; const isLoading = toolResult?.status === "loading";
                    return <button key={tool.name} onClick={() => handleMCPTool(tool)} disabled={isLoading} title={tool.description} className={`flex min-h-10 items-center gap-1.5 rounded-lg border px-3 py-2 text-xs transition-colors ${isLoaded ? "border-green-200 bg-green-50 text-green-700" : isLoading ? "border-blue-200 bg-blue-50 text-blue-600" : "border-zinc-200 text-zinc-600 hover:border-blue-300 hover:text-blue-600"}`}>{isLoaded ? <Check className="h-3 w-3" /> : isLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}{tool.name}</button>;
                  })}</div></div>)}</div>
                </details>
              </>
            )}
            {mcpContext.length > 0 && (
              <div className="mt-3 rounded-lg border border-green-200 bg-green-50 p-3">
                <p className="mb-2 text-xs font-medium text-green-700">
                  Загружено проверенных контекстов: {mcpContext.length}. Они будут переданы AI вместе с вашим вопросом.
                </p>
                <button
                  onClick={() => {
                    setMcpContext([]);
                    setMcpResults({});
                  }}
                  className="min-h-11 rounded-lg px-3 text-xs text-green-700 underline hover:bg-green-100 hover:text-green-900"
                >
                  Очистить контекст
                </button>
              </div>
            )}
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("analysis.prompt")}</h2>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={t("analysis.prompt_placeholder")}
              rows={4}
              className="w-full resize-none rounded-lg border border-zinc-300 px-3 py-2 text-sm"
              aria-label={t("analysis.prompt")}
            />
          </section>
        </ErrorBoundary>

        <button
          onClick={handleAnalyze}
          disabled={!prompt.trim() || loading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 py-3 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          aria-busy={loading}
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
              {t("analysis.analyzing")}
            </>
          ) : (
            <>
              <MessageSquare className="h-5 w-5" aria-hidden="true" />
              {t("analysis.analyze")}
            </>
          )}
        </button>

        {error && (
          <section className="rounded-xl border border-red-200 bg-red-50 p-6" role="alert" aria-live="assertive">
            <p className="text-sm text-red-600">{error.startsWith("\u274c") ? error : `${t("predict.error")}: ${error}`}</p>
          </section>
        )}

        {result && (
          <section className="rounded-xl bg-white p-6 shadow-sm" role="status" aria-live="polite">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t("analysis.result")}</h2>
              <div className="flex items-center gap-2">
                <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs text-zinc-500">
                  {result.provider || selectedProvider} / {result.model || selectedModel}
                </span>
                {result.fallback_used && (
                  <span className="flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-600">
                    <RefreshCw className="h-3 w-3" aria-hidden="true" />
                    {t("analysis.fallback")}
                  </span>
                )}
              </div>
            </div>
            <div className="prose prose-sm max-w-none whitespace-pre-wrap rounded-lg bg-zinc-50 p-4 text-zinc-700">
              {result.content}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
