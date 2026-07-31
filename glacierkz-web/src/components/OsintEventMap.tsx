"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { OsintEvent } from "@/lib/api";

interface OsintEventMapProps {
  events: OsintEvent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const COLORS: Record<string, string> = {
  earthquake: "#f97316",
  flood: "#2563eb",
  mudflow: "#dc2626",
  glacier_lake: "#06b6d4",
  heavy_precipitation: "#7c3aed",
  avalanche: "#64748b",
};

function markerRadius(priority: number): number {
  return Math.max(6, Math.min(13, 5 + priority / 14));
}

function popupContent(event: OsintEvent): HTMLElement {
  const root = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = event.title;
  root.append(title);
  for (const line of [
    event.source_name,
    event.link_rationale,
    `Приоритет наблюдения: ${event.observation_priority_0_100}/100`,
    "Не является вероятностью опасного события.",
  ]) {
    const paragraph = document.createElement("p");
    paragraph.className = "mt-1 text-xs leading-4";
    paragraph.textContent = line;
    root.append(paragraph);
  }
  return root;
}

export default function OsintEventMap({ events, selectedId, onSelect }: OsintEventMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const markersRef = useRef(new Map<string, L.CircleMarker>());

  useEffect(() => {
    if (!elementRef.current || mapRef.current) return;
    // SVG is more stable than Leaflet's shared canvas renderer during fast
    // Next.js route transitions and is sufficient for this bounded event set.
    const map = L.map(elementRef.current, { preferCanvas: false, zoomControl: false }).setView([43.2, 77.1], 6);
    mapRef.current = map;
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);
    const streets = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: "© OpenStreetMap contributors",
    }).addTo(map);
    const satellite = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 18, attribution: "Tiles © Esri" },
    );
    L.control.layers({ "OpenStreetMap": streets, "Satellite": satellite }, undefined, { position: "topright" }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = layerRef.current;
    if (!map || !layer) return;
    layer.clearLayers();
    markersRef.current.clear();
    const bounds = L.latLngBounds([]);
    const glacierIds = new Set<string>();
    for (const event of events) {
      if (event.latitude == null || event.longitude == null) continue;
      const color = COLORS[event.event_type] ?? "#475569";
      const marker = L.circleMarker([event.latitude, event.longitude], {
        radius: markerRadius(event.observation_priority_0_100),
        color: selectedId === event.id ? "#ffffff" : color,
        weight: selectedId === event.id ? 4 : 2,
        fillColor: color,
        fillOpacity: 0.82,
      });
      marker.bindPopup(popupContent(event), { maxWidth: 330 });
      marker.on("click", () => onSelect(event.id));
      marker.addTo(layer);
      markersRef.current.set(event.id, marker);
      bounds.extend([event.latitude, event.longitude]);

      const glacier = event.linked_glacier;
      if (glacier && !glacierIds.has(glacier.rgi_id)) {
        glacierIds.add(glacier.rgi_id);
        const point = L.circleMarker([glacier.centroid.latitude, glacier.centroid.longitude], {
          radius: 5,
          color: "#ecfeff",
          weight: 2,
          fillColor: "#0891b2",
          fillOpacity: 1,
        });
        point.bindPopup(`<strong>${glacier.name_ru}</strong><p class="mt-1 text-xs">RGI inventory centroid</p>`);
        point.addTo(layer);
        bounds.extend([glacier.centroid.latitude, glacier.centroid.longitude]);
      }
    }
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.15), { maxZoom: 9 });
  }, [events, onSelect, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    const marker = markersRef.current.get(selectedId);
    if (marker) {
      mapRef.current?.panTo(marker.getLatLng());
      marker.openPopup();
    }
  }, [selectedId]);

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-950 shadow-2xl">
      <div ref={elementRef} className="h-[480px] w-full" aria-label="Карта подтверждаемых OSINT-сигналов" />
      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-slate-800 bg-slate-950 px-4 py-3 text-xs text-slate-300">
        <span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-orange-500" />землетрясение</span>
        <span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-blue-600" />наводнение</span>
        <span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-cyan-600" />ледник RGI</span>
        <span>Название появляется только после нажатия.</span>
      </div>
    </div>
  );
}
