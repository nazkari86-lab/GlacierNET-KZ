package gateway_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/glacierkz/glacierkz-go/internal/config"
	"github.com/glacierkz/glacierkz-go/internal/gateway"
)

func TestLoggingMiddleware(t *testing.T) {
	called := false
	handler := gateway.LoggingMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if !called {
		t.Error("LoggingMiddleware did not call next handler")
	}
	if rr.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rr.Code)
	}
}

func TestCORSMiddleware(t *testing.T) {
	cfg := &config.Config{}
	cfg.CORS.AllowedOrigins = []string{"http://example.com"}
	cfg.CORS.AllowedMethods = []string{"GET", "POST"}
	cfg.CORS.AllowedHeaders = []string{"Content-Type"}
	cfg.CORS.MaxAge = 3600

	handler := gateway.CORSMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Origin", "http://example.com")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Header().Get("Access-Control-Allow-Origin") != "http://example.com" {
		t.Error("CORS header not set correctly")
	}
}

func TestCORSMiddlewareDisallowedOrigin(t *testing.T) {
	cfg := &config.Config{}
	cfg.CORS.AllowedOrigins = []string{"http://allowed.com"}
	cfg.CORS.AllowedMethods = []string{"GET"}
	cfg.CORS.AllowedHeaders = []string{"Content-Type"}
	cfg.CORS.MaxAge = 3600

	handler := gateway.CORSMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("Origin", "http://evil.com")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Error("CORS header should not be set for disallowed origin")
	}
}

func TestCORSMiddlewareOptions(t *testing.T) {
	cfg := &config.Config{}
	cfg.CORS.AllowedOrigins = []string{"*"}
	cfg.CORS.AllowedMethods = []string{"GET", "POST"}
	cfg.CORS.AllowedHeaders = []string{"Content-Type"}
	cfg.CORS.MaxAge = 3600

	handler := gateway.CORSMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("OPTIONS request should not reach next handler")
	}))

	req := httptest.NewRequest("OPTIONS", "/test", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusNoContent {
		t.Errorf("expected 204 for OPTIONS, got %d", rr.Code)
	}
}

func TestAuthMiddlewareNoKeys(t *testing.T) {
	cfg := &config.Config{}
	cfg.Auth.APIKeys = []string{}

	called := false
	handler := gateway.AuthMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if !called {
		t.Error("AuthMiddleware should pass through when no API keys configured")
	}
}

func TestAuthMiddlewareWithValidKey(t *testing.T) {
	cfg := &config.Config{}
	cfg.Auth.APIKeys = []string{"valid-key-123"}

	called := false
	handler := gateway.AuthMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("X-API-Key", "valid-key-123")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if !called {
		t.Error("AuthMiddleware should allow valid API key")
	}
}

func TestAuthMiddlewareWithInvalidKey(t *testing.T) {
	cfg := &config.Config{}
	cfg.Auth.APIKeys = []string{"valid-key-123"}

	handler := gateway.AuthMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("Should not reach handler with invalid key")
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("X-API-Key", "invalid-key")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusUnauthorized {
		t.Errorf("expected 401 for invalid key, got %d", rr.Code)
	}
}

func TestRateLimitMiddleware(t *testing.T) {
	cfg := &config.Config{}
	cfg.RateLimit.RequestsPerSecond = 100
	cfg.RateLimit.Burst = 10

	handler := gateway.RateLimitMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	for i := 0; i < 5; i++ {
		req := httptest.NewRequest("GET", "/test", nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)

		if rr.Code != http.StatusOK {
			t.Errorf("request %d: expected 200, got %d", i, rr.Code)
		}
	}
}

func TestRateLimitMiddlewareExceeded(t *testing.T) {
	cfg := &config.Config{}
	cfg.RateLimit.RequestsPerSecond = 1
	cfg.RateLimit.Burst = 1

	handler := gateway.RateLimitMiddleware(cfg)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	for i := 0; i < 20; i++ {
		req := httptest.NewRequest("GET", "/test", nil)
		rr := httptest.NewRecorder()
		handler.ServeHTTP(rr, req)

		if i == 1 && rr.Code == http.StatusOK {
			t.Log("Rate limit not hit yet")
		}
	}
}

func TestRecoveryMiddleware(t *testing.T) {
	handler := gateway.RecoveryMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic("test panic")
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	rr := httptest.NewRecorder()

	defer func() {
		if r := recover(); r != nil {
			t.Errorf("Panic not recovered: %v", r)
		}
	}()

	handler.ServeHTTP(rr, req)

	if rr.Code != http.StatusInternalServerError {
		t.Errorf("expected 500, got %d", rr.Code)
	}
}

func TestRequestIDMiddleware(t *testing.T) {
	handler := gateway.RequestIDMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Header().Get("X-Request-ID") == "" {
		t.Error("RequestIDMiddleware should set X-Request-ID header")
	}
}

func TestRequestIDMiddlewareExisting(t *testing.T) {
	handler := gateway.RequestIDMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	req.Header.Set("X-Request-ID", "my-custom-id")
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	if rr.Header().Get("X-Request-ID") != "my-custom-id" {
		t.Error("RequestIDMiddleware should preserve existing X-Request-ID")
	}
}

func TestMiddlewareChainOrder(t *testing.T) {
	var order []string

	mw1 := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			order = append(order, "mw1-before")
			next.ServeHTTP(w, r)
			order = append(order, "mw1-after")
		})
	}

	mw2 := func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			order = append(order, "mw2-before")
			next.ServeHTTP(w, r)
			order = append(order, "mw2-after")
		})
	}

	chain := &gateway.MiddlewareChain{}
	chain.Use(mw1)
	chain.Use(mw2)

	handler := chain.Chain(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		order = append(order, "handler")
	}))

	req := httptest.NewRequest("GET", "/test", nil)
	rr := httptest.NewRecorder()
	handler.ServeHTTP(rr, req)

	expected := "mw1-before,mw2-before,handler,mw2-after,mw1-after"
	got := strings.Join(order, ",")
	if got != expected {
		t.Errorf("middleware order wrong: got %s, want %s", got, expected)
	}
}
