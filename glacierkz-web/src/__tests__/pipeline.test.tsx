import { describe, it, expect } from "vitest";
import React from "react";
import { render, screen } from "@testing-library/react";
import PipelineStage from "@/components/PipelineStage";
import MetricGauge from "@/components/MetricGauge";
import ActivityFeed from "@/components/ActivityFeed";

describe("Pipeline Stage Visualization", () => {
  const stages = [
    { id: "1", name: "Data Ingestion", status: "completed" as const, progress: 100 },
    { id: "2", name: "Preprocessing", status: "running" as const, progress: 65 },
    { id: "3", name: "Analysis", status: "pending" as const, progress: 0 },
  ];

  it("renders pipeline stages horizontally", () => {
    render(<PipelineStage stages={stages} orientation="horizontal" />);
    expect(screen.getByText("Data Ingestion")).toBeDefined();
    expect(screen.getByText("Preprocessing")).toBeDefined();
    expect(screen.getByText("Analysis")).toBeDefined();
  });

  it("renders pipeline stages vertically", () => {
    render(<PipelineStage stages={stages} orientation="vertical" />);
    expect(screen.getByText("Data Ingestion")).toBeDefined();
  });

  it("shows overall progress", () => {
    render(<PipelineStage stages={stages} />);
    expect(screen.getByText(/33%|67%|100%/)).toBeDefined();
  });
});

describe("Pipeline Metrics", () => {
  it("renders pipeline performance gauges", () => {
    render(
      <div>
        <MetricGauge label="Throughput" value={850} max={1000} unit=" files/hr" format={(v) => String(v)} />
        <MetricGauge label="Error Rate" value={2} max={100} unit="%" format={(v) => String(v)} />
      </div>
    );
    expect(screen.getByText("Throughput")).toBeDefined();
    expect(screen.getByText("Error Rate")).toBeDefined();
  });
});

describe("Pipeline Activity", () => {
  it("renders pipeline activity feed", () => {
    render(
      <ActivityFeed
        items={[
          { id: "1", type: "process", title: "Pipeline run started", timestamp: new Date().toISOString() },
        ]}
        showFilter={false}
      />
    );
    expect(screen.getByText("Pipeline run started")).toBeDefined();
  });
});
