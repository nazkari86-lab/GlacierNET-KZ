import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import EvidenceInspector from "@/components/risk-twin/EvidenceInspector";
import EvidenceIssueQueue from "@/components/risk-twin/EvidenceIssueQueue";
import type { EvidenceIssue, EvidenceMapObject } from "@/lib/riskTwinEvidence";

const lakeObject: EvidenceMapObject = {
  id: "lake:TS-001",
  kind: "lake",
  name: "Lake ID: TS-001",
  geometry: { type: "Point", coordinates: [77.081, 43.051] } as GeoJSON.Point,
  source: "Tien Shan lake inventory",
  temporalCoverage: "2023",
  maturity: "spatial_context",
  visibleFact: "Контур воды виден в локальном инвентаре.",
  allowedClaim: "Можно показать контур и дату инвентаря.",
  prohibitedClaim: "Контур воды не является прогнозом опасности.",
  inspectorFacts: [{ label: "Lake ID", value: "TS-001" }],
};

const outletIssue: EvidenceIssue = {
  id: "gap-outlet_capacity_fraction",
  objectId: "lake:TS-001",
  decisionImpact: "high",
  title: "Пропускная способность выпуска не подтверждена",
  rationale: "Этот пробел меняет допустимость сценариев.",
  nextAction: "Снять геометрию выпуска и канала в поле или с БПЛА.",
  blockedClaim: "Нельзя сравнивать сценарии понижения уровня или прорыва.",
};

describe("Risk Twin evidence workspace components", () => {
  it("selects an issue and exposes its next action and decision impact", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<EvidenceIssueQueue issues={[outletIssue]} selectedId={null} onSelect={onSelect} />);

    await user.click(screen.getByRole("button", { name: /пропускная способность выпуска/i }));

    expect(onSelect).toHaveBeenCalledWith("gap-outlet_capacity_fraction");
    expect(screen.getByText("Влияние на решение: высокое")).toBeInTheDocument();
    expect(screen.getByText(/снять геометрию выпуска/i)).toBeInTheDocument();
  });

  it("shows facts, allowed claim, prohibited claim and next verification", () => {
    render(<EvidenceInspector object={lakeObject} issue={outletIssue} />);

    expect(screen.getByText("Что видно")).toBeInTheDocument();
    expect(screen.getByText(/контур воды виден/i)).toBeInTheDocument();
    expect(screen.getByText("Чего утверждать нельзя")).toBeInTheDocument();
    expect(screen.getByText(/не является прогнозом опасности/i)).toBeInTheDocument();
    expect(screen.getByText("Следующая проверка")).toBeInTheDocument();
    expect(screen.getByText(/снять геометрию выпуска/i)).toBeInTheDocument();
  });

  it("does not substitute a synthetic object when nothing is selected", () => {
    render(<EvidenceInspector object={null} issue={null} />);

    expect(screen.getByText("Выберите объект или проблему на карте.")).toBeInTheDocument();
    expect(screen.queryByText(/synthetic|demo/i)).not.toBeInTheDocument();
  });
});
