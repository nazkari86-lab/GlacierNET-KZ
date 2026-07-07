"use client";

import type { FeatureCollection } from "geojson";
import { useEffect, useRef, useState, useCallback } from "react";
import { MapContainer, TileLayer, GeoJSON, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { cn } from "@/lib/utils";
import { ZoomIn, ZoomOut, Maximize2, Satellite, Map as MapIcon } from "lucide-react";

interface GlacierFeature {
  type: "Feature";
  geometry: { type: string; coordinates: number[][][] };
  properties: {
    name: string;
    area_km2: number;
    elevation: number;
    status: "stable" | "retreating" | "advancing";
    id?: string;
  };
}

interface WebGLMapProps {
  center?: [number, number];
  zoom?: number;
  glacierData?: GlacierFeature[];
  selectedGlacier?: string | null;
  onGlacierSelect?: (id: string) => void;
  className?: string;
  showControls?: boolean;
  showSatellite?: boolean;
  height?: string;
  markers?: Array<{ lat: number; lng: number; label: string; type?: string }>;
}

const STATUS_COLORS: Record<string, string> = {
  stable: "#3b82f6",
  retreating: "#ef4444",
  advancing: "#22c55e",
};

function MapControls() {
  useMap();
  return null;
}

function MapEvents({
  onZoomChange,
  onMoveEnd,
}: {
  onZoomChange?: (zoom: number) => void;
  onMoveEnd?: (center: [number, number]) => void;
}) {
  const map = useMap();
  useEffect(() => {
    const handleZoom = () => {
      onZoomChange?.(map.getZoom());
    };
    const handleMoveEnd = () => {
      const c = map.getCenter();
      onMoveEnd?.([c.lat, c.lng]);
    };
    map.on("zoomend", handleZoom);
    map.on("moveend", handleMoveEnd);
    return () => {
      map.off("zoomend", handleZoom);
      map.off("moveend", handleMoveEnd);
    };
  }, [map, onZoomChange, onMoveEnd]);
  return null;
}

function FitBounds({ features }: { features: GlacierFeature[] }) {
  const map = useMap();
  useEffect(() => {
    if (features.length === 0) return;
    const coords: [number, number][] = [];
    features.forEach((f) => {
      const flat = f.geometry.coordinates.flat(2);
      for (let i = 0; i < flat.length; i += 2) {
        coords.push([flat[i + 1], flat[i]]);
      }
    });
    if (coords.length > 0) {
      const bounds = L.latLngBounds(coords);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 12 });
    }
  }, [features, map]);
  return null;
}

