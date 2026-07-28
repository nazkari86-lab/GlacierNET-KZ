"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { GlacierRecord, YearMapLayer } from "@/lib/api";
import type { EvidenceKind, EvidenceMapObject } from "@/lib/riskTwinEvidence";

type MapMode = "evidence" | "route" | "people";
type Basemap = "terrain" | "satellite";

interface RiskTwinMapProps {
  glacier: GlacierRecord | null;
  objects: EvidenceMapObject[];
  selectedObjectId: string | null;
  onSelectObject: (id: string) => void;
  mode: MapMode;
  yearLayer: YearMapLayer | null;
  comparisonLayer: YearMapLayer | null;
}

const KIND_LABELS: Record<EvidenceKind, string> = {
  glacier: "Ледник RGI",
  annual_segmentation: "Годовая сегментация",
  lake: "Озёра",
  river: "Русла HydroRIVERS",
  basin: "Бассейны HydroBASINS",
  historical_record: "Архивные записи",
  asset: "Объекты OSM",
};

const KIND_STYLE: Record<EvidenceKind, L.PathOptions> = {
  glacier: { color: "#67e8f9", weight: 3.5, fillColor: "#22d3ee", fillOpacity: 0.22 },
  annual_segmentation: { color: "#818cf8", weight: 2.5, fillColor: "#818cf8", fillOpacity: 0.08, dashArray: "6 5" },
  lake: { color: "#60a5fa", weight: 2, fillColor: "#2563eb", fillOpacity: 0.34 },
  river: { color: "#38bdf8", weight: 3, opacity: 0.9 },
  basin: { color: "#c084fc", weight: 1.8, fillColor: "#a855f7", fillOpacity: 0.05, dashArray: "6 6" },
  historical_record: { color: "#ffffff", weight: 2, fillColor: "#ef4444", fillOpacity: 0.95 },
  asset: { color: "#ffffff", weight: 1.5, fillColor: "#8b5cf6", fillOpacity: 0.95 },
};

