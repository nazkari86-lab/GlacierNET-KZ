import { describe, it, expect, beforeEach } from "vitest";
import {
  getStoredToken,
  getStoredRefreshToken,
  getStoredUser,
  setAuthTokens,
  setStoredUser,
  clearAuth,
  getAuthState,
  parseJwtPayload,
  getTokenExpiry,
  isTokenExpired,
  hasRole,
  refreshAccessToken,
} from "@/lib/auth";
import type { AuthUser } from "@/lib/auth";

const mockUser: AuthUser = {
  id: "1",
  email: "test@example.com",
  name: "Test User",
  role: "admin",
};

function createTestJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  const sig = btoa("signature");
  return `${header}.${body}.${sig}`;
}

describe("Token Management", () => {
  beforeEach(() => {
    clearAuth();
    localStorage.clear();
  });

  it("stores and retrieves access token", () => {
    setAuthTokens("test-access-token");
    expect(getStoredToken()).toBe("test-access-token");
  });

  it("stores and retrieves refresh token", () => {
    setAuthTokens("access", "refresh-token");
    expect(getStoredRefreshToken()).toBe("refresh-token");
  });

  it("clears tokens", () => {
    setAuthTokens("test-token");
    clearAuth();
    expect(getStoredToken()).toBeNull();
    expect(getStoredRefreshToken()).toBeNull();
  });

  it("returns null when no token", () => {
    expect(getStoredToken()).toBeNull();
  });
});

describe("User Management", () => {
  beforeEach(() => {
    clearAuth();
    localStorage.clear();
  });

  it("stores and retrieves user", () => {
    setStoredUser(mockUser);
    expect(getStoredUser()).toEqual(mockUser);
  });

  it("returns null when no user", () => {
    expect(getStoredUser()).toBeNull();
  });
});

describe("isAuthenticated", () => {
  beforeEach(() => {
    clearAuth();
    localStorage.clear();
  });

  it("returns true when valid token and user exist", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    setAuthTokens(createTestJwt({ exp }));
    setStoredUser(mockUser);
    expect(getAuthState().isAuthenticated).toBe(true);
  });

  it("returns false when no token", () => {
    expect(getAuthState().isAuthenticated).toBe(false);
  });

  it("returns false when no user", () => {
    setAuthTokens("some-token");
    expect(getAuthState().isAuthenticated).toBe(false);
  });
});

describe("parseJwtPayload", () => {
  it("parses valid JWT payload", () => {
    const payload = { sub: "1", name: "Test" };
    const token = createTestJwt(payload);
    expect(parseJwtPayload(token)).toEqual(payload);
  });

  it("returns null for invalid token", () => {
    expect(parseJwtPayload("not-a-jwt")).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(parseJwtPayload("")).toBeNull();
  });
});

describe("getTokenExpiry", () => {
  it("returns Date for valid token", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const token = createTestJwt({ exp });
    const result = getTokenExpiry(token);
    expect(result).toBeInstanceOf(Date);
    expect(result!.getTime()).toBeGreaterThan(Date.now());
  });

  it("returns null for invalid token", () => {
    expect(getTokenExpiry("invalid")).toBeNull();
  });
});

describe("isTokenExpired", () => {
  it("returns false for valid non-expired token", () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    const token = createTestJwt({ exp });
    expect(isTokenExpired(token)).toBe(false);
  });

  it("returns true for expired token", () => {
    const exp = Math.floor(Date.now() / 1000) - 3600;
    const token = createTestJwt({ exp });
    expect(isTokenExpired(token)).toBe(true);
  });

  it("returns true for invalid token", () => {
    expect(isTokenExpired("invalid")).toBe(true);
  });
});

describe("hasRole", () => {
  it("returns true when user role meets requirement", () => {
    expect(hasRole("admin", "admin")).toBe(true);
    expect(hasRole("viewer", "admin")).toBe(true);
    expect(hasRole("viewer", "analyst")).toBe(true);
  });

  it("returns false when user role is insufficient", () => {
    expect(hasRole("admin", "viewer")).toBe(false);
    expect(hasRole("admin", "analyst")).toBe(false);
  });

  it("returns false when no user role", () => {
    expect(hasRole("admin")).toBe(false);
  });
});

describe("refreshAccessToken", () => {
  it("is exported and callable", () => {
    expect(typeof refreshAccessToken).toBe("function");
  });
});