package gateway

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"sync"
	"time"

	"github.com/glacierkz/glacierkz-go/internal/config"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

type Backend struct {
	URL           *url.URL
	Alive         bool
	Weight        int
	Connections   int
	LastHealth    time.Time
	ResponseTimes []time.Duration
	mu            sync.RWMutex
}

func (b *Backend) IsAlive() bool {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.Alive
}

func (b *Backend) SetAlive(alive bool) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.Alive = alive
}

func (b *Backend) RecordResponse(d time.Duration) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.ResponseTimes = append(b.ResponseTimes, d)
	if len(b.ResponseTimes) > 100 {
		b.ResponseTimes = b.ResponseTimes[len(b.ResponseTimes)-100:]
	}
}

func (b *Backend) AvgResponseTime() time.Duration {
	b.mu.RLock()
	defer b.mu.RUnlock()
	if len(b.ResponseTimes) == 0 {
		return 0
	}
	var total time.Duration
	for _, d := range b.ResponseTimes {
		total += d
	}
	return total / time.Duration(len(b.ResponseTimes))
}

type ReverseProxy struct {
	backends  []*Backend
	config    *config.Config
	transport *http.Transport
	mu        sync.RWMutex
	startTime time.Time
	totalReq  int64
}

func NewReverseProxy(cfg *config.Config) *ReverseProxy {
	rp := &ReverseProxy{
		config: cfg,
		transport: &http.Transport{
			MaxIdleConns:        cfg.Backend.MaxConns,
			MaxIdleConnsPerHost: cfg.Backend.MaxConns / 2,
			IdleConnTimeout:     90 * time.Second,
			DisableCompression:  false,
			DisableKeepAlives:   false,
		},
		startTime: time.Now(),
	}

	rp.loadBackends()
	return rp
}

func (rp *ReverseProxy) loadBackends() {
	rawURL, err := url.Parse(rp.config.Backend.BaseURL)
	if err != nil {
		log.Printf("Invalid backend URL %s: %v", rp.config.Backend.BaseURL, err)
		return
	}

	rp.backends = append(rp.backends, &Backend{
		URL:    rawURL,
		Alive:  true,
		Weight: 100,
	})
}

func (rp *ReverseProxy) ProxyRequest(w http.ResponseWriter, r *http.Request, route *Route) {
	backend := rp.selectBackend()
	if backend == nil {
		models.WriteJSON(w, http.StatusBadGateway, models.NewErrorResponse(502, "No healthy backends", ""))
		return
	}

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = backend.URL.Scheme
			req.URL.Host = backend.URL.Host

			if route.StripPath != "" {
				req.URL.Path = strings.TrimPrefix(req.URL.Path, route.StripPath)
			}

			req.Header.Set("X-Forwarded-For", r.RemoteAddr)
			req.Header.Set("X-Forwarded-Host", r.Host)
			req.Header.Set("X-Gateway-Backend", backend.URL.String())

			if route.Headers != nil {
				for k, v := range route.Headers {
					req.Header.Set(k, v)
				}
			}
		},
		Transport:      rp.transport,
		BufferPool:     newBufferPool(),
		ModifyResponse: rp.modifyResponse(backend),
		ErrorHandler:   rp.errorHandler(w, r, backend),
	}

	backend.mu.Lock()
	backend.Connections++
	backend.mu.Unlock()

	start := time.Now()
	proxy.ServeHTTP(w, r)
	elapsed := time.Since(start)

	backend.mu.Lock()
	backend.Connections--
	backend.mu.Unlock()

	backend.RecordResponse(elapsed)
	rp.mu.Lock()
	rp.totalReq++
	rp.mu.Unlock()
}

func (rp *ReverseProxy) selectBackend() *Backend {
	rp.mu.RLock()
	defer rp.mu.RUnlock()

	var best *Backend
	bestScore := -1.0

	for _, b := range rp.backends {
		if !b.IsAlive() {
			continue
		}
		score := rp.scoreBackend(b)
		if score > bestScore {
			bestScore = score
			best = b
		}
	}

	return best
}

func (rp *ReverseProxy) scoreBackend(b *Backend) float64 {
	b.mu.RLock()
	defer b.mu.RUnlock()

	score := float64(b.Weight)
	avgRT := b.AvgResponseTime()
	if avgRT > 0 {
		score /= avgRT.Seconds()
	}
	score -= float64(b.Connections) * 0.5
	return score
}

func (rp *ReverseProxy) modifyResponse(b *Backend) func(*http.Response) error {
	return func(resp *http.Response) error {
		resp.Header.Set("X-Backend-Host", b.URL.Host)

		if resp.StatusCode >= 500 {
			b.SetAlive(false)
			go rp.recoverBackend(b)
		}

		return nil
	}
}

func (rp *ReverseProxy) errorHandler(w http.ResponseWriter, r *http.Request, b *Backend) func(http.ResponseWriter, *http.Request, error) {
	return func(w http.ResponseWriter, r *http.Request, err error) {
		log.Printf("Proxy error for %s: %v", b.URL.String(), err)
		b.SetAlive(false)
		go rp.recoverBackend(b)

		retryBackend := rp.selectBackend()
		if retryBackend != nil && retryBackend.URL.String() != b.URL.String() {
			log.Printf("Retrying on %s", retryBackend.URL.String())
			proxy := &httputil.ReverseProxy{
				Director: func(req *http.Request) {
					req.URL.Scheme = retryBackend.URL.Scheme
					req.URL.Host = retryBackend.URL.Host
				},
				Transport: rp.transport,
			}
			proxy.ServeHTTP(w, r)
			return
		}

		models.WriteJSON(w, http.StatusBadGateway, models.NewErrorResponse(502, "Backend unavailable", err.Error()))
	}
}

func (rp *ReverseProxy) recoverBackend(b *Backend) {
	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()

	maxAttempts := 30
	for i := 0; i < maxAttempts; i++ {
		<-ticker.C
		if rp.healthCheck(b) {
			b.SetAlive(true)
			log.Printf("Backend %s recovered", b.URL.String())
			return
		}
	}
	log.Printf("Backend %s failed to recover after %d attempts", b.URL.String(), maxAttempts)
}

func (rp *ReverseProxy) healthCheck(b *Backend) bool {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	checkURL := b.URL.String() + "/health"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, checkURL, nil)
	if err != nil {
		return false
	}

	resp, err := rp.transport.RoundTrip(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	io.Copy(io.Discard, resp.Body)
	return resp.StatusCode == http.StatusOK
}

func (rp *ReverseProxy) AllBackendsHealthy() bool {
	rp.mu.RLock()
	defer rp.mu.RUnlock()
	for _, b := range rp.backends {
		if !b.IsAlive() {
			return false
		}
	}
	return true
}

func (rp *ReverseProxy) BackendCount() int {
	rp.mu.RLock()
	defer rp.mu.RUnlock()
	return len(rp.backends)
}

type bufferPool struct {
	pool sync.Pool
}

func newBufferPool() *bufferPool {
	return &bufferPool{
		pool: sync.Pool{
			New: func() any {
				buf := make([]byte, 32*1024)
				return &buf
			},
		},
	}
}

func (bp *bufferPool) Get() []byte {
	return *bp.pool.Get().(*[]byte)
}

func (bp *bufferPool) Put(buf []byte) {
	bp.pool.Put(&buf)
}

func FormatBackendURL(host string, port int) string {
	return fmt.Sprintf("http://%s:%d", host, port)
}
