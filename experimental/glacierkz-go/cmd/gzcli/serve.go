package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os/signal"
	"syscall"
	"time"

	"github.com/spf13/cobra"

	"github.com/glacierkz/glacierkz-go/internal/config"
	"github.com/glacierkz/glacierkz-go/internal/gateway"
	"github.com/glacierkz/glacierkz-go/internal/health"
)

func newServeCmd() *cobra.Command {
	var (
		port      int
		logLevel  string
		daemonize bool
	)

	cmd := &cobra.Command{
		Use:   "serve",
		Short: "Start the GlacierNET-KZ API gateway",
		Long: `Start the API gateway that routes requests to backend services.

The gateway provides:
  - Reverse proxy to FastAPI backend
  - Health check aggregation
  - Rate limiting and authentication
  - CORS handling
  - Request logging

Examples:
  gzcli serve
  gzcli serve --port 9090
  gzcli serve --config /etc/glacierkz/gateway.yaml`,
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			c, err := initConfig()
			if err != nil {
				return err
			}
			if port > 0 {
				c.Server.Port = port
			}
			if logLevel != "" {
				c.Log.Level = logLevel
			}

			return runGateway(c, cmd)
		},
	}

	cmd.Flags().IntVarP(&port, "port", "p", 0, "server port (overrides config)")
	cmd.Flags().StringVar(&logLevel, "log-level", "", "log level (debug|info|warn|error)")
	cmd.Flags().BoolVar(&daemonize, "daemon", false, "run as background daemon (not implemented)")

	return cmd
}

func runGateway(c *config.Config, cmd *cobra.Command) error {
	gw := gateway.New(c)

	aggregator := health.NewAggregator(c)

	ctx, cancel := signal.NotifyContext(cmd.Context(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	go aggregator.Start(time.Duration(c.Health.Interval) * time.Second)

	addr := fmt.Sprintf("%s:%d", c.Server.Host, c.Server.Port)
	srv := &http.Server{
		Addr:         addr,
		Handler:      gw,
		ReadTimeout:  time.Duration(c.Server.ReadTimeout) * time.Second,
		WriteTimeout: time.Duration(c.Server.WriteTimeout) * time.Second,
		IdleTimeout:  time.Duration(c.Server.IdleTimeout) * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		log.Printf("GlacierNET-KZ gateway starting on %s", addr)
		log.Printf("Backend: %s", c.Backend.BaseURL)
		log.Printf("gRPC: %s", c.GRPC.Address)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- err
		}
	}()

	select {
	case <-ctx.Done():
		log.Println("Shutting down gateway...")
	case err := <-errCh:
		log.Printf("Server error: %v", err)
	}

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 15*time.Second)
	defer shutdownCancel()

	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("Shutdown error: %v", err)
		return err
	}

	log.Println("Gateway stopped gracefully")
	return nil
}
