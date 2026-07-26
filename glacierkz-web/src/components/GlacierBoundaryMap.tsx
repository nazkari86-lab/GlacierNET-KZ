"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface GlacierBoundaryMapProps {
  geometry: { type: string; coordinates: unknown };
  name: string;
}

export default function GlacierBoundaryMap({ geometry, name }: GlacierBoundaryMapProps) {
  const elementRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!elementRef.current) return;
    mapRef.current?.remove();

    const map = L.map(elementRef.current, {
      zoomControl: true,
      attributionControl: true,
    });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap © CARTO",
    }).addTo(map);

    const boundary = L.geoJSON(
      {
        type: "Feature",
        properties: { name },
        geometry,
      } as GeoJSON.Feature,
      {
        style: {
          color: "#2563eb",
          weight: 3,
          fillColor: "#38bdf8",
          fillOpacity: 0.35,
        },
      }
    ).addTo(map);
    boundary.bindPopup(name);
    map.fitBounds(boundary.getBounds(), { padding: [24, 24], maxZoom: 14 });
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [geometry, name]);

  return <div ref={elementRef} className="h-full min-h-80 w-full rounded-lg" aria-label={`RGI boundary map for ${name}`} />;
}
