package models

import (
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type PageRequest struct {
	Page     int    `json:"page"`
	PageSize int    `json:"page_size"`
	SortBy   string `json:"sort_by"`
	Order    string `json:"order"`
}

func NewPageRequest(page, pageSize int) PageRequest {
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	if pageSize > 100 {
		pageSize = 100
	}
	return PageRequest{
		Page:     page,
		PageSize: pageSize,
		SortBy:   "created_at",
		Order:    "desc",
	}
}

func (p PageRequest) Offset() int {
	return (p.Page - 1) * p.PageSize
}

type PageResponse struct {
	Total      int   `json:"total"`
	Page       int   `json:"page"`
	PageSize   int   `json:"page_size"`
	TotalPages int   `json:"total_pages"`
	Data       any   `json:"data"`
}

func NewPageResponse(total, page, pageSize int) PageResponse {
	totalPages := total / pageSize
	if total%pageSize > 0 {
		totalPages++
	}
	return PageResponse{
		Total:      total,
		Page:       page,
		PageSize:   pageSize,
		TotalPages: totalPages,
	}
}

type ErrorResponse struct {
	Code       int    `json:"code"`
	Message    string `json:"message"`
	Details    string `json:"details,omitempty"`
	Timestamp  string `json:"timestamp"`
	RequestID  string `json:"request_id,omitempty"`
}

func NewErrorResponse(code int, message, details string) ErrorResponse {
	return ErrorResponse{
		Code:      code,
		Message:   message,
		Details:   details,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}
}

func ErrorResponseFromHTTP(code int, msg string) ErrorResponse {
	return NewErrorResponse(code, msg, "")
}

type HealthStatus string

const (
	HealthStatusHealthy   HealthStatus = "healthy"
	HealthStatusDegraded  HealthStatus = "degraded"
	HealthStatusUnhealthy HealthStatus = "unhealthy"
	HealthStatusUnknown   HealthStatus = "unknown"
)

type ServiceHealth struct {
	Name      string       `json:"name"`
	Status    HealthStatus `json:"status"`
	Latency   time.Duration `json:"latency"`
	Message   string       `json:"message,omitempty"`
	LastCheck time.Time    `json:"last_check"`
	Error     string       `json:"error,omitempty"`
}

type SystemHealth struct {
	Status    HealthStatus    `json:"status"`
	Services  []ServiceHealth `json:"services"`
	Uptime    time.Duration   `json:"uptime"`
	Version   string          `json:"version"`
	Timestamp string          `json:"timestamp"`
}

func WriteJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := encodeJSON(w, v); err != nil {
		http.Error(w, fmt.Sprintf(`{"message":"encoding error: %v"}`, err), http.StatusInternalServerError)
	}
}

func WriteError(w http.ResponseWriter, status int, message string) {
	WriteJSON(w, status, NewErrorResponse(status, message, ""))
}

func encodeJSON(w http.ResponseWriter, v any) error {
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	return enc.Encode(v)
}
