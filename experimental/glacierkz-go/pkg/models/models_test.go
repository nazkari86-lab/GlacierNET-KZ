package models_test

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func TestGlacierJSON(t *testing.T) {
	g := models.Glacier{
		ID:        "g-001",
		Name:      "Test Glacier",
		Region:    "Kazakhstan",
		Country:   "KZ",
		Latitude:  42.5,
		Longitude: 44.0,
		Status:    "active",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	data, err := json.Marshal(g)
	if err != nil {
		t.Fatalf("failed to marshal glacier: %v", err)
	}

	var decoded models.Glacier
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal glacier: %v", err)
	}

	if decoded.ID != "g-001" {
		t.Errorf("expected ID g-001, got %s", decoded.ID)
	}
	if decoded.Name != "Test Glacier" {
		t.Errorf("expected name Test Glacier, got %s", decoded.Name)
	}
}

func TestGlacierCreateRequestJSON(t *testing.T) {
	req := models.GlacierCreateRequest{
		Name:      "New Glacier",
		Region:    "Almaty",
		Country:   "KZ",
		Latitude:  43.0,
		Longitude: 45.0,
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	if string(data) == "" {
		t.Error("marshaled data should not be empty")
	}
}

func TestTaskJSON(t *testing.T) {
	task := models.Task{
		ID:        "t-001",
		GlacierID: "g-001",
		Type:      models.TaskTypeAnalysis,
		Status:    models.TaskStatusPending,
		CreatedAt: time.Now(),
	}

	data, err := json.Marshal(task)
	if err != nil {
		t.Fatalf("failed to marshal task: %v", err)
	}

	var decoded models.Task
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal task: %v", err)
	}

	if decoded.ID != "t-001" {
		t.Errorf("expected ID t-001, got %s", decoded.ID)
	}
	if decoded.Type != models.TaskTypeAnalysis {
		t.Errorf("expected type analysis, got %s", decoded.Type)
	}
}

func TestTaskStatusConstants(t *testing.T) {
	statuses := []models.TaskStatus{
		models.TaskStatusPending,
		models.TaskStatusRunning,
		models.TaskStatusCompleted,
		models.TaskStatusFailed,
		models.TaskStatusCancelled,
	}

	if len(statuses) != 5 {
		t.Errorf("expected 5 task statuses, got %d", len(statuses))
	}
}

func TestAnalysisResultJSON(t *testing.T) {
	result := models.AnalysisResult{
		ID:        "a-001",
		GlacierID: "g-001",
		Type:      models.AnalysisTypeVelocity,
		Status:    models.AnalysisStatusCompleted,
		Summary:   "Test analysis completed",
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	data, err := json.Marshal(result)
	if err != nil {
		t.Fatalf("failed to marshal analysis: %v", err)
	}

	var decoded models.AnalysisResult
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal analysis: %v", err)
	}

	if decoded.ID != "a-001" {
		t.Errorf("expected ID a-001, got %s", decoded.ID)
	}
	if decoded.Type != models.AnalysisTypeVelocity {
		t.Errorf("expected type velocity, got %s", decoded.Type)
	}
}

func TestAnalysisTypeConstants(t *testing.T) {
	types := []models.AnalysisType{
		models.AnalysisTypeVelocity,
		models.AnalysisTypeMassBalance,
		models.AnalysisTypeAreaChange,
		models.AnalysisTypeClimateImpact,
		models.AnalysisTypePrediction,
		models.AnalysisTypeComparison,
		models.AnalysisTypeMultiYear,
	}

	if len(types) != 7 {
		t.Errorf("expected 7 analysis types, got %d", len(types))
	}
}

func TestPageRequestJSON(t *testing.T) {
	pr := models.PageRequest{
		Page:     1,
		PageSize: 20,
	}

	data, err := json.Marshal(pr)
	if err != nil {
		t.Fatalf("failed to marshal page request: %v", err)
	}

	var decoded models.PageRequest
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal page request: %v", err)
	}

	if decoded.Page != 1 || decoded.PageSize != 20 {
		t.Errorf("expected page 1 page_size 20, got page %d page_size %d", decoded.Page, decoded.PageSize)
	}
}

func TestPageResponseJSON(t *testing.T) {
	pr := models.PageResponse{
		Page:       1,
		PageSize:   20,
		Total:      100,
		TotalPages: 5,
	}

	data, err := json.Marshal(pr)
	if err != nil {
		t.Fatalf("failed to marshal page response: %v", err)
	}

	var decoded models.PageResponse
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal page response: %v", err)
	}

	if decoded.TotalPages != 5 {
		t.Errorf("expected total pages 5, got %d", decoded.TotalPages)
	}
}

func TestErrorResponseJSON(t *testing.T) {
	errResp := models.NewErrorResponse(404, "Not Found", "Resource does not exist")

	data, err := json.Marshal(errResp)
	if err != nil {
		t.Fatalf("failed to marshal error: %v", err)
	}

	var decoded models.ErrorResponse
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal error: %v", err)
	}

	if decoded.Code != 404 {
		t.Errorf("expected code 404, got %d", decoded.Code)
	}
	if decoded.Message != "Not Found" {
		t.Errorf("expected message Not Found, got %s", decoded.Message)
	}
}

func TestHealthStatusConstants(t *testing.T) {
	statuses := []models.HealthStatus{
		models.HealthStatusHealthy,
		models.HealthStatusDegraded,
		models.HealthStatusUnhealthy,
		models.HealthStatusUnknown,
	}

	if len(statuses) != 4 {
		t.Errorf("expected 4 health statuses, got %d", len(statuses))
	}
}

func TestGlacierFilterJSON(t *testing.T) {
	filter := models.GlacierFilter{
		Search: "test",
		Status: "active",
	}

	data, err := json.Marshal(filter)
	if err != nil {
		t.Fatalf("failed to marshal filter: %v", err)
	}

	var decoded models.GlacierFilter
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal filter: %v", err)
	}

	if decoded.Search != "test" {
		t.Errorf("expected name test, got %s", decoded.Search)
	}
}

func TestTaskCreateRequestJSON(t *testing.T) {
	req := models.TaskCreateRequest{
		GlacierID: "g-001",
		Type:      models.TaskTypeAnalysis,
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	if len(data) == 0 {
		t.Error("marshaled data should not be empty")
	}
}

func TestAnalysisCompareRequestJSON(t *testing.T) {
	req := models.AnalysisCompareRequest{
		GlacierIDs: []string{"g-001", "g-002"},
		Type:       models.AnalysisTypeComparison,
	}

	data, err := json.Marshal(req)
	if err != nil {
		t.Fatalf("failed to marshal request: %v", err)
	}

	var decoded models.AnalysisCompareRequest
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("failed to unmarshal request: %v", err)
	}

	if len(decoded.GlacierIDs) != 2 {
		t.Errorf("expected 2 glacier IDs, got %d", len(decoded.GlacierIDs))
	}
}
