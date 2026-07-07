package kz.glacier.geo;

import org.locationtech.jts.geom.Coordinate;
import org.locationtech.jts.geom.Geometry;
import org.locationtech.jts.geom.GeometryFactory;
import org.locationtech.jts.geom.Point;
import org.locationtech.jts.geom.Polygon;
import org.locationtech.jts.io.ParseException;
import org.locationtech.jts.io.WKTReader;
import org.locationtech.jts.io.WKTWriter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

@Component
public class SpatialQuery {
    
    private static final Logger log = LoggerFactory.getLogger(SpatialQuery.class);
    private static final GeometryFactory geometryFactory = new GeometryFactory();
    private static final WKTReader wktReader = new WKTReader();
    private static final WKTWriter wktWriter = new WKTWriter();
    
    public Point createPoint(double longitude, double latitude) {
        if (longitude < -180 || longitude > 180) {
            throw new IllegalArgumentException("Longitude must be between -180 and 180");
        }
        if (latitude < -90 || latitude > 90) {
            throw new IllegalArgumentException("Latitude must be between -90 and 90");
        }
        
        Coordinate coordinate = new Coordinate(longitude, latitude);
        return geometryFactory.createPoint(coordinate);
    }
    
    public Point createPointFromWKT(String wkt) {
        try {
            Geometry geometry = wktReader.read(wkt);
            if (!(geometry instanceof Point)) {
                throw new IllegalArgumentException("WKT does not represent a Point");
            }
            return (Point) geometry;
        } catch (ParseException e) {
            log.error("Failed to parse WKT as Point: {}", wkt, e);
            throw new IllegalArgumentException("Invalid WKT format", e);
        }
    }
    
    public Polygon createBoundingBox(double minLon, double minLat, 
                                    double maxLon, double maxLat) {
        Coordinate[] coordinates = new Coordinate[]{
            new Coordinate(minLon, minLat),
            new Coordinate(maxLon, minLat),
            new Coordinate(maxLon, maxLat),
            new Coordinate(minLon, maxLat),
            new Coordinate(minLon, minLat) // Close the polygon
        };
        
        return geometryFactory.createPolygon(coordinates);
    }
    
    public Polygon createPolygonFromWKT(String wkt) {
        try {
            Geometry geometry = wktReader.read(wkt);
            if (!(geometry instanceof Polygon)) {
                throw new IllegalArgumentException("WKT does not represent a Polygon");
            }
            return (Polygon) geometry;
        } catch (ParseException e) {
            log.error("Failed to parse WKT as Polygon: {}", wkt, e);
            throw new IllegalArgumentException("Invalid WKT format", e);
        }
    }
    
    public boolean intersects(Geometry geometry1, Geometry geometry2) {
        if (geometry1 == null || geometry2 == null) {
            return false;
        }
        return geometry1.intersects(geometry2);
    }
    
    public boolean contains(Geometry container, Geometry contained) {
        if (container == null || contained == null) {
            return false;
        }
        return container.contains(contained);
    }
    
    public boolean within(Geometry geometry, Geometry container) {
        if (geometry == null || container == null) {
            return false;
        }
        return geometry.within(container);
    }
    
    public double distance(Point point1, Point point2) {
        if (point1 == null || point2 == null) {
            throw new IllegalArgumentException("Points cannot be null");
        }
        return point1.distance(point2);
    }
    
    public Geometry intersection(Geometry geometry1, Geometry geometry2) {
        if (geometry1 == null || geometry2 == null) {
            return null;
        }
        return geometry1.intersection(geometry2);
    }
    
    public Geometry union(Geometry geometry1, Geometry geometry2) {
        if (geometry1 == null) {
            return geometry2;
        }
        if (geometry2 == null) {
            return geometry1;
        }
        return geometry1.union(geometry2);
    }
    
    public Geometry difference(Geometry geometry1, Geometry geometry2) {
        if (geometry1 == null) {
            return null;
        }
        if (geometry2 == null) {
            return geometry1;
        }
        return geometry1.difference(geometry2);
    }
    
    public Geometry buffer(Geometry geometry, double distance) {
        if (geometry == null) {
            return null;
        }
        return geometry.buffer(distance);
    }
    
    public Geometry convexHull(Geometry geometry) {
        if (geometry == null) {
            return null;
        }
        return geometry.convexHull();
    }
    
    public String toWKT(Geometry geometry) {
        if (geometry == null) {
            return null;
        }
        return wktWriter.write(geometry);
    }
    
    public Geometry fromWKT(String wkt) {
        try {
            return wktReader.read(wkt);
        } catch (ParseException e) {
            log.error("Failed to parse WKT: {}", wkt, e);
            throw new IllegalArgumentException("Invalid WKT format", e);
        }
    }
    
    public Point getCentroid(Geometry geometry) {
        if (geometry == null) {
            return null;
        }
        return geometry.getCentroid();
    }
    
    public double getArea(Geometry geometry) {
        if (geometry == null) {
            return 0.0;
        }
        return geometry.getArea();
    }
    
    public double getLength(Geometry geometry) {
        if (geometry == null) {
            return 0.0;
        }
        return geometry.getLength();
    }
    
    public boolean isEmpty(Geometry geometry) {
        if (geometry == null) {
            return true;
        }
        return geometry.isEmpty();
    }
    
    public boolean isValid(Geometry geometry) {
        if (geometry == null) {
            return false;
        }
        return geometry.isValid();
    }
    
    public Geometry makeValid(Geometry geometry) {
        if (geometry == null) {
            return null;
        }
        
        if (geometry.isValid()) {
            return geometry;
        }
        
        // Try to fix invalid geometry
        try {
            // Buffer by 0 to fix self-intersections
            Geometry fixed = geometry.buffer(0);
            if (fixed.isValid()) {
                return fixed;
            }
            
            // Try convex hull as fallback
            fixed = geometry.convexHull();
            if (fixed.isValid()) {
                return fixed;
            }
            
            log.warn("Could not fix invalid geometry, returning original");
            return geometry;
            
        } catch (Exception e) {
            log.error("Failed to fix invalid geometry: {}", e.getMessage(), e);
            return geometry;
        }
    }
    
    public List<Point> extractPoints(Geometry geometry) {
        List<Point> points = new ArrayList<>();
        if (geometry == null) {
            return points;
        }
        
        if (geometry instanceof Point) {
            points.add((Point) geometry);
        } else {
            Coordinate[] coordinates = geometry.getCoordinates();
            for (Coordinate coord : coordinates) {
                points.add(geometryFactory.createPoint(coord));
            }
        }
        
        return points;
    }
    
    public Geometry createMultiPoint(List<Point> points) {
        if (points == null || points.isEmpty()) {
            return null;
        }
        return geometryFactory.createMultiPoint(points.toArray(new Point[0]));
    }
    
    public Geometry createLineString(List<Point> points) {
        if (points == null || points.size() < 2) {
            return null;
        }
        
        Coordinate[] coordinates = points.stream()
            .map(Point::getCoordinate)
            .toArray(Coordinate[]::new);
        
        return geometryFactory.createLineString(coordinates);
    }
}