package models

import "time"

type AnalysisType string

const (
	AnalysisTypeMassBalance   AnalysisType = "mass_balance"
	AnalysisTypeRetreat       AnalysisType = "retreat"
	AnalysisTypeVelocity      AnalysisType = "velocity"
	AnalysisTypeTemperature   AnalysisType = "temperature"
	AnalysisTypePredictive    AnalysisType = "predictive"
	AnalysisTypeAreaChange    AnalysisType = "area_change"
	AnalysisTypeClimateImpact AnalysisType = "climate_impact"
	AnalysisTypePrediction    AnalysisType = "prediction"
	AnalysisTypeComparison    AnalysisType = "comparison"
	AnalysisTypeMultiYear     AnalysisType = "multi_year"
)

type AnalysisStatus string

const (
	AnalysisStatusPending    AnalysisStatus = "pending"
	AnalysisStatusRunning    AnalysisStatus = "running"
	AnalysisStatusCompleted  AnalysisStatus = "completed"
	AnalysisStatusFailed     AnalysisStatus = "failed"
)

type AnalysisResult struct {
	ID           string         `json:"id"`
	GlacierID    string         `json:"glacier_id"`
	Type         AnalysisType  `json:"type"`
	Status       AnalysisStatus `json:"status"`
	Score        float64       `json:"score"`
	Summary      string        `json:"summary"`
	DataPoints   int           `json:"data_points"`
	UpdatedAt    time.Time     `json:"updated_at"`
	CreatedAt    time.Time     `json:"created_at"`
	CompletedAt  *time.Time    `json:"completed_at,omitempty"`
	Trends       []TrendData   `json:"trends,omitempty"`
	Confidence   float64       `json:"confidence"`
	Recommendations []string    `json:"recommendations,omitempty"`
}

type TrendData struct {
	Label    string    `json:"label"`
	Value    float64   `json:"value"`
	Date     time.Time `json:"date"`
	Change   float64   `json:"change"`
	Unit     string    `json:"unit"`
}

type AnalysisRequest struct {
	GlacierID   string       `json:"glacier_id" validate:"required"`
	Type        AnalysisType `json:"type" validate:"required"`
	StartDate   string       `json:"start_date"`
	EndDate     string       `json:"end_date"`
	Resolution  string       `json:"resolution"`
}

type AnalysisCompareRequest struct {
	GlacierIDs []string     `json:"glacier_ids" validate:"required,min=2"`
	Type       AnalysisType `json:"type" validate:"required"`
	StartDate  string       `json:"start_date"`
	EndDate    string       `json:"end_date"`
}

type AnalysisSummary struct {
	TotalAnalyses  int            `json:"total_analyses"`
	ByType         map[AnalysisType]int `json:"by_type"`
	ByStatus       map[AnalysisStatus]int `json:"by_status"`
	AverageScore   float64        `json:"average_score"`
	LastAnalysis   *time.Time     `json:"last_analysis,omitempty"`
}
