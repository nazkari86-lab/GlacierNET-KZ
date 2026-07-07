package gateway

import (
	"compress/gzip"
	"io"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/glacierkz/glacierkz-go/internal/config"
	"github.com/glacierkz/glacierkz-go/pkg/models"
)

type Middleware func(http.Handler) http.Handler

type MiddlewareChain struct {
	middlewares []Middleware
}

func NewMiddlewareChain(cfg *config.Config) *MiddlewareChain {
	chain := &MiddlewareChain{
		middlewares: make([]Middleware, 0),
	}

	chain.Use(RecoveryMiddleware)
	chain.Use(RequestIDMiddleware)
	chain.Use(LoggingMiddleware)
	chain.Use(CORSMiddleware(cfg))
	chain.Use(RateLimitMiddleware(cfg))
	chain.Use(AuthMiddleware(cfg))

	return chain
}

func (mc *MiddlewareChain) Use(mw Middleware) {
	mc.middlewares = append(mc.middlewares, mw)
}

func (mc *MiddlewareChain) Chain(handler http.Handler) http.Handler {
	for i := len(mc.middlewares) - 1; i >= 0; i-- {
		handler = mc.middlewares[i](handler)
	}
	return handler
}

type rateLimiter struct {
	mu       sync.Mutex
	tokens   float64
	maxRate  float64
	burst    int
	lastTime time.Time
}

func newRateLimiter(rps int, burst int) *rateLimiter {
	return &rateLimiter{
		tokens:  float64(burst),
		maxRate: float64(rps),
		burst:   burst,
		lastTime: time.Now(),
	}
}

func (rl *rateLimiter) allow() bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	now := time.Now()
	elapsed := now.Sub(rl.lastTime).Seconds()
	rl.tokens += elapsed * rl.maxRate
	if rl.tokens > float64(rl.burst) {
		rl.tokens = float64(rl.burst)
	}
	rl.lastTime = now

	if rl.tokens < 1 {
		return false
	}
	rl.tokens--
	return true
}

func RecoveryMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if rec := recover(); rec != nil {
				log.Printf("PANIC recovered: %v", rec)
				http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
			}
		}()
		next.ServeHTTP(w, r)
	})
}

func RequestIDMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		id := r.Header.Get("X-Request-ID")
		if id == "" {
			id = generateRequestID()
		}
		w.Header().Set("X-Request-ID", id)
		next.ServeHTTP(w, r)
	})
}

func LoggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		sw := &statusWriter{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(sw, r)
		elapsed := time.Since(start)
		log.Printf("%s %s %d %v %s", r.Method, r.URL.Path, sw.status, elapsed, r.RemoteAddr)
	})
}

type statusWriter struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (sw *statusWriter) WriteHeader(code int) {
	if !sw.wroteHeader {
		sw.status = code
		sw.wroteHeader = true
	}
	sw.ResponseWriter.WriteHeader(code)
}

func (sw *statusWriter) Write(b []byte) (int, error) {
	if !sw.wroteHeader {
		sw.wroteHeader = true
	}
	return sw.ResponseWriter.Write(b)
}

func CORSMiddleware(cfg *config.Config) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			allowed := false
			for _, o := range cfg.CORS.AllowedOrigins {
				if o == "*" || o == origin {
					allowed = true
					break
				}
			}

			if allowed {
				w.Header().Set("Access-Control-Allow-Origin", origin)
			}

			w.Header().Set("Access-Control-Allow-Methods", strings.Join(cfg.CORS.AllowedMethods, ", "))
			w.Header().Set("Access-Control-Allow-Headers", strings.Join(cfg.CORS.AllowedHeaders, ", "))
			w.Header().Set("Access-Control-Max-Age", itoa(cfg.CORS.MaxAge))

			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func AuthMiddleware(cfg *config.Config) Middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if len(cfg.Auth.APIKeys) == 0 {
				next.ServeHTTP(w, r)
				return
			}

			if isPublicPath(r.URL.Path) {
				next.ServeHTTP(w, r)
				return
			}

			apiKey := r.Header.Get("X-API-Key")
			if apiKey == "" {
				apiKey = r.URL.Query().Get("api_key")
			}

			if apiKey == "" {
				next.ServeHTTP(w, r)
				return
			}

			valid := false
			for _, k := range cfg.Auth.APIKeys {
				if k == apiKey {
					valid = true
					break
				}
			}

			if !valid {
				models.WriteJSON(w, http.StatusUnauthorized, models.NewErrorResponse(401, "Invalid API key", ""))
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}

func RateLimitMiddleware(cfg *config.Config) Middleware {
	limiter := newRateLimiter(cfg.RateLimit.RequestsPerSecond, cfg.RateLimit.Burst)

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if !limiter.allow() {
				w.Header().Set("Retry-After", "1")
				w.Header().Set("X-RateLimit-Limit", itoa(cfg.RateLimit.RequestsPerSecond))
				w.Header().Set("X-RateLimit-Remaining", "0")
				models.WriteJSON(w, http.StatusTooManyRequests, models.NewErrorResponse(429, "Rate limit exceeded", ""))
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

func CompressionMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") {
			next.ServeHTTP(w, r)
			return
		}

		w.Header().Set("Content-Encoding", "gzip")
		gz, err := gzip.NewWriterLevel(w, gzip.DefaultCompression)
		if err != nil {
			next.ServeHTTP(w, r)
			return
		}
		defer gz.Close()

		gzw := &gzipResponseWriter{Writer: gz, ResponseWriter: w}
		next.ServeHTTP(gzw, r)
	})
}

type gzipResponseWriter struct {
	io.Writer
	http.ResponseWriter
}

func (gzw *gzipResponseWriter) Write(b []byte) (int, error) {
	return gzw.Writer.Write(b)
}

func isPublicPath(path string) bool {
	publics := []string{"/health", "/healthz", "/ready", "/api/v1/public/"}
	for _, p := range publics {
		if strings.HasPrefix(path, p) {
			return true
		}
	}
	return false
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	if n < 0 {
		return "-" + itoa(-n)
	}
	digits := make([]byte, 0, 10)
	for n > 0 {
		digits = append([]byte{byte('0' + n%10)}, digits...)
		n /= 10
	}
	return string(digits)
}
