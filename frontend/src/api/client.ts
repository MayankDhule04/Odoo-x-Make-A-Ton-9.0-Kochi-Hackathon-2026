/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type UserRole = "ADMIN" | "STAFF" | "CUSTOMER";

export type User = {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
};

export type Page<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type AuditLogEntry = {
  id: number;
  actor_id: number | null;
  entity_type: string;
  entity_id: number;
  action: string;
  changes: string | null;
  created_at: string;
};

export type EmailOutboxEntry = {
  id: number;
  to_email: string;
  subject: string;
  body: string;
  created_at: string;
};

export type Customer = {
  id: number;
  user_id: number | null;
  name: string;
  email: string;
  phone: string | null;
  billing_address: string | null;
  is_active: boolean;
};

export type PasswordPolicy = {
  min_length: number;
  max_length: number;
  requires_uppercase: boolean;
  requires_lowercase: boolean;
  requires_special: boolean;
};

/* ------------------------------------------------------------------ */
/*  API error                                                          */
/* ------------------------------------------------------------------ */

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly errors: Array<{ field: string; message: string }> | undefined;

  constructor(
    status: number,
    detail: string,
    errors?: Array<{ field: string; message: string }>,
  ) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.errors = errors;
  }
}

/* ------------------------------------------------------------------ */
/*  In-memory access token                                             */
/* ------------------------------------------------------------------ */

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

/* ------------------------------------------------------------------ */
/*  Internal request helper                                            */
/* ------------------------------------------------------------------ */

async function request<T>(
  method: string,
  url: string,
  body?: unknown,
  params?: Record<string, string>,
): Promise<T> {
  const fullUrl = params
    ? `${url}?${new URLSearchParams(params).toString()}`
    : url;

  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  const init: RequestInit = {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };

  let response = await fetch(fullUrl, init);

  /* On 401, attempt a single token refresh using the httpOnly cookie. */
  if (response.status === 401) {
    const refreshRes = await fetch("/api/auth/refresh", {
      method: "POST",
      credentials: "include",
    });

    if (refreshRes.ok) {
      const data = (await refreshRes.json()) as TokenResponse;
      accessToken = data.access_token;
      headers["Authorization"] = `Bearer ${accessToken}`;
      response = await fetch(fullUrl, { ...init, headers });
    } else {
      accessToken = null;
      window.location.href = "/login";
      throw new ApiError(401, "Session expired");
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({
      detail: "An unexpected error occurred",
    }));
    throw new ApiError(
      response.status,
      payload.detail ?? "An unexpected error occurred",
      payload.errors,
    );
  }

  return (await response.json()) as T;
}

/* ------------------------------------------------------------------ */
/*  Public API client                                                  */
/* ------------------------------------------------------------------ */

export const api = {
  get<T>(url: string, params?: Record<string, string>): Promise<T> {
    return request<T>("GET", url, undefined, params);
  },
  post<T>(url: string, body?: unknown): Promise<T> {
    return request<T>("POST", url, body);
  },
  patch<T>(url: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", url, body);
  },
  delete<T>(url: string): Promise<T> {
    return request<T>("DELETE", url);
  },
};
