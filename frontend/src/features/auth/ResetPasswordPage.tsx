import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router";

import { api, ApiError } from "../../api/client.js";
import type { PasswordPolicy } from "../../api/client.js";
import { PasswordChecklist } from "../../components/PasswordChecklist.js";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const policyQuery = useQuery({
    queryKey: ["password-policy"],
    queryFn: () => api.get<PasswordPolicy>("/api/auth/password-policy"),
  });

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post("/api/auth/reset-password", {
        token,
        new_password: password,
      });
      setSuccess(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : "Failed to reset password",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
        <h1 className="text-center text-2xl font-semibold text-slate-900">
          Reset password
        </h1>

        {success ? (
          <div className="mt-6 space-y-4">
            <div className="rounded-lg bg-green-50 p-3 text-sm text-green-600">
              Your password has been reset successfully.
            </div>
            <Link
              to="/login"
              className="block text-center text-sm text-indigo-600 hover:text-indigo-500"
            >
              Sign in with your new password
            </Link>
          </div>
        ) : (
          <>
            {!token && (
              <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                Missing reset token. Please use the link from your email.
              </div>
            )}

            {error && (
              <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-600">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="mt-6 space-y-4">
              <div>
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-slate-700"
                >
                  New password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none"
                />
                {policyQuery.data && (
                  <PasswordChecklist
                    password={password}
                    policy={policyQuery.data}
                  />
                )}
              </div>

              <button
                type="submit"
                disabled={submitting || !token}
                className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? "Resetting…" : "Reset password"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
