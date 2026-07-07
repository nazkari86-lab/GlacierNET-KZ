package health

import (
	"sync"
	"time"
)

type State int

const (
	StateClosed   State = iota
	StateOpen
	StateHalfOpen
)

func (s State) String() string {
	switch s {
	case StateClosed:
		return "closed"
	case StateOpen:
		return "open"
	case StateHalfOpen:
		return "half-open"
	default:
		return "unknown"
	}
}

type CircuitBreaker struct {
	failureThreshold int
	timeout          time.Duration
	state            State
	failures         int
	successes        int
	lastFailure      time.Time
	halfOpenMax      int
	mu               sync.RWMutex
}

func NewCircuitBreaker(failureThreshold int, timeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		failureThreshold: failureThreshold,
		timeout:          timeout,
		state:            StateClosed,
		halfOpenMax:      3,
	}
}

func (cb *CircuitBreaker) AllowRequest() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case StateClosed:
		return true
	case StateOpen:
		if time.Since(cb.lastFailure) > cb.timeout {
			cb.state = StateHalfOpen
			cb.successes = 0
			cb.failures = 0
			return true
		}
		return false
	case StateHalfOpen:
		return cb.successes < cb.halfOpenMax
	default:
		return false
	}
}

func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case StateHalfOpen:
		cb.successes++
		if cb.successes >= cb.halfOpenMax {
			cb.state = StateClosed
			cb.failures = 0
			cb.successes = 0
		}
	case StateClosed:
		cb.failures = 0
	}
}

func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	cb.failures++
	cb.lastFailure = time.Now()

	switch cb.state {
	case StateClosed:
		if cb.failures >= cb.failureThreshold {
			cb.state = StateOpen
		}
	case StateHalfOpen:
		cb.state = StateOpen
		cb.successes = 0
	}
}

func (cb *CircuitBreaker) State() State {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

func (cb *CircuitBreaker) Failures() int {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.failures
}

func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	cb.state = StateClosed
	cb.failures = 0
	cb.successes = 0
}

func (cb *CircuitBreaker) Trip() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	cb.state = StateOpen
	cb.lastFailure = time.Now()
}

func (cb *CircuitBreaker) IsOpen() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state == StateOpen
}

func (cb *CircuitBreaker) IsClosed() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state == StateClosed
}

func (cb *CircuitBreaker) IsHalfOpen() bool {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state == StateHalfOpen
}

func (cb *CircuitBreaker) TimeUntilRetry() time.Duration {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	if cb.state != StateOpen {
		return 0
	}
	elapsed := time.Since(cb.lastFailure)
	if elapsed >= cb.timeout {
		return 0
	}
	return cb.timeout - elapsed
}
