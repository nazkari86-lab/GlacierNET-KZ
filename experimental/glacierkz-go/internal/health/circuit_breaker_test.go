package health_test

import (
	"testing"
	"time"

	"github.com/glacierkz/glacierkz-go/internal/health"
)

func TestCircuitBreakerClosed(t *testing.T) {
	cb := health.NewCircuitBreaker(3, 5*time.Second)

	if !cb.AllowRequest() {
		t.Error("circuit breaker should allow request when closed")
	}
	if cb.State() != health.StateClosed {
		t.Errorf("expected closed state, got %v", cb.State())
	}
}

func TestCircuitBreakerOpen(t *testing.T) {
	cb := health.NewCircuitBreaker(2, 10*time.Second)

	cb.RecordFailure()
	if cb.State() != health.StateClosed {
		t.Error("should still be closed after 1 failure")
	}

	cb.RecordFailure()
	if cb.State() != health.StateOpen {
		t.Errorf("expected open state after 2 failures, got %v", cb.State())
	}

	if cb.AllowRequest() {
		t.Error("circuit breaker should not allow request when open")
	}
}

func TestCircuitBreakerHalfOpen(t *testing.T) {
	cb := health.NewCircuitBreaker(2, 1*time.Millisecond)

	cb.RecordFailure()
	cb.RecordFailure()
	if cb.State() != health.StateOpen {
		t.Error("should be open")
	}

	time.Sleep(2 * time.Millisecond)

	if !cb.AllowRequest() {
		t.Error("should allow request after timeout (half-open)")
	}
	if cb.State() != health.StateHalfOpen {
		t.Errorf("expected half-open state, got %v", cb.State())
	}
}

func TestCircuitBreakerHalfOpenToClosed(t *testing.T) {
	cb := health.NewCircuitBreaker(2, 1*time.Millisecond)

	cb.RecordFailure()
	cb.RecordFailure()
	time.Sleep(2 * time.Millisecond)
	cb.AllowRequest() // transition to half-open

	for i := 0; i < 3; i++ {
		cb.RecordSuccess()
	}

	if cb.State() != health.StateClosed {
		t.Errorf("expected closed state after successes in half-open, got %v", cb.State())
	}
}

func TestCircuitBreakerHalfOpenToOpen(t *testing.T) {
	cb := health.NewCircuitBreaker(2, 1*time.Millisecond)

	cb.RecordFailure()
	cb.RecordFailure()
	time.Sleep(2 * time.Millisecond)
	cb.AllowRequest()

	cb.RecordFailure()
	if cb.State() != health.StateOpen {
		t.Errorf("expected open state after failure in half-open, got %v", cb.State())
	}
}

func TestCircuitBreakerReset(t *testing.T) {
	cb := health.NewCircuitBreaker(2, 5*time.Second)
	cb.RecordFailure()
	cb.RecordFailure()
	cb.Reset()

	if cb.State() != health.StateClosed {
		t.Error("should be closed after reset")
	}
	if cb.Failures() != 0 {
		t.Error("failures should be 0 after reset")
	}
}

func TestCircuitBreakerTrip(t *testing.T) {
	cb := health.NewCircuitBreaker(100, 5*time.Second)
	cb.Trip()

	if cb.State() != health.StateOpen {
		t.Error("should be open after trip")
	}
	if cb.AllowRequest() {
		t.Error("should not allow request after trip")
	}
}

func TestCircuitBreakerTimeUntilRetry(t *testing.T) {
	cb := health.NewCircuitBreaker(1, 100*time.Millisecond)
	cb.RecordFailure()

	tr := cb.TimeUntilRetry()
	if tr <= 0 {
		t.Error("TimeUntilRetry should be positive when open")
	}
	if tr > 100*time.Millisecond {
		t.Error("TimeUntilRetry should not exceed timeout")
	}
}

func TestCircuitBreakerTimeUntilRetryNotOpen(t *testing.T) {
	cb := health.NewCircuitBreaker(100, 5*time.Second)
	tr := cb.TimeUntilRetry()
	if tr != 0 {
		t.Error("TimeUntilRetry should be 0 when not open")
	}
}

func TestHTTPCheckerName(t *testing.T) {
	checker := health.NewHTTPChecker("test-http", "http://localhost:9999/health", 1*time.Second)
	if checker.Name() != "test-http" {
		t.Errorf("expected test-http, got %s", checker.Name())
	}
}

func TestTCPCheckerCheck(t *testing.T) {
	checker := health.NewTCPChecker("test-tcp", "localhost", 9999, 1*time.Second)
	err := checker.Check()
	if err == nil {
		t.Log("TCP check passed (port 9999 may be open)")
	}
}

func TestTCPCheckerName(t *testing.T) {
	checker := health.NewTCPChecker("test-tcp", "localhost", 9999, 1*time.Second)
	if checker.Name() != "test-tcp" {
		t.Errorf("expected test-tcp, got %s", checker.Name())
	}
}

func TestFileChecker(t *testing.T) {
	checker := health.NewFileChecker("test-file", "/tmp")
	err := checker.Check()
	if err != nil {
		t.Errorf("file check failed: %v", err)
	}
}

func TestFileCheckerMissing(t *testing.T) {
	checker := health.NewFileChecker("test-file", "/nonexistent/path")
	err := checker.Check()
	if err == nil {
		t.Error("expected error for missing file")
	}
}

func TestPortChecker(t *testing.T) {
	checker := health.NewPortChecker("test-port", "localhost", 9999)
	err := checker.Check()
	if err == nil {
		t.Log("Port check passed (port 9999 may be open)")
	}
}
