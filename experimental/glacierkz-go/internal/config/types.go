package config

type Config struct {
	Server   ServerConfig   `yaml:"server" mapstructure:"server"`
	Backend  BackendConfig  `yaml:"backend" mapstructure:"backend"`
	Health   HealthConfig   `yaml:"health" mapstructure:"health"`
	GRPC     GRPCConfig     `yaml:"grpc" mapstructure:"grpc"`
	Log      LogConfig      `yaml:"log" mapstructure:"log"`
	Auth     AuthConfig     `yaml:"auth" mapstructure:"auth"`
	RateLimit RateLimitConfig `yaml:"rate_limit" mapstructure:"rate_limit"`
	CORS     CORSConfig     `yaml:"cors" mapstructure:"cors"`
}

type ServerConfig struct {
	Host         string `yaml:"host" mapstructure:"host"`
	Port         int    `yaml:"port" mapstructure:"port"`
	ReadTimeout  int    `yaml:"read_timeout" mapstructure:"read_timeout"`
	WriteTimeout int    `yaml:"write_timeout" mapstructure:"write_timeout"`
	IdleTimeout  int    `yaml:"idle_timeout" mapstructure:"idle_timeout"`
}

type BackendConfig struct {
	BaseURL      string `yaml:"base_url" mapstructure:"base_url"`
	Timeout      int    `yaml:"timeout" mapstructure:"timeout"`
	MaxRetries   int    `yaml:"max_retries" mapstructure:"max_retries"`
	RetryDelay   int    `yaml:"retry_delay" mapstructure:"retry_delay"`
	MaxConns     int    `yaml:"max_conns" mapstructure:"max_conns"`
}

type HealthConfig struct {
	Interval    int    `yaml:"interval" mapstructure:"interval"`
	Timeout     int    `yaml:"timeout" mapstructure:"timeout"`
	Threshold   int    `yaml:"threshold" mapstructure:"threshold"`
	Services    []HealthServiceConfig `yaml:"services" mapstructure:"services"`
}

type HealthServiceConfig struct {
	Name    string `yaml:"name" mapstructure:"name"`
	URL     string `yaml:"url" mapstructure:"url"`
	Type    string `yaml:"type" mapstructure:"type"`
	Timeout int    `yaml:"timeout" mapstructure:"timeout"`
}

type GRPCConfig struct {
	Address        string `yaml:"address" mapstructure:"address"`
	Timeout        int    `yaml:"timeout" mapstructure:"timeout"`
	MaxRetries     int    `yaml:"max_retries" mapstructure:"max_retries"`
	MaxMsgSize     int    `yaml:"max_msg_size" mapstructure:"max_msg_size"`
}

type LogConfig struct {
	Level  string `yaml:"level" mapstructure:"level"`
	Format string `yaml:"format" mapstructure:"format"`
	Output string `yaml:"output" mapstructure:"output"`
}

type AuthConfig struct {
	JWTSecret     string `yaml:"jwt_secret" mapstructure:"jwt_secret"`
	TokenExpiry   int    `yaml:"token_expiry" mapstructure:"token_expiry"`
	APIKeys       []string `yaml:"api_keys" mapstructure:"api_keys"`
}

type RateLimitConfig struct {
	RequestsPerSecond int `yaml:"requests_per_second" mapstructure:"requests_per_second"`
	Burst             int `yaml:"burst" mapstructure:"burst"`
}

type CORSConfig struct {
	AllowedOrigins []string `yaml:"allowed_origins" mapstructure:"allowed_origins"`
	AllowedMethods []string `yaml:"allowed_methods" mapstructure:"allowed_methods"`
	AllowedHeaders []string `yaml:"allowed_headers" mapstructure:"allowed_headers"`
	MaxAge         int      `yaml:"max_age" mapstructure:"max_age"`
}

func DefaultConfig() *Config {
	return &Config{
		Server: ServerConfig{
			Host:         "0.0.0.0",
			Port:         8080,
			ReadTimeout:  30,
			WriteTimeout: 30,
			IdleTimeout:  60,
		},
		Backend: BackendConfig{
			BaseURL:    "http://localhost:5000",
			Timeout:    10,
			MaxRetries: 3,
			RetryDelay: 1,
			MaxConns:   100,
		},
		Health: HealthConfig{
			Interval:  30,
			Timeout:   5,
			Threshold: 3,
		},
		GRPC: GRPCConfig{
			Address:    "localhost:9090",
			Timeout:    5,
			MaxRetries: 3,
			MaxMsgSize: 4 * 1024 * 1024,
		},
		Log: LogConfig{
			Level:  "info",
			Format: "json",
			Output: "stdout",
		},
		RateLimit: RateLimitConfig{
			RequestsPerSecond: 100,
			Burst:             200,
		},
		CORS: CORSConfig{
			AllowedOrigins: []string{"*"},
			AllowedMethods: []string{"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"},
			AllowedHeaders: []string{"Content-Type", "Authorization", "X-Request-ID"},
			MaxAge:         3600,
		},
	}
}

func (c *Config) ListenAddr() string {
	return c.Server.Host + ":" + itoa(c.Server.Port)
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
