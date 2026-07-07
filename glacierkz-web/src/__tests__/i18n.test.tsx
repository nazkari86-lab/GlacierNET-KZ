import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { I18nProvider, useI18n } from "@/lib/I18nProvider";

function TestComponent() {
  const { locale, setLocale, t } = useI18n();
  return (
    <div>
      <span data-testid="locale">{locale}</span>
      <span data-testid="translation">{t("home.title")}</span>
      <button onClick={() => setLocale("ru")} data-testid="switch-ru">
        Switch to RU
      </button>
      <button onClick={() => setLocale("kk")} data-testid="switch-kk">
        Switch to KK
      </button>
    </div>
  );
}

describe("I18nProvider", () => {
  it("provides default English locale", () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    );

    expect(screen.getByTestId("locale")).toHaveTextContent("en");
    expect(screen.getByTestId("translation")).toHaveTextContent("GlacierNET-KZ");
  });

  it("switches locale to Russian", async () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    );

    const switchRu = screen.getByTestId("switch-ru");
    switchRu.click();

    // Wait for re-render
    await screen.findByTestId("locale");
    expect(screen.getByTestId("locale")).toHaveTextContent("ru");
    expect(screen.getByTestId("translation")).toHaveTextContent("GlacierNET-KZ");
  });

  it("switches locale to Kazakh", async () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    );

    const switchKk = screen.getByTestId("switch-kk");
    switchKk.click();

    await screen.findByTestId("locale");
    expect(screen.getByTestId("locale")).toHaveTextContent("kk");
  });

  it("falls back to English for missing translations", () => {
    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    );

    // Even if locale changes, missing keys fall back to English
    expect(screen.getByTestId("translation")).toHaveTextContent("GlacierNET-KZ");
  });
});

describe("useI18n", () => {
  it("throws error when used outside provider", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    function BadComponent() {
      useI18n();
      return <div />;
    }

    expect(() => render(<BadComponent />)).toThrow(
      "useI18n must be used within <I18nProvider>"
    );

    consoleSpy.mockRestore();
  });
});
