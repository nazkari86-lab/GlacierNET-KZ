package api

import (
	"context"
	"fmt"

	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func (c *Client) ListTasks(ctx context.Context, filter models.TaskListFilter) ([]models.Task, error) {
	params := map[string]string{
		"limit":  "50",
		"offset": "0",
	}
	if filter.Status != nil {
		params["status"] = string(*filter.Status)
	}
	if filter.Type != nil {
		params["type"] = string(*filter.Type)
	}
	if filter.GlacierID != "" {
		params["glacier_id"] = filter.GlacierID
	}
	if filter.Limit > 0 {
		params["limit"] = fmt.Sprintf("%d", filter.Limit)
	}
	if filter.Offset > 0 {
		params["offset"] = fmt.Sprintf("%d", filter.Offset)
	}

	path := "/api/v1/tasks" + buildQueryString(params)
	var tasks []models.Task
	if err := c.Get(ctx, path, &tasks); err != nil {
		return nil, fmt.Errorf("listing tasks: %w", err)
	}
	return tasks, nil
}

func (c *Client) GetTask(ctx context.Context, id string) (*models.Task, error) {
	path := fmt.Sprintf("/api/v1/tasks/%s", id)
	var task models.Task
	if err := c.Get(ctx, path, &task); err != nil {
		return nil, fmt.Errorf("getting task %s: %w", id, err)
	}
	return &task, nil
}

func (c *Client) CreateTask(ctx context.Context, req models.TaskCreateRequest) (*models.Task, error) {
	var task models.Task
	if err := c.Post(ctx, "/api/v1/tasks", req, &task); err != nil {
		return nil, fmt.Errorf("creating task: %w", err)
	}
	return &task, nil
}

func (c *Client) CancelTask(ctx context.Context, id string) error {
	path := fmt.Sprintf("/api/v1/tasks/%s/cancel", id)
	if err := c.Post(ctx, path, nil, nil); err != nil {
		return fmt.Errorf("cancelling task %s: %w", id, err)
	}
	return nil
}

func (c *Client) GetTaskProgress(ctx context.Context, id string) (int, string, error) {
	type progressResponse struct {
		Progress int    `json:"progress"`
		Status   string `json:"status"`
	}
	path := fmt.Sprintf("/api/v1/tasks/%s/progress", id)
	var resp progressResponse
	if err := c.Get(ctx, path, &resp); err != nil {
		return 0, "", fmt.Errorf("getting task progress %s: %w", id, err)
	}
	return resp.Progress, resp.Status, nil
}

func (c *Client) GetTaskResult(ctx context.Context, id string) (*models.TaskResult, error) {
	path := fmt.Sprintf("/api/v1/tasks/%s/result", id)
	var result models.TaskResult
	if err := c.Get(ctx, path, &result); err != nil {
		return nil, fmt.Errorf("getting task result %s: %w", id, err)
	}
	return &result, nil
}

func (c *Client) RetryTask(ctx context.Context, id string) (*models.Task, error) {
	path := fmt.Sprintf("/api/v1/tasks/%s/retry", id)
	var task models.Task
	if err := c.Post(ctx, path, nil, &task); err != nil {
		return nil, fmt.Errorf("retrying task %s: %w", id, err)
	}
	return &task, nil
}

func (c *Client) GetTasksByGlacier(ctx context.Context, glacierID string) ([]models.Task, error) {
	filter := models.TaskListFilter{
		GlacierID: glacierID,
		Limit:     100,
	}
	return c.ListTasks(ctx, filter)
}

func (c *Client) DeleteTask(ctx context.Context, id string) error {
	path := fmt.Sprintf("/api/v1/tasks/%s", id)
	if err := c.Delete(ctx, path); err != nil {
		return fmt.Errorf("deleting task %s: %w", id, err)
	}
	return nil
}
