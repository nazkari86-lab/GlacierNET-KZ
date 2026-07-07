"use client";

import React, { useEffect, useRef } from "react";
import type { Map as LeafletMap, Layer, LeafletMouseEvent } from "leaflet";

interface MapViewProps {
  center?: [number, number];
  zoom?: number;
  markers?: MapMarker[];
  geoJson?: GeoJSON.FeatureCollection;
  height?: string;
  onClick?: (lat: number, lng: number) => void;
}

export interface MapMarker {
  lat: number;
  lng: number;
  label?: string;
  color?: string;
  popup?: string;
}

export function MapView({
  center = [43.2380, 76.9450],
  zoom = 10,
  markers = [],
  height = "400px",
  onClick,
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<LeafletMap | null>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) return;

    const init = async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      const map = L.map(mapRef.current!, {
        center,
        zoom,
        scrollWheelZoom: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://osm.org/copyright">OpenStreetMap</a>',
        maxZoom: 18,
      }).addTo(map);

      if (onClick) {
        map.on("click", (e: LeafletMouseEvent) => {
          onClick(e.latlng.lat, e.latlng.lng);
        });
      }

      mapInstanceRef.current = map;
    };

    init();

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [center, onClick, zoom]);

  useEffect(() => {
    if (!mapInstanceRef.current) return;
    mapInstanceRef.current.setView(center, zoom);
  }, [center, zoom]);

  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    void (async () => {
      const L = (await import("leaflet")).default;
      map.eachLayer((layer: Layer) => {
        if (layer instanceof L.Marker) {
          map.removeLayer(layer);
        }
      });
      markers.forEach((m) => {
        const color = m.color || "#3b82f6";
        const icon = L.divIcon({
          className: "custom-marker",
          html: `<div style="width:12px;height:12px;background:${color};border-radius:50%;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,0.3)"></div>`,
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });
        const marker = L.marker([m.lat, m.lng], { icon }).addTo(map);
        if (m.popup) marker.bindPopup(m.popup);
      });
    })();
  }, [markers]);

  return <div ref={mapRef} style={{ height, width: "100%" }} className="rounded-lg z-0" />;
}
