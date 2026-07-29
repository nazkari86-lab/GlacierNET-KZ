"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { GlacierRecord } from "@/lib/api";
import type { CryoGenesisTwinMatch } from "@/lib/cryogenesis";

interface CryoGenesisMapProps {
  target: GlacierRecord | null;
  twins: Array<{ glacier: GlacierRecord; match: CryoGenesisTwinMatch }>;
  selectedRgiId: string;
  onSelect: (rgiId: string) => void;
}

export default function CryoGenesisMap({
  target,
  twins,
  selectedRgiId,
  onSelect,
}: CryoGenesisMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!elementRef.current || mapRef.current) return;
    const map = L.map(elementRef.current, {
      preferCanvas: true,
      zoomControl: false,
    }).setView([43.1, 77.1], 9);
    mapRef.current = map;
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);
    const street = L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 18, attribution: "© OpenStreetMap contributors" },
    ).addTo(map);
    const satellite = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 18, attribution: "Tiles © Esri" },
    );
    L.control
      .layers({ Terrain: street, Satellite: satellite }, undefined, {
        collapsed: true,
      })
      .addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const group = layerRef.current;
    if (!map || !group) return;
    group.clearLayers();
    const bounds = L.latLngBounds([]);

    const add = (
      glacier: GlacierRecord,
      role: "target" | "twin",
      match?: CryoGenesisTwinMatch,
    ) => {
      if (!glacier.geometry) return;
      const selected = glacier.rgi_id === selectedRgiId;
      const layer = L.geoJSON(glacier.geometry as GeoJSON.GeoJsonObject, {
        style: {
          color: role === "target" ? "#06b6d4" : "#8b5cf6",
          weight: selected ? 5 : role === "target" ? 4 : 2.5,
          fillColor: role === "target" ? "#22d3ee" : "#a78bfa",
          fillOpacity: selected ? 0.36 : 0.18,
        },
      });
      const root = document.createElement("div");
      const heading = document.createElement("strong");
      heading.textContent = glacier.name || glacier.rgi_id;
      const identifier = document.createElement("p");
      identifier.textContent = `${role === "target" ? "Target" : "Matched twin"} · ${glacier.rgi_id}`;
      const detail = document.createElement("p");
      detail.textContent = match
        ? `Distance ${match.total_distance.toFixed(3)} · weight ${(match.weight * 100).toFixed(1)}%`
        : `RGI area ${glacier.rgi_area_km2.toFixed(3)} km²`;
      root.append(heading, identifier, detail);
      layer.bindPopup(root);
      layer.on("click", () => onSelect(glacier.rgi_id));
      layer.addTo(group);
      bounds.extend(layer.getBounds());
    };

    if (target) add(target, "target");
    twins.forEach(({ glacier, match }) => add(glacier, "twin", match));
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.2), { maxZoom: 13 });
  }, [onSelect, selectedRgiId, target, twins]);

  return (
    <div className="relative h-[520px] overflow-hidden rounded-3xl bg-slate-900">
      <div
        ref={elementRef}
        className="absolute inset-0"
        role="application"
        aria-label="Map of exact target glacier and matched twins; names appear after selection"
      />
      <div className="pointer-events-none absolute bottom-3 left-3 z-[500] flex gap-2 text-xs">
        <span className="rounded-full bg-slate-950/90 px-3 py-1 text-cyan-200">
          Target
        </span>
        <span className="rounded-full bg-slate-950/90 px-3 py-1 text-violet-200">
          Matched twins
        </span>
      </div>
    </div>
  );
}

