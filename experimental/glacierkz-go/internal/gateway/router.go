package gateway

import (
	"fmt"
	"net/http"
	"regexp"
	"strings"
	"sync"

	"github.com/glacierkz/glacierkz-go/internal/config"
)

type Route struct {
	Path       string
	Methods    []string
	Backend    string
	Prefix     string
	Rewrite    bool
	StripPath  string
	Headers    map[string]string
	Timeout    int
	MaxBody    int
}

type Router struct {
	routes    []Route
	mu        sync.RWMutex
	cfg       *config.Config
	compiled  map[string]*regexp.Regexp
}

func NewRouter(cfg *config.Config) *Router {
	r := &Router{
		routes:   make([]Route, 0),
		cfg:      cfg,
		compiled: make(map[string]*regexp.Regexp),
	}
	r.loadDefaults()
	return r
}

func (r *Router) loadDefaults() {
	backends := []string{r.cfg.Backend.BaseURL}

	for _, backend := range backends {
		r.AddRoute(Route{
			Path:    "/api/v1/glaciers",
			Methods: []string{"GET", "POST", "PUT", "DELETE", "PATCH"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/tasks",
			Methods: []string{"GET", "POST", "PUT", "DELETE"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/analysis",
			Methods: []string{"GET", "POST", "DELETE"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/export",
			Methods: []string{"GET", "POST"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/auth",
			Methods: []string{"POST"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/users",
			Methods: []string{"GET", "POST", "PUT"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/reports",
			Methods: []string{"GET", "POST"},
			Backend: backend,
			Prefix:  "/api/v1",
		})

		r.AddRoute(Route{
			Path:    "/ws",
			Methods: []string{"GET"},
			Backend: backend,
			Prefix:  "/",
		})

		r.AddRoute(Route{
			Path:       "/static",
			Methods:    []string{"GET"},
			Backend:    backend,
			Prefix:     "/static",
			StripPath:  "/static",
		})

		r.AddRoute(Route{
			Path:    "/api/v1/llm",
			Methods: []string{"POST"},
			Backend: backend,
			Prefix:  "/api/v1",
			Timeout: 60,
		})
	}
}

func (r *Router) AddRoute(route Route) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.routes = append(r.routes, route)
}

func (r *Router) Match(req *http.Request) (*Route, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	path := req.URL.Path
	method := req.Method

	for i := range r.routes {
		route := &r.routes[i]
		if r.matchesRoute(route, path, method) {
			return route, nil
		}
	}

	return nil, fmt.Errorf("no route found for %s %s", method, path)
}

func (r *Router) matchesRoute(route *Route, path, method string) bool {
	if !r.methodAllowed(route, method) {
		return false
	}
	return r.pathMatches(route, path)
}

func (r *Router) methodAllowed(route *Route, method string) bool {
	if len(route.Methods) == 0 {
		return true
	}
	for _, m := range route.Methods {
		if m == method {
			return true
		}
	}
	return false
}

func (r *Router) pathMatches(route *Route, path string) bool {
	if route.Path == "/" {
		return true
	}

	normalizedPath := strings.TrimSuffix(path, "/")
	normalizedRoute := strings.TrimSuffix(route.Path, "/")

	if normalizedPath == normalizedRoute {
		return true
	}

	if strings.HasPrefix(normalizedPath, normalizedRoute+"/") {
		return true
	}

	if strings.HasPrefix(path, "/ws") && strings.HasPrefix(route.Path, "/ws") {
		return true
	}

	return false
}

func (r *Router) Count() int {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return len(r.routes)
}

func (r *Router) ListRoutes() []Route {
	r.mu.RLock()
	defer r.mu.RUnlock()
	result := make([]Route, len(r.routes))
	copy(result, r.routes)
	return result
}

func (r *Router) RemoveRoute(path string) bool {
	r.mu.Lock()
	defer r.mu.Unlock()

	for i, route := range r.routes {
		if route.Path == path {
			r.routes = append(r.routes[:i], r.routes[i+1:]...)
			return true
		}
	}
	return false
}

func (r *Router) BackendForPath(path string) string {
	r.mu.RLock()
	defer r.mu.RUnlock()

	for i := range r.routes {
		if r.pathMatches(&r.routes[i], path) {
			return r.routes[i].Backend
		}
	}
	if r.cfg != nil {
		return r.cfg.Backend.BaseURL
	}
	return ""
}

func compilePattern(pattern string) (*regexp.Regexp, error) {
	escaped := regexp.QuoteMeta(pattern)
	escaped = strings.ReplaceAll(escaped, "\\*", ".*")
	escaped = strings.ReplaceAll(escaped, "\\{", "(")
	escaped = strings.ReplaceAll(escaped, "\\}", ")")
	return regexp.Compile("^" + escaped + "$")
}

func mergeHeaders(base, override map[string]string) map[string]string {
	result := make(map[string]string)
	for k, v := range base {
		result[k] = v
	}
	for k, v := range override {
		result[k] = v
	}
	return result
}