export default function WebGLMap({
  center = [43.2, 76.9],
  zoom = 7,
  glacierData = [],
  selectedGlacier,
  onGlacierSelect,
  className,
  showControls = true,
  showSatellite = false,
  height = "500px",
  markers = [],
}: WebGLMapProps) {
  const [currentZoom, setCurrentZoom] = useState(zoom);
  const [currentCenter, setCurrentCenter] = useState<[number, number]>(center);
  const [mapStyle, setMapStyle] = useState<"street" | "satellite">(showSatellite ? "satellite" : "street");
  const mapRef = useRef<L.Map | null>(null);

  const tileUrls: Record<string, { url: string; attribution: string }> = {
    street: {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution: "&copy; OpenStreetMap contributors",
    },
    satellite: {
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      attribution: "Tiles &copy; Esri",
    },
  };

  const handleZoomIn = useCallback(() => {
    mapRef.current?.setZoom(currentZoom + 1);
  }, [currentZoom]);

  const handleZoomOut = useCallback(() => {
    mapRef.current?.setZoom(currentZoom - 1);
  }, [currentZoom]);

  const handleFullscreen = useCallback(() => {
    const container = mapRef.current?.getContainer();
    if (container) {
      if (document.fullscreenElement) {
        document.exitFullscreen();
      } else {
        container.requestFullscreen();
      }
    }
  }, []);

  const toggleMapStyle = useCallback(() => {
    setMapStyle((prev) => (prev === "street" ? "satellite" : "street"));
  }, []);

  const geoJsonStyle = useCallback(
    (feature?: GeoJSON.Feature) => {
      const status = (feature?.properties as Record<string, unknown>)?.status as string;
      const isSelected = (feature?.properties as Record<string, unknown>)?.id === selectedGlacier;
      return {
        color: isSelected ? "#facc15" : STATUS_COLORS[status] || "#6b7280",
        weight: isSelected ? 3 : 1.5,
        opacity: isSelected ? 1 : 0.8,
        fillOpacity: isSelected ? 0.4 : 0.2,
      };
    },
    [selectedGlacier]
  );

  const onEachFeature = useCallback(
    (feature: GlacierFeature, layer: L.Layer) => {
      const p = feature.properties;
      layer.bindPopup(
        `<div style="min-width:180px">
          <strong>${p.name}</strong><br/>
          Area: ${p.area_km2.toFixed(1)} km²<br/>
          Elevation: ${p.elevation} m<br/>
          Status: <span style="color:${STATUS_COLORS[p.status]}">${p.status}</span>
        </div>`
      );
      layer.on("click", () => {
        if (feature.properties.id) onGlacierSelect?.(feature.properties.id);
      });
    },
    [onGlacierSelect]
  );

  return (
    <div className={cn("relative rounded-lg overflow-hidden border border-gray-200", className)} style={{ height }}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={true}
        ref={mapRef}
      >
        <TileLayer
          key={mapStyle}
          url={tileUrls[mapStyle].url}
          attribution={tileUrls[mapStyle].attribution}
          maxZoom={18}
        />
        <MapEvents onZoomChange={setCurrentZoom} onMoveEnd={setCurrentCenter} />
        <MapControls />
        {glacierData.length > 0 && <FitBounds features={glacierData} />}
        {glacierData.length > 0 && (
          <GeoJSON
            key={`geojson-${selectedGlacier}-${glacierData.length}`}
            data={
              {
                type: "FeatureCollection",
                features: glacierData,
              } as FeatureCollection
            }
            style={geoJsonStyle}
            onEachFeature={(feature, layer) =>
              onEachFeature(feature as GlacierFeature, layer as L.Layer)
            }
          />
        )}
        {markers.map((m, i) => (
          <Marker key={i} position={[m.lat, m.lng]}>
            <Popup>{m.label}</Popup>
          </Marker>
        ))}
      </MapContainer>

      {showControls && (
        <div className="absolute top-3 right-3 flex flex-col gap-1.5 z-[1000]">
          <button
            onClick={handleZoomIn}
            className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
            aria-label="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
            aria-label="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={toggleMapStyle}
            className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
            aria-label="Toggle map style"
          >
            {mapStyle === "street" ? (
              <Satellite className="w-4 h-4" />
            ) : (
              <MapIcon className="w-4 h-4" />
            )}
          </button>
          <button
            onClick={handleFullscreen}
            className="p-2 bg-white rounded-lg shadow-md hover:bg-gray-50 transition-colors"
            aria-label="Fullscreen"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="absolute bottom-3 left-3 z-[1000] flex items-center gap-3 bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1.5 text-xs shadow-md">
        {Object.entries(STATUS_COLORS).map(([status, color]) => (
          <div key={status} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: color, opacity: 0.7 }} />
            <span className="capitalize">{status}</span>
          </div>
        ))}
      </div>

      <div className="absolute bottom-3 right-3 z-[1000] bg-white/90 backdrop-blur-sm rounded-lg px-3 py-1.5 text-xs text-gray-500 shadow-md">
        Zoom: {currentZoom} | Center: {currentCenter[0].toFixed(4)}, {currentCenter[1].toFixed(4)}
      </div>
    </div>
  );
}

export type { WebGLMapProps, GlacierFeature };
