import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HubPage from "@/app/hub/page";
import { I18nProvider } from "@/lib/I18nProvider";

describe("project hub", () => {
  it("promotes the evidence workflow instead of legacy or duplicate surfaces", () => {
    render(
      <I18nProvider>
        <HubPage />
      </I18nProvider>,
    );

    expect(screen.getByText("Primary evidence workflow")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ML Evidence Workspace/i })).toHaveAttribute("href", "/ml");
    expect(screen.getByRole("link", { name: /Active Cryosphere Risk Twin/i })).toHaveAttribute("href", "/risk-twin");
    expect(screen.getByRole("link", { name: /Source-backed Event Radar/i })).toHaveAttribute("href", "/event-radar");
    expect(screen.getByRole("link", { name: /Operations & action queue/i })).toHaveAttribute("href", "/operations");
    expect(screen.getByRole("link", { name: /Scientific evidence cockpit/i })).toHaveAttribute("href", "/jury");
    expect(screen.queryByRole("link", { name: /demo/i })).not.toBeInTheDocument();
  });
});
