import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  exportToCSV,
  exportToJSON,
  exportToPDF,
  generateFilename,
  downloadFile,
  downloadBlob,
  formatDataForExport,
  arrayToCSVString,
} from "@/lib/export";

vi.mock("jspdf", () => ({
  jsPDF: class {
    setFontSize = vi.fn();
    text = vi.fn();
    setTextColor = vi.fn();
    save = vi.fn();
    autoTable = vi.fn();
  },
}));

describe("generateFilename", () => {
  it("generates filename with extension", () => {
    const result = generateFilename("report", "csv");
    expect(result).toMatch(/^report_\d{4}-\d{2}-\d{2}_\d{6}\.csv$/);
  });

  it("handles empty prefix", () => {
    const result = generateFilename("", "csv");
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2}_\d{6}\.csv$/);
  });
});

describe("downloadFile", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates and clicks download link", () => {
    const click = vi.fn();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-url");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(document, "createElement").mockReturnValue({
      href: "",
      download: "",
      style: { display: "none" },
      click,
    } as unknown as HTMLAnchorElement);
    const appendSpy = vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as Node);
    const removeSpy = vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as Node);

    downloadFile("test content", "test.txt", "text/plain");
    expect(click).toHaveBeenCalled();
    appendSpy.mockRestore();
    removeSpy.mockRestore();
  });
});

describe("downloadBlob", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("downloads blob", () => {
    const click = vi.fn();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-url");
    vi.spyOn(document, "createElement").mockReturnValue({
      href: "",
      download: "",
      style: { display: "none" },
      click,
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as Node);
    vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as Node);

    downloadBlob(new Blob(["test"], { type: "text/csv" }), "test.csv");
    expect(click).toHaveBeenCalled();
  });
});

describe("exportToCSV", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(document, "createElement").mockReturnValue({
      click: vi.fn(),
      style: {},
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as Node);
    vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as Node);
  });

  it("generates CSV from data", () => {
    expect(() =>
      exportToCSV([{ name: "Alice", age: 30 }], [{ key: "name", header: "Name" }], "test")
    ).not.toThrow();
  });
});

describe("exportToJSON", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  beforeEach(() => {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock");
    vi.spyOn(document, "createElement").mockReturnValue({
      click: vi.fn(),
      style: {},
    } as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, "appendChild").mockImplementation(() => null as unknown as Node);
    vi.spyOn(document.body, "removeChild").mockImplementation(() => null as unknown as Node);
  });

  it("generates JSON from data", () => {
    expect(() => exportToJSON([{ name: "Alice" }], "test")).not.toThrow();
  });
});

describe("exportToPDF", () => {
  it("is exported and callable", async () => {
    expect(typeof exportToPDF).toBe("function");
  });
});

describe("formatDataForExport", () => {
  it("formats data with accessors", () => {
    const data = [{ id: 1, first: "Alice", last: "Smith" }];
    const columns = [
      { key: "id", header: "ID" },
      { key: "name", header: "Name", accessor: (row: (typeof data)[0]) => `${row.first} ${row.last}` },
    ];
    const result = formatDataForExport(data, columns);
    expect(result[0]).toEqual({ ID: 1, Name: "Alice Smith" });
  });
});

describe("arrayToCSVString", () => {
  it("converts array to CSV string", () => {
    const result = arrayToCSVString(
      [
        ["a", "b"],
        ["c", "d"],
      ],
      ["col1", "col2"]
    );
    expect(result).toContain("col1,col2");
    expect(result).toContain("a,b");
  });
});
