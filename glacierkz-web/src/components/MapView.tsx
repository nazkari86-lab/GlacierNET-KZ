"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface MapViewProps {
  imageUrl?: string;
  maskUrl?: string;
  overlayUrl?: string;
  uncertaintyUrl?: string;
  className?: string;
}

export default function MapView({
  maskUrl,
  overlayUrl,
  uncertaintyUrl,
  className = "",
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;
    mapInstance.current = L.map(mapRef.current, { zoomControl: true, attributionControl: false }).setView(
      [43.0, 77.0],
      10
    );
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
    }).addTo(mapInstance.current);
    return () => {
      mapInstance.current?.remove();
      mapInstance.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapInstance.current;
    if (!map) return;
    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) map.removeLayer(layer);
    });
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
    }).addTo(map);

    const addOverlay = (url: string | undefined, label: string, color: string) => {
      if (!url) return;
      fetch(url)
        .then((r) => r.blob())
        .then((blob) => {
          const reader = new FileReader();
          reader.onload = () => {
            const img = new Image();
            img.onload = () => {
              const canvas = document.createElement("canvas");
              canvas.width = img.width;
              canvas.height = img.height;
              const ctx = canvas.getContext("2d")!;
              ctx.drawImage(img, 0, 0);
              const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
              const data = imageData.data;
              for (let i = 0; i < data.length; i += 4) {
                if (data[i] > 128) {
                  data[i] = parseInt(color.slice(1, 3), 16);
                  data[i + 1] = parseInt(color.slice(3, 5), 16);
                  data[i + 2] = parseInt(color.slice(5, 7), 16);
                  data[i + 3] = 180;
                }
              }
              ctx.putImageData(imageData, 0, 0);
              canvas.toBlob((coloredBlob) => {
                if (coloredBlob) {
                  const coloredUrl = URL.createObjectURL(coloredBlob);
                  const bounds = map.getBounds();
                  L.imageOverlay(coloredUrl, bounds, { opacity: 0.6 }).addTo(map);
                }
              });
            };
            img.src = reader.result as string;
          };
          reader.readAsDataURL(blob);
        });
    };

    addOverlay(maskUrl, "Mask", "#2563eb");
    addOverlay(uncertaintyUrl, "Uncertainty", "#dc2626");
  }, [maskUrl, overlayUrl, uncertaintyUrl]);

  return <div ref={mapRef} className={`h-full w-full rounded-xl ${className}`} />;
}
