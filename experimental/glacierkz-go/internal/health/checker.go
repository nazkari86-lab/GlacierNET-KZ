package health

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"os"
	"strconv"
	"syscall"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

type HealthChecker interface {
	Check() error
	Name() string
}

type HTTPChecker struct {
	name    string
	url     string
	timeout time.Duration
	client  *http.Client
}

func NewHTTPChecker(name, url string, timeout time.Duration) *HTTPChecker {
	return &HTTPChecker{
		name:    name,
		url:     url,
		timeout: timeout,
		client: &http.Client{
			Timeout: timeout,
			CheckRedirect: func(req *http.Request, via []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
	}
}

func (h *HTTPChecker) Check() error {
	ctx, cancel := context.WithTimeout(context.Background(), h.timeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, h.url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := h.client.Do(req)
	if err != nil {
		return fmt.Errorf("HTTP check failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		return fmt.Errorf("HTTP check returned status %d", resp.StatusCode)
	}

	return nil
}

func (h *HTTPChecker) Name() string {
	return h.name
}

type TCPChecker struct {
	name    string
	host    string
	port    int
	timeout time.Duration
}

func NewTCPChecker(name, host string, port int, timeout time.Duration) *TCPChecker {
	return &TCPChecker{
		name:    name,
		host:    host,
		port:    port,
		timeout: timeout,
	}
}

func (t *TCPChecker) Check() error {
	addr := net.JoinHostPort(t.host, strconv.Itoa(t.port))
	conn, err := net.DialTimeout("tcp", addr, t.timeout)
	if err != nil {
		return fmt.Errorf("TCP check failed for %s: %w", addr, err)
	}
	conn.Close()
	return nil
}

func (t *TCPChecker) Name() string {
	return t.name
}

type GRPCChecker struct {
	name    string
	addr    string
	timeout time.Duration
}

func NewGRPCChecker(name, addr string, timeout time.Duration) *GRPCChecker {
	return &GRPCChecker{
		name:    name,
		addr:    addr,
		timeout: timeout,
	}
}

func (g *GRPCChecker) Check() error {
	ctx, cancel := context.WithTimeout(context.Background(), g.timeout)
	defer cancel()

	conn, err := grpc.DialContext(ctx, g.addr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
		grpc.WithBlock(),
	)
	if err != nil {
		return fmt.Errorf("gRPC check failed for %s: %w", g.addr, err)
	}
	conn.Close()
	return nil
}

func (g *GRPCChecker) Name() string {
	return g.name
}

type DiskChecker struct {
	name       string
	path       string
	maxPercent int
}

func NewDiskChecker(name, path string, maxPercent int) *DiskChecker {
	return &DiskChecker{
		name:       name,
		path:       path,
		maxPercent: maxPercent,
	}
}

func (d *DiskChecker) Check() error {
	var stat syscall.Statfs_t
	if err := syscall.Statfs(d.path, &stat); err != nil {
		return fmt.Errorf("disk check failed: %w", err)
	}

	total := stat.Blocks
	free := stat.Bavail
	if total == 0 {
		return nil
	}

	usedPercent := int(((total - free) * 100) / total)
	if usedPercent > d.maxPercent {
		return fmt.Errorf("disk usage %d%% exceeds threshold %d%%", usedPercent, d.maxPercent)
	}

	return nil
}

func (d *DiskChecker) Name() string {
	return d.name
}

type FileChecker struct {
	name string
	path string
}

func NewFileChecker(name, path string) *FileChecker {
	return &FileChecker{name: name, path: path}
}

func (f *FileChecker) Check() error {
	_, err := os.Stat(f.path)
	if err != nil {
		return fmt.Errorf("file check failed for %s: %w", f.path, err)
	}
	return nil
}

func (f *FileChecker) Name() string {
	return f.name
}

type PortChecker struct {
	name string
	host string
	port int
}

func NewPortChecker(name, host string, port int) *PortChecker {
	return &PortChecker{name: name, host: host, port: port}
}

func (p *PortChecker) Check() error {
	addr := net.JoinHostPort(p.host, strconv.Itoa(p.port))
	conn, err := net.DialTimeout("tcp", addr, 3*time.Second)
	if err != nil {
		return fmt.Errorf("port check failed for %s: %w", addr, err)
	}
	conn.Close()
	return nil
}

func (p *PortChecker) Name() string {
	return p.name
}
