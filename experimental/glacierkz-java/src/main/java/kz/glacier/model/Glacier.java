package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.Type;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.spatial.JTSGeometryType;
import org.locationtech.jts.geom.Geometry;

import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "glaciers", indexes = {
        @Index(name = "idx_glacier_name", columnList = "name"),
        @Index(name = "idx_glacier_region", columnList = "region"),
        @Index(name = "idx_glacier_geom", columnList = "geometry", spatial = true)
})
public class Glacier {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 255)
    private String name;

    @Column(length = 500)
    private String description;

    @Column(nullable = false, length = 100)
    private String region;

    @Column(name = "country_code", length = 3)
    private String countryCode = "KZ";

    @Column(name = "mountain_range", length = 200)
    private String mountainRange;

    @Column(nullable = false, length = 50)
    private String status;

    @Column(name = "elevation_min")
    private Double elevationMin;

    @Column(name = "elevation_max")
    private Double elevationMax;

    @Column(name = "area_square_km")
    private Double areaSquareKm;

    @Column(name = "length_km")
    private Double lengthKm;

    @Column(name = "last_survey_date")
    private LocalDate lastSurveyDate;

    @Column(name = "classification", length = 50)
    private String classification;

    @Column(name = "mass_balance")
    private Double massBalance;

    @Column(name = "flow_velocity_ms")
    private Double flowVelocityMs;

    @Type(JTSGeometryType.class)
    @Column(name = "geometry", columnDefinition = "geometry(Geometry, 4326)")
    private Geometry geometry;

    @Column(name = "centroid_lat")
    private Double centroidLat;

    @Column(name = "centroid_lon")
    private Double centroidLon;

    @Column(name = "kriging_weight")
    private Double krigingWeight;

    @OneToMany(mappedBy = "glacier", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<SatelliteImage> satelliteImages = new ArrayList<>();

    @OneToMany(mappedBy = "glacier", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<AnalysisReport> analysisReports = new ArrayList<>();

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Column(name = "deleted")
    private Boolean deleted = false;

    @Version
    private Long version;

    public Glacier() {
    }

    public Glacier(String name, String region, Geometry geometry) {
        this.name = name;
        this.region = region;
        this.geometry = geometry;
        this.status = "ACTIVE";
    }

    public boolean isRetreating() {
        return massBalance != null && massBalance < 0;
    }

    public boolean isAdvancing() {
        return massBalance != null && massBalance > 0;
    }

    public boolean hasElevationRange() {
        return elevationMin != null && elevationMax != null && elevationMax > elevationMin;
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }

    public String getRegion() { return region; }
    public void setRegion(String region) { this.region = region; }

    public String getCountryCode() { return countryCode; }
    public void setCountryCode(String countryCode) { this.countryCode = countryCode; }

    public String getMountainRange() { return mountainRange; }
    public void setMountainRange(String mountainRange) { this.mountainRange = mountainRange; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Double getElevationMin() { return elevationMin; }
    public void setElevationMin(Double elevationMin) { this.elevationMin = elevationMin; }

    public Double getElevationMax() { return elevationMax; }
    public void setElevationMax(Double elevationMax) { this.elevationMax = elevationMax; }

    public Double getAreaSquareKm() { return areaSquareKm; }
    public void setAreaSquareKm(Double areaSquareKm) { this.areaSquareKm = areaSquareKm; }

    public Double getLengthKm() { return lengthKm; }
    public void setLengthKm(Double lengthKm) { this.lengthKm = lengthKm; }

    public LocalDate getLastSurveyDate() { return lastSurveyDate; }
    public void setLastSurveyDate(LocalDate lastSurveyDate) { this.lastSurveyDate = lastSurveyDate; }

    public String getClassification() { return classification; }
    public void setClassification(String classification) { this.classification = classification; }

    public Double getMassBalance() { return massBalance; }
    public void setMassBalance(Double massBalance) { this.massBalance = massBalance; }

    public Double getFlowVelocityMs() { return flowVelocityMs; }
    public void setFlowVelocityMs(Double flowVelocityMs) { this.flowVelocityMs = flowVelocityMs; }

    public Geometry getGeometry() { return geometry; }
    public void setGeometry(Geometry geometry) { this.geometry = geometry; }

    public Double getCentroidLat() { return centroidLat; }
    public void setCentroidLat(Double centroidLat) { this.centroidLat = centroidLat; }

    public Double getCentroidLon() { return centroidLon; }
    public void setCentroidLon(Double centroidLon) { this.centroidLon = centroidLon; }

    public Double getKrigingWeight() { return krigingWeight; }
    public void setKrigingWeight(Double krigingWeight) { this.krigingWeight = krigingWeight; }

    public List<SatelliteImage> getSatelliteImages() { return satelliteImages; }
    public void setSatelliteImages(List<SatelliteImage> satelliteImages) { this.satelliteImages = satelliteImages; }

    public List<AnalysisReport> getAnalysisReports() { return analysisReports; }
    public void setAnalysisReports(List<AnalysisReport> analysisReports) { this.analysisReports = analysisReports; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public Boolean getDeleted() { return deleted; }
    public void setDeleted(Boolean deleted) { this.deleted = deleted; }

    public Long getVersion() { return version; }
    public void setVersion(Long version) { this.version = version; }

    @Override
    public String toString() {
        return "Glacier{" +
                "id=" + id +
                ", name='" + name + '\'' +
                ", region='" + region + '\'' +
                ", status='" + status + '\'' +
                ", areaSquareKm=" + areaSquareKm +
                '}';
    }
}
