import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { I18nProvider } from "@/lib/I18nProvider";
import LanguageSwitcher from "@/components/LanguageSwitcher";

function renderWithProvider(ui: React.ReactNode) {
  return render(<I18nProvider>{ui}</I18nProvider>);
}

describe("LanguageSwitcher", () => {
  it("renders three language buttons (EN, RU, KK)", () => {
    renderWithProvider(<LanguageSwitcher />);

    expect(screen.getByRole("radio", { name: "EN" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "RU" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "KK" })).toBeInTheDocument();
  });

  it("marks English as checked by default", () => {
    renderWithProvider(<LanguageSwitcher />);

    const enButton = screen.getByRole("radio", { name: "EN" });
    expect(enButton).toHaveAttribute("aria-checked", "true");
  });

  it("has proper radiogroup role", () => {
    renderWithProvider(<LanguageSwitcher />);

    const radiogroup = screen.getByRole("radiogroup", {
      name: "Language selection",
    });
    expect(radiogroup).toBeInTheDocument();
  });

  it("switches to Russian when RU is clicked", async () => {
    renderWithProvider(<LanguageSwitcher />);

    const ruButton = screen.getByRole("radio", { name: "RU" });
    ruButton.click();

    // Wait for re-render
    await screen.findByRole("radio", { name: "RU" });
    expect(ruButton).toHaveAttribute("aria-checked", "true");

    // EN should no longer be checked
    const enButton = screen.getByRole("radio", { name: "EN" });
    expect(enButton).toHaveAttribute("aria-checked", "false");
  });

  it("switches to Kazakh when KK is clicked", async () => {
    renderWithProvider(<LanguageSwitcher />);

    const kkButton = screen.getByRole("radio", { name: "KK" });
    kkButton.click();

    await screen.findByRole("radio", { name: "KK" });
    expect(kkButton).toHaveAttribute("aria-checked", "true");
  });
});
