"use client";

import { Component, type ReactNode, type ErrorInfo } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex min-h-[300px] flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 p-8 text-center">
          <AlertTriangle className="mb-4 h-10 w-10 text-red-500" aria-hidden="true" />
          <h2 className="mb-2 text-lg font-semibold text-red-700">Something went wrong</h2>
          <p className="mb-4 max-w-md text-sm text-red-600">
            {this.state.error?.message || "An unexpected error occurred."}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          >
            <RefreshCw className="h-4 w-4" />
            Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
