"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GlacierRecord, MlEvidenceCase, YearMapLayer } from "@/lib/api";
import type { EvidenceKind, EvidenceMapObject } from "@/lib/riskTwinEvidence";
import { apiUrl } from "@/lib/utils";

type MapMode = "evidence" | "route" | "people";
type Basemap = "offline" | "terrain" | "satellite";

interface RiskTwinMapProps {
  glacier: GlacierRecord | null;
  objects: EvidenceMapObject[];
  selectedObjectId: string | null;
  onSelectObject: (id: string) => void;
  mode: MapMode;
  yearLayer: YearMapLayer | null;
  comparisonLayer: YearMapLayer | null;
  mlEvidence?: MlEvidenceCase | null;
  compact?: boolean;
  pinnedObjectIds?: string[];
}

const KIND_LABELS: Record<EvidenceKind, string> = {
  glacier: "Ледник RGI",
  annual_segmentation: "Годовая сегментация",
  lake: "Озёра",
  river: "Русла HydroRIVERS",
  corridor: "Коридор проверки",
  basin: "Бассейны HydroBASINS",
  historical_record: "Архивные записи",
  asset: "Объекты OSM",
};

const KIND_STYLE: Record<EvidenceKind, L.PathOptions> = {
  glacier: { color: "#67e8f9", weight: 3.5, fillColor: "#22d3ee", fillOpacity: 0.22 },
  annual_segmentation: { color: "#818cf8", weight: 2.5, fillColor: "#818cf8", fillOpacity: 0.08, dashArray: "6 5" },
  lake: { color: "#60a5fa", weight: 2, fillColor: "#2563eb", fillOpacity: 0.34 },
  river: { color: "#38bdf8", weight: 3, opacity: 0.9 },
  corridor: { color: "#fb923c", weight: 2, fillColor: "#f97316", fillOpacity: 0.12, dashArray: "8 6" },
  basin: { color: "#c084fc", weight: 1.8, fillColor: "#a855f7", fillOpacity: 0.05, dashArray: "6 6" },
  historical_record: { color: "#ffffff", weight: 2, fillColor: "#ef4444", fillOpacity: 0.95 },
  asset: { color: "#ffffff", weight: 1.5, fillColor: "#8b5cf6", fillOpacity: 0.95 },
};
const NO_PINNED_OBJECT_IDS: string[] = [];

function popup(object: EvidenceMapObject, compact = false): HTMLElement {
  const root = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = object.name;
  root.append(heading);
  const lines = compact ? [object.source, object.visibleFact] : [object.source, object.visibleFact, `Можно: ${object.allowedClaim}`, `Нельзя: ${object.prohibitedClaim}`];
  for (const line of lines) {
    const paragraph = document.createElement("p");
    paragraph.className = "mt-1 text-xs leading-4";
    paragraph.textContent = line;
    root.append(paragraph);
  }
  return root;
}

function pointStyle(kind: EvidenceKind, latlng: L.LatLng): L.CircleMarker {
  const style = KIND_STYLE[kind];
  return L.circleMarker(latlng, { ...style, radius: kind === "historical_record" ? 7 : 6 });
}

