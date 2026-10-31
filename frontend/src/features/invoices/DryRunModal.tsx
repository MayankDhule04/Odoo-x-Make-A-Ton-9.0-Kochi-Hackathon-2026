import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "../../api/client.js";
import type { BillingRunResponse, DryRunResponse } from "./types.js";
import { inr } from "./types.js";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onRunSuccess: () => void;
};

export default function DryRunModal({ isOpen, onClose, onRunSuccess }: Props) {
  const todayStr = new Date().toISOString().split("T")[0];
  const [asOfDate, setAsOfDate] = useState<string>(todayStr);
  const [activeTab, setActiveTab] = useState<"projected" | "exceptions">("projected");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const dryRunQuery = useQuery({
    queryKey: ["billing-dry-run", asOfDate],
    queryFn: () =>
      api.post<DryRunResponse>("/api/billing/dry-run", {
        as_of_date: asOfDate || null,
      }),
    enabled: isOpen,
  });

  const runMutation = useMutation({
    mutationFn: () =>
      api.post<BillingRunResponse>("/api/billing/run", {
        as_of_date: asOfDate || null,
      }),
    onSuccess: (data) => {
      setSuccessMessage(
        `Successfully created ${data.created_count} invoices totaling ₹${data.total_amount}.`
      );
      setTimeout(() => {
        setSuccessMessage(null);
        onRunSuccess();
        onClose();
      }, 1500);
    },
  });

  if (!isOpen) return null;

  const data = dryRunQuery.data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl bg-white shadow-2xl ring-1 ring-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-100 text-indigo-700">
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </span>
              <h2 className="text-lg font-bold text-slate-900">Dry-Run Billing Preview</h2>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              Preview invoices and evaluate the exceptions queue before committing a live billing run.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {/* Success alert */}
        {successMessage && (
          <div className="mx-6 mt-4 rounded-xl bg-emerald-50 p-4 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200">
            {successMessage}
          </div>
        )}

        {/* Date Filter & Summary */}
        <div className="border-b border-slate-100 bg-slate-50/50 px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <label htmlFor="asOfDate" className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Billing Date:
              </label>
              <input
                id="asOfDate"
                type="date"
                value={asOfDate}
                onChange={(e) => setAsOfDate(e.target.value)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                type="button"
                onClick={() => dryRunQuery.refetch()}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Refresh
              </button>
            </div>

            {data && (
              <div className="flex gap-4">
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-center shadow-xs">
                  <div className="text-xs text-slate-500">Projected Invoices</div>
                  <div className="text-base font-bold text-indigo-600">
                    {data.projected_invoices_count}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-center shadow-xs">
                  <div className="text-xs text-slate-500">Projected Revenue</div>
                  <div className="text-base font-bold text-emerald-600">
                    {inr(data.projected_total_amount)}
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-center shadow-xs">
                  <div className="text-xs text-slate-500">Exceptions</div>
                  <div className={`text-base font-bold ${data.exceptions_count > 0 ? "text-amber-600" : "text-slate-600"}`}>
                    {data.exceptions_count}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 px-6">
          <button
            type="button"
            onClick={() => setActiveTab("projected")}
            className={`border-b-2 px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "projected"
                ? "border-indigo-600 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            Projected Invoices ({data?.projected_invoices_count ?? 0})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("exceptions")}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-semibold transition-colors ${
              activeTab === "exceptions"
                ? "border-amber-600 text-amber-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <span>Exceptions Queue</span>
            {(data?.exceptions_count ?? 0) > 0 && (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
                {data?.exceptions_count}
              </span>
            )}
          </button>
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-y-auto p-6">
          {dryRunQuery.isLoading ? (
            <div className="flex h-48 items-center justify-center text-sm text-slate-500">
              Evaluating billing rules, taxes, discounts, and subscriptions...
            </div>
          ) : activeTab === "projected" ? (
            (data?.projected_invoices.length ?? 0) === 0 ? (
              <div className="flex h-40 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 text-center">
                <p className="text-sm font-medium text-slate-600">No subscriptions due for billing</p>
                <p className="text-xs text-slate-400">All active subscriptions are billed up to date.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
                    <tr>
                      <th className="px-4 py-2.5">Subscription</th>
                      <th className="px-4 py-2.5">Customer</th>
                      <th className="px-4 py-2.5">Billing Period</th>
                      <th className="px-4 py-2.5 text-right">Subtotal</th>
                      <th className="px-4 py-2.5 text-right">Tax</th>
                      <th className="px-4 py-2.5 text-right">Discount</th>
                      <th className="px-4 py-2.5 text-right">Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {data?.projected_invoices.map((inv) => (
                      <tr key={inv.subscription_id} className="hover:bg-slate-50/60">
                        <td className="px-4 py-3 font-semibold text-slate-900">{inv.subscription_number}</td>
                        <td className="px-4 py-3 text-slate-700">{inv.customer_name}</td>
                        <td className="px-4 py-3 text-xs text-slate-500">
                          {inv.period_start} → {inv.period_end}
                        </td>
                        <td className="px-4 py-3 text-right text-slate-600">{inr(inv.amount_subtotal)}</td>
                        <td className="px-4 py-3 text-right text-slate-600">{inr(inv.amount_tax)}</td>
                        <td className="px-4 py-3 text-right text-emerald-600">
                          {Number(inv.amount_discount) > 0 ? `-${inr(inv.amount_discount)}` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right font-bold text-slate-900">{inr(inv.amount_total)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          ) : (
            (data?.exceptions.length ?? 0) === 0 ? (
              <div className="flex h-40 flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 text-center">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">✓</div>
                <p className="mt-2 text-sm font-semibold text-slate-800">Exceptions Queue is clean!</p>
                <p className="text-xs text-slate-500">No anomalies, missing taxes, or expired plans detected.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {data?.exceptions.map((ex, idx) => (
                  <div
                    key={`${ex.subscription_id}-${idx}`}
                    className={`rounded-xl border p-4 ${
                      ex.severity === "BLOCKER"
                        ? "border-rose-200 bg-rose-50/50"
                        : "border-amber-200 bg-amber-50/50"
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full px-2 py-0.5 text-xs font-bold ${
                            ex.severity === "BLOCKER"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {ex.severity}
                        </span>
                        <span className="font-semibold text-slate-900">{ex.subscription_number}</span>
                        <span className="text-xs text-slate-500">({ex.customer_name})</span>
                      </div>
                      <span className="font-mono text-xs text-slate-500">{ex.error_code}</span>
                    </div>
                    <p className="mt-1 text-sm text-slate-700">{ex.message}</p>
                    <div className="mt-2 rounded-lg bg-white/80 px-3 py-1.5 text-xs text-slate-600 ring-1 ring-slate-200/60">
                      <span className="font-semibold text-slate-700">Recommendation:</span> {ex.recommendation}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Close
          </button>
          <button
            type="button"
            disabled={
              runMutation.isPending ||
              (data?.projected_invoices_count ?? 0) === 0
            }
            onClick={() => runMutation.mutate()}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 disabled:opacity-50"
          >
            {runMutation.isPending ? "Executing billing..." : `Approve & Run Billing (${data?.projected_invoices_count ?? 0})`}
          </button>
        </div>
      </div>
    </div>
  );
}

