package main

import (
	"context"
	"fmt"
	"os"
	"time"

	"github.com/spf13/cobra"

	"github.com/glacierkz/glacierkz-go/internal/api"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func newAnalyzeCmd() *cobra.Command {
	var (
		glacierID  string
		analysisType string
		startDate  string
		endDate    string
		resolution string
		format     string
		wait       bool
		timeout    time.Duration
	)

	cmd := &cobra.Command{
		Use:   "analyze",
		Short: "Run an analysis on a glacier",
		Long: `Trigger an analysis task for a specific glacier.

Supported analysis types:
  mass_balance  — mass balance estimation from satellite data
  retreat       — glacier retreat/advance measurement
  velocity      — surface velocity mapping
  temperature   — surface temperature analysis
  predictive    — ML-based predictive modeling

Examples:
  gzcli analyze --glacier-id gl-001 --type mass_balance
  gzcli analyze --glacier-id gl-002 --type retreat --start 2020-01-01 --end 2023-12-31
  gzcli analyze --glacier-id gl-003 --type velocity --wait --timeout 5m`,
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if glacierID == "" {
				return fmt.Errorf("--glacier-id is required")
			}
			if analysisType == "" {
				return fmt.Errorf("--type is required")
			}

			c, err := initConfig()
			if err != nil {
				return err
			}
			client := api.NewClient(c.Backend.BaseURL,
				api.WithTimeout(time.Duration(c.Backend.Timeout)*time.Second),
				api.WithRetries(c.Backend.MaxRetries, time.Duration(c.Backend.RetryDelay)*time.Second),
				api.WithAPIKeys(c.Auth.APIKeys),
			)

			ctx, cancel := context.WithTimeout(context.Background(), timeout)
			defer cancel()

			req := models.AnalysisRequest{
				GlacierID:  glacierID,
				Type:       models.AnalysisType(analysisType),
				StartDate:  startDate,
				EndDate:    endDate,
				Resolution: resolution,
			}

			fmt.Fprintf(os.Stderr, "Starting %s analysis for glacier %s...\n", analysisType, glacierID)
			result, err := client.RunAnalysis(ctx, req)
			if err != nil {
				return fmt.Errorf("running analysis: %w", err)
			}

			if !wait {
				fmt.Fprintf(os.Stderr, "Analysis started: %s (status: %s)\n", result.ID, result.Status)
				if format == "json" {
					return printJSON(result)
				}
				fmt.Printf("ID:     %s\n", result.ID)
				fmt.Printf("Status: %s\n", result.Status)
				fmt.Printf("Score:  %.2f\n", result.Score)
				return nil
			}

			fmt.Fprintf(os.Stderr, "Waiting for analysis %s to complete...\n", result.ID)
			return pollAnalysisUntilDone(ctx, client, result.ID, format)
		},
	}

	cmd.Flags().StringVar(&glacierID, "glacier-id", "", "glacier ID to analyze")
	cmd.Flags().StringVar(&analysisType, "type", "", "analysis type (mass_balance|retreat|velocity|temperature|predictive)")
	cmd.Flags().StringVar(&startDate, "start", "", "start date (YYYY-MM-DD)")
	cmd.Flags().StringVar(&endDate, "end", "", "end date (YYYY-MM-DD)")
	cmd.Flags().StringVar(&resolution, "resolution", "", "data resolution (daily|weekly|monthly|yearly)")
	cmd.Flags().StringVarP(&format, "output", "o", "table", "output format (table|json)")
	cmd.Flags().BoolVarP(&wait, "wait", "w", false, "wait for analysis to complete")
	cmd.Flags().DurationVar(&timeout, "timeout", 10*time.Minute, "command timeout")

	return cmd
}

func pollAnalysisUntilDone(ctx context.Context, client *api.Client, analysisID, format string) error {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return fmt.Errorf("timeout waiting for analysis %s", analysisID)
		case <-ticker.C:
			result, err := client.GetAnalysis(ctx, analysisID)
			if err != nil {
				return fmt.Errorf("checking analysis status: %w", err)
			}

			switch result.Status {
			case models.AnalysisStatusCompleted:
				fmt.Fprintf(os.Stderr, "Analysis completed successfully.\n")
				if format == "json" {
					return printJSON(result)
				}
				fmt.Printf("ID:           %s\n", result.ID)
				fmt.Printf("Glacier:      %s\n", result.GlacierID)
				fmt.Printf("Type:         %s\n", result.Type)
				fmt.Printf("Status:       %s\n", result.Status)
				fmt.Printf("Score:        %.4f\n", result.Score)
				fmt.Printf("Confidence:   %.2f%%\n", result.Confidence*100)
				fmt.Printf("Data Points:  %d\n", result.DataPoints)
				fmt.Printf("Summary:      %s\n", result.Summary)
				if len(result.Recommendations) > 0 {
					fmt.Println("\nRecommendations:")
					for i, rec := range result.Recommendations {
						fmt.Printf("  %d. %s\n", i+1, rec)
					}
				}
				return nil

			case models.AnalysisStatusFailed:
				return fmt.Errorf("analysis failed: %s", result.Summary)

			case models.AnalysisStatusPending, models.AnalysisStatusRunning:
				fmt.Fprintf(os.Stderr, "\r  Status: %s (%.0f%%)", result.Status, result.Confidence*100)

			default:
				fmt.Fprintf(os.Stderr, "\r  Unknown status: %s", result.Status)
			}
		}
	}
}
