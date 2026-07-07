package health

import (
	"sync"
	"time"

	"github.com/glacierkz/glacierkz-go/internal/config"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

type Aggregator struct {
	config   *config.Config
	services map[string]*ServiceStatus
	mu       sync.RWMutex
	stopCh   chan struct{}
}

type ServiceStatus struct {
	Name      string                `json:"name"`
	Status    models.HealthStatus   `json:"status"`
	Message   string                `json:"message,omitempty"`
	LastCheck time.Time             `json:"last_check"`
	Latency   time.Duration         `json:"latency"`
	Checkers  []HealthChecker       `json:"-"`
	Breakers  map[string]*CircuitBreaker `json:"-"`
	mu        sync.RWMutex
}

func NewAggregator(cfg *config.Config) *Aggregator {
	agg := &Aggregator{
		config:   cfg,
		services: make(map[string]*ServiceStatus),
		stopCh:   make(chan struct{}),
	}
	agg.registerServices()
	return agg
}

func (a *Aggregator) registerServices() {
	services := []struct {
		name    string
		checker HealthChecker
	}{
		{"database", NewTCPChecker("database", "localhost", 5432, 5*time.Second)},
		{"redis", NewTCPChecker("redis", "localhost", 6379, 3*time.Second)},
		{"backend", NewHTTPChecker("backend", "http://localhost:8080/health", 5*time.Second)},
		{"grpc", NewGRPCChecker("grpc", "localhost:9090", 5*time.Second)},
		{"disk", NewDiskChecker("disk", "/", 90)},
	}

	for _, svc := range services {
		status := &ServiceStatus{
			Name:     svc.name,
			Status:   models.HealthStatusUnknown,
			Breakers: make(map[string]*CircuitBreaker),
		}
		status.Checkers = append(status.Checkers, svc.checker)
		status.Breakers[svc.name] = NewCircuitBreaker(5, 30*time.Second)
		a.services[svc.name] = status
	}
}

func (a *Aggregator) Start(interval time.Duration) {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	a.checkAll()
	for {
		select {
		case <-ticker.C:
			a.checkAll()
		case <-a.stopCh:
			return
		}
	}
}

func (a *Aggregator) Stop() {
	close(a.stopCh)
}

func (a *Aggregator) checkAll() {
	a.mu.Lock()
	defer a.mu.Unlock()

	for name, svc := range a.services {
		svc.mu.Lock()
		start := time.Now()

		breaker := svc.Breakers[name]
		if breaker != nil && !breaker.AllowRequest() {
			svc.Status = models.HealthStatusUnhealthy
			svc.Message = "circuit breaker open"
			svc.LastCheck = time.Now()
			svc.mu.Unlock()
			continue
		}

		healthy := true
		var lastErr error
		for _, checker := range svc.Checkers {
			if err := checker.Check(); err != nil {
				healthy = false
				lastErr = err
				break
			}
		}

		latency := time.Since(start)
		svc.Latency = latency
		svc.LastCheck = time.Now()

		if healthy {
			svc.Status = models.HealthStatusHealthy
			svc.Message = ""
			if breaker != nil {
				breaker.RecordSuccess()
			}
		} else {
			svc.Status = models.HealthStatusUnhealthy
			if lastErr != nil {
				svc.Message = lastErr.Error()
			}
			if breaker != nil {
				breaker.RecordFailure()
			}
		}
		svc.mu.Unlock()
	}
}

func (a *Aggregator) GetStatus() map[string]*ServiceStatus {
	a.mu.RLock()
	defer a.mu.RUnlock()
	result := make(map[string]*ServiceStatus)
	for k, v := range a.services {
		v.mu.RLock()
		status := &ServiceStatus{
			Name:      v.Name,
			Status:    v.Status,
			Message:   v.Message,
			LastCheck: v.LastCheck,
			Latency:   v.Latency,
			Checkers:  v.Checkers,
			Breakers:  v.Breakers,
		}
		v.mu.RUnlock()
		result[k] = status
	}
	return result
}

func (a *Aggregator) OverallStatus() models.HealthStatus {
	a.mu.RLock()
	defer a.mu.RUnlock()
	anyUnhealthy := false
	for _, svc := range a.services {
		svc.mu.RLock()
		switch svc.Status {
		case models.HealthStatusUnhealthy:
			svc.mu.RUnlock()
			return models.HealthStatusUnhealthy
		case models.HealthStatusDegraded:
			anyUnhealthy = true
		}
		svc.mu.RUnlock()
	}
	if anyUnhealthy {
		return models.HealthStatusDegraded
	}
	return models.HealthStatusHealthy
}

func (a *Aggregator) ServiceStatus(name string) (*ServiceStatus, bool) {
	a.mu.RLock()
	defer a.mu.RUnlock()
	svc, ok := a.services[name]
	if !ok {
		return nil, false
	}
	svc.mu.RLock()
	status := &ServiceStatus{
		Name:      svc.Name,
		Status:    svc.Status,
		Message:   svc.Message,
		LastCheck: svc.LastCheck,
		Latency:   svc.Latency,
		Checkers:  svc.Checkers,
		Breakers:  svc.Breakers,
	}
	svc.mu.RUnlock()
	return status, true
}
