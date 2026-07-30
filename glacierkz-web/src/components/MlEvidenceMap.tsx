"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { apiUrl } from "@/lib/utils";
import type { MlEvidenceCase } from "@/lib/api";

interface MlEvidenceMapProps {
  evidence: MlEvidenceCase;
}

export default function MlEvidenceMap({ evidence }: MlEvidenceMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!elementRef.current) return;
    const map = L.map(elementRef.current, {
      zoomControl: true,
      attributionControl: true,
      preferCanvas: true,
    });
    const streets = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap © CARTO",
    });
    const satellite = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 19, attribution: "Esri World Imagery" }
    ).addTo(map);

    const rgi = L.geoJSON(
      {
        type: "Feature",
        properties: { layer: "RGI 7.0 inventory" },
        geometry: evidence.map.rgi_geometry,
      } as GeoJSON.Feature,
      {
        style: {
          color: "#38bdf8",
          weight: 3,
          dashArray: "7 5",
          fillColor: "#38bdf8",
          fillOpacity: 0.08,
        },
      }
    ).bindPopup(
      `<strong>RGI 7.0</strong><br/>Inventory reference: ${evidence.metrics.rgi_rasterized_area_km2.toFixed(4)} km²`
    ).addTo(map);

    const model = evidence.map.model_geometry
      ? L.geoJSON(
          {
            type: "Feature",
            properties: { layer: "ML boundary" },
            geometry: evidence.map.model_geometry,
          } as GeoJSON.Feature,
          {
            style: {
              color: "#22c55e",
              weight: 3,
              fillColor: "#22c55e",
              fillOpacity: 0.22,
            },
          }
        ).bindPopup(
          `<strong>ML boundary · ${evidence.year}</strong><br/>${evidence.metrics.predicted_area_km2.toFixed(4)} km²<br/>Click layers to inspect evidence.`
        ).addTo(map)
      : null;
    const guided = evidence.map.inventory_guided_geometry
      ? L.geoJSON(
          {
            type: "Feature",
            properties: { layer: "Generalisation Sentinel" },
            geometry: evidence.map.inventory_guided_geometry,
          } as GeoJSON.Feature,
          {
            style: {
              color: "#a855f7",
              weight: 3,
              dashArray: "3 4",
              fillColor: "#a855f7",
              fillOpacity: 0.18,
            },
          }
        ).bindPopup(
          `<strong>Inventory-guided safeguard · ${evidence.year}</strong><br/>${evidence.metrics.inventory_guided_area_km2.toFixed(4)} km²<br/>Physical candidate for review, not independent accuracy.`
        ).addTo(map)
      : null;

    const probabilityUrl = evidence.artifacts.probability_preview_url;
    const entropyUrl = evidence.artifacts.entropy_preview_url;
    const probability = probabilityUrl
      ? L.imageOverlay(apiUrl(probabilityUrl), evidence.map.bounds, { opacity: 0.55 })
      : null;
    const entropy = entropyUrl
      ? L.imageOverlay(apiUrl(entropyUrl), evidence.map.bounds, { opacity: 0.62 })
      : null;

    const overlays: Record<string, L.Layer> = {
      "RGI 7.0 · inventory": rgi,
    };
    if (model) overlays[`${evidence.year} · ML boundary`] = model;
    if (guided) overlays[`${evidence.year} · Generalisation Sentinel`] = guided;
    if (probability) overlays["Model probability"] = probability;
    if (entropy) overlays["Predictive entropy"] = entropy;
    L.control.layers({ "Satellite imagery": satellite, "Light map": streets }, overlays, {
      collapsed: false,
      position: "topright",
    }).addTo(map);
    L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);
    map.fitBounds(evidence.map.bounds, { padding: [20, 20], maxZoom: 15 });

    return () => {
      map.remove();
    };
  }, [evidence]);

  return (
    <div className="relative h-full min-h-[500px] w-full overflow-hidden rounded-2xl" aria-label="ML evidence map">
      <div ref={elementRef} className="h-full min-h-[500px] w-full" />
      <div className="pointer-events-none absolute bottom-5 right-4 z-[500] rounded-xl border border-white/20 bg-slate-950/88 px-3 py-2 text-xs text-white shadow-xl backdrop-blur">
        <div className="flex items-center gap-2"><span className="h-0.5 w-5 bg-emerald-400" />ML boundary</div>
        <div className="mt-1 flex items-center gap-2"><span className="w-5 border-t-2 border-dashed border-sky-400" />RGI inventory</div>
        <div className="mt-1 flex items-center gap-2"><span className="w-5 border-t-2 border-dotted border-violet-400" />Safeguarded candidate</div>
      </div>
    </div>
  );
}
