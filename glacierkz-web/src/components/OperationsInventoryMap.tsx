"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { FeatureCollection, Geometry } from "geojson";
import { fetchYearMapLayer, regionalObservationCandidateKey, type ChangeCandidate, type GlacierRecord, type OperationsAsset, type RegionalObservationScan, type YearMapLayer } from "@/lib/api";

interface OperationsInventoryMapProps { glaciers: GlacierRecord[]; assets: OperationsAsset[]; candidates: ChangeCandidate[]; selectedAssetId: string; onSelectAsset: (id: string) => void; riskTwinCandidates: RegionalObservationScan["candidates"]; selectedRiskTwinKey: string; onSelectRiskTwin: (key: string) => void; selectedYear: number; }

function popup(lines: Array<[string, string]>): HTMLElement {
  const root = document.createElement("div"); root.className = "space-y-1";
  for (const [label, value] of lines) { const row = document.createElement("p"); const strong = document.createElement("strong"); strong.textContent = `${label}: `; row.append(strong, document.createTextNode(value)); root.append(row); }
  return root;
}

export default function OperationsInventoryMap({ glaciers, assets, candidates, selectedAssetId, onSelectAsset, riskTwinCandidates, selectedRiskTwinKey, onSelectRiskTwin, selectedYear }: OperationsInventoryMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const inventoryRef = useRef<L.LayerGroup | null>(null);
  const operationsRef = useRef<L.LayerGroup | null>(null);
  const annualRef = useRef<L.LayerGroup | null>(null);
  const riskTwinRef = useRef<L.LayerGroup | null>(null);
  const glacierLayersRef = useRef(new Map<string, L.Layer>());
  const initialBoundsSet = useRef(false);
  const [query, setQuery] = useState("");
  const [selectedGlacier, setSelectedGlacier] = useState<GlacierRecord | null>(null);
  const [yearLayer, setYearLayer] = useState<YearMapLayer | null>(null);
  const [yearLayerError, setYearLayerError] = useState("");

  useEffect(() => {
    if (!elementRef.current || mapRef.current) return;
    // SVG is more reliable than Leaflet's shared canvas renderer during React
    // development remounts and route transitions. The regional inventory is
    // small enough that canvas brings no measurable benefit here.
    const map = L.map(elementRef.current, { zoomControl: true, attributionControl: true, preferCanvas: false }).setView([43.05, 77.2], 9);
    const street = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { maxZoom: 18, attribution: "© OpenStreetMap contributors" }).addTo(map);
    const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{x}/{y}", { maxZoom: 18, attribution: "Tiles © Esri" });
    inventoryRef.current = L.layerGroup().addTo(map); operationsRef.current = L.layerGroup().addTo(map); annualRef.current = L.layerGroup().addTo(map); riskTwinRef.current = L.layerGroup().addTo(map);
    L.control.layers({ "OpenStreetMap": street, "Satellite imagery": satellite }, { "RGI 7.0 glacier boundaries": inventoryRef.current, "Model segmentation (screening)": annualRef.current, "Risk Twin follow-up cases": riskTwinRef.current, "Observation objects": operationsRef.current }, { collapsed: true }).addTo(map);
    mapRef.current = map;
    return () => { map.remove(); mapRef.current = null; inventoryRef.current = null; operationsRef.current = null; annualRef.current = null; riskTwinRef.current = null; };
  }, []);

  useEffect(() => {
    setYearLayer(null); setYearLayerError(""); let active = true;
    fetchYearMapLayer(selectedYear).then((layer) => { if (active) setYearLayer(layer); }).catch((cause) => { if (active) setYearLayerError(cause instanceof Error ? cause.message : String(cause)); });
    return () => { active = false; };
  }, [selectedYear]);

  useEffect(() => {
    const target = inventoryRef.current; const map = mapRef.current; if (!target || !map) return;
    target.clearLayers(); glacierLayersRef.current.clear();
    const collection: FeatureCollection = { type: "FeatureCollection", features: glaciers.filter((glacier) => glacier.geometry).map((glacier) => ({ type: "Feature" as const, properties: { rgi_id: glacier.rgi_id, name: glacier.name_ru, area_km2: glacier.rgi_area_km2, wgms_reference: glacier.wgms_reference }, geometry: glacier.geometry as Geometry })) };
    const inventory = L.geoJSON(collection, { style: (feature) => ({ color: feature?.properties?.wgms_reference ? "#1d4ed8" : "#0369a1", weight: feature?.properties?.wgms_reference ? 2.5 : 1, fillColor: feature?.properties?.wgms_reference ? "#60a5fa" : "#38bdf8", fillOpacity: feature?.properties?.wgms_reference ? 0.55 : 0.25 }), onEachFeature: (feature, layer) => { const rgiId = String(feature.properties?.rgi_id ?? ""); glacierLayersRef.current.set(rgiId, layer); layer.bindPopup(popup([["Glacier", String(feature.properties?.name ?? "Unnamed")], ["RGI ID", rgiId], ["Inventory area", `${Number(feature.properties?.area_km2 ?? 0).toFixed(3)} km²`], ["Source", "Randolph Glacier Inventory 7.0"]])); layer.on("click", () => setSelectedGlacier(glaciers.find((item) => item.rgi_id === rgiId) ?? null)); } });
    inventory.addTo(target);
    if (!initialBoundsSet.current) { const bounds = inventory.getBounds(); if (bounds.isValid()) { map.fitBounds(bounds, { padding: [28, 28], maxZoom: 11 }); initialBoundsSet.current = true; } }
  }, [glaciers]);

  useEffect(() => {
    const target = operationsRef.current; if (!target) return; target.clearLayers();
    for (const asset of assets) { const candidate = candidates.find((item) => item.asset_id === asset.id); const selected = asset.id === selectedAssetId; const marker = L.circleMarker([asset.latitude, asset.longitude], { radius: selected ? 10 : 8, color: "#ffffff", weight: 3, fillColor: candidate?.status === "requires_review" ? "#6d28d9" : "#1d4ed8", fillOpacity: 1 }); marker.bindPopup(popup([["Observation object", asset.name], ["Status", candidate?.status?.replaceAll("_", " ") ?? asset.status], ["Evidence tier", asset.evidence_tier], ["Allowed use", asset.allowed_use]])); marker.on("click", () => onSelectAsset(asset.id)); marker.addTo(target); }
  }, [assets, candidates, onSelectAsset, selectedAssetId]);

  useEffect(() => {
    const target = riskTwinRef.current; if (!target) return; target.clearLayers();
    for (const candidate of riskTwinCandidates) { const key = regionalObservationCandidateKey(candidate); const selected = key === selectedRiskTwinKey; const marker = L.circleMarker([candidate.latitude, candidate.longitude], { radius: selected ? 11 : 7, color: "#ffffff", weight: 2.5, fillColor: "#0891b2", fillOpacity: 0.95 }); marker.bindPopup(popup([["Risk Twin follow-up case", candidate.glacier.name_ru || candidate.glacier.name], ["Lake", candidate.lake_id ?? "without ID"], ["Observation priority", `${candidate.observation_priority_0_100.toFixed(0)}/100`], ["Area change", candidate.area_change_percent === null ? "no reliable match" : `${candidate.area_change_percent.toFixed(1)}%`], ["RGI distance", `${candidate.distance_to_rgi_boundary_m.toFixed(0)} m`]])); marker.on("click", () => onSelectRiskTwin(key)); marker.addTo(target); }
  }, [onSelectRiskTwin, riskTwinCandidates, selectedRiskTwinKey]);

  useEffect(() => {
    const target = annualRef.current; if (!target) return; target.clearLayers();
    if (!yearLayer || yearLayer.year !== selectedYear) return;
    const overlay = L.imageOverlay(yearLayer.image_url, yearLayer.bounds as L.LatLngBoundsExpression, { opacity: 0.62, interactive: true, alt: `${selectedYear} segmentation screening layer` }); overlay.bindPopup(popup([["Year layer", `${selectedYear} · ${yearLayer.method.toUpperCase()}`], ["Scope", yearLayer.scope], ["Limitation", yearLayer.caveat]])); overlay.addTo(target);
  }, [selectedYear, yearLayer]);

  const matches = useMemo(() => { const normalized = query.trim().toLocaleLowerCase(); return normalized ? glaciers.filter((glacier) => `${glacier.name} ${glacier.name_ru} ${glacier.rgi_id}`.toLocaleLowerCase().includes(normalized)).slice(0, 8) : []; }, [glaciers, query]);
  const focusGlacier = useCallback((glacier: GlacierRecord) => { setSelectedGlacier(glacier); setQuery(glacier.name_ru); const layer = glacierLayersRef.current.get(glacier.rgi_id); if (layer instanceof L.Polygon) { mapRef.current?.fitBounds(layer.getBounds(), { padding: [60, 60], maxZoom: 14, animate: false }); layer.openPopup(); } else { mapRef.current?.setView([glacier.centroid.latitude, glacier.centroid.longitude], 13, { animate: false }); } }, []);

  return <div className="relative h-full min-h-[520px]"><div ref={elementRef} className="absolute inset-0 bg-slate-100" role="application" aria-label={`Interactive map with ${glaciers.length} real RGI glacier boundaries, ${selectedYear} model layer, and ${riskTwinCandidates.length} real Risk Twin follow-up cases`} data-testid="real-inventory-map" />
    <details className="absolute bottom-8 left-3 z-[600] w-[min(330px,calc(100%-24px))] rounded-xl border border-slate-200 bg-white/95 shadow-lg backdrop-blur" open={Boolean(query)}><summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold">Find any glacier · {glaciers.length} in registry</summary><div className="border-t border-slate-200 p-3"><label className="block"><span className="sr-only">Search by glacier name or RGI ID</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name or RGI ID" className="min-h-11 w-full rounded-lg border border-slate-300 px-3 text-sm" data-testid="map-glacier-search" /></label>{matches.length > 0 && <div className="mt-2 max-h-52 space-y-1 overflow-y-auto">{matches.map((glacier) => <button key={glacier.rgi_id} type="button" onClick={() => focusGlacier(glacier)} className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-blue-50"><span className="block font-medium">{glacier.name_ru}</span><span className="block truncate text-xs text-slate-500">{glacier.rgi_id} · {glacier.rgi_area_km2.toFixed(3)} km²</span></button>)}</div>}{query && matches.length === 0 && <p className="mt-2 text-sm text-slate-500">No matching glacier.</p>}{selectedGlacier && <div className="mt-3 rounded-lg bg-blue-50 p-3 text-xs text-blue-950"><strong className="block">{selectedGlacier.name_ru}</strong><span>{selectedGlacier.rgi_area_km2.toFixed(3)} km² · mean elevation {selectedGlacier.elevation.mean_m.toFixed(0)} m</span></div>}</div></details>
    <div className="pointer-events-none absolute bottom-2 right-2 z-[500] flex flex-wrap justify-end gap-2 text-[11px]"><span className="rounded bg-white/90 px-2 py-1 shadow"><i className="mr-1 inline-block h-2.5 w-2.5 bg-sky-500/70" />{selectedYear} segmentation</span><span className="rounded bg-white/90 px-2 py-1 shadow"><i className="mr-1 inline-block h-2.5 w-2.5 border border-sky-700 bg-sky-200" />RGI boundary</span><span className="rounded bg-white/90 px-2 py-1 shadow"><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-cyan-600" />Risk Twin case</span></div>
    {yearLayerError && <p className="absolute bottom-16 right-3 z-[600] max-w-sm rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">{selectedYear} map layer unavailable: {yearLayerError}</p>}
  </div>;
}
