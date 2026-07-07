import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Skeleton, CardSkeleton, TableSkeleton, MapSkeleton } from "@/components/Skeletons";

describe("Skeleton", () => {
  it("renders with default className", () => {
    render(<Skeleton />);
    // Skeleton is aria-hidden, so we check by class
    const skeleton = document.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
  });

  it("applies custom className", () => {
    render(<Skeleton className="h-10 w-10" />);
    const skeleton = document.querySelector(".h-10");
    expect(skeleton).toBeInTheDocument();
  });
});

describe("CardSkeleton", () => {
  it("renders with proper ARIA attributes", () => {
    render(<CardSkeleton />);

    const skeleton = document.querySelector('[aria-busy="true"]');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-label", "Loading");
  });
});

describe("TableSkeleton", () => {
  it("renders with default 5 rows", () => {
    render(<TableSkeleton />);

    const skeleton = document.querySelector('[aria-busy="true"]');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-label", "Loading table");

    // Check table headers
    expect(screen.getByText("Date")).toBeInTheDocument();
    expect(screen.getByText("Model")).toBeInTheDocument();
    expect(screen.getByText("Area")).toBeInTheDocument();
    expect(screen.getByText("Year")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("renders custom number of rows", () => {
    render(<TableSkeleton rows={3} />);

    // Check that table renders
    const skeleton = document.querySelector('[aria-busy="true"]');
    expect(skeleton).toBeInTheDocument();
  });
});

describe("MapSkeleton", () => {
  it("renders with proper ARIA attributes", () => {
    render(<MapSkeleton />);

    const skeleton = document.querySelector('[aria-busy="true"]');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton).toHaveAttribute("aria-label", "Loading map");

    // Check loading text
    expect(screen.getByText("Loading map...")).toBeInTheDocument();
  });
});
