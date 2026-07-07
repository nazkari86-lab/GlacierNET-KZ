import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  cn,
  apiUrl,
  formatBytes,
  formatNumber,
  formatCompact,
  formatDate,
  formatDateTime,
  formatRelativeTime,
  debounce,
  throttle,
  clamp,
  lerp,
  generateId,
  groupBy,
  sortBy,
  unique,
  sleep,
  truncate,
  capitalize,
  slugify,
  interpolateColor,
  getContrastColor,
  classNames,
  omit,
  pick,
  zip,
  sum,
  mean,
  median,
  standardDeviation,
  movingAverage,
} from "@/lib/utils";

describe("cn", () => {
  it("merges class names", () => {
    const result = cn("text-red-500", "text-blue-500");
    expect(result).toBe("text-blue-500");
  });

  it("handles conditional classes", () => {
    const result = cn("base", false && "hidden", "extra");
    expect(result).toContain("base");
    expect(result).toContain("extra");
    expect(result).not.toContain("hidden");
  });

  it("handles undefined and empty", () => {
    const result = cn("base", undefined, null, "");
    expect(result).toBe("base");
  });
});

describe("apiUrl", () => {
  it("prepends base URL", () => {
    const result = apiUrl("/api/datasets");
    expect(typeof result).toBe("string");
    expect(result).toContain("/api/datasets");
  });
});

describe("formatBytes", () => {
  it("formats bytes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1 KB");
    expect(formatBytes(1048576)).toBe("1 MB");
  });

  it("formats with custom decimals", () => {
    const result = formatBytes(1536, 1);
    expect(result).toBe("1.5 KB");
  });
});

describe("formatNumber", () => {
  it("adds thousand separators", () => {
    expect(formatNumber(1000)).toBe("1,000");
    expect(formatNumber(1000000)).toBe("1,000,000");
  });

  it("formats decimals", () => {
    const result = formatNumber(1234.56);
    expect(result).toContain("1,234.56");
  });
});

describe("formatCompact", () => {
  it("formats large numbers compactly", () => {
    const result = formatCompact(1500);
    expect(typeof result).toBe("string");
  });
});

describe("formatDate", () => {
  it("formats ISO date string", () => {
    const result = formatDate("2024-01-15T10:30:00Z");
    expect(typeof result).toBe("string");
    expect(result.length).toBeGreaterThan(0);
  });

  it("formats with custom options", () => {
    const result = formatDate("2024-01-15T10:30:00Z", { year: "numeric" });
    expect(typeof result).toBe("string");
  });

  it("handles Date objects", () => {
    const result = formatDate(new Date("2024-01-15"));
    expect(typeof result).toBe("string");
  });
});

describe("formatDateTime", () => {
  it("formats with time", () => {
    const result = formatDateTime("2024-01-15T10:30:00Z");
    expect(typeof result).toBe("string");
  });
});

describe("formatRelativeTime", () => {
  it("returns 'just now' for recent timestamps", () => {
    const now = new Date().toISOString();
    const result = formatRelativeTime(now);
    expect(result).toBe("just now");
  });

  it("returns minutes ago", () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    const result = formatRelativeTime(fiveMinAgo);
    expect(result).toBe("5m ago");
  });

  it("returns hours ago", () => {
    const twoHrAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    const result = formatRelativeTime(twoHrAgo);
    expect(result).toBe("2h ago");
  });

  it("returns days ago", () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
    const result = formatRelativeTime(threeDaysAgo);
    expect(result).toBe("3d ago");
  });

  it("returns formatted date for old timestamps", () => {
    const oldDate = new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString();
    const result = formatRelativeTime(oldDate);
    expect(typeof result).toBe("string");
    expect(result).not.toContain("ago");
  });
});

describe("debounce", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("delays execution", () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    debounced();
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("cancels previous calls", () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    debounced();
    debounced();
    debounced();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

describe("throttle", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("limits call frequency", () => {
    const fn = vi.fn();
    const throttled = throttle(fn, 100);
    throttled();
    throttled();
    throttled();
    expect(fn).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(100);
    throttled();
    expect(fn).toHaveBeenCalledTimes(2);
  });
});

describe("clamp", () => {
  it("clamps value within range", () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(-5, 0, 10)).toBe(0);
    expect(clamp(15, 0, 10)).toBe(10);
  });
});

describe("lerp", () => {
  it("interpolates between values", () => {
    expect(lerp(0, 10, 0)).toBe(0);
    expect(lerp(0, 10, 1)).toBe(10);
    expect(lerp(0, 10, 0.5)).toBe(5);
  });
});

describe("generateId", () => {
  it("generates unique ids", () => {
    const id1 = generateId();
    const id2 = generateId();
    expect(id1).not.toBe(id2);
    expect(id1.length).toBeGreaterThan(0);
  });
});

