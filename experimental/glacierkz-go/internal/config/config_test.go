package config_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/glacierkz/glacierkz-go/internal/config"
)

func TestLoadConfigDefault(t *testing.T) {
	cfg, err := config.Load()
	if err != nil {
		t.Fatalf("failed to load default config: %v", err)
	}
	if cfg == nil {
		t.Fatal("config should not be nil")
	}
	if cfg.Server.Port != 8080 {
		t.Errorf("expected port 8080, got %d", cfg.Server.Port)
	}
}

func TestLoadConfigFromFile(t *testing.T) {
	dir := t.TempDir()
	yamlContent := `
server:
  host: "0.0.0.0"
  port: 9090
  read_timeout: 30
backend:
  base_url: "http://localhost:8081"
  timeout: 10
grpc:
  port: 9091
log:
  level: "debug"
`
	path := filepath.Join(dir, "config.yaml")
	err := os.WriteFile(path, []byte(yamlContent), 0644)
	if err != nil {
		t.Fatalf("failed to write config: %v", err)
	}

	cfg, err := config.Load(config.WithConfigFile(path))
	if err != nil {
		t.Fatalf("failed to load config: %v", err)
	}
	if cfg.Server.Port != 9090 {
		t.Errorf("expected port 9090, got %d", cfg.Server.Port)
	}
	if cfg.Backend.BaseURL != "http://localhost:8081" {
		t.Errorf("expected backend URL http://localhost:8081, got %s", cfg.Backend.BaseURL)
	}
	if cfg.Log.Level != "debug" {
		t.Errorf("expected log level debug, got %s", cfg.Log.Level)
	}
}

func TestLoadConfigFromEnv(t *testing.T) {
	os.Setenv("GLACIERKZ_SERVER_PORT", "7070")
	defer os.Unsetenv("GLACIERKZ_SERVER_PORT")

	cfg, err := config.Load()
	if err != nil {
		t.Fatalf("failed to load config from env: %v", err)
	}
	if cfg.Server.Port != 7070 {
		t.Errorf("expected port 7070 from env, got %d", cfg.Server.Port)
	}
}

func TestDefaultConfig(t *testing.T) {
	cfg := config.DefaultConfig()
	if cfg.Server.Port != 8080 {
		t.Errorf("expected default port 8080, got %d", cfg.Server.Port)
	}
	if cfg.Server.Host != "0.0.0.0" {
		t.Errorf("expected default host 0.0.0.0, got %s", cfg.Server.Host)
	}
	if cfg.Backend.BaseURL != "http://localhost:5000" {
		t.Errorf("expected default backend URL, got %s", cfg.Backend.BaseURL)
	}
	if cfg.Health.Interval != 30 {
		t.Errorf("expected health interval 30, got %d", cfg.Health.Interval)
	}
	if cfg.GRPC.Address != "localhost:9090" {
		t.Errorf("expected gRPC address localhost:9090, got %s", cfg.GRPC.Address)
	}
	if cfg.RateLimit.RequestsPerSecond != 100 {
		t.Errorf("expected rate limit 100, got %d", cfg.RateLimit.RequestsPerSecond)
	}
	if cfg.RateLimit.Burst != 200 {
		t.Errorf("expected burst 200, got %d", cfg.RateLimit.Burst)
	}
	if cfg.CORS.MaxAge != 3600 {
		t.Errorf("expected CORS max age 3600, got %d", cfg.CORS.MaxAge)
	}
}

func TestValidate(t *testing.T) {
	tests := []struct {
		name    string
		cfg     *config.Config
		wantErr bool
	}{
		{
			name:    "valid config",
			cfg:     config.DefaultConfig(),
			wantErr: false,
		},
		{
			name: "invalid port",
			cfg: func() *config.Config {
				cfg := config.DefaultConfig()
				cfg.Server.Port = -1
				return cfg
			}(),
			wantErr: true,
		},
		{
			name: "empty backend URL",
			cfg: func() *config.Config {
				cfg := config.DefaultConfig()
				cfg.Backend.BaseURL = ""
				return cfg
			}(),
			wantErr: true,
		},
		{
			name: "invalid log level",
			cfg: func() *config.Config {
				cfg := config.DefaultConfig()
				cfg.Log.Level = "invalid"
				return cfg
			}(),
			wantErr: true,
		},
		{
			name: "negative rate limit",
			cfg: func() *config.Config {
				cfg := config.DefaultConfig()
				cfg.RateLimit.RequestsPerSecond = -1
				return cfg
			}(),
			wantErr: true,
		},
		{
			name: "port too high",
			cfg: func() *config.Config {
				cfg := config.DefaultConfig()
				cfg.Server.Port = 99999
				return cfg
			}(),
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := config.Validate(tt.cfg)
			if (err != nil) != tt.wantErr {
				t.Errorf("Validate() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestConfigIsolation(t *testing.T) {
	cfg1 := config.DefaultConfig()
	cfg1.Server.Port = 1111

	cfg2 := config.DefaultConfig()
	cfg2.Server.Port = 2222

	if cfg1.Server.Port == cfg2.Server.Port {
		t.Error("configs should be independent")
	}
}
