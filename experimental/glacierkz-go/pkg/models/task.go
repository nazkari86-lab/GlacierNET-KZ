package models

import "time"

type TaskType string

const (
	TaskTypeAnalysis  TaskType = "analysis"
	TaskTypeExport    TaskType = "export"
	TaskTypeIngestion TaskType = "ingestion"
	TaskTypeReport    TaskType = "report"
)

type TaskStatus string

const (
	TaskStatusPending   TaskStatus = "pending"
	TaskStatusRunning   TaskStatus = "running"
	TaskStatusCompleted TaskStatus = "completed"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusCancelled TaskStatus = "cancelled"
)

type Task struct {
	ID          string            `json:"id"`
	Type        TaskType          `json:"type"`
	Status      TaskStatus        `json:"status"`
	GlacierID   string            `json:"glacier_id"`
	Description string            `json:"description"`
	Progress    int               `json:"progress"`
	Result      *TaskResult       `json:"result,omitempty"`
	Error       string            `json:"error,omitempty"`
	CreatedAt   time.Time         `json:"created_at"`
	StartedAt   *time.Time        `json:"started_at,omitempty"`
	CompletedAt *time.Time        `json:"completed_at,omitempty"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

type TaskResult struct {
	Summary     string         `json:"summary"`
	Data        map[string]any `json:"data,omitempty"`
	DownloadURL string         `json:"download_url,omitempty"`
}

type TaskCreateRequest struct {
	Type        TaskType          `json:"type" validate:"required"`
	GlacierID   string            `json:"glacier_id" validate:"required"`
	Description string            `json:"description"`
	Parameters  map[string]string `json:"parameters,omitempty"`
}

type TaskListFilter struct {
	Status    *TaskStatus `json:"status,omitempty"`
	Type      *TaskType   `json:"type,omitempty"`
	GlacierID string      `json:"glacier_id,omitempty"`
	Limit     int         `json:"limit,omitempty"`
	Offset    int         `json:"offset,omitempty"`
}

type TaskUpdateStatusRequest struct {
	Status   TaskStatus  `json:"status"`
	Progress int         `json:"progress"`
	Error    string      `json:"error,omitempty"`
	Result   *TaskResult `json:"result,omitempty"`
}
