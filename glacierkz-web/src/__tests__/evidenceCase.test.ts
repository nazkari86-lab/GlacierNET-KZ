import { describe, expect, it } from "vitest";
import { parseEvidenceCase, riskTwinHref, serializeEvidenceCase } from "@/lib/evidenceCase";

describe("EvidenceCaseRef", () => {
  it("parses a valid local lake case", () => {
    expect(parseEvidenceCase("?rgi=RGI-1&lake=L-2&year=2024&scope=local_inventory")).toEqual({ rgiId: "RGI-1", lakeId: "L-2", year: 2024, sourceScope: "local_inventory" });
  });

  it("rejects missing RGI IDs, invalid years and unknown scopes", () => {
    expect(parseEvidenceCase("?rgi=&year=x")).toBeNull();
    expect(parseEvidenceCase("?rgi=RGI-1&year=2024.5")).toBeNull();
    expect(parseEvidenceCase("?rgi=RGI-1&scope=anything")).toBeNull();
  });

  it("serializes only canonical case fields and preserves a map link", () => {
    const ref = { rgiId: "RGI-1", sourceScope: "annual_screening" as const };
    expect(serializeEvidenceCase(ref)).toBe("rgi=RGI-1&scope=annual_screening");
    expect(riskTwinHref(ref)).toBe("/risk-twin?rgi=RGI-1&scope=annual_screening");
  });
});
