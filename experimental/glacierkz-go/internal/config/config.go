package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/viper"
)

const (
	defaultConfigName = "glacierkz"
	defaultConfigType = "yaml"
	envPrefix         = "GLACIERKZ"
)

type configOptions struct {
	configPath string
}

type ConfigOption func(*configOptions)

func WithConfigFile(path string) ConfigOption {
	return func(opts *configOptions) {
		opts.configPath = path
	}
}

func Load(opts ...ConfigOption) (*Config, error) {
	cfg := DefaultConfig()

	options := &configOptions{}
	for _, opt := range opts {
		opt(options)
	}

	v := viper.New()
	v.SetConfigName(defaultConfigName)
	v.SetConfigType(defaultConfigType)
	v.AddConfigPath(".")
	v.AddConfigPath("$HOME/.glacierkz")
	v.AddConfigPath("/etc/glacierkz")

	v.SetEnvPrefix(envPrefix)
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	v.AutomaticEnv()

	if options.configPath != "" {
		absPath, err := filepath.Abs(options.configPath)
		if err != nil {
			return nil, fmt.Errorf("resolving config path: %w", err)
		}
		v.SetConfigFile(absPath)
	}

	setDefaults(v)

	if err := v.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return nil, fmt.Errorf("reading config file: %w", err)
		}
	}

	if err := v.Unmarshal(cfg); err != nil {
		return nil, fmt.Errorf("unmarshaling config: %w", err)
	}

	applyEnvOverrides(cfg)

	return cfg, nil
}

func setDefaults(v *viper.Viper) {
	v.SetDefault("server.host", "0.0.0.0")
	v.SetDefault("server.port", 8080)
	v.SetDefault("server.read_timeout", 30)
	v.SetDefault("server.write_timeout", 30)
	v.SetDefault("server.idle_timeout", 60)

	v.SetDefault("backend.base_url", "http://localhost:5000")
	v.SetDefault("backend.timeout", 10)
	v.SetDefault("backend.max_retries", 3)
	v.SetDefault("backend.retry_delay", 1)
	v.SetDefault("backend.max_conns", 100)

	v.SetDefault("health.interval", 30)
	v.SetDefault("health.timeout", 5)
	v.SetDefault("health.threshold", 3)

	v.SetDefault("grpc.address", "localhost:9090")
	v.SetDefault("grpc.timeout", 5)
	v.SetDefault("grpc.max_retries", 3)

	v.SetDefault("log.level", "info")
	v.SetDefault("log.format", "json")
	v.SetDefault("log.output", "stdout")

	v.SetDefault("rate_limit.requests_per_second", 100)
	v.SetDefault("rate_limit.burst", 200)

	v.SetDefault("cors.allowed_origins", []string{"*"})
	v.SetDefault("cors.allowed_methods", []string{"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"})
	v.SetDefault("cors.allowed_headers", []string{"Content-Type", "Authorization", "X-Request-ID"})
	v.SetDefault("cors.max_age", 3600)
}

func applyEnvOverrides(cfg *Config) {
	if v := os.Getenv("GLACIERKZ_SERVER_PORT"); v != "" {
		var port int
		if _, err := fmt.Sscanf(v, "%d", &port); err == nil {
			cfg.Server.Port = port
		}
	}
	if v := os.Getenv("GLACIERKZ_BACKEND_BASE_URL"); v != "" {
		cfg.Backend.BaseURL = v
	}
	if v := os.Getenv("GLACIERKZ_GRPC_ADDRESS"); v != "" {
		cfg.GRPC.Address = v
	}
	if v := os.Getenv("GLACIERKZ_AUTH_JWT_SECRET"); v != "" {
		cfg.Auth.JWTSecret = v
	}
	if v := os.Getenv("GLACIERKZ_LOG_LEVEL"); v != "" {
		cfg.Log.Level = v
	}
}

func Save(cfg *Config, path string) error {
	v := viper.New()
	v.Set("server", cfg.Server)
	v.Set("backend", cfg.Backend)
	v.Set("health", cfg.Health)
	v.Set("grpc", cfg.GRPC)
	v.Set("log", cfg.Log)
	v.Set("auth", cfg.Auth)
	v.Set("rate_limit", cfg.RateLimit)
	v.Set("cors", cfg.CORS)

	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("creating config directory: %w", err)
	}

	return v.WriteConfigAs(path)
}

func Validate(cfg *Config) error {
	if cfg.Server.Port < 1 || cfg.Server.Port > 65535 {
		return fmt.Errorf("invalid server port: %d", cfg.Server.Port)
	}
	if cfg.Backend.BaseURL == "" {
		return fmt.Errorf("backend base URL is required")
	}
	if cfg.Backend.MaxRetries < 0 {
		return fmt.Errorf("backend max retries must be non-negative")
	}
	if cfg.Health.Interval < 1 {
		return fmt.Errorf("health check interval must be positive")
	}
	if cfg.RateLimit.RequestsPerSecond < 1 {
		return fmt.Errorf("rate limit must be positive")
	}
	if cfg.Log.Level != "" &&
		cfg.Log.Level != "debug" &&
		cfg.Log.Level != "info" &&
		cfg.Log.Level != "warn" &&
		cfg.Log.Level != "error" {
		return fmt.Errorf("invalid log level: %s", cfg.Log.Level)
	}
	return nil
}