function popup(object: EvidenceMapObject): HTMLElement {
  const root = document.createElement("div");
  const heading = document.createElement("strong");
  heading.textContent = object.name;
  root.append(heading);
  for (const line of [object.source, object.visibleFact, `Можно: ${object.allowedClaim}`, `Нельзя: ${object.prohibitedClaim}`]) {
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

export default function RiskTwinMap({ glacier, objects, selectedObjectId, onSelectObject, mode, yearLayer, comparisonLayer }: RiskTwinMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const contentLayerRef = useRef<L.LayerGroup | null>(null);
  const objectLayerRef = useRef(new Map<string, L.Layer>());
  const baseLayersRef = useRef<Partial<Record<Basemap, L.TileLayer>>>({});
  const fittedGlacierRef = useRef<string | null>(null);
  const [mapError, setMapError] = useState("");
  const [basemap, setBasemap] = useState<Basemap>("terrain");
  const [visibleKinds, setVisibleKinds] = useState<Record<EvidenceKind, boolean>>({
    glacier: true, annual_segmentation: true, lake: true, river: true, basin: true, historical_record: true, asset: true,
  });

  useEffect(() => {
    if (!elementRef.current || mapRef.current) return;
    const objectLayers = objectLayerRef.current;
    const map = L.map(elementRef.current, { preferCanvas: true, zoomControl: false, attributionControl: true });
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
    const active = layers[basemap];
    const inactive = basemap === "terrain" ? layers.satellite : layers.terrain;
    if (!active || !inactive) return;
    if (map.hasLayer(inactive)) map.removeLayer(inactive);
    if (!map.hasLayer(active)) active.addTo(map);
  }, [basemap]);

  useEffect(() => {
    const map = mapRef.current;
    const content = contentLayerRef.current;
    if (!map || !content) return;
    content.clearLayers();
    objectLayerRef.current.clear();
    setMapError("");

    const attach = (object: EvidenceMapObject, layer: L.Layer & { bindPopup?: (content: HTMLElement) => unknown; bindTooltip?: (content: string, options?: L.TooltipOptions) => unknown }) => {
      layer.bindPopup?.(popup(object));
      layer.bindTooltip?.(object.name, { permanent: object.kind !== "basin", direction: "top", className: "risk-twin-object-label" });
      layer.on("click", () => onSelectObject(object.id));
      content.addLayer(layer);
      objectLayerRef.current.set(object.id, layer);
    };

    if (yearLayer && visibleKinds.annual_segmentation) {
      const annualImage = L.imageOverlay(yearLayer.image_url, yearLayer.bounds as L.LatLngBoundsExpression, { opacity: comparisonLayer ? 0.4 : 0.58, alt: `${yearLayer.year} segmentation screening layer` });
      annualImage.on("error", () => setMapError(`${yearLayer.year} map layer unavailable; other local layers remain visible.`));
      content.addLayer(annualImage);
    }
    if (comparisonLayer && visibleKinds.annual_segmentation) {
      const comparisonImage = L.imageOverlay(comparisonLayer.image_url, comparisonLayer.bounds as L.LatLngBoundsExpression, { opacity: 0.34, alt: `${comparisonLayer.year} comparison segmentation screening layer` });
      comparisonImage.on("error", () => setMapError(`${comparisonLayer.year} comparison layer unavailable; current local layer remains visible.`));
      content.addLayer(comparisonImage);
    }

    for (const object of objects) {
      if (!visibleKinds[object.kind]) continue;
      const selected = object.id === selectedObjectId;
      const style = { ...KIND_STYLE[object.kind], weight: (KIND_STYLE[object.kind].weight ?? 2) + (selected ? 1.7 : 0), className: mode === "route" && object.kind === "river" ? "risk-twin-route-flow" : undefined };
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
  }, [comparisonLayer, glacier, mode, objects, onSelectObject, selectedObjectId, visibleKinds, yearLayer]);

  useEffect(() => {
    if (!selectedObjectId) return;
    const map = mapRef.current;
    const layer = objectLayerRef.current.get(selectedObjectId) as (L.Layer & { getBounds?: () => L.LatLngBounds; openPopup?: () => unknown }) | undefined;
    if (!map || !layer) return;
    const bounds = layer.getBounds?.();
    if (bounds?.isValid()) map.fitBounds(bounds, { padding: [64, 64], maxZoom: 14 });
    layer.openPopup?.();
  }, [selectedObjectId]);

  const toggleKind = (kind: EvidenceKind) => setVisibleKinds((current) => ({ ...current, [kind]: !current[kind] }));

  return (
    <div className="space-y-3">
      <div className="risk-twin-map relative overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-[0_24px_60px_-30px_rgba(15,23,42,0.75)]">
        <div ref={elementRef} className="h-[620px] w-full" aria-label="Risk Twin evidence map" />
        <div className="absolute left-3 top-3 z-[500] max-w-[268px] rounded-xl border border-white/15 bg-slate-950/90 p-3 text-white shadow-lg backdrop-blur">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-200">Карта доказательств</p>
          <p className="mt-1 text-sm font-semibold">Именованные объекты и границы вывода</p>
          <p className="mt-1 text-xs leading-4 text-slate-300">Выберите объект: справа появятся источник, допустимое утверждение и следующая проверка.</p>
        </div>
        <div className="absolute right-3 top-3 z-[500] flex max-w-[calc(100%-24px)] flex-wrap justify-end gap-1.5">
          <button type="button" onClick={() => setBasemap("terrain")} aria-pressed={basemap === "terrain"} className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold shadow-sm backdrop-blur ${basemap === "terrain" ? "border-cyan-200 bg-cyan-100 text-cyan-950" : "border-white/20 bg-slate-950/85 text-white"}`}>Карта</button>
          <button type="button" onClick={() => setBasemap("satellite")} aria-pressed={basemap === "satellite"} className={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold shadow-sm backdrop-blur ${basemap === "satellite" ? "border-cyan-200 bg-cyan-100 text-cyan-950" : "border-white/20 bg-slate-950/85 text-white"}`}>Спутник</button>
        </div>
        <div className="absolute bottom-8 left-3 right-16 z-[500] flex flex-wrap gap-1.5">
          {(Object.keys(KIND_LABELS) as EvidenceKind[]).map((kind) => <button key={kind} type="button" aria-pressed={visibleKinds[kind]} onClick={() => toggleKind(kind)} className={`rounded-full border px-2 py-1 text-[10px] font-semibold shadow-sm backdrop-blur ${visibleKinds[kind] ? "border-cyan-100 bg-slate-950/90 text-white" : "border-slate-500 bg-slate-950/70 text-slate-400 line-through"}`}>{KIND_LABELS[kind]}</button>)}
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600" aria-label="Map legend"><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-cyan-400" />инвентарь/слой</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-blue-500" />вода и русла</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-violet-500" />бассейн/OSM</span><span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-red-500" />архивная запись</span></div>
      {mapError && <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-medium text-amber-900">{mapError}</p>}
    </div>
  );
}
