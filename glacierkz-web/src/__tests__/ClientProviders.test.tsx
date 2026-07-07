import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ClientProviders from "@/app/providers";

function TestChild() {
  return <div data-testid="child">Test content</div>;
}

describe("ClientProviders", () => {
  it("renders children within providers", () => {
    render(
      <ClientProviders>
        <TestChild />
      </ClientProviders>
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByText("Test content")).toBeInTheDocument();
  });

  it("provides skip-to-content link", () => {
    render(
      <ClientProviders>
        <TestChild />
      </ClientProviders>
    );

    const skipLink = screen.getByText("Skip to content");
    expect(skipLink).toBeInTheDocument();
    expect(skipLink).toHaveAttribute("href", "#main-content");
  });

  it("skip link is hidden until focused", () => {
    render(
      <ClientProviders>
        <TestChild />
      </ClientProviders>
    );

    const skipLink = screen.getByText("Skip to content");
    // Should have sr-only class (visually hidden)
    expect(skipLink.className).toContain("sr-only");
  });
});
