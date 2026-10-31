import { Navigate } from "react-router";

import type { UserRole } from "../api/client.js";
import { useAuth } from "./auth-context.js";

/* ------------------------------------------------------------------ */
/*  RequireAuth – redirects unauthenticated visitors to /login         */
/* ------------------------------------------------------------------ */

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">Loading…</p>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  RequireRole – shows a 403 screen when the role doesn't match       */
/* ------------------------------------------------------------------ */

export function RequireRole({
  roles,
  children,
}: {
  roles: UserRole[];
  children: React.ReactNode;
}) {
  const { user } = useAuth();

  if (!user || !roles.includes(user.role)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <div className="rounded-xl bg-white p-10 text-center shadow-sm">
          <h1 className="text-2xl font-semibold text-slate-900">403</h1>
          <p className="mt-2 text-slate-500">
            You don't have permission to view this page.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

/* ------------------------------------------------------------------ */
/*  RequireGuest – redirects authenticated users away from login/signup*/
/* ------------------------------------------------------------------ */

export function RequireGuest({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <p className="text-sm text-slate-500">Loading…</p>
      </div>
    );
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}
