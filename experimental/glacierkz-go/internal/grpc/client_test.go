package grpc_test

import (
	"context"
	"testing"
	"time"

	grpcclient "github.com/glacierkz/glacierkz-go/internal/grpc"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

func TestNewClient(t *testing.T) {
	_, err := grpcclient.NewClient("localhost:9999",
		grpcclient.WithTimeout(5*time.Second),
		grpcclient.WithRetries(2),
	)
	if err == nil {
		t.Log("Client created (connection may fail in test env)")
	}
}

func TestAnalysisTypeFromPB(t *testing.T) {
	tests := []struct {
		pb   grpcclient.AnalysisTypePB
		want string
	}{
		{grpcclient.AnalysisTypePB_VELOCITY, "velocity"},
		{grpcclient.AnalysisTypePB_MASS_BALANCE, "mass_balance"},
		{grpcclient.AnalysisTypePB_AREA_CHANGE, "area_change"},
		{grpcclient.AnalysisTypePB_CLIMATE, "climate"},
		{grpcclient.AnalysisTypePB_PREDICTION, "prediction"},
		{grpcclient.AnalysisTypePB_COMPARISON, "comparison"},
		{grpcclient.AnalysisTypePB_MULTI_YEAR, "multi_year"},
		{grpcclient.AnalysisTypePB_UNKNOWN, "unknown"},
	}

	for _, tt := range tests {
		got := grpcclient.AnalysisTypeFromPB(tt.pb)
		if got != tt.want {
			t.Errorf("AnalysisTypeFromPB(%d) = %q, want %q", tt.pb, got, tt.want)
		}
	}
}

func TestAnalysisTypeToPB(t *testing.T) {
	tests := []struct {
		input string
		want  grpcclient.AnalysisTypePB
	}{
		{"velocity", grpcclient.AnalysisTypePB_VELOCITY},
		{"mass_balance", grpcclient.AnalysisTypePB_MASS_BALANCE},
		{"area_change", grpcclient.AnalysisTypePB_AREA_CHANGE},
		{"climate", grpcclient.AnalysisTypePB_CLIMATE},
		{"prediction", grpcclient.AnalysisTypePB_PREDICTION},
		{"comparison", grpcclient.AnalysisTypePB_COMPARISON},
		{"multi_year", grpcclient.AnalysisTypePB_MULTI_YEAR},
		{"unknown_type", grpcclient.AnalysisTypePB_UNKNOWN},
		{"", grpcclient.AnalysisTypePB_UNKNOWN},
	}

	for _, tt := range tests {
		got := grpcclient.AnalysisTypeToPB(tt.input)
		if got != tt.want {
			t.Errorf("AnalysisTypeToPB(%q) = %d, want %d", tt.input, got, tt.want)
		}
	}
}

func TestTimeConversions(t *testing.T) {
	now := time.Now().Truncate(time.Second)
	pb := grpcclient.TimeToPB(now)
	back := grpcclient.PBToTime(pb)

	if !now.Equal(back) {
		t.Errorf("Time round-trip failed: %v != %v", now, back)
	}
}

func TestRunAnalysisWithoutServer(t *testing.T) {
	req := &grpcclient.AnalysisRequest{
		GlacierIDs: []string{"glacier-1"},
		Type:       models.AnalysisTypeVelocity,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	client, err := grpcclient.NewClient("localhost:9999")
	if err != nil {
		t.Skip("Cannot connect to gRPC server:", err)
	}
	defer client.Close()

	_, err = client.RunAnalysis(ctx, req)
	if err == nil {
		t.Log("RunAnalysis completed (unexpected in test env)")
	}
}

func TestStreamAnalysisWithoutServer(t *testing.T) {
	req := &grpcclient.AnalysisRequest{
		GlacierIDs: []string{"glacier-1"},
		Type:       models.AnalysisTypeVelocity,
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	client, err := grpcclient.NewClient("localhost:9999")
	if err != nil {
		t.Skip("Cannot connect to gRPC server:", err)
	}
	defer client.Close()

	events, err := client.StreamAnalysis(ctx, req)
	if err != nil {
		t.Skip("StreamAnalysis failed:", err)
	}

	timeout := time.After(5 * time.Second)
	for {
		select {
		case event, ok := <-events:
			if !ok {
				return
			}
			t.Logf("Event: %s - %s", event.Type, event.Message)
		case <-timeout:
			return
		case <-ctx.Done():
			return
		}
	}
}

func TestGetStatusWithoutServer(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	client, err := grpcclient.NewClient("localhost:9999")
	if err != nil {
		t.Skip("Cannot connect to gRPC server:", err)
	}
	defer client.Close()

	status, err := client.GetStatus(ctx, "task-123")
	if err != nil {
		t.Skip("GetStatus failed:", err)
	}

	if status.TaskID != "task-123" {
		t.Errorf("Expected task ID task-123, got %s", status.TaskID)
	}
}

func TestCancelTaskWithoutServer(t *testing.T) {
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()

	client, err := grpcclient.NewClient("localhost:9999")
	if err != nil {
		t.Skip("Cannot connect to gRPC server:", err)
	}
	defer client.Close()

	err = client.CancelTask(ctx, "task-123")
	if err != nil {
		t.Skip("CancelTask failed:", err)
	}
}
