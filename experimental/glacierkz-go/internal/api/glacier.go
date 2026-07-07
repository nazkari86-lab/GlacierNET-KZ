package api

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func (c *Client) ListGlaciers(ctx context.Context, filter models.GlacierFilter, page models.PageRequest) (*models.PageResponse, error) {
	params := map[string]string{
		"page":      fmt.Sprintf("%d", page.Page),
		"page_size": fmt.Sprintf("%d", page.PageSize),
	}
	if filter.Region != "" {
		params["region"] = filter.Region
	}
	if filter.Country != "" {
		params["country"] = filter.Country
	}
	if filter.Status != "" {
		params["status"] = filter.Status
	}
	if filter.Trend != "" {
		params["trend"] = filter.Trend
	}
	if filter.Search != "" {
		params["search"] = filter.Search
	}
	if filter.MinArea != nil {
		params["min_area"] = fmt.Sprintf("%f", *filter.MinArea)
	}
	if filter.MaxArea != nil {
		params["max_area"] = fmt.Sprintf("%f", *filter.MaxArea)
	}

	path := "/api/v1/glaciers" + buildQueryString(params)

	var result models.PageResponse
	if err := c.Get(ctx, path, &result); err != nil {
		return nil, fmt.Errorf("listing glaciers: %w", err)
	}
	return &result, nil
}

func (c *Client) GetGlacier(ctx context.Context, id string) (*models.Glacier, error) {
	path := fmt.Sprintf("/api/v1/glaciers/%s", id)
	var glacier models.Glacier
	if err := c.Get(ctx, path, &glacier); err != nil {
		return nil, fmt.Errorf("getting glacier %s: %w", id, err)
	}
	return &glacier, nil
}

func (c *Client) CreateGlacier(ctx context.Context, req models.GlacierCreateRequest) (*models.Glacier, error) {
	var glacier models.Glacier
	if err := c.Post(ctx, "/api/v1/glaciers", req, &glacier); err != nil {
		return nil, fmt.Errorf("creating glacier: %w", err)
	}
	return &glacier, nil
}

func (c *Client) UpdateGlacier(ctx context.Context, id string, req models.GlacierUpdateRequest) (*models.Glacier, error) {
	path := fmt.Sprintf("/api/v1/glaciers/%s", id)
	var glacier models.Glacier
	if err := c.Put(ctx, path, req, &glacier); err != nil {
		return nil, fmt.Errorf("updating glacier %s: %w", id, err)
	}
	return &glacier, nil
}

func (c *Client) DeleteGlacier(ctx context.Context, id string) error {
	path := fmt.Sprintf("/api/v1/glaciers/%s", id)
	if err := c.Delete(ctx, path); err != nil {
		return fmt.Errorf("deleting glacier %s: %w", id, err)
	}
	return nil
}

func (c *Client) GetGlacierStats(ctx context.Context, id string) (map[string]any, error) {
	path := fmt.Sprintf("/api/v1/glaciers/%s/stats", id)
	var stats map[string]any
	if err := c.Get(ctx, path, &stats); err != nil {
		return nil, fmt.Errorf("getting glacier stats %s: %w", id, err)
	}
	return stats, nil
}

func (c *Client) BulkImportGlaciers(ctx context.Context, glaciers []models.GlacierCreateRequest) (int, error) {
	type bulkRequest struct {
		Glaciers []models.GlacierCreateRequest `json:"glaciers"`
	}
	type bulkResponse struct {
		Imported int `json:"imported"`
	}
	req := bulkRequest{Glaciers: glaciers}
	var resp bulkResponse
	if err := c.Post(ctx, "/api/v1/glaciers/bulk", req, &resp); err != nil {
		return 0, fmt.Errorf("bulk importing glaciers: %w", err)
	}
	return resp.Imported, nil
}

func (c *Client) SearchGlaciers(ctx context.Context, query string) ([]models.Glacier, error) {
	path := "/api/v1/glaciers/search" + buildQueryString(map[string]string{"q": query})
	var results []models.Glacier
	if err := c.Get(ctx, path, &results); err != nil {
		return nil, fmt.Errorf("searching glaciers: %w", err)
	}
	return results, nil
}

func (c *Client) GetGlacierTimeline(ctx context.Context, id, startDate, endDate string) ([]models.TrendData, error) {
	params := map[string]string{
		"start_date": startDate,
		"end_date":   endDate,
	}
	path := fmt.Sprintf("/api/v1/glaciers/%s/timeline%s", id, buildQueryString(params))
	var timeline []models.TrendData
	if err := c.Get(ctx, path, &timeline); err != nil {
		return nil, fmt.Errorf("getting glacier timeline %s: %w", id, err)
	}
	return timeline, nil
}

func parseGlacierList(data any) ([]models.Glacier, error) {
	if data == nil {
		return nil, nil
	}
	switch v := data.(type) {
	case []models.Glacier:
		return v, nil
	case []any:
		result := make([]models.Glacier, 0, len(v))
		for _, item := range v {
			b, err := json.Marshal(item)
			if err != nil {
				return nil, err
			}
			var g models.Glacier
			if err := json.Unmarshal(b, &g); err != nil {
				return nil, err
			}
			result = append(result, g)
		}
		return result, nil
	default:
		return nil, fmt.Errorf("unexpected type for glacier list: %T", data)
	}
}

func formatGlacierPath(parts ...string) string {
	return "/api/v1/glaciers/" + strings.Join(parts, "/")
}
