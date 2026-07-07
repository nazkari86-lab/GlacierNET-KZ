package kz.glacier.geo;

import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.Envelope;
import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.operation.overlay.OverlayOp;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class GeometryUtils {
    
    private static final Logger log = LoggerFactory.getLogger(GeometryUtils.class);
    private static final GeometryFactory geometryFactory = new GeometryFactory();
    
    // Coordinate transformation constants (WGS84)
    private static final double EARTH_RADIUS_KM = 6371.0;
    private static final double DEG_TO_RAD = Math.PI / 180.0;
    private static final double RAD_TO_DEG = 180.0 / Math.PI;
    
    public double calculateDistanceHaversine(double lat1, double lon1, 
                                           double lat2, double lon2) {
        double dLat = Math.toRadians(lat2 - lat1);
        double dLon = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                   Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                   Math.sin(dLon / 2) * Math.sin(dLon / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return EARTH_RADIUS_KM * c;
    }
    
    public double calculateDistanceHaversineMeters(double lat1, double lon1,
                                                   double lat2, double lon2) {
        return calculateDistanceHaversine(lat1, lon1, lat2, lon2) * 1000.0;
    }
    
    public double calculateBearing(double lat1, double lon1, 
                                  double lat2, double lon2) {
        double dLon = Math.toRadians(lon2 - lon1);
        double y = Math.sin(dLon) * Math.cos(Math.toRadians(lat2));
        double x = Math.cos(Math.toRadians(lat1)) * Math.sin(Math.toRadians(lat2)) -
                   Math.sin(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2)) *
                   Math.cos(dLon);
        double bearing = Math.toDegrees(Math.atan2(y, x));
        return (bearing + 360) % 360;
    }
    
    public Point calculateDestination(double lat, double lon, 
                                     double distanceKm, double bearingDegrees) {
        double bearingRad = Math.toRadians(bearingDegrees);
        double latRad = Math.toRadians(lat);
        double lonRad = Math.toRadians(lon);
        
        double angularDistance = distanceKm / EARTH_RADIUS_KM;
        
        double lat2 = Math.asin(Math.sin(latRad) * Math.cos(angularDistance) +
                               Math.cos(latRad) * Math.sin(angularDistance) *
                               Math.cos(bearingRad));
        
        double lon2 = lonRad + Math.atan2(Math.sin(bearingRad) *
                     Math.sin(angularDistance) * Math.cos(latRad),
                     Math.cos(angularDistance) - Math.sin(latRad) *
                     Math.sin(lat2));
        
        return geometryFactory.createPoint(new Coordinate(
            Math.toDegrees(lon2), Math.toDegrees(lat2)));
    }
    
    public Envelope calculateBoundingBox(double lat, double lon, double radiusKm) {
        double latDelta = Math.toDegrees(radiusKm / EARTH_RADIUS_KM);
        double lonDelta = Math.toDegrees(radiusKm / (EARTH_RADIUS_KM * 
                          Math.cos(Math.toRadians(lat))));
        
        return new Envelope(
            lon - lonDelta, lon + lonDelta,
            lat - latDelta, lat + latDelta
        );
    }
    
    public Polygon createCircle(double centerLat, double centerLon, 
                               double radiusKm, int numPoints) {
        if (numPoints < 3) {
            numPoints = 32; // Default to 32 points for smooth circle
        }
        
        Coordinate[] coordinates = new Coordinate[numPoints + 1];
        
        for (int i = 0; i <= numPoints; i++) {
            double bearing = (360.0 * i) / numPoints;
            Point point = calculateDestination(centerLat, centerLon, 
                                              radiusKm, bearing);
            coordinates[i] = point.getCoordinate();
        }
        
        return geometryFactory.createPolygon(coordinates);
    }
    
    public Polygon createEllipse(double centerLat, double centerLon,
                                double semiMajorKm, double semiMinorKm,
                                double rotationDegrees, int numPoints) {
        if (numPoints < 3) {
            numPoints = 32;
        }
        
        Coordinate[] coordinates = new Coordinate[numPoints + 1];
        double rotationRad = Math.toRadians(rotationDegrees);
        
        for (int i = 0; i <= numPoints; i++) {
            double angle = (2 * Math.PI * i) / numPoints;
            
            double x = semiMajorKm * Math.cos(angle);
            double y = semiMinorKm * Math.sin(angle);
            
            // Apply rotation
            double rotatedX = x * Math.cos(rotationRad) - y * Math.sin(rotationRad);
            double rotatedY = x * Math.sin(rotationRad) + y * Math.cos(rotationRad);
            
            // Convert to lat/lon
            double latDelta = Math.toDegrees(rotatedY / EARTH_RADIUS_KM);
            double lonDelta = Math.toDegrees(rotatedX / 
                              (EARTH_RADIUS_KM * Math.cos(Math.toRadians(centerLat))));
            
            coordinates[i] = new Coordinate(centerLon + lonDelta, centerLat + latDelta);
        }
        
        return geometryFactory.createPolygon(coordinates);
    }
    
    public double calculatePolygonAreaKm2(Polygon polygon) {
        if (polygon == null) {
            return 0.0;
        }
        
        // For small polygons, use Shoelace formula with projection
        Coordinate[] coords = polygon.getCoordinates();
        if (coords.length < 3) {
            return 0.0;
        }
        
        double area = 0.0;
        for (int i = 0; i < coords.length - 1; i++) {
            double lat1 = Math.toRadians(coords[i].y);
            double lon1 = Math.toRadians(coords[i].x);
            double lat2 = Math.toRadians(coords[i + 1].y);
            double lon2 = Math.toRadians(coords[i + 1].x);
            
            area += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
        }
        
        area = Math.abs(area * EARTH_RADIUS_KM * EARTH_RADIUS_KM / 2.0);
        return area;
    }
    
    public double calculatePerimeterKm(Polygon polygon) {
        if (polygon == null) {
            return 0.0;
        }
        
        double perimeter = 0.0;
        Coordinate[] coords = polygon.getCoordinates();
        
        for (int i = 0; i < coords.length - 1; i++) {
            perimeter += calculateDistanceHaversine(
                coords[i].y, coords[i].x,
                coords[i + 1].y, coords[i + 1].x
            );
        }
        
        return perimeter;
    }
    
    public Point getCentroid(List<Point> points) {
        if (points == null || points.isEmpty()) {
            return null;
        }
        
        double sumX = 0.0;
        double sumY = 0.0;
        
        for (Point point : points) {
            sumX += point.getX();
            sumY += point.getY();
        }
        
        return geometryFactory.createPoint(new Coordinate(
            sumX / points.size(), sumY / points.size()));
    }
    
    public Envelope calculateBounds(List<Point> points) {
        if (points == null || points.isEmpty()) {
            return null;
        }
        
        double minX = Double.MAX_VALUE;
        double maxX = Double.MIN_VALUE;
        double minY = Double.MAX_VALUE;
        double maxY = Double.MIN_VALUE;
        
        for (Point point : points) {
            minX = Math.min(minX, point.getX());
            maxX = Math.max(maxX, point.getX());
            minY = Math.min(minY, point.getY());
            maxY = Math.max(maxY, point.getY());
        }
        
        return new Envelope(minX, maxX, minY, maxY);
    }
    
    public boolean isPointInPolygon(Point point, Polygon polygon) {
        if (point == null || polygon == null) {
            return false;
        }
        return polygon.contains(point);
    }
    
    public List<Point> findIntersections(Geometry geom1, Geometry geom2) {
        List<Point> intersections = new ArrayList<>();
        
        if (geom1 == null || geom2 == null) {
            return intersections;
        }
        
        try {
            Geometry intersection = geom1.intersection(geom2);
            
            if (intersection instanceof Point) {
                intersections.add((Point) intersection);
            } else if (intersection instanceof org.locationtech.jts.geom.MultiPoint) {
                for (int i = 0; i < intersection.getNumGeometries(); i++) {
                    if (intersection.getGeometryN(i) instanceof Point) {
                        intersections.add((Point) intersection.getGeometryN(i));
                    }
                }
            }
        } catch (Exception e) {
            log.error("Failed to calculate intersections: {}", e.getMessage(), e);
        }
        
        return intersections;
    }
    
    public Geometry simplify(Geometry geometry, double toleranceDegrees) {
        if (geometry == null) {
            return null;
        }
        
        try {
            Geometry simplified = geometry.simplify(toleranceDegrees);
            if (simplified.isValid() && !simplified.isEmpty()) {
                return simplified;
            }
        } catch (Exception e) {
            log.warn("Simplification failed, returning original: {}", e.getMessage());
        }
        
        return geometry;
    }
    
    public Geometry snapToGrid(Geometry geometry, double gridSizeDegrees) {
        if (geometry == null) {
            return null;
        }
        
        Coordinate[] coords = geometry.getCoordinates();
        Coordinate[] snapped = new Coordinate[coords.length];
        
        for (int i = 0; i < coords.length; i++) {
            double snappedX = Math.round(coords[i].x / gridSizeDegrees) * gridSizeDegrees;
            double snappedY = Math.round(coords[i].y / gridSizeDegrees) * gridSizeDegrees;
            snapped[i] = new Coordinate(snappedX, snappedY);
        }
        
        return geometryFactory.createGeometry(geometry.getFactory().createPolygon(snapped));
    }
    
    public String toGeoJSON(Geometry geometry) {
        if (geometry == null) {
            return null;
        }
        
        StringBuilder geojson = new StringBuilder();
        geojson.append("{\"type\": \"");
        geojson.append(geometry.getGeometryType());
        geojson.append("\", \"coordinates\": ");
        
        if (geometry instanceof Point) {
            Point point = (Point) geometry;
            geojson.append("[");
            geojson.append(point.getX());
            geojson.append(", ");
            geojson.append(point.getY());
            geojson.append("]");
        } else {
            // For complex geometries, use WKT as fallback
            geojson.append("\"");
            geojson.append(geometry.toText());
            geojson.append("\"");
        }
        
        geojson.append("}");
        return geojson.toString();
    }
    
    public Geometry fromGeoJSON(String geojson) {
        // Simple GeoJSON parsing (for Point type only)
        if (geojson == null || geojson.isEmpty()) {
            return null;
        }
        
        try {
            // Extract coordinates from simple Point GeoJSON
            if (geojson.contains("\"Point\"")) {
                int coordsStart = geojson.indexOf("[");
                int coordsEnd = geojson.indexOf("]");
                
                if (coordsStart >= 0 && coordsEnd > coordsStart) {
                    String coordsStr = geojson.substring(coordsStart + 1, coordsEnd);
                    String[] coords = coordsStr.split(",");
                    
                    if (coords.length >= 2) {
                        double x = Double.parseDouble(coords[0].trim());
                        double y = Double.parseDouble(coords[1].trim());
                        return geometryFactory.createPoint(new Coordinate(x, y));
                    }
                }
            }
            
            log.warn("Unsupported GeoJSON type or invalid format");
            return null;
            
        } catch (Exception e) {
            log.error("Failed to parse GeoJSON: {}", e.getMessage(), e);
            return null;
        }
    }
}