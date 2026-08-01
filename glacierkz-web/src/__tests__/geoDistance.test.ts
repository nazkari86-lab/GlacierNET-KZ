import { describe, expect, it } from "vitest";
import type { GeoJsonFeatureCollection } from "@/lib/api";
import { distanceToRouteMeters } from "@/lib/geoDistance";

describe("company asset to HydroRIVERS route distance", () => {
  it("returns a near-zero distance for an asset located on a mapped route", () => {
    const route = {
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        properties: {},
        geometry: { type: "LineString", coordinates: [[76.9, 43.1], [77, 43.2]] },
      }],
    } as GeoJsonFeatureCollection;

    expect(distanceToRouteMeters(43.15, 76.95, route)).toBeLessThan(10);
  });

  it("handles MultiLineString features and reports a metric planning distance", () => {
    const route = {
      type: "FeatureCollection",
      features: [{
        type: "Feature",
        properties: {},
        geometry: { type: "MultiLineString", coordinates: [[[76.9, 43.1], [76.9, 43.2]]] },
      }],
    } as GeoJsonFeatureCollection;

    const distance = distanceToRouteMeters(43.15, 76.91, route);
    expect(distance).not.toBeNull();
    expect(distance!).toBeGreaterThan(790);
    expect(distance!).toBeLessThan(830);
  });

  it("fails closed when no route geometry is available", () => {
    expect(distanceToRouteMeters(43.1, 76.9, null)).toBeNull();
    expect(distanceToRouteMeters(43.1, 76.9, { type: "FeatureCollection", features: [] })).toBeNull();
  });
});
