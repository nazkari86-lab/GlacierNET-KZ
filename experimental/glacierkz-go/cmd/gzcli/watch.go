package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
	"github.com/spf13/cobra"

	"github.com/glacierkz/glacierkz-go/internal/api"
)

type WSMessage struct {
	Type      string         `json:"type"`
	TaskID    string         `json:"task_id,omitempty"`
	Status    string         `json:"status,omitempty"`
	Progress  int            `json:"progress,omitempty"`
	Data      map[string]any `json:"data,omitempty"`
	Error     string         `json:"error,omitempty"`
	Timestamp string         `json:"timestamp"`
}

func newWatchCmd() *cobra.Command {
	var (
		taskIDs   []string
		allTasks  bool
		pollInt   time.Duration
		timeout   time.Duration
		rawOutput bool
	)

	cmd := &cobra.Command{
		Use:   "watch [task-id...]",
		Short: "Monitor task progress via WebSocket or polling",
		Long: `Watch one or more tasks for progress updates.

If WebSocket is available, connects for real-time updates.
Falls back to HTTP polling when WebSocket is unavailable.

Examples:
  gzcli watch task-abc-123
  gzcli watch task-abc-123 task-def-456
  gzcli watch --all --poll-interval 5s
  gzcli watch task-abc-123 --timeout 10m`,
		SilenceUsage: true,
		RunE: func(cmd *cobra.Command, args []string) error {
			if len(args) > 0 {
				taskIDs = append(taskIDs, args...)
			}
			if len(taskIDs) == 0 && !allTasks {
				return fmt.Errorf("specify task IDs or use --all")
			}

			c, err := initConfig()
			if err != nil {
				return err
			}
			client := api.NewClient(c.Backend.BaseURL,
				api.WithTimeout(time.Duration(c.Backend.Timeout)*time.Second),
				api.WithAPIKeys(c.Auth.APIKeys),
			)

			ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
			defer cancel()

			if timeout > 0 {
				var cancelFn context.CancelFunc
				ctx, cancelFn = context.WithTimeout(ctx, timeout)
				defer cancelFn()
			}

			wsURL := buildWSURL(c.Backend.BaseURL)
			if wsURL != "" {
				fmt.Fprintf(os.Stderr, "Connecting to WebSocket at %s...\n", wsURL)
				return watchWebSocket(ctx, wsURL, taskIDs, rawOutput)
			}

			fmt.Fprintf(os.Stderr, "WebSocket unavailable, falling back to polling.\n")
			return watchPolling(ctx, client, taskIDs, pollInt, rawOutput)
		},
	}

	cmd.Flags().StringSliceVar(&taskIDs, "task-id", nil, "task ID(s) to watch")
	cmd.Flags().BoolVar(&allTasks, "all", false, "watch all active tasks")
	cmd.Flags().DurationVar(&pollInt, "poll-interval", 3*time.Second, "polling interval for HTTP fallback")
	cmd.Flags().DurationVar(&timeout, "timeout", 0, "overall timeout (0 = no timeout)")
	cmd.Flags().BoolVar(&rawOutput, "raw", false, "output raw JSON messages")

	return cmd
}

func buildWSURL(baseURL string) string {
	wsURL := strings.Replace(baseURL, "http://", "ws://", 1)
	wsURL = strings.Replace(wsURL, "https://", "wss://", 1)
	return wsURL + "/ws/tasks"
}

func watchWebSocket(ctx context.Context, wsURL string, taskIDs []string, raw bool) error {
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}

	conn, _, err := dialer.DialContext(ctx, wsURL, nil)
	if err != nil {
		return fmt.Errorf("connecting to WebSocket: %w", err)
	}
	defer conn.Close()

	subscribe := map[string]any{
		"type":     "subscribe",
		"task_ids": taskIDs,
	}
	if err := conn.WriteJSON(subscribe); err != nil {
		return fmt.Errorf("sending subscribe: %w", err)
	}

	fmt.Fprintf(os.Stderr, "Watching %d task(s). Press Ctrl+C to stop.\n", len(taskIDs))

	done := make(chan error, 1)
	go func() {
		defer close(done)
		for {
			_, message, err := conn.ReadMessage()
			if err != nil {
				done <- fmt.Errorf("reading WebSocket message: %w", err)
				return
			}

			var msg WSMessage
			if err := json.Unmarshal(message, &msg); err != nil {
				fmt.Fprintf(os.Stderr, "Invalid message: %s\n", string(message))
				continue
			}

			if raw {
				fmt.Println(string(message))
				continue
			}

			printWSMessage(&msg)
			if msg.Status == "completed" || msg.Status == "failed" {
				if isWatchingDone(msg.TaskID, taskIDs) {
					return
				}
			}
		}
	}()

	select {
	case <-ctx.Done():
		return ctx.Err()
	case err := <-done:
		return err
	}
}

func watchPolling(ctx context.Context, client *api.Client, taskIDs []string, interval time.Duration, raw bool) error {
	fmt.Fprintf(os.Stderr, "Polling %d task(s) every %s. Press Ctrl+C to stop.\n", len(taskIDs), interval)
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	completed := make(map[string]bool)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			for _, id := range taskIDs {
				if completed[id] {
					continue
				}
				task, err := client.GetTask(ctx, id)
				if err != nil {
					fmt.Fprintf(os.Stderr, "Error polling task %s: %v\n", id, err)
					continue
				}
				msg := &WSMessage{
					Type:      "progress",
					TaskID:    task.ID,
					Status:    string(task.Status),
					Progress:  task.Progress,
					Timestamp: time.Now().UTC().Format(time.RFC3339),
				}
				if raw {
					data, _ := json.Marshal(msg)
					fmt.Println(string(data))
				} else {
					printWSMessage(msg)
				}
				if task.Status == "completed" || task.Status == "failed" {
					completed[id] = true
				}
			}
			if len(completed) == len(taskIDs) {
				fmt.Fprintf(os.Stderr, "\nAll tasks finished.\n")
				return nil
			}
		}
	}
}

func printWSMessage(msg *WSMessage) {
	statusColor := "\033[32m"
	switch msg.Status {
	case "failed":
		statusColor = "\033[31m"
	case "running", "pending":
		statusColor = "\033[33m"
	}
	reset := "\033[0m"

	fmt.Printf("[%s] Task %s: %s%s%s (%d%%)\n",
		msg.Timestamp, msg.TaskID, statusColor, msg.Status, reset, msg.Progress)

	if msg.Error != "" {
		fmt.Printf("  Error: %s\n", msg.Error)
	}
}

func isWatchingDone(taskID string, taskIDs []string) bool {
	if len(taskIDs) == 0 {
		return true
	}
	for _, id := range taskIDs {
		if id == taskID {
			return true
		}
	}
	return false
}
