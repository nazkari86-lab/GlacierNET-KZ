package gateway

import (
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/glacierkz/glacierkz-go/internal/config"
)

type Gateway struct {
	config     *config.Config
	router     *Router
	proxy      *ReverseProxy
	middleware *MiddlewareChain
	healthURL  string
	startTime  time.Time
	mu         sync.RWMutex
}

func New(cfg *config.Config) *Gateway {
	gw := &Gateway{
		config:    cfg,
		router:    NewRouter(cfg),
		startTime: time.Now(),
	}

	gw.proxy = NewReverseProxy(cfg)
	gw.middleware = NewMiddlewareChain(cfg)
	gw.healthURL = "/health"

	return gw
}

func (gw *Gateway) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	start := time.Now()

	if r.URL.Path == gw.healthURL || r.URL.Path == "/healthz" {
		gw.handleHealth(w, r)
		return
	}

	if r.URL.Path == "/ready" {
		gw.handleReady(w, r)
		return
	}

	handler := gw.middleware.Chain(http.HandlerFunc(gw.routeAndProxy))

	reqID := r.Header.Get("X-Request-ID")
	if reqID == "" {
		reqID = generateRequestID()
	}
	w.Header().Set("X-Request-ID", reqID)

	handler.ServeHTTP(w, r)

	elapsed := time.Since(start)
	log.Printf("[%s] %s %s %v", reqID, r.Method, r.URL.Path, elapsed)
}

func (gw *Gateway) routeAndProxy(w http.ResponseWriter, r *http.Request) {
	route, err := gw.router.Match(r)
	if err != nil {
		http.Error(w, `{"error":"no route matched","path":"`+r.URL.Path+`"}`, http.StatusBadGateway)
		return
	}

	gw.proxy.ProxyRequest(w, r, route)
}

func (gw *Gateway) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	uptime := time.Since(gw.startTime)
	resp := `{"status":"ok","uptime":"` + uptime.String() + `","service":"glacierkz-gateway"}`
	w.Write([]byte(resp))
}

func (gw *Gateway) handleReady(w http.ResponseWriter, r *http.Request) {
	if !gw.proxy.AllBackendsHealthy() {
		http.Error(w, `{"status":"not ready"}`, http.StatusServiceUnavailable)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"ready"}`))
}

func (gw *Gateway) Stats() GatewayStats {
	gw.mu.RLock()
	defer gw.mu.RUnlock()
	uptime := time.Since(gw.startTime)
	return GatewayStats{
		Uptime:   uptime,
		Routes:   gw.router.Count(),
		Backends: gw.proxy.BackendCount(),
	}
}

type GatewayStats struct {
	Uptime   time.Duration `json:"uptime"`
	Routes   int           `json:"routes"`
	Backends int           `json:"backends"`
}

func generateRequestID() string {
	return time.Now().Format("20060102150405.000000000")
}

func sanitizePath(path string) string {
	path = strings.TrimPrefix(path, "/")
	segments := strings.Split(path, "/")
	cleaned := make([]string, 0, len(segments))
	for _, s := range segments {
		if s != "" && s != "." && s != ".." {
			cleaned = append(cleaned, s)
		}
	}
	return "/" + strings.Join(cleaned, "/")
}
