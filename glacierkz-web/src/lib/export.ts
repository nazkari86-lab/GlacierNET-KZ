export interface ExportColumn<T = unknown> {
  key: string;
  header: string;
  accessor?: (row: T) => unknown;
}

export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  columns: ExportColumn<T>[],
  filename: string
): void {
  const headers = columns.map((c) => c.header);
  const rows = data.map((row) =>
    columns
      .map((col) => {
        const value = col.accessor ? col.accessor(row) : row[col.key];
        const str = value === null || value === undefined ? "" : String(value);
        const escaped = str.includes(",") || str.includes('"') || str.includes("\n")
          ? `"${str.replace(/"/g, '""')}"`
          : str;
        return escaped;
      })
      .join(",")
  );

  const csv = [headers.join(","), ...rows].join("\n");
  downloadFile(csv, `${filename}.csv`, "text/csv;charset=utf-8;");
}

export function exportToJSON<T>(
  data: T[],
  filename: string,
  pretty = true
): void {
  const json = pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data);
  downloadFile(json, `${filename}.json`, "application/json;charset=utf-8;");
}

export async function exportToPDF(
  data: Record<string, unknown>[],
  columns: ExportColumn[],
  filename: string,
  title: string
): Promise<void> {
  const { jsPDF } = await import("jspdf");
  await import("jspdf-autotable");

  const doc = new jsPDF();
  doc.setFontSize(16);
  doc.text(title, 14, 22);
  doc.setFontSize(10);
  doc.setTextColor(128);
  doc.text(`Generated on ${new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}`, 14, 30);

  const headers = columns.map((c) => c.header);
  const rows = data.map((row) =>
    columns.map((col) => {
      const value = col.accessor ? col.accessor(row) : row[col.key];
      return value === null || value === undefined ? "" : String(value);
    })
  );

  type JsPdfWithAutoTable = InstanceType<typeof jsPDF> & {
    autoTable: (options: {
      head: string[][];
      body: string[][];
      startY: number;
      styles: Record<string, unknown>;
      headStyles: Record<string, unknown>;
      alternateRowStyles: Record<string, unknown>;
    }) => void;
  };

  (doc as JsPdfWithAutoTable).autoTable({
    head: [headers],
    body: rows,
    startY: 36,
    styles: { fontSize: 8, cellPadding: 2 },
    headStyles: { fillColor: [59, 130, 246] },
    alternateRowStyles: { fillColor: [245, 247, 250] },
  });

  doc.save(`${filename}.pdf`);
}

export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function generateFilename(prefix: string, ext: string): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 8).replace(/:/g, "");
  const base = prefix ? `${prefix}_${date}_${time}` : `${date}_${time}`;
  return `${base}.${ext}`;
}

export function arrayToCSVString(data: unknown[][], headers?: string[]): string {
  const lines: string[] = [];
  if (headers) {
    lines.push(headers.join(","));
  }
  for (const row of data) {
    lines.push(
      row
        .map((cell) => {
          const str = cell === null || cell === undefined ? "" : String(cell);
          return str.includes(",") || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str;
        })
        .join(",")
    );
  }
  return lines.join("\n");
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function formatDataForExport<T>(
  data: T[],
  columns: ExportColumn<T>[]
): Record<string, unknown>[] {
  return data.map((row) => {
    const exportRow: Record<string, unknown> = {};
    for (const col of columns) {
      const value = col.accessor ? col.accessor(row) : (row as Record<string, unknown>)[col.key];
      exportRow[col.header] = value;
    }
    return exportRow;
  });
}
