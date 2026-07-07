package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"github.com/glacierkz/glacierkz-go/internal/api"
	"github.com/glacierkz/glacierkz-go/internal/config"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func newExportCmd() *cobra.Command {
	var (
		glacierID  string
		outputFile string
		format     string
		startDate  string
		endDate    string
		analysisType string
		timeout    time.Duration
	)

	cmd := &cobra.Command{
		Use:   "export",
		Short: "Export glacier data to CSV or JSON",
		Long: `Export glacier data and analysis results to local files.

Supports exporting:
  - Individual glacier records
  - Analysis results and summaries
  - Timeline data for time-series analysis

Examples:
  gzcli export --glacier-id gl-001 -o glacier_data.csv
  gzcli export --glacier-id gl-001 --type mass_balance -o analysis.json --format json
  gzcli export --glacier-id gl-001 --start 2020-01-01 --end 2023-12-31 -o timeline.csv`,
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if glacierID == "" {
				return fmt.Errorf("--glacier-id is required")
			}
			if outputFile == "" {
				return fmt.Errorf("-o output file is required")
			}

			c, err := initConfig()
			if err != nil {
				return err
			}
			client := api.NewClient(c.Backend.BaseURL,
				glacierTimeoutOpt(c),
				glacierRetryOpt(c),
				api.WithAPIKeys(c.Auth.APIKeys),
			)

			ctx, cancel := context.WithTimeout(context.Background(), timeout)
			defer cancel()

			if analysisType != "" {
				return exportAnalysis(ctx, client, glacierID, analysisType, startDate, endDate, outputFile, format)
			}
			return exportGlacier(ctx, client, glacierID, outputFile, format)
		},
	}

	cmd.Flags().StringVar(&glacierID, "glacier-id", "", "glacier ID to export")
	cmd.Flags().StringVarP(&outputFile, "output", "o", "", "output file path")
	cmd.Flags().StringVarP(&format, "format", "f", "csv", "output format (csv|json)")
	cmd.Flags().StringVar(&startDate, "start", "", "start date filter (YYYY-MM-DD)")
	cmd.Flags().StringVar(&endDate, "end", "", "end date filter (YYYY-MM-DD)")
	cmd.Flags().StringVar(&analysisType, "type", "", "export analysis of this type instead of raw glacier data")
	cmd.Flags().DurationVar(&timeout, "timeout", 5*time.Minute, "command timeout")

	return cmd
}

func exportGlacier(ctx context.Context, client *api.Client, glacierID, outputFile, format string) error {
	fmt.Fprintf(os.Stderr, "Fetching glacier %s...\n", glacierID)
	glacier, err := client.GetGlacier(ctx, glacierID)
	if err != nil {
		return fmt.Errorf("fetching glacier: %w", err)
	}

	fmt.Fprintf(os.Stderr, "Fetching timeline data...\n")
	timeline, err := client.GetGlacierTimeline(ctx, glacierID, "", "")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Warning: could not fetch timeline: %v\n", err)
		timeline = nil
	}

	f, err := os.Create(outputFile)
	if err != nil {
		return fmt.Errorf("creating output file: %w", err)
	}
	defer f.Close()

	switch strings.ToLower(format) {
	case "json":
		return exportGlacierJSON(f, glacier, timeline)
	case "csv":
		return exportGlacierCSV(f, glacier, timeline)
	default:
		return fmt.Errorf("unsupported format: %s (use csv or json)", format)
	}
}

func exportGlacierJSON(f *os.File, glacier *models.Glacier, timeline []models.TrendData) error {
	export := map[string]any{
		"glacier":  glacier,
		"timeline": timeline,
	}
	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(export); err != nil {
		return fmt.Errorf("encoding JSON: %w", err)
	}
	fmt.Fprintf(os.Stderr, "Exported glacier data to JSON.\n")
	return nil
}

