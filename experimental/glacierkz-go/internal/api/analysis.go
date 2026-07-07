package api

import (
	"context"
	"fmt"

	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func (c *Client) RunAnalysis(ctx context.Context, req models.AnalysisRequest) (*models.AnalysisResult, error) {
	var result models.AnalysisResult
	if err := c.Post(ctx, "/api/v1/analysis", req, &result); err != nil {
		return nil, fmt.Errorf("running analysis: %w", err)
	}
	return &result, nil
}

func (c *Client) GetAnalysis(ctx context.Context, id string) (*models.AnalysisResult, error) {
	path := fmt.Sprintf("/api/v1/analysis/%s", id)
	var result models.AnalysisResult
	if err := c.Get(ctx, path, &result); err != nil {
		return nil, fmt.Errorf("getting analysis %s: %w", id, err)
	}
	return &result, nil
}

func (c *Client) ListAnalysis(ctx context.Context, glacierID string, page models.PageRequest) (*models.PageResponse, error) {
	params := map[string]string{
		"page":      fmt.Sprintf("%d", page.Page),
		"page_size": fmt.Sprintf("%d", page.PageSize),
	}
	if glacierID != "" {
		params["glacier_id"] = glacierID
	}
	path := "/api/v1/analysis" + buildQueryString(params)
	var result models.PageResponse
	if err := c.Get(ctx, path, &result); err != nil {
		return nil, fmt.Errorf("listing analysis: %w", err)
	}
	return &result, nil
}

func (c *Client) CompareAnalysis(ctx context.Context, req models.AnalysisCompareRequest) ([]models.AnalysisResult, error) {
	var results []models.AnalysisResult
	if err := c.Post(ctx, "/api/v1/analysis/compare", req, &results); err != nil {
		return nil, fmt.Errorf("comparing analysis: %w", err)
	}
	return results, nil
}

func (c *Client) GetAnalysisSummary(ctx context.Context) (*models.AnalysisSummary, error) {
	var summary models.AnalysisSummary
	if err := c.Get(ctx, "/api/v1/analysis/summary", &summary); err != nil {
		return nil, fmt.Errorf("getting analysis summary: %w", err)
	}
	return &summary, nil
}

func (c *Client) DeleteAnalysis(ctx context.Context, id string) error {
	path := fmt.Sprintf("/api/v1/analysis/%s", id)
	if err := c.Delete(ctx, path); err != nil {
		return fmt.Errorf("deleting analysis %s: %w", id, err)
	}
	return nil
}

func (c *Client) ExportAnalysis(ctx context.Context, id, format string) ([]byte, error) {
	path := fmt.Sprintf("/api/v1/analysis/%s/export?format=%s", id, format)
	var data []byte
	if err := c.Get(ctx, path, &data); err != nil {
		return nil, fmt.Errorf("exporting analysis %s: %w", id, err)
	}
	return data, nil
}
