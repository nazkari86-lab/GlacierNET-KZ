package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var version = "0.1.0"

func main() {
	rootCmd := newRootCmd()
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func newRootCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:     "gzcli",
		Short:   "GlacierNET-KZ CLI — glacier monitoring and analysis tool",
		Version: version,
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	cmd.AddCommand(
		newServeCmd(),
		newAnalyzeCmd(),
		newWatchCmd(),
		newExportCmd(),
		newStatusCmd(),
	)

	return cmd
}
