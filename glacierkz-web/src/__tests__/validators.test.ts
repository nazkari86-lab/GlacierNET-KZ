import { describe, it, expect } from "vitest";
import {
  validateField,
  validateForm,
  isFormValid,
  validators,
  emailPattern,
  urlPattern,
  strongPasswordPattern,
  userFormSchema,
  datasetFormSchema,
} from "@/lib/validators";
import type { ValidationRule } from "@/lib/validators";

describe("validateField", () => {
  describe("required", () => {
    it("returns null for valid value", () => {
      expect(validateField("hello", { required: true })).toBeNull();
      expect(validateField(123, { required: true })).toBeNull();
      expect(validateField([1, 2], { required: true })).toBeNull();
    });

    it("returns error for empty value", () => {
      expect(validateField("", { required: true })).toBeTruthy();
      expect(validateField(null, { required: true })).toBeTruthy();
      expect(validateField(undefined, { required: true })).toBeTruthy();
      expect(validateField([], { required: true })).toBeTruthy();
    });
  });

  describe("minLength", () => {
    it("returns null for sufficient length", () => {
      expect(validateField("hello", { minLength: 3 })).toBeNull();
      expect(validateField("abc", { minLength: 3 })).toBeNull();
    });

    it("returns error for insufficient length", () => {
      expect(validateField("hi", { minLength: 3 })).toBeTruthy();
    });
  });

  describe("maxLength", () => {
    it("returns null for acceptable length", () => {
      expect(validateField("hi", { maxLength: 5 })).toBeNull();
      expect(validateField("hello", { maxLength: 5 })).toBeNull();
    });

    it("returns error for exceeding length", () => {
      expect(validateField("hello world", { maxLength: 5 })).toBeTruthy();
    });
  });

  describe("min/max range", () => {
    it("returns null for value in range", () => {
      expect(validateField(50, { min: 0, max: 100 })).toBeNull();
      expect(validateField(0, { min: 0, max: 100 })).toBeNull();
      expect(validateField(100, { min: 0, max: 100 })).toBeNull();
    });

    it("returns error for value out of range", () => {
      expect(validateField(-1, { min: 0, max: 100 })).toBeTruthy();
      expect(validateField(101, { min: 0, max: 100 })).toBeTruthy();
    });
  });

  describe("pattern", () => {
    it("returns null for matching pattern", () => {
      expect(validateField("123", { pattern: /^\d{3}$/ })).toBeNull();
    });

    it("returns error for non-matching pattern", () => {
      expect(validateField("abc", { pattern: /^\d{3}$/ })).toBeTruthy();
      expect(validateField("1234", { pattern: /^\d{3}$/ })).toBeTruthy();
    });
  });

  describe("custom validator", () => {
    it("uses custom function", () => {
      const rule: ValidationRule = {
        custom: (v) => (v === "bad" ? "is bad" : null),
      };
      expect(validateField("good", rule)).toBeNull();
      expect(validateField("bad", rule)).toBe("is bad");
    });
  });
});

describe("validateForm", () => {
  it("returns empty errors for valid form", () => {
    const errors = validateForm(
      { name: "John", email: "john@example.com" },
      { name: { required: true }, email: { required: true, pattern: emailPattern } }
    );
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it("returns errors for invalid form", () => {
    const errors = validateForm(
      { name: "", email: "invalid" },
      { name: { required: true }, email: { required: true, pattern: emailPattern } }
    );
    expect(errors.name).toBeTruthy();
    expect(errors.email).toBeTruthy();
  });
});

describe("isFormValid", () => {
  it("returns true for empty errors", () => {
    expect(isFormValid({})).toBe(true);
  });

  it("returns false for errors", () => {
    expect(isFormValid({ name: "Required" })).toBe(false);
  });
});

describe("validators factory", () => {
  it("validators.required returns rule with custom", () => {
    const rule = validators.required();
    expect(rule.required).toBe(true);
    expect(rule.custom?.("")).toBeTruthy();
    expect(rule.custom?.("hello")).toBeNull();
  });

  it("validators.email returns pattern rule", () => {
    const rule = validators.email();
    expect(rule.required).toBe(true);
    expect(rule.pattern).toBe(emailPattern);
  });

  it("validators.password returns strong password pattern", () => {
    const rule = validators.password();
    expect(rule.pattern).toBe(strongPasswordPattern);
  });

  it("validators.url returns url pattern", () => {
    const rule = validators.url();
    expect(rule.pattern).toBe(urlPattern);
  });

  it("validators.minLength returns rule", () => {
    const rule = validators.minLength(5);
    expect(rule.minLength).toBe(5);
  });

  it("validators.maxLength returns rule", () => {
    const rule = validators.maxLength(10);
    expect(rule.maxLength).toBe(10);
  });

  it("validators.range returns rule", () => {
    const rule = validators.range(0, 100);
    expect(rule.min).toBe(0);
    expect(rule.max).toBe(100);
  });
});

describe("schemas", () => {
  it("userFormSchema validates valid user", () => {
    const errors = validateForm(
      { name: "John Doe", email: "john@example.com", role: "admin" },
      userFormSchema
    );
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it("userFormSchema catches invalid user", () => {
    const errors = validateForm(
      { name: "", email: "invalid", role: "" },
      userFormSchema
    );
    expect(errors.name).toBeTruthy();
    expect(errors.email).toBeTruthy();
    expect(errors.role).toBeTruthy();
  });

  it("datasetFormSchema validates valid dataset", () => {
    const errors = validateForm(
      { name: "Test Dataset", description: "A test", year: 2024, region: "Tien Shan" },
      datasetFormSchema
    );
    expect(Object.keys(errors)).toHaveLength(0);
  });

  it("datasetFormSchema catches invalid dataset", () => {
    const errors = validateForm(
      { name: "", description: "", year: 1800, region: "" },
      datasetFormSchema
    );
    expect(errors.name).toBeTruthy();
    expect(errors.year).toBeTruthy();
    expect(errors.region).toBeTruthy();
  });
});
