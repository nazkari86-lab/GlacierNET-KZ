"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import Link from "next/link";
import { ArrowLeft, MessageSquare, Loader2, Bot, RefreshCw, Key, Filter, Wrench, Play, Check } from "lucide-react";
import { fetchAnalysisModels, fetchProviderModels, analyzeWithLLM, LLMProviderInfo, LLMModelInfo, LLMAnalyzeResponse, fetchMCPTools, callMCPTool, MCPTool, MCPToolCallResult } from "@/lib/api";
import ErrorBoundary from "@/components/ErrorBoundary";
import { useI18n } from "@/lib/I18nProvider";

const QUICK_PROMPT_VALUES = [
  { label: "Описать ледник", mode: "describe" as const, prompt: "Опиши состояние ледников по данным спутниковой сегментации. Выдели ключевые зоны таяния." },
  { label: "Тренд таяния", mode: "trend" as const, prompt: "Проанализируй многолетний тренд изменения площади ледников. Укажи скорость потери льда и аномальные годы." },
  { label: "Сравнить модели", mode: "compare" as const, prompt: "Сравни результаты разных моделей сегментации. Какая модель точнее выделяет границы ледника?" },
];

export default function AnalysisPage() {
  const { t } = useI18n();
  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<"describe" | "trend" | "compare">("describe");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LLMAnalyzeResponse | null>(null);
  const [error, setError] = useState("");
  const [showFreeOnly, setShowFreeOnly] = useState(false);
  const [dynamicModels, setDynamicModels] = useState<LLMModelInfo[] | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // MCP Tools state
  const [mcpTools, setMcpTools] = useState<MCPTool[]>([]);
  const [mcpLoading, setMcpLoading] = useState(false);
  const [mcpResults, setMcpResults] = useState<Record<string, MCPToolCallResult>>({});
  const [mcpContext, setMcpContext] = useState<string[]>([]);

  useEffect(() => {
    fetchAnalysisModels().then((p) => {
      setProviders(p);
      if (p.length > 0) setSelectedProvider(p[0].provider);
    });
  }, []);

  // Fetch models when API key changes (debounced)
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    const currentProvider = providers.find((p) => p.provider === selectedProvider);
    if (!currentProvider?.needs_key || !apiKey.trim()) {
      setDynamicModels(null);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      try {
        const models = await fetchProviderModels(selectedProvider, apiKey.trim());
        if (models.length > 0) {
          setDynamicModels(models);
        }
      } catch (e) {
        console.warn("Failed to fetch models with API key:", e);
      }
    }, 800);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [apiKey, selectedProvider, providers]);

  const currentProvider = providers.find((p) => p.provider === selectedProvider);

  const filteredModels = useMemo(() => {
    if (!currentProvider) return [];
    const models = dynamicModels || currentProvider.models;
    if (!showFreeOnly) return models;
    return models.filter((m) => m.free);
  }, [currentProvider, showFreeOnly, dynamicModels]);

  useEffect(() => {
    if (filteredModels.length > 0) {
      setSelectedModel(filteredModels[0].id);
    }
  }, [selectedProvider, showFreeOnly, filteredModels]);

  // Load MCP tools on mount
  useEffect(() => {
    setMcpLoading(true);
    fetchMCPTools()
      .then(setMcpTools)
      .catch(console.error)
      .finally(() => setMcpLoading(false));
  }, []);

  const handleMCPTool = useCallback(async (tool: MCPTool) => {
    // Extract args from schema defaults — works for flat and nested (config) schemas
    const extractDefaults = (props: Record<string, unknown>): Record<string, unknown> => {
      const result: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(props)) {
        const prop = v as { default?: unknown; properties?: Record<string, unknown>; type?: string };
        if (prop.default !== undefined) {
          result[k] = prop.default;
        } else if (prop.type === "object" && prop.properties) {
          // Nested object (e.g. config for run_experiment) — recurse
          const nested = extractDefaults(prop.properties);
          if (Object.keys(nested).length > 0) result[k] = nested;
        }
      }
      return result;
    };

    const args = tool.inputSchema?.properties
      ? extractDefaults(tool.inputSchema.properties as Record<string, unknown>)
      : {};
    
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
      <header className="border-b bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-3 px-4 py-3">
          <Link href="/" className="text-zinc-400 hover:text-zinc-600" aria-label={t("nav.back")}>
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <Bot className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <span className="font-bold">{t("analysis.title")}</span>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <ErrorBoundary>
          <section className="rounded-xl bg-white p-6 shadow-sm">
            <h2 className="mb-4 text-lg font-semibold">{t("analysis.provider")}</h2>
            <div className="flex flex-wrap gap-4">
              <div className="flex-1">
                <label className="mb-1 block text-xs text-zinc-400">{t("analysis.provider")}</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => setSelectedProvider(e.target.value)}
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                  aria-label={t("analysis.provider")}
                >
                  {providers.map((p) => (
                    <option key={p.provider} value={p.provider}>
                      {p.label} {p.needs_key ? "" : "(free)"}
                    </option>
                  ))}
                </select>
              </div>
              {currentProvider && (
                <div className="flex-[2]">
                  <label className="mb-1 flex items-center justify-between text-xs text-zinc-400">
                    <span>{t("analysis.model")} ({filteredModels.length})</span>
                    <button
                      onClick={() => setShowFreeOnly(!showFreeOnly)}
                      className={`flex items-center gap-1 rounded px-1.5 py-0.5 transition-colors ${
                        showFreeOnly
                          ? "bg-green-100 text-green-700"
                          : "text-zinc-400 hover:text-zinc-600"
                      }`}
                    >
                      <Filter className="h-3 w-3" aria-hidden="true" />
                      {t("analysis.free_only")}
                    </button>
                  </label>
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
                  placeholder="sk-..."
                  className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                  aria-label={t("analysis.api_key")}
                />
              </div>
            )}
          </section>

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
                  className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm text-zinc-600 transition-colors hover:border-blue-300 hover:text-blue-600"
                >
                  {q.label}
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-xl bg-white p-6 shadow-sm">
            <div className="mb-4 flex items-center gap-2">
              <Wrench className="h-5 w-5 text-zinc-500" aria-hidden="true" />
              <h2 className="text-lg font-semibold">MCP Tools — Данные проекта</h2>
            </div>
            <p className="mb-4 text-sm text-zinc-500">
              Вызовите инструменты для получения реальных данных перед анализом
            </p>
            
            {mcpLoading ? (
              <div className="flex items-center gap-2 text-zinc-400">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Загрузка инструментов...
              </div>
            ) : mcpTools.length === 0 ? (
              <p className="text-sm text-zinc-400">Нет доступных MCP инструментов</p>
            ) : (
              <>
                <div className="mb-3 flex flex-wrap gap-2">
                  {mcpTools.map((tool) => {
                    const toolResult = mcpResults[tool.name];
                    const isLoaded = toolResult?.status === "success";
                    const isLoading = toolResult?.status === "loading";
                    return (
                      <button
                        key={tool.name}
                        onClick={() => handleMCPTool(tool)}
                        disabled={isLoading}
                        className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors ${
                          isLoaded
                            ? "border-green-200 bg-green-50 text-green-700"
                            : isLoading
                            ? "border-blue-200 bg-blue-50 text-blue-600"
                            : "border-zinc-200 text-zinc-600 hover:border-blue-300 hover:text-blue-600"
                        }`}
                      >
                        {isLoaded ? (
                          <Check className="h-3 w-3" aria-hidden="true" />
                        ) : isLoading ? (
                          <Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" />
                        ) : (
                          <Play className="h-3 w-3" aria-hidden="true" />
                        )}
                        {tool.name}
                      </button>
                    );
                  })}
                </div>
                
                {mcpContext.length > 0 && (
                  <div className="rounded-lg border border-green-200 bg-green-50 p-3">
                    <p className="mb-2 text-xs font-medium text-green-700">
                      Загружено контекстов: {mcpContext.length}
                    </p>
                    <button
                      onClick={() => {
                        setMcpContext([]);
                        setMcpResults({});
                      }}
                      className="text-xs text-green-600 underline hover:text-green-800"
                    >
                      Очистить контекст
                    </button>
                  </div>
                )}
              </>
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
          <section className="rounded-xl border border-red-200 bg-red-50 p-6" role="alert">
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
