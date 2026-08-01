import type { GeoJsonFeatureCollection } from "@/lib/api";

type Position = [number, number];

function segmentDistanceMeters(point: Position, start: Position, end: Position) {
  const latitudeRadians = point[1] * Math.PI / 180;
  const metersPerDegreeLatitude = 111_132;
  const metersPerDegreeLongitude = 111_320 * Math.cos(latitudeRadians);
  const project = ([longitude, latitude]: Position): Position => [
    (longitude - point[0]) * metersPerDegreeLongitude,
    (latitude - point[1]) * metersPerDegreeLatitude,
  ];
  const [startX, startY] = project(start);
  const [endX, endY] = project(end);
  const deltaX = endX - startX;
  const deltaY = endY - startY;
  const squaredLength = deltaX * deltaX + deltaY * deltaY;
  if (squaredLength === 0) return Math.hypot(startX, startY);
  const fraction = Math.max(0, Math.min(1, -(startX * deltaX + startY * deltaY) / squaredLength));
  return Math.hypot(startX + fraction * deltaX, startY + fraction * deltaY);
}

function lineDistanceMeters(point: Position, coordinates: Position[]) {
  let minimum = Number.POSITIVE_INFINITY;
  for (let index = 1; index < coordinates.length; index += 1) {
    minimum = Math.min(minimum, segmentDistanceMeters(point, coordinates[index - 1], coordinates[index]));
  }
  return minimum;
}

export function distanceToRouteMeters(latitude: number, longitude: number, collection: GeoJsonFeatureCollection | null | undefined) {
  if (!collection?.features.length) return null;
  const point: Position = [longitude, latitude];
  let minimum = Number.POSITIVE_INFINITY;
  for (const feature of collection.features) {
    const geometry = feature.geometry;
    if (!geometry) continue;
    if (geometry.type === "LineString") {
      minimum = Math.min(minimum, lineDistanceMeters(point, geometry.coordinates as Position[]));
    } else if (geometry.type === "MultiLineString") {
      for (const line of geometry.coordinates as Position[][]) minimum = Math.min(minimum, lineDistanceMeters(point, line));
    }
  }
  return Number.isFinite(minimum) ? minimum : null;
}
