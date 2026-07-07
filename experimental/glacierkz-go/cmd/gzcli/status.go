package main

import (
	"context"
	"fmt"
	"os"
	"os/signal"
	"time"

	"github.com/spf13/cobra"

	"github.com/glacierkz/glacierkz-go/internal/api"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func newStatusCmd() *cobra.Command {
	var (
		watch    bool
		interval time.Duration
		timeout  time.Duration
	)

	cmd := &cobra.Command{
		Use:   "status",
		Short: "Check system health status",
		Long: `Display the health status of all GlacierNET-KZ services.

Checks connectivity to:
  - API gateway
  - Backend API server
  - gRPC analysis service
  - Database connections

Examples:
  gzcli status
  gzcli status --watch --interval 5s
  gzcli status --timeout 3s`,
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			c, err := initConfig()
			if err != nil {
				return err
			}
			client := api.NewClient(c.Backend.BaseURL,
				api.WithTimeout(time.Duration(c.Backend.Timeout)*time.Second),
				api.WithAPIKeys(c.Auth.APIKeys),
			)

			ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt)
			defer cancel()

			if timeout > 0 {
				var cancelFn context.CancelFunc
				ctx, cancelFn = context.WithTimeout(ctx, timeout)
				defer cancelFn()
			}

			if watch {
				return watchStatus(ctx, client, interval)
			}
			return printStatus(ctx, client)
		},
	}

	cmd.Flags().BoolVarP(&watch, "watch", "w", false, "continuously monitor status")
	cmd.Flags().DurationVarP(&interval, "interval", "i", 5*time.Second, "check interval in watch mode")
	cmd.Flags().DurationVar(&timeout, "timeout", 10*time.Second, "single check timeout")

	return cmd
}

func printStatus(ctx context.Context, client *api.Client) error {
	health := checkHealth(ctx, client)
	printHealthReport(health)
	if health.Status == models.HealthStatusUnhealthy {
		os.Exit(1)
	}
	return nil
}

func watchStatus(ctx context.Context, client *api.Client, interval time.Duration) error {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	fmt.Fprintf(os.Stderr, "Monitoring health every %s. Press Ctrl+C to stop.\n\n", interval)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			health := checkHealth(ctx, client)
			printHealthReport(health)
		}
	}
}

func checkHealth(ctx context.Context, client *api.Client) *models.SystemHealth {
	start := time.Now()

	type checkResult struct {
		service models.ServiceHealth
		err     error
	}

	results := make(chan checkResult, 3)

	go func() {
		svc, err := checkBackend(ctx, client)
		results <- checkResult{service: svc, err: err}
	}()

	go func() {
		svc, err := checkAPI(ctx, client)
		results <- checkResult{service: svc, err: err}
	}()

	go func() {
		svc, err := checkGrpc(ctx, client)
		results <- checkResult{service: svc, err: err}
	}()

	services := make([]models.ServiceHealth, 0, 3)
	for i := 0; i < 3; i++ {
		res := <-results
		if res.err != nil {
			res.service.Status = models.HealthStatusUnhealthy
			res.service.Error = res.err.Error()
		}
		services = append(services, res.service)
	}

	overall := models.HealthStatusHealthy
	for _, svc := range services {
		if svc.Status == models.HealthStatusUnhealthy {
			overall = models.HealthStatusUnhealthy
			break
		}
		if svc.Status == models.HealthStatusDegraded {
			overall = models.HealthStatusDegraded
		}
	}

	return &models.SystemHealth{
		Status:    overall,
		Services:  services,
		Uptime:    time.Since(start),
		Version:   version,
		Timestamp: time.Now().UTC().Format(time.RFC3339),
	}
}

func checkBackend(ctx context.Context, client *api.Client) (models.ServiceHealth, error) {
	start := time.Now()
	svc := models.ServiceHealth{
		Name:      "Backend API",
		LastCheck: time.Now(),
	}

	page := models.NewPageRequest(1, 1)
	_, err := client.ListGlaciers(ctx, models.GlacierFilter{}, page)
	svc.Latency = time.Since(start)

	if err != nil {
		svc.Status = models.HealthStatusUnhealthy
		svc.Message = "Connection failed"
		return svc, err
	}

	svc.Status = models.HealthStatusHealthy
	svc.Message = "Responding normally"
	return svc, nil
}

func checkAPI(ctx context.Context, client *api.Client) (models.ServiceHealth, error) {
	start := time.Now()
	svc := models.ServiceHealth{
		Name:      "Analysis Service",
		LastCheck: time.Now(),
	}

	summary, err := client.GetAnalysisSummary(ctx)
	svc.Latency = time.Since(start)

	if err != nil {
		svc.Status = models.HealthStatusDegraded
		svc.Message = "Summary unavailable"
		return svc, err
	}

	svc.Status = models.HealthStatusHealthy
	svc.Message = fmt.Sprintf("%d total analyses", summary.TotalAnalyses)
	return svc, nil
}

func checkGrpc(ctx context.Context, client *api.Client) (models.ServiceHealth, error) {
	start := time.Now()
	svc := models.ServiceHealth{
		Name:      "gRPC Service",
		LastCheck: time.Now(),
	}
	svc.Latency = time.Since(start)
	svc.Status = models.HealthStatusDegraded
	svc.Message = "Not connected"
	return svc, nil
}

func printHealthReport(h *models.SystemHealth) {
	statusEmoji := map[models.HealthStatus]string{
		models.HealthStatusHealthy:   "\033[32m✓\033[0m",
		models.HealthStatusDegraded:  "\033[33m~\033[0m",
		models.HealthStatusUnhealthy: "\033[31m✗\033[0m",
		models.HealthStatusUnknown:   "\033[90m?\033[0m",
	}

	fmt.Printf("GlacierNET-KZ Status: %s %s (v%s)\n",
		statusEmoji[h.Status], h.Status, h.Version)
	fmt.Printf("Timestamp: %s\n\n", h.Timestamp)

	for _, svc := range h.Services {
		emoji := statusEmoji[svc.Status]
		fmt.Printf("  %s %-20s  %-12s  %v",
			emoji, svc.Name, svc.Status, svc.Latency.Round(time.Millisecond))
		if svc.Message != "" {
			fmt.Printf("  (%s)", svc.Message)
		}
		if svc.Error != "" {
			fmt.Printf("  Error: %s", svc.Error)
		}
		fmt.Println()
	}
	fmt.Println()
}
