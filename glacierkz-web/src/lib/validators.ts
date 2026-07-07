export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  min?: number;
  max?: number;
  pattern?: RegExp;
  patternMessage?: string;
  custom?: (value: unknown, ctx?: unknown) => string | null;
}

export interface ValidationSchema {
  [field: string]: ValidationRule;
}

export type ValidationErrors = Record<string, string>;

export function validateField(value: unknown, rules: ValidationRule): string | null {
  if (rules.required) {
    if (value === null || value === undefined || value === "") {
      return "This field is required";
    }
    if (Array.isArray(value) && value.length === 0) {
      return "At least one item is required";
    }
  }

  if (value === null || value === undefined || value === "") {
    return null;
  }

  const strValue = String(value);
  const numValue = typeof value === "number" ? value : Number(value);

  if (rules.minLength !== undefined && strValue.length < rules.minLength) {
    return `Minimum length is ${rules.minLength} characters`;
  }

  if (rules.maxLength !== undefined && strValue.length > rules.maxLength) {
    return `Maximum length is ${rules.maxLength} characters`;
  }

  if (rules.min !== undefined && !isNaN(numValue) && numValue < rules.min) {
    return `Minimum value is ${rules.min}`;
  }

  if (rules.max !== undefined && !isNaN(numValue) && numValue > rules.max) {
    return `Maximum value is ${rules.max}`;
  }

  if (rules.pattern && !rules.pattern.test(strValue)) {
    return rules.patternMessage || "Invalid format";
  }

  if (rules.custom) {
    return rules.custom(value);
  }

  return null;
}

export function validateForm(data: Record<string, unknown>, schema: ValidationSchema): ValidationErrors {
  const errors: ValidationErrors = {};
  for (const [field, rules] of Object.entries(schema)) {
    const error = validateField(data[field], rules);
    if (error) {
      errors[field] = error;
    }
  }
  return errors;
}

export function isFormValid(errors: ValidationErrors): boolean {
  return Object.keys(errors).length === 0;
}

export const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const phonePattern = /^\+?[\d\s\-()]{7,}$/;
export const urlPattern = /^https?:\/\/.+/;
export const strongPasswordPattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;

export const validators = {
  required: (msg?: string): ValidationRule => ({
    required: true,
    custom: (v) => {
      if (!v || (typeof v === "string" && v.trim() === "")) return msg || "Required";
      return null;
    },
  }),

  email: (msg?: string): ValidationRule => ({
    required: true,
    pattern: emailPattern,
    patternMessage: msg || "Enter a valid email address",
  }),

  minLength: (min: number, msg?: string): ValidationRule => ({
    minLength: min,
    patternMessage: msg || `At least ${min} characters`,
  }),

  maxLength: (max: number, msg?: string): ValidationRule => ({
    maxLength: max,
    patternMessage: msg || `At most ${max} characters`,
  }),

  range: (min: number, max: number, msg?: string): ValidationRule => ({
    min,
    max,
    patternMessage: msg || `Must be between ${min} and ${max}`,
  }),

  url: (msg?: string): ValidationRule => ({
    pattern: urlPattern,
    patternMessage: msg || "Enter a valid URL",
  }),

  phone: (msg?: string): ValidationRule => ({
    pattern: phonePattern,
    patternMessage: msg || "Enter a valid phone number",
  }),

  password: (msg?: string): ValidationRule => ({
    pattern: strongPasswordPattern,
    patternMessage: msg || "Password must include uppercase, lowercase, number, and special character",
  }),

  oneOf: (allowed: unknown[], msg?: string): ValidationRule => ({
    custom: (v) => (allowed.includes(v) ? null : msg || "Invalid value"),
  }),

  matches: (otherField: string, fieldName: string, msg?: string): ValidationRule => ({
    custom: (_v: unknown, ctx: unknown) => {
      const ctxObj = ctx as Record<string, unknown> | undefined;
      if (ctxObj && ctxObj[otherField] !== _v) {
        return msg || `${fieldName} must match`;
      }
      return null;
    },
  }),
};

export interface UserFormValues {
  name: string;
  email: string;
  role: string;
}

export const userFormSchema: ValidationSchema = {
  name: { required: true, minLength: 2, maxLength: 100 },
  email: validators.email(),
  role: {
    required: true,
    custom: (v) =>
      ["admin", "analyst", "viewer"].includes(String(v)) ? null : "Select a valid role",
  },
};

export interface DatasetFormValues {
  name: string;
  description: string;
  year: number;
  region: string;
}

export const datasetFormSchema: ValidationSchema = {
  name: { required: true, minLength: 2, maxLength: 200 },
  description: { maxLength: 1000 },
  year: { required: true, min: 1990, max: 2100 },
  region: { required: true },
};

export interface SettingsFormValues {
  apiUrl: string;
  wsUrl: string;
  defaultModel: string;
  maxConcurrentTasks: number;
}

export const settingsFormSchema: ValidationSchema = {
  apiUrl: { required: true, pattern: urlPattern, patternMessage: "Enter a valid API URL" },
  wsUrl: { required: true, pattern: urlPattern, patternMessage: "Enter a valid WebSocket URL" },
  defaultModel: { required: true },
  maxConcurrentTasks: { required: true, min: 1, max: 50 },
};
