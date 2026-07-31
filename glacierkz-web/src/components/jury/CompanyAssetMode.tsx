"use client";

import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { Building2, FileUp, LocateFixed, MapPinned, Trash2 } from "lucide-react";
import { regionalObservationCandidateKey, type RegionalObservationScan } from "@/lib/api";

type Candidate = RegionalObservationScan["candidates"][number];

export type CompanyAsset = {
  id: string;
  name: string;
  type: string;
  latitude: number;
  longitude: number;
  createdAt: string;
};

type CompanyAssetModeProps = {
  candidates: Candidate[];
  scannedLakes: number;
  onSelectCandidate: (candidate: Candidate, asset: CompanyAsset) => void;
  routeContext?: {
    assetId: string;
    status: "loading" | "available" | "unavailable";
    routeLengthKm: number | null;
    corridorWidthM: number | null;
  } | null;
};

const STORAGE_KEY = "glaciernet-kz.company-assets.v1";
const ASSET_TYPES = ["Инфраструктура", "Дорога", "ГЭС / водозабор", "Карьер / шахта", "Лагерь / объект", "Другое"];
export const MAX_GEOJSON_BYTES = 1_000_000;
const MAX_GEOJSON_FEATURES = 100;

function numberFromInput(value: string) {
  const parsed = Number(value.trim().replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function distanceKm(latitudeA: number, longitudeA: number, latitudeB: number, longitudeB: number) {
  const radians = (value: number) => value * Math.PI / 180;
  const earthRadiusKm = 6371.0088;
  const deltaLatitude = radians(latitudeB - latitudeA);
  const deltaLongitude = radians(longitudeB - longitudeA);
  const a = Math.sin(deltaLatitude / 2) ** 2 + Math.cos(radians(latitudeA)) * Math.cos(radians(latitudeB)) * Math.sin(deltaLongitude / 2) ** 2;
  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function newId() {
  return globalThis.crypto?.randomUUID?.() ?? `asset-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function parseGeoJsonAssets(payload: unknown): CompanyAsset[] {
  const collection = payload as { type?: unknown; features?: unknown };
  if (collection.type !== "FeatureCollection" || !Array.isArray(collection.features)) throw new Error("Нужен GeoJSON FeatureCollection с точечными объектами.");
  const assets = collection.features.flatMap((feature, index) => {
    const item = feature as { geometry?: { type?: unknown; coordinates?: unknown }; properties?: Record<string, unknown> };
    const coordinates = item.geometry?.coordinates;
    if (item.geometry?.type !== "Point" || !Array.isArray(coordinates) || coordinates.length < 2) return [];
    const longitude = Number(coordinates[0]);
    const latitude = Number(coordinates[1]);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return [];
    const properties = item.properties ?? {};
    return [{
      id: newId(),
      name: String(properties.name ?? properties.NAME ?? properties.title ?? `Объект ${index + 1}`),
      type: String(properties.asset_type ?? properties.type ?? properties.kind ?? "Инфраструктура"),
      latitude,
      longitude,
      createdAt: new Date().toISOString(),
    }];
  });
  if (assets.length === 0) throw new Error("В файле не найдено ни одной корректной Point‑геометрии.");
  return assets.slice(0, MAX_GEOJSON_FEATURES);
}

function formatCoordinate(value: number) {
  return value.toLocaleString("ru-RU", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
}

export default function CompanyAssetMode({ candidates, scannedLakes, onSelectCandidate, routeContext = null }: CompanyAssetModeProps) {
  const [assets, setAssets] = useState<CompanyAsset[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [radiusKm, setRadiusKm] = useState(25);
  const [name, setName] = useState("");
  const [type, setType] = useState(ASSET_TYPES[0]);
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [message, setMessage] = useState("");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      const parsed = stored ? JSON.parse(stored) : [];
      if (Array.isArray(parsed)) {
        const valid = parsed.filter((asset): asset is CompanyAsset => typeof asset?.id === "string" && typeof asset?.name === "string" && Number.isFinite(asset?.latitude) && Number.isFinite(asset?.longitude));
        setAssets(valid);
        setSelectedAssetId(valid[0]?.id ?? "");
      }
    } catch {
      setMessage("Не удалось прочитать сохранённые объекты этого браузера.");
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (hydrated) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(assets));
  }, [assets, hydrated]);

  const selectedAsset = assets.find((asset) => asset.id === selectedAssetId) ?? null;
  const nearbyCandidates = useMemo(() => {
    if (!selectedAsset) return [];
    return candidates
      .map((candidate) => ({ candidate, distanceKm: distanceKm(selectedAsset.latitude, selectedAsset.longitude, candidate.latitude, candidate.longitude) }))
      .sort((left, right) => left.distanceKm - right.distanceKm);
  }, [candidates, selectedAsset]);
  const withinRadius = nearbyCandidates.filter((item) => item.distanceKm <= radiusKm);

  const addAsset = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const parsedLatitude = numberFromInput(latitude);
    const parsedLongitude = numberFromInput(longitude);
    if (!name.trim() || parsedLatitude === null || parsedLongitude === null || Math.abs(parsedLatitude) > 90 || Math.abs(parsedLongitude) > 180) {
      setMessage("Введите название и корректные координаты: широта −90…90, долгота −180…180.");
      return;
    }
    const asset: CompanyAsset = { id: newId(), name: name.trim(), type, latitude: parsedLatitude, longitude: parsedLongitude, createdAt: new Date().toISOString() };
    setAssets((current) => [...current, asset]);
    setSelectedAssetId(asset.id);
    setName("");
    setLatitude("");
    setLongitude("");
    setMessage("Объект добавлен только в хранилище этого браузера.");
  };

  const importGeoJson = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    if (file.size > MAX_GEOJSON_BYTES) {
      setMessage(`GeoJSON больше ${(MAX_GEOJSON_BYTES / 1_000_000).toFixed(0)} МБ не импортируется: сначала оставьте не более ${MAX_GEOJSON_FEATURES} нужных Point-объектов.`);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const imported = parseGeoJsonAssets(JSON.parse(String(reader.result)));
        setAssets((current) => [...current, ...imported]);
        setSelectedAssetId(imported[0].id);
        setMessage(`Импортировано объектов: ${imported.length}${imported.length === MAX_GEOJSON_FEATURES ? ` (лимит ${MAX_GEOJSON_FEATURES})` : ""}. Они не отправлялись на сервер.`);
      } catch (cause) {
        setMessage(cause instanceof Error ? cause.message : "Не удалось импортировать GeoJSON.");
      }
    };
    reader.onerror = () => setMessage("Не удалось прочитать выбранный файл.");
    reader.readAsText(file);
  };

  const removeAsset = (assetId: string) => {
    const next = assets.filter((asset) => asset.id !== assetId);
    setAssets(next);
    if (selectedAssetId === assetId) setSelectedAssetId(next[0]?.id ?? "");
    setMessage("Объект удалён из хранилища этого браузера.");
  };

  const visibleRouteContext = routeContext?.assetId === selectedAsset?.id ? routeContext : null;

  return <section id="asset-mode" aria-labelledby="asset-mode-title" className="scroll-mt-20 rounded-3xl border border-emerald-200 bg-emerald-50 p-5 shadow-sm sm:p-7">
    <div className="flex flex-wrap items-start justify-between gap-4"><div className="max-w-4xl"><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-800">Asset mode · для инфраструктурных команд</p><h2 id="asset-mode-title" className="mt-1 text-2xl font-bold tracking-tight text-emerald-950">Покажите, что проверить рядом с объектом компании</h2><p className="mt-2 text-sm leading-6 text-emerald-950">Добавьте координату дороги, карьера, ГЭС, водозабора или другого объекта. GlacierNET‑KZ найдёт реальные инвентарные озёра поблизости и даст объяснимую очередь проверки. Это географическая близость, <strong>не расчёт зоны поражения и не вероятность события.</strong></p></div><Building2 className="h-8 w-8 shrink-0 text-emerald-700" /></div>

    <div className="mt-5 grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
      <div className="rounded-2xl border border-emerald-200 bg-white p-4"><h3 className="font-bold text-slate-950">Добавить объект</h3><form onSubmit={addAsset} className="mt-4 grid gap-3"><label className="grid gap-1.5 text-sm font-semibold text-slate-700">Название объекта<input aria-label="Название объекта" value={name} onChange={(event) => setName(event.target.value)} className="min-h-11 rounded-lg border border-slate-300 px-3 text-slate-950 focus:border-emerald-600 focus:outline-2 focus:outline-emerald-200" placeholder="Например: водозабор №1" /></label><label className="grid gap-1.5 text-sm font-semibold text-slate-700">Тип<select aria-label="Тип объекта" value={type} onChange={(event) => setType(event.target.value)} className="min-h-11 rounded-lg border border-slate-300 bg-white px-3 text-slate-950 focus:border-emerald-600 focus:outline-2 focus:outline-emerald-200">{ASSET_TYPES.map((option) => <option key={option}>{option}</option>)}</select></label><div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1.5 text-sm font-semibold text-slate-700">Широта<input aria-label="Широта" inputMode="decimal" value={latitude} onChange={(event) => setLatitude(event.target.value)} className="min-h-11 rounded-lg border border-slate-300 px-3 text-slate-950 focus:border-emerald-600 focus:outline-2 focus:outline-emerald-200" placeholder="42.9753" /></label><label className="grid gap-1.5 text-sm font-semibold text-slate-700">Долгота<input aria-label="Долгота" inputMode="decimal" value={longitude} onChange={(event) => setLongitude(event.target.value)} className="min-h-11 rounded-lg border border-slate-300 px-3 text-slate-950 focus:border-emerald-600 focus:outline-2 focus:outline-emerald-200" placeholder="76.9723" /></label></div><button type="submit" className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-emerald-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"><MapPinned className="h-4 w-4" />Добавить и проверить</button></form><label className="mt-4 flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl border border-dashed border-emerald-300 px-4 py-2 text-sm font-bold text-emerald-900 transition hover:bg-emerald-50 focus-within:outline-2 focus-within:outline-emerald-700"><FileUp className="h-4 w-4" />Импортировать GeoJSON<input aria-label="Импортировать GeoJSON" type="file" accept=".geojson,application/geo+json,application/json" onChange={importGeoJson} className="sr-only" /></label><p className="mt-3 text-xs leading-5 text-slate-600">Поддерживаются Point‑объекты GeoJSON до 1 МБ; импорт ограничен {MAX_GEOJSON_FEATURES} объектами. Координаты остаются только в браузере и не передаются API.</p></div>

      <div className="rounded-2xl border border-emerald-200 bg-white p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold text-slate-950">Очередь вокруг объекта</h3><p className="mt-1 text-sm text-slate-600">Поиск среди {candidates.length.toLocaleString("ru-RU")} доступных кандидатов из {scannedLakes.toLocaleString("ru-RU")} озёр.</p></div><label className="text-sm font-semibold text-slate-700">Радиус <select aria-label="Радиус поиска" value={radiusKm} onChange={(event) => setRadiusKm(Number(event.target.value))} className="ml-2 min-h-10 rounded-lg border border-slate-300 bg-white px-2 text-slate-950 focus:border-emerald-600 focus:outline-2 focus:outline-emerald-200"><option value={10}>10 км</option><option value={25}>25 км</option><option value={50}>50 км</option></select></label></div>
        {!selectedAsset ? <div className="mt-5 rounded-xl bg-slate-50 p-5 text-sm leading-6 text-slate-600"><LocateFixed className="mb-2 h-5 w-5 text-emerald-700" />Добавьте объект компании слева. После этого здесь появятся ближайшие реальные озёра, приоритеты и кнопка перехода к карте.</div> : <><div className="mt-4 flex flex-wrap gap-2">{assets.map((asset) => <div key={asset.id} className={`inline-flex min-h-10 max-w-full items-center gap-1 rounded-lg border p-1 ${asset.id === selectedAsset.id ? "border-emerald-500 bg-emerald-100 text-emerald-950" : "border-slate-200 bg-white text-slate-700"}`}><button type="button" onClick={() => setSelectedAssetId(asset.id)} aria-pressed={asset.id === selectedAsset.id} className="min-h-9 min-w-0 rounded-md px-2 text-left text-sm font-semibold hover:bg-white/70 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"><span className="block truncate">{asset.name}</span><span className="block text-xs font-normal">{asset.type}</span></button><button type="button" aria-label={`Удалить ${asset.name}`} onClick={() => removeAsset(asset.id)} className="grid h-9 w-9 shrink-0 place-items-center rounded text-slate-500 hover:bg-white hover:text-red-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-700"><Trash2 className="h-4 w-4" /></button></div>)}</div><p className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-950"><strong>{selectedAsset.name}</strong> · {formatCoordinate(selectedAsset.latitude)}° N · {formatCoordinate(selectedAsset.longitude)}° E. В радиусе {radiusKm} км: <strong>{withinRadius.length}</strong> кандидатов из доступной очереди.</p>{visibleRouteContext && <p className="mt-3 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm leading-6 text-sky-950"><strong>Контекст HydroRIVERS:</strong> {visibleRouteContext.status === "loading" ? "проверяем локальный маршрут и planning-corridor…" : visibleRouteContext.status === "available" ? <>на карте показано {visibleRouteContext.routeLengthKm?.toFixed(1) ?? "—"} км маршрута и {visibleRouteContext.corridorWidthM ?? "—"} м planning‑corridor.</> : <>для выбранного RGI локальный маршрут недоступен; показана только координата объекта и инвентарный screening.</>} Это маршрут проверки по справочной гидрографии, <strong>не модель потока, затопления или воздействия.</strong></p>}{withinRadius.length === 0 ? <p className="mt-4 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">В выбранном радиусе нет кандидатов из доступной очереди. Это не означает отсутствия риска: увеличьте радиус или используйте полный Risk Twin.</p> : <ol className="mt-4 space-y-2">{withinRadius.slice(0, 3).map(({ candidate, distanceKm: distance }, index) => <li key={regionalObservationCandidateKey(candidate)} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 p-3"><div><p className="text-xs font-black text-emerald-800">{index + 1}. {distance.toFixed(1)} км от объекта</p><p className="mt-1 font-bold text-slate-950">{(candidate.area_current_m2 / 1_000_000).toFixed(3)} км² · {candidate.area_change_percent === null ? "нет сравнения" : `${candidate.area_change_percent > 0 ? "+" : ""}${candidate.area_change_percent.toFixed(1)}%`}</p><p className="mt-1 text-xs text-slate-600">Приоритет проверки {candidate.observation_priority_0_100.toFixed(0)}/100</p></div><button type="button" onClick={() => onSelectCandidate(candidate, selectedAsset)} className="min-h-10 rounded-lg bg-slate-950 px-3 py-2 text-sm font-bold text-white transition hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700">Показать маршрут на карте</button></li>)}</ol>}</>}
      </div>
    </div>
    {message && <p role="status" aria-live="polite" className="mt-4 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm text-emerald-950">{message}</p>}
  </section>;
}
