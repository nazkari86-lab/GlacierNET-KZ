package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"github.com/glacierkz/glacierkz-go/internal/config"
)

var (
	cfgFile string
	cfg     *config.Config
	verbose bool
)

func initConfig() (*config.Config, error) {
	c, err := config.Load(config.WithConfigFile(cfgFile))
	if err != nil {
		return nil, fmt.Errorf("loading config: %w", err)
	}
	if err := config.Validate(c); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}
	return c, nil
}

func configDir() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return "."
	}
	return filepath.Join(home, ".glacierkz")
}

func ensureConfigDir() error {
	dir := configDir()
	return os.MkdirAll(dir, 0755)
}

func setupViper() {
	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		dir := configDir()
		viper.AddConfigPath(dir)
		viper.AddConfigPath(".")
		viper.SetConfigName("glacierkz")
		viper.SetConfigType("yaml")
	}
	viper.SetEnvPrefix("GLACIERKZ")
	viper.AutomaticEnv()
}

func addGlobalFlags(cmd *cobra.Command) {
	cmd.PersistentFlags().StringVar(&cfgFile, "config", "", "path to config file (default: $HOME/.glacierkz/glacierkz.yaml)")
	cmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "enable verbose output")
}

func marshalJSON(v any) ([]byte, error) {
	return json.MarshalIndent(v, "", "  ")
}

func printJSON(v any) error {
	data, err := marshalJSON(v)
	if err != nil {
		return err
	}
	fmt.Println(string(data))
	return nil
}

func printTable(headers []string, rows [][]string) {
	if len(headers) == 0 {
		return
	}
	widths := make([]int, len(headers))
	for i, h := range headers {
		widths[i] = len(h)
	}
	for _, row := range rows {
		for i, cell := range row {
			if i < len(widths) && len(cell) > widths[i] {
				widths[i] = len(cell)
			}
		}
	}
	format := ""
	for i, w := range widths {
		if i > 0 {
			format += "  "
		}
		format += fmt.Sprintf("%%-%ds", w)
	}
	format += "\n"

	fmt.Fprintf(os.Stdout, format, toAny(headers)...)
	for _, row := range rows {
		fmt.Fprintf(os.Stdout, format, toAny(row)...)
	}
}

func toAny(ss []string) []any {
	result := make([]any, len(ss))
	for i, s := range ss {
		result[i] = s
	}
	return result
}
