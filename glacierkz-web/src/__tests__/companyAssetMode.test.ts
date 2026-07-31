import { describe, expect, it } from "vitest";
import { MAX_GEOJSON_BYTES, parseGeoJsonAssets } from "@/components/jury/CompanyAssetMode";

describe("CompanyAssetMode GeoJSON import", () => {
  it("imports only valid Point features and preserves the supplied coordinates", () => {
    const assets = parseGeoJsonAssets({
      type: "FeatureCollection",
      features: [
        { type: "Feature", properties: { name: "Водозабор", asset_type: "ГЭС / водозабор" }, geometry: { type: "Point", coordinates: [76.9723, 42.9753] } },
        { type: "Feature", properties: { name: "Не точка" }, geometry: { type: "LineString", coordinates: [[76.9, 42.9], [77, 43]] } },
      ],
    });

    expect(assets).toHaveLength(1);
    expect(assets[0]).toMatchObject({ name: "Водозабор", type: "ГЭС / водозабор", longitude: 76.9723, latitude: 42.9753 });
  });

  it("rejects malformed or point-free GeoJSON instead of inventing an asset", () => {
    expect(() => parseGeoJsonAssets({ type: "FeatureCollection", features: [] })).toThrow(/не найдено/i);
    expect(() => parseGeoJsonAssets({ type: "Feature", geometry: { type: "Point", coordinates: [76.9, 42.9] } })).toThrow(/FeatureCollection/i);
  });

  it("keeps an explicit client-side import size guard", () => {
    expect(MAX_GEOJSON_BYTES).toBe(1_000_000);
  });
});