describe("groupBy", () => {
  it("groups items by key", () => {
    const items = [
      { type: "a", val: 1 },
      { type: "b", val: 2 },
      { type: "a", val: 3 },
    ];
    const result = groupBy(items, (i) => i.type);
    expect(result.a).toHaveLength(2);
    expect(result.b).toHaveLength(1);
  });
});

describe("sortBy", () => {
  it("sorts ascending", () => {
    const items = [3, 1, 2];
    expect(sortBy(items, (i) => i)).toEqual([1, 2, 3]);
  });

  it("sorts descending", () => {
    const items = [3, 1, 2];
    expect(sortBy(items, (i) => i, "desc")).toEqual([3, 2, 1]);
  });

  it("does not mutate original", () => {
    const items = [3, 1, 2];
    sortBy(items, (i) => i);
    expect(items).toEqual([3, 1, 2]);
  });
});

describe("unique", () => {
  it("removes duplicates", () => {
    expect(unique([1, 2, 2, 3, 3])).toEqual([1, 2, 3]);
  });
});

describe("sleep", () => {
  it("resolves after delay", async () => {
    vi.useFakeTimers();
    const promise = sleep(100);
    vi.advanceTimersByTime(100);
    await promise;
    expect(true).toBe(true);
  });
});

describe("truncate", () => {
  it("truncates long strings with ellipsis", () => {
    expect(truncate("hello world", 5)).toBe("hello…");
  });

  it("does not truncate short strings", () => {
    expect(truncate("hi", 5)).toBe("hi");
  });
});

describe("capitalize", () => {
  it("capitalizes first letter", () => {
    expect(capitalize("hello")).toBe("Hello");
    expect(capitalize("HELLO")).toBe("HELLO");
    expect(capitalize("")).toBe("");
  });
});

describe("slugify", () => {
  it("creates slug from string", () => {
    expect(slugify("Hello World")).toBe("hello-world");
    expect(slugify("My  Cool  Thing")).toBe("my-cool-thing");
  });

  it("removes leading/trailing dashes", () => {
    expect(slugify(" Hello World ")).toBe("hello-world");
  });
});

describe("interpolateColor", () => {
  it("returns first color at factor 0", () => {
    expect(interpolateColor("#000000", "#ffffff", 0)).toBe("#000000");
  });

  it("returns second color at factor 1", () => {
    expect(interpolateColor("#000000", "#ffffff", 1)).toBe("#ffffff");
  });
});

describe("getContrastColor", () => {
  it("returns dark for light backgrounds", () => {
    expect(getContrastColor("#ffffff")).toBe("#000000");
  });

  it("returns light for dark backgrounds", () => {
    expect(getContrastColor("#000000")).toBe("#ffffff");
  });
});

describe("classNames", () => {
  it("joins truthy classes", () => {
    expect(classNames("a", "b", "c")).toBe("a b c");
  });

  it("filters falsy values", () => {
    expect(classNames("a", false, null, undefined, "b")).toBe("a b");
  });
});

describe("omit", () => {
  it("removes specified keys", () => {
    const obj = { a: 1, b: 2, c: 3 };
    expect(omit(obj, ["a", "c"])).toEqual({ b: 2 });
  });
});

describe("pick", () => {
  it("picks specified keys", () => {
    const obj = { a: 1, b: 2, c: 3 };
    expect(pick(obj, ["a", "c"])).toEqual({ a: 1, c: 3 });
  });
});

describe("zip", () => {
  it("zips two arrays", () => {
    expect(zip([1, 2], ["a", "b"])).toEqual([
      [1, "a"],
      [2, "b"],
    ]);
  });

  it("truncates to shorter array", () => {
    expect(zip([1, 2, 3], ["a"])).toEqual([[1, "a"]]);
  });
});

describe("sum", () => {
  it("sums numbers", () => {
    expect(sum([1, 2, 3, 4])).toBe(10);
  });

  it("returns 0 for empty array", () => {
    expect(sum([])).toBe(0);
  });
});

describe("mean", () => {
  it("calculates mean", () => {
    expect(mean([2, 4, 6])).toBe(4);
  });

  it("returns 0 for empty array", () => {
    expect(mean([])).toBe(0);
  });
});

describe("median", () => {
  it("calculates median for odd length", () => {
    expect(median([1, 3, 5])).toBe(3);
  });

  it("calculates median for even length", () => {
    expect(median([1, 2, 3, 4])).toBe(2.5);
  });

  it("returns 0 for empty array", () => {
    expect(median([])).toBe(0);
  });
});

describe("standardDeviation", () => {
  it("calculates standard deviation", () => {
    const result = standardDeviation([2, 4, 4, 4, 5, 5, 7, 9]);
    expect(Math.round(result * 100) / 100).toBe(2);
  });

  it("returns 0 for empty array", () => {
    expect(standardDeviation([])).toBe(0);
  });
});

describe("movingAverage", () => {
  it("calculates moving average", () => {
    const result = movingAverage([1, 2, 3, 4, 5], 3);
    expect(result).toHaveLength(5);
    expect(result[0]).toBe(1);
    expect(result[2]).toBe(2);
  });
});