export default function RiskTwinMap({ glacier, objects, selectedObjectId, onSelectObject, mode, yearLayer, comparisonLayer, mlEvidence = null, compact = false, pinnedObjectIds = NO_PINNED_OBJECT_IDS }: RiskTwinMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const contentLayerRef = useRef<L.LayerGroup | null>(null);
  const objectLayerRef = useRef(new Map<string, L.Layer>());
  const baseLayersRef = useRef<Partial<Record<Basemap, L.TileLayer>>>({});
  const fittedGlacierRef = useRef<string | null>(null);
  const [mapError, setMapError] = useState("");
  const [basemap, setBasemap] = useState<Basemap>(() => compact ? "satellite" : "offline");
  const [showMlBoundary, setShowMlBoundary] = useState(true);
  const [visibleKinds, setVisibleKinds] = useState<Record<EvidenceKind, boolean>>({
    glacier: true, annual_segmentation: true, lake: true, river: false, corridor: false, basin: false, historical_record: false, asset: false,
  });
  const selectedObject = objects.find((object) => object.id === selectedObjectId) ?? null;
  // A selected glacier context is intentionally finite (10 km by default),
  // so hiding all but the three highest ranked lakes loses useful evidence.
  // Render every supplied local object; users can still toggle source kinds.
  const mapObjects = objects;

  useEffect(() => {
    if (!elementRef.current || mapRef.current) return;
    const objectLayers = objectLayerRef.current;
    // Leaflet's shared canvas renderer can redraw after its canvas is torn
    // down during React/Turbopack updates, producing a visible dev overlay.
    // SVG keeps this evidence map stable while preserving the same GeoJSON.
    const map = L.map(elementRef.current, { preferCanvas: false, zoomControl: false, attributionControl: true });
    mapRef.current = map;
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);
    const terrain = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap contributors" });
    const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", { maxZoom: 18, attribution: "Tiles © Esri" });
    terrain.addTo(map);
    terrain.on("tileerror", () => setMapError("Базовая карта недоступна; локальные научные слои остаются на экране."));
    satellite.on("tileerror", () => setMapError("Спутниковая подложка недоступна; локальные научные слои остаются на экране."));
    baseLayersRef.current = { terrain, satellite };
    contentLayerRef.current = L.layerGroup().addTo(map);
    map.setView([43.1, 77.2], 9);
    return () => {
      map.remove();
      mapRef.current = null;
      contentLayerRef.current = null;
      objectLayers.clear();
      baseLayersRef.current = {};
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layers = baseLayersRef.current;
    if (!map || !layers.terrain || !layers.satellite) return;
    if (basemap === "offline") {
      if (map.hasLayer(layers.terrain)) map.removeLayer(layers.terrain);
      if (map.hasLayer(layers.satellite)) map.removeLayer(layers.satellite);
      return;
    }
    const active = layers[basemap];
    const inactive = basemap === "terrain" ? layers.satellite : layers.terrain;
    if (!active || !inactive) return;
    if (map.hasLayer(inactive)) map.removeLayer(inactive);
    if (!map.hasLayer(active)) active.addTo(map);
  }, [basemap]);

  useEffect(() => {
    // Mode changes never manufacture a routed impact. They merely expose the
    // local source layers that support the user’s current inspection task.
    if (mode === "route") setVisibleKinds((current) => ({ ...current, river: true, corridor: true, basin: true }));
    if (mode === "people") setVisibleKinds((current) => ({ ...current, asset: true }));
  }, [mode]);

  useEffect(() => {
    const map = mapRef.current;
    const content = contentLayerRef.current;
    if (!map || !content) return;
    content.clearLayers();
    objectLayerRef.current.clear();
    setMapError("");

    const attach = (object: EvidenceMapObject, layer: L.Layer & { bindPopup?: (content: HTMLElement) => unknown }) => {
      layer.bindPopup?.(popup(object, compact));
      // Keep the geographic evidence readable: object names belong in the
      // click-triggered popup and inspector, not as permanently overlapping labels.
      layer.on("click", () => onSelectObject(object.id));
      content.addLayer(layer);
      objectLayerRef.current.set(object.id, layer);
    };

    // The decision view must foreground the actual lake and RGI boundaries.
    // A regional segmentation raster is still available in the full Risk Twin,
    // but makes the selected small object difficult to see on first contact.
    if (!compact && yearLayer && visibleKinds.annual_segmentation) {
      const annualImage = L.imageOverlay(apiUrl(yearLayer.image_url), yearLayer.bounds as L.LatLngBoundsExpression, { opacity: comparisonLayer ? 0.4 : 0.58, alt: `${yearLayer.year} segmentation screening layer` });
      annualImage.on("error", () => setMapError(`${yearLayer.year} map layer unavailable; other local layers remain visible.`));
      content.addLayer(annualImage);
    }
    if (!compact && comparisonLayer && visibleKinds.annual_segmentation) {
      const comparisonImage = L.imageOverlay(apiUrl(comparisonLayer.image_url), comparisonLayer.bounds as L.LatLngBoundsExpression, { opacity: 0.34, alt: `${comparisonLayer.year} comparison segmentation screening layer` });
      comparisonImage.on("error", () => setMapError(`${comparisonLayer.year} comparison layer unavailable; current local layer remains visible.`));
      content.addLayer(comparisonImage);
    }
    if (mlEvidence?.map.model_geometry && showMlBoundary) {
      const mlLayer = L.geoJSON(mlEvidence.map.model_geometry as GeoJSON.GeoJsonObject, {
        style: {
          color: "#22c55e",
          weight: 4,
          fillColor: "#22c55e",
          fillOpacity: 0.2,
        },
      });
      const details = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `${mlEvidence.year} multimodal ML boundary`;
      const metrics = document.createElement("p");
      metrics.className = "mt-1 text-xs leading-4";
      metrics.textContent = `${mlEvidence.metrics.predicted_area_km2.toFixed(4)} km² · RGI agreement ${(mlEvidence.metrics.rgi_overlap_iou * 100).toFixed(1)}% · review priority ${mlEvidence.metrics.review_priority_0_100}/100`;
      const limit = document.createElement("p");
      limit.className = "mt-1 text-xs leading-4";
      limit.textContent = "Model screening evidence; not independent accuracy or an event probability.";
      details.append(title, metrics, limit);
      mlLayer.bindPopup(details);
      content.addLayer(mlLayer);
    }

    for (const object of mapObjects) {
      if (!visibleKinds[object.kind] && !pinnedObjectIds.includes(object.id)) continue;
      const selected = object.id === selectedObjectId;
      const routeStyle = object.isRoute ? { color: "#f97316", weight: 5, opacity: 1 } : {};
      const style = { ...KIND_STYLE[object.kind], ...routeStyle, weight: (object.isRoute ? 5 : KIND_STYLE[object.kind].weight ?? 2) + (selected ? 1.7 : 0), className: mode === "route" && object.isRoute ? "risk-twin-route-flow" : undefined };
      const vector = L.geoJSON(object.geometry, {
        style,
        pointToLayer: (_, latlng) => pointStyle(object.kind, latlng),
      });
      attach(object, vector);
      if (selected) vector.openPopup();
    }

    const glacierLayer = glacier ? objectLayerRef.current.get(`glacier:${glacier.rgi_id}`) as L.FeatureGroup | undefined : undefined;
    if (glacierLayer && fittedGlacierRef.current !== glacier?.rgi_id) {
      const bounds = glacierLayer.getBounds();
      if (bounds.isValid()) map.fitBounds(bounds, { padding: [44, 44], maxZoom: 13 });
      fittedGlacierRef.current = glacier?.rgi_id ?? null;
    }
  }, [comparisonLayer, compact, glacier, mapObjects, mlEvidence, mode, onSelectObject, pinnedObjectIds, selectedObjectId, showMlBoundary, visibleKinds, yearLayer]);

  useEffect(() => {
    if (!selectedObjectId) return;
    const map = mapRef.current;
    const layer = objectLayerRef.current.get(selectedObjectId) as (L.Layer & { getBounds?: () => L.LatLngBounds; openPopup?: () => unknown }) | undefined;
    if (!map || !layer) return;
    const bounds = layer.getBounds?.();
    const glacierLayer = glacier ? objectLayerRef.current.get(`glacier:${glacier.rgi_id}`) as (L.Layer & { getBounds?: () => L.LatLngBounds }) | undefined : undefined;
    const glacierBounds = glacierLayer?.getBounds?.();
    if (bounds?.isValid() && glacierBounds?.isValid()) {
      map.fitBounds(bounds.extend(glacierBounds), { padding: [64, 64], maxZoom: 14 });
    } else if (bounds?.isValid()) {
      map.fitBounds(bounds, { padding: [64, 64], maxZoom: 14 });
    }
    layer.openPopup?.();
  }, [glacier, selectedObjectId]);

  const toggleKind = (kind: EvidenceKind) => setVisibleKinds((current) => ({ ...current, [kind]: !current[kind] }));

  const focusSelectedObject = () => {
    const map = mapRef.current;
    const layer = selectedObjectId ? objectLayerRef.current.get(selectedObjectId) as (L.Layer & { getBounds?: () => L.LatLngBounds }) | undefined : undefined;
    const bounds = layer?.getBounds?.();
    if (map && bounds?.isValid()) map.fitBounds(bounds, { padding: [64, 64], maxZoom: 14 });
  };

  return (
    <div className="space-y-3">
      <div className="risk-twin-map relative overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-[0_24px_60px_-30px_rgba(15,23,42,0.75)]">
        <div ref={elementRef} className="h-[620px] w-full" aria-label="Risk Twin evidence map" />
        <div className="absolute left-3 top-3 z-[500] max-w-[268px] rounded-xl border border-white/15 bg-slate-950/90 p-3 text-white shadow-lg backdrop-blur">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-200">Карта доказательств</p>
          {compact ? <><p className="mt-1 text-sm font-semibold">Выбранное озеро и граница ледника</p><p className="mt-1 text-xs leading-4 text-slate-300">Синий — озеро из инвентаря; бирюзовый — RGI‑граница. Нажмите контур для источника.</p><button type="button" onClick={focusSelectedObject} className="mt-3 inline-flex min-h-9 items-center rounded-lg bg-cyan-300 px-2.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">Приблизить выбранное озеро</button></> : selectedObject?.screening ? <>
            <p className="mt-1 text-sm font-semibold">Точный кейс: {selectedObject.name}</p>
            <p className="mt-1 text-xs leading-4 text-slate-200">{(selectedObject.screening.areaM2 / 1_000_000).toFixed(3)} км² · {selectedObject.screening.distanceToRgiBoundaryM.toFixed(0)} м до RGI · {selectedObject.screening.areaChangePercent === null ? "нет надёжного match 2020" : `${selectedObject.screening.areaChangePercent > 0 ? "+" : ""}${selectedObject.screening.areaChangePercent.toFixed(1)}% к 2020`}</p>
          </> : <>
            <p className="mt-1 text-sm font-semibold">Локальный набор для проверки</p>
            <p className="mt-1 text-xs leading-4 text-slate-300">Показаны все локальные объекты выбранного контекста. Включайте источники ниже, чтобы не перегружать карту.</p>
          </>}
          {selectedObject && !compact && <a href="#case-action-plan" className="mt-3 inline-flex min-h-9 items-center rounded-lg bg-cyan-300 px-2.5 text-xs font-bold text-slate-950 transition hover:bg-cyan-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white">{selectedObject.screening ? "Открыть действия по кейсу" : "Открыть план проверки"}</a>}
        </div>
        <div className={`absolute right-3 top-3 z-[500] flex max-w-[calc(100%-24px)] flex-wrap justify-end gap-1.5 ${compact ? "max-w-[190px]" : ""}`}>
          <button type="button" onClick={() => setBasemap("offline")} aria-pressed={basemap === "offline"} className={`min-h-10 rounded-lg border px-3 py-2 text-xs font-semibold shadow-sm backdrop-blur ${basemap === "offline" ? "border-cyan-200 bg-cyan-100 text-cyan-950" : "border-white/20 bg-slate-950/85 text-white"}`}>Локально</button>
          <button type="button" onClick={() => setBasemap("terrain")} aria-pressed={basemap === "terrain"} className={`min-h-10 rounded-lg border px-3 py-2 text-xs font-semibold shadow-sm backdrop-blur ${basemap === "terrain" ? "border-cyan-200 bg-cyan-100 text-cyan-950" : "border-white/20 bg-slate-950/85 text-white"}`}>Карта</button>
          <button type="button" onClick={() => setBasemap("satellite")} aria-pressed={basemap === "satellite"} className={`min-h-10 rounded-lg border px-3 py-2 text-xs font-semibold shadow-sm backdrop-blur ${basemap === "satellite" ? "border-cyan-200 bg-cyan-100 text-cyan-950" : "border-white/20 bg-slate-950/85 text-white"}`}>Спутник</button>
        </div>
        {!compact && <div className="absolute bottom-8 left-3 right-16 z-[500] flex flex-wrap gap-1.5">
          {mlEvidence && <button type="button" aria-pressed={showMlBoundary} onClick={() => setShowMlBoundary((current) => !current)} className={`min-h-9 rounded-full border px-3 py-2 text-[11px] font-semibold shadow-sm backdrop-blur ${showMlBoundary ? "border-emerald-200 bg-emerald-950/90 text-emerald-100" : "border-slate-500 bg-slate-950/70 text-slate-400 line-through"}`}>ML boundary · {mlEvidence.year}</button>}
          {(Object.keys(KIND_LABELS) as EvidenceKind[]).map((kind) => <button key={kind} type="button" aria-pressed={visibleKinds[kind]} onClick={() => toggleKind(kind)} className={`min-h-9 rounded-full border px-3 py-2 text-[11px] font-semibold shadow-sm backdrop-blur ${visibleKinds[kind] ? "border-cyan-100 bg-slate-950/90 text-white" : "border-slate-500 bg-slate-950/70 text-slate-400 line-through"}`}>{KIND_LABELS[kind]}{!mapObjects.some((object) => object.kind === kind) ? " · нет точного кейса" : ""}</button>)}
        </div>}
      </div>
      {basemap === "offline" && <p role="status" aria-live="polite" className="rounded-xl border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs font-medium text-cyan-950">Локальный презентационный режим: внешняя подложка отключена, но все локальные научные слои и выбранный кейс остаются доступны.</p>}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600" aria-label="Map legend"><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-emerald-500" />ML boundary</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-cyan-400" />инвентарь/слой</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-blue-500" />вода и русла</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-violet-500" />бассейн/OSM</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-red-500" />архивная запись</span></div>
      {mapError && <p role="status" aria-live="polite" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">{mapError}</p>}
    </div>
  );
}
