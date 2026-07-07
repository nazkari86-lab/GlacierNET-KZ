import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import { MetricGaugeBar } from "@/components/MetricGauge";
import ActivityFeed from "@/components/ActivityFeed";
import UserAvatar from "@/components/UserAvatar";
import Breadcrumb from "@/components/Breadcrumb";

describe("Admin Components", () => {
  describe("MetricGaugeBar", () => {
    it("renders with value", () => {
      render(<MetricGaugeBar label="CPU Usage" value={75} max={100} unit="%" />);
      expect(screen.getByText("CPU Usage")).toBeDefined();
      expect(screen.getByText("75.0% (75%)")).toBeDefined();
    });

    it("renders with format function", () => {
      render(
        <MetricGaugeBar
          label="Storage"
          value={1073741824}
          max={2147483648}
          format={(v) => (v < 1024 ** 3 ? `${(v / 1024 ** 2).toFixed(0)} MB` : `${(v / 1024 ** 3).toFixed(1)} GB`)}
          showPercentage
        />
      );
      expect(screen.getByText("Storage")).toBeDefined();
    });
  });

  describe("ActivityFeed", () => {
    it("renders activities", () => {
      render(
        <ActivityFeed
          items={[
            { id: "1", type: "alert", title: "Dataset uploaded by admin", timestamp: new Date().toISOString() },
            { id: "2", type: "system", title: "User logged in", timestamp: new Date().toISOString() },
          ]}
          compact
          showFilter={false}
        />
      );
      expect(screen.getByText("Dataset uploaded by admin")).toBeDefined();
      expect(screen.getByText("User logged in")).toBeDefined();
    });

    it("shows empty state", () => {
      render(<ActivityFeed items={[]} showFilter={false} />);
      expect(screen.getByText("No activity")).toBeDefined();
    });
  });

  describe("UserAvatar", () => {
    it("renders initials", () => {
      render(<UserAvatar name="Admin User" />);
      expect(screen.getByText("AU")).toBeDefined();
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

  describe("Breadcrumb", () => {
    it("renders admin breadcrumb", () => {
      render(
        <Breadcrumb
          items={[
            { label: "Admin", href: "/admin" },
            { label: "Users" },
          ]}
        />
      );
      expect(screen.getByText("Admin")).toBeDefined();
      expect(screen.getByText("Users")).toBeDefined();
    });
  });
});