func exportGlacierCSV(f *os.File, glacier *models.Glacier, timeline []models.TrendData) error {
	w := csv.NewWriter(f)
	defer w.Flush()

	headers := []string{
		"glacier_id", "name", "region", "country",
		"area_km2", "elevation", "latitude", "longitude",
		"status", "trend", "mass_balance", "temperature",
	}
	if err := w.Write(headers); err != nil {
		return fmt.Errorf("writing CSV header: %w", err)
	}

	record := []string{
		glacier.ID,
		glacier.Name,
		glacier.Region,
		glacier.Country,
		fmt.Sprintf("%.2f", glacier.AreaKm2),
		fmt.Sprintf("%.1f", glacier.Elevation),
		fmt.Sprintf("%.6f", glacier.Latitude),
		fmt.Sprintf("%.6f", glacier.Longitude),
		glacier.Status,
		glacier.Trend,
		fmt.Sprintf("%.2f", glacier.MassBalance),
		fmt.Sprintf("%.2f", glacier.Temperature),
	}
	if err := w.Write(record); err != nil {
		return fmt.Errorf("writing CSV record: %w", err)
	}

	if len(timeline) > 0 {
		if err := w.Write(nil); err != nil {
			return err
		}
		timelineHeaders := []string{"label", "value", "date", "change", "unit"}
		if err := w.Write(timelineHeaders); err != nil {
			return fmt.Errorf("writing timeline header: %w", err)
		}
		for _, t := range timeline {
			row := []string{
				t.Label,
				fmt.Sprintf("%.4f", t.Value),
				t.Date.Format(time.RFC3339),
				fmt.Sprintf("%.4f", t.Change),
				t.Unit,
			}
			if err := w.Write(row); err != nil {
				return fmt.Errorf("writing timeline row: %w", err)
			}
		}
	}

	fmt.Fprintf(os.Stderr, "Exported glacier data to CSV.\n")
	return nil
}

func exportAnalysis(ctx context.Context, client *api.Client, glacierID, analysisType, startDate, endDate, outputFile, format string) error {
	req := models.AnalysisRequest{
		GlacierID: glacierID,
		Type:      models.AnalysisType(analysisType),
		StartDate: startDate,
		EndDate:   endDate,
	}

	fmt.Fprintf(os.Stderr, "Running %s analysis for export...\n", analysisType)
	result, err := client.RunAnalysis(ctx, req)
	if err != nil {
		return fmt.Errorf("running analysis: %w", err)
	}

	f, err := os.Create(outputFile)
	if err != nil {
		return fmt.Errorf("creating output file: %w", err)
	}
	defer f.Close()

	switch strings.ToLower(format) {
	case "json":
		enc := json.NewEncoder(f)
		enc.SetIndent("", "  ")
		if err := enc.Encode(result); err != nil {
			return fmt.Errorf("encoding analysis JSON: %w", err)
		}
	case "csv":
		w := csv.NewWriter(f)
		defer w.Flush()
		headers := []string{"id", "glacier_id", "type", "status", "score", "confidence", "data_points", "summary"}
		if err := w.Write(headers); err != nil {
			return fmt.Errorf("writing analysis header: %w", err)
		}
		record := []string{
			result.ID, result.GlacierID, string(result.Type), string(result.Status),
			fmt.Sprintf("%.4f", result.Score), fmt.Sprintf("%.2f", result.Confidence),
			fmt.Sprintf("%d", result.DataPoints), result.Summary,
		}
		if err := w.Write(record); err != nil {
			return fmt.Errorf("writing analysis row: %w", err)
		}
	default:
		return fmt.Errorf("unsupported format: %s", format)
	}

	fmt.Fprintf(os.Stderr, "Exported analysis results to %s.\n", outputFile)
	return nil
}

func glacierTimeoutOpt(c *config.Config) api.ClientOption {
	return api.WithTimeout(time.Duration(c.Backend.Timeout) * time.Second)
}

func glacierRetryOpt(c *config.Config) api.ClientOption {
	return api.WithRetries(c.Backend.MaxRetries, time.Duration(c.Backend.RetryDelay)*time.Second)
}
