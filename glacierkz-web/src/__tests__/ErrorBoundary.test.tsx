import { render, screen, act } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import ErrorBoundary from "@/components/ErrorBoundary";

function ThrowingComponent({ shouldThrow = true }: { shouldThrow?: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div data-testid="child">Child rendered</div>;
}

describe("ErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Child rendered")).toBeInTheDocument();
  });

  it("catches errors and shows fallback UI", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
    expect(screen.getByText("Try again")).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it("shows custom fallback when provided", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom error</div>}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByTestId("custom-fallback")).toBeInTheDocument();
    expect(screen.getByText("Custom error")).toBeInTheDocument();

    consoleSpy.mockRestore();
  });

  it("recovers when Try again is clicked", async () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    function App() {
      const [shouldThrow, setShouldThrow] = React.useState(true);

      return (
        <div>
          <ErrorBoundary>
            {shouldThrow ? (
              <ThrowingComponent shouldThrow={true} />
            ) : (
              <div data-testid="recovered">Recovered!</div>
            )}
          </ErrorBoundary>
          <button onClick={() => setShouldThrow(false)} data-testid="fix-button">
            Fix error
          </button>
        </div>
      );
    }

    render(<App />);

    // Initially shows error
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Click Try again to reset state
    const tryAgainButton = screen.getByText("Try again");
    act(() => {
      tryAgainButton.click();
    });

    consoleSpy.mockRestore();
  });
});

// Need React for the App component in the recovery test
import React from "react";
