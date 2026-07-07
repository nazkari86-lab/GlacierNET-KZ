import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ConfirmationDialog from "@/components/ConfirmationDialog";
import SearchBar from "@/components/SearchBar";
import Breadcrumb from "@/components/Breadcrumb";
import UserAvatar from "@/components/UserAvatar";
import MetricGauge from "@/components/MetricGauge";
import ActivityFeed from "@/components/ActivityFeed";

describe("ConfirmationDialog", () => {
  it("renders with title and message", () => {
    render(
      <ConfirmationDialog open title="Delete Item" message="Are you sure?" onConfirm={vi.fn()} onCancel={vi.fn()} />
    );
    expect(screen.getByText("Delete Item")).toBeDefined();
    expect(screen.getByText("Are you sure?")).toBeDefined();
  });

  it("calls onConfirm when confirm clicked", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmationDialog
        open
        title="Confirm action"
        message="Proceed?"
        confirmLabel="Proceed"
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: "Proceed" }));
    expect(onConfirm).toHaveBeenCalled();
  });

  it("shows loading state", () => {
    render(
      <ConfirmationDialog open title="Delete" message="Sure?" onConfirm={vi.fn()} onCancel={vi.fn()} loading />
    );
    expect(screen.getByText("Processing...")).toBeDefined();
  });

  it("requires confirmation text", () => {
    render(
      <ConfirmationDialog
        open
        title="Delete"
        message="Type DELETE to confirm"
        requireConfirmation
        confirmationText="DELETE"
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />
    );
    const input = screen.getByPlaceholderText("DELETE");
    fireEvent.change(input, { target: { value: "wrong" } });
    const dialog = screen.getByRole("button", { name: "Confirm" });
    expect(dialog).toHaveProperty("disabled", true);
  });
});

describe("SearchBar", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("renders search input", () => {
    render(<SearchBar placeholder="Search..." onSearch={vi.fn()} debounceMs={0} />);
    expect(screen.getByPlaceholderText("Search...")).toBeDefined();
  });

  it("calls onSearch on input change", () => {
    const onSearch = vi.fn();
    render(<SearchBar placeholder="Search..." onSearch={onSearch} debounceMs={0} />);
    fireEvent.change(screen.getByPlaceholderText("Search..."), { target: { value: "test" } });
    vi.runAllTimers();
    expect(onSearch).toHaveBeenCalledWith("test");
  });

  it("displays suggestions", () => {
    render(
      <SearchBar
        placeholder="Search..."
        onSearch={vi.fn()}
        debounceMs={0}
        suggestions={[
          { id: "1", label: "Result 1", category: "Recent" },
          { id: "2", label: "Result 2", category: "Recent" },
        ]}
      />
    );
    fireEvent.focus(screen.getByPlaceholderText("Search..."));
    expect(screen.getByText("Result 1")).toBeDefined();
  });
});

describe("Breadcrumb", () => {
  it("renders breadcrumb items", () => {
    render(
      <Breadcrumb
        items={[
          { label: "Home", href: "/" },
          { label: "Admin", href: "/admin" },
          { label: "Users" },
        ]}
      />
    );
    expect(screen.getByText("Home")).toBeDefined();
    expect(screen.getByText("Admin")).toBeDefined();
    expect(screen.getByText("Users")).toBeDefined();
  });
});

describe("UserAvatar", () => {
  it("renders with user name", () => {
    render(<UserAvatar name="John Doe" />);
    expect(screen.getByText("JD")).toBeDefined();
  });

  it("renders with status indicator", () => {
    render(<UserAvatar name="John Doe" status="online" showStatus />);
    expect(screen.getByText("JD")).toBeDefined();
  });

  it("renders image when provided", () => {
    render(<UserAvatar name="John Doe" src="/avatar.jpg" />);
    expect(screen.getByRole("img")).toBeDefined();
  });
});

describe("MetricGauge", () => {
  it("renders with value", () => {
    render(<MetricGauge label="CPU" value={75} max={100} unit="%" />);
    expect(screen.getByText("CPU")).toBeDefined();
  });

  it("renders with different units", () => {
    render(<MetricGauge label="Memory" value={8} max={16} unit=" GB" format={(v) => String(v)} />);
    expect(screen.getByText("Memory")).toBeDefined();
  });
});

describe("ActivityFeed", () => {
  it("renders activities", () => {
    render(
      <ActivityFeed
        items={[
          {
            id: "1",
            type: "upload",
            title: "New dataset uploaded",
            timestamp: new Date().toISOString(),
          },
        ]}
        showFilter={false}
      />
    );
    expect(screen.getByText("New dataset uploaded")).toBeDefined();
  });

  it("shows empty state", () => {
    render(<ActivityFeed items={[]} showFilter={false} />);
    expect(screen.getByText("No activity")).toBeDefined();
  });
});
