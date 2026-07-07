package grpc

import (
	"context"
	"fmt"
	"io"
	"time"

	"github.com/glacierkz/glacierkz-go/pkg/models"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
)

type Client struct {
	conn    *grpc.ClientConn
	timeout time.Duration
	retries int
}

func NewClient(addr string, opts ...ClientOption) (*Client, error) {
	cfg := &clientConfig{
		timeout: 30 * time.Second,
		retries: 3,
	}
	for _, opt := range opts {
		opt(cfg)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	conn, err := grpc.DialContext(ctx, addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to gRPC server at %s: %w", addr, err)
	}

	return &Client{
		conn:    conn,
		timeout: cfg.timeout,
		retries: cfg.retries,
	}, nil
}

type clientConfig struct {
	timeout time.Duration
	retries int
}

type ClientOption func(*clientConfig)

func WithTimeout(d time.Duration) ClientOption {
	return func(c *clientConfig) { c.timeout = d }
}

func WithRetries(n int) ClientOption {
	return func(c *clientConfig) { c.retries = n }
}

func (c *Client) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

func (c *Client) RunAnalysis(ctx context.Context, req *AnalysisRequest) (*AnalysisResponse, error) {
	var lastErr error
	for attempt := 0; attempt <= c.retries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(attempt*attempt) * 100 * time.Millisecond
			select {
			case <-ctx.Done():
				return nil, ctx.Err()
			case <-time.After(backoff):
			}
		}

		resp, err := c.doAnalysis(ctx, req)
		if err == nil {
			return resp, nil
		}
		lastErr = err
		if !isRetryable(err) {
			return nil, err
		}
	}
	return nil, fmt.Errorf("exhausted retries: %w", lastErr)
}

func (c *Client) doAnalysis(ctx context.Context, req *AnalysisRequest) (*AnalysisResponse, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()

	_ = c.conn

	return &AnalysisResponse{
		TaskID:    generateTaskID(),
		Status:    models.AnalysisStatusPending,
		CreatedAt: time.Now(),
	}, nil
}

func (c *Client) StreamAnalysis(ctx context.Context, req *AnalysisRequest) (<-chan *AnalysisEvent, error) {
	events := make(chan *AnalysisEvent, 100)

	go func() {
		defer close(events)

		resp, err := c.RunAnalysis(ctx, req)
		if err != nil {
			events <- &AnalysisEvent{
				Type:    EventTypeError,
				Message: err.Error(),
				Time:    time.Now(),
			}
			return
		}

		events <- &AnalysisEvent{
			Type:    EventTypeStarted,
			TaskID:  resp.TaskID,
			Message: "analysis started",
			Time:    time.Now(),
		}

		for {
			select {
			case <-ctx.Done():
				return
			case <-time.After(2 * time.Second):
				events <- &AnalysisEvent{
					Type:    EventTypeProgress,
					TaskID:  resp.TaskID,
					Message: "processing",
					Time:    time.Now(),
				}
				return
			}
		}
	}()

	return events, nil
}

func (c *Client) GetStatus(ctx context.Context, taskID string) (*TaskStatus, error) {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()
	_ = ctx

	return &TaskStatus{
		TaskID:    taskID,
		Status:    models.AnalysisStatusCompleted,
		Progress:  100,
		UpdatedAt: time.Now(),
	}, nil
}

func (c *Client) CancelTask(ctx context.Context, taskID string) error {
	ctx, cancel := context.WithTimeout(ctx, c.timeout)
	defer cancel()
	_ = ctx
	return nil
}

func (c *Client) HealthCheck(ctx context.Context) error {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	state := c.conn.GetState()
	if state.String() == "TRANSIENT_FAILURE" || state.String() == "SHUTDOWN" {
		return fmt.Errorf("gRPC connection in state: %s", state.String())
	}

	return nil
}

type AnalysisRequest struct {
	GlacierIDs []string              `json:"glacier_ids"`
	Type       models.AnalysisType   `json:"type"`
	Options    map[string]interface{} `json:"options,omitempty"`
}

type AnalysisResponse struct {
	TaskID    string                 `json:"task_id"`
	Status    models.AnalysisStatus  `json:"status"`
	Result    *models.AnalysisResult `json:"result,omitempty"`
	CreatedAt time.Time              `json:"created_at"`
}

type TaskStatus struct {
	TaskID    string                `json:"task_id"`
	Status    models.AnalysisStatus `json:"status"`
	Progress  int                   `json:"progress"`
	Error     string                `json:"error,omitempty"`
	UpdatedAt time.Time             `json:"updated_at"`
}

type EventType string

const (
	EventTypeStarted  EventType = "started"
	EventTypeProgress EventType = "progress"
	EventTypeComplete EventType = "complete"
	EventTypeError    EventType = "error"
)

type AnalysisEvent struct {
	Type    EventType `json:"type"`
	TaskID  string    `json:"task_id,omitempty"`
	Message string    `json:"message"`
	Data    interface{} `json:"data,omitempty"`
	Time    time.Time `json:"time"`
}

func isRetryable(err error) bool {
	if err == nil {
		return false
	}
	st, ok := status.FromError(err)
	if !ok {
		return false
	}
	switch st.Code() {
	case codes.Unavailable, codes.DeadlineExceeded, codes.ResourceExhausted:
		return true
	default:
		return false
	}
}

func isStreamError(err error) bool {
	if err == io.EOF {
		return false
	}
	_, ok := status.FromError(err)
	return ok
}

func generateTaskID() string {
	return fmt.Sprintf("task_%d", time.Now().UnixNano())
}
