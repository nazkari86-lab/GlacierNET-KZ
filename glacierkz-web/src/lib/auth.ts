const TOKEN_KEY = "glacierkz_token";
const REFRESH_KEY = "glacierkz_refresh";
const USER_KEY = "glacierkz_user";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  role: "admin" | "analyst" | "viewer";
  avatar?: string;
  lastLogin?: string;
  createdAt?: string;
}

export interface AuthState {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(REFRESH_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setAuthTokens(accessToken: string, refreshToken?: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken);
  }
}

export function setStoredUser(user: AuthUser): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getAuthState(): AuthState {
  const token = getStoredToken();
  const user = getStoredUser();
  return {
    user,
    token,
    isAuthenticated: !!token && !!user,
  };
}

export function parseJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => `%${("00" + c.charCodeAt(0).toString(16)).slice(-2)}`)
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function isTokenExpired(token: string): boolean {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return true;
  const now = Math.floor(Date.now() / 1000);
  return payload.exp < now;
}

export function getTokenExpiry(token: string): Date | null {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return null;
  return new Date(payload.exp * 1000);
}

export function getTokenRemainingSeconds(token: string): number {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return 0;
  const now = Math.floor(Date.now() / 1000);
  return Math.max(0, payload.exp - now);
}

export function createAuthHeaders(): Record<string, string> {
  const token = getStoredToken();
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export async function refreshAccessToken(
  refreshToken: string
): Promise<{ accessToken: string; refreshToken?: string } | null> {
  try {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "";
    const res = await fetch(`${baseUrl}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
  } catch {
    return null;
  }
}

export async function tryRefreshToken(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;
  const result = await refreshAccessToken(refreshToken);
  if (!result) {
    clearAuth();
    return null;
  }
  setAuthTokens(result.accessToken, result.refreshToken);
  return result.accessToken;
}

export function hasRole(requiredRole: string, userRole?: string): boolean {
  if (!userRole) return false;
  const hierarchy: Record<string, number> = { admin: 3, analyst: 2, viewer: 1 };
  return (hierarchy[userRole] || 0) >= (hierarchy[requiredRole] || 0);
}

export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    const newToken = await tryRefreshToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      res = await fetch(url, { ...options, headers });
    }
  }

  return res;
}
