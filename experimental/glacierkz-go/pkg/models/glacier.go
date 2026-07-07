package models

import "time"

type Glacier struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Region      string    `json:"region"`
	Country     string    `json:"country"`
	AreaKm2     float64   `json:"area_km2"`
	Elevation   float64   `json:"elevation"`
	Latitude    float64   `json:"latitude"`
	Longitude   float64   `json:"longitude"`
	Status      string    `json:"status"`
	Trend       string    `json:"trend"`
	MassBalance float64   `json:"mass_balance"`
	Temperature float64   `json:"temperature"`
	Precip      float64   `json:"precipitation"`
	Source      string    `json:"source"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	Tags        []string  `json:"tags,omitempty"`
	Metadata    map[string]string `json:"metadata,omitempty"`
}

type GlacierCreateRequest struct {
	Name      string            `json:"name" validate:"required"`
	Region    string            `json:"region" validate:"required"`
	Country   string            `json:"country" validate:"required"`
	AreaKm2   float64           `json:"area_km2"`
	Elevation float64           `json:"elevation"`
	Latitude  float64           `json:"latitude"`
	Longitude float64           `json:"longitude"`
	Tags      []string          `json:"tags,omitempty"`
	Metadata  map[string]string `json:"metadata,omitempty"`
}

type GlacierUpdateRequest struct {
	Name      *string            `json:"name,omitempty"`
	AreaKm2   *float64           `json:"area_km2,omitempty"`
	Elevation *float64           `json:"elevation,omitempty"`
	Status    *string            `json:"status,omitempty"`
	Trend     *string            `json:"trend,omitempty"`
	Tags      []string           `json:"tags,omitempty"`
	Metadata  map[string]string  `json:"metadata,omitempty"`
}

type GlacierFilter struct {
	Region   string `json:"region,omitempty"`
	Country  string `json:"country,omitempty"`
	Status   string `json:"status,omitempty"`
	Trend    string `json:"trend,omitempty"`
	MinArea  *float64 `json:"min_area,omitempty"`
	MaxArea  *float64 `json:"max_area,omitempty"`
	Search   string `json:"search,omitempty"`
}
