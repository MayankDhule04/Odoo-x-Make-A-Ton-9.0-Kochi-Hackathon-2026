import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";

import type { Page } from "../../api/client.js";
import { api } from "../../api/client.js";
import { useAuth } from "../../lib/auth-context.js";
import DryRunModal from "./DryRunModal.js";
import type { Invoice } from "./types.js";
import { inr, invoiceStatusBadge } from "./types.js";

type Props = {
  customerMode?: boolean;
};

export default function InvoicesPage({ customerMode = false }: Props) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isStaffOrAdmin = user?.role === "ADMIN" || user?.role === "STAFF";

  const [page, setPage] = useState(1);
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [search, setSearch] = useState("");
  const [isDryRunOpen, setIsDryRunOpen] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const queryParams: Record<string, string> = {
    page: String(page),
    page_size: "15",
  };
  if (selectedStatus !== "ALL") {
    queryParams.status = selectedStatus;
  }
  if (search.trim()) {
    queryParams.search = search.trim();
  }

  const { data, isLoading, refetch } = useQuery<Page<Invoice>>({
    queryKey: ["invoices", page, selectedStatus, search, customerMode],
    queryFn: () => api.get<Page<Invoice>>("/api/billing/invoices", queryParams),
  });

  const sendMutation = useMutation({
    mutationFn: (invoiceId: number) =>
      api.post<{ message: string }>(`/api/billing/invoices/${invoiceId}/send`),
    onSuccess: (res) => {
      setActionNotice(res.message);
      setTimeout(() => setActionNotice(null), 3000);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: (invoiceId: number) =>
      api.post<Invoice>(`/api/billing/invoices/${invoiceId}/confirm`),
    onSuccess: (inv) => {
      setActionNotice(`Invoice ${inv.number} confirmed.`);
      queryClient.invalidateQueries({ queryKey: ["invoices"] });
      setTimeout(() => setActionNotice(null), 3000);
    },
  });

  const invoices = data?.items ?? [];

  // Summary statistics calculation
  const totalAmount = invoices.reduce((sum, inv) => sum + Number(inv.amount_total), 0);
  const overdueCount = invoices.filter((inv) => inv.is_overdue).length;
  const paidCount = invoices.filter((inv) => inv.status === "PAID").length;

  return (
    <div className="space-y-6">
      {/* Top Banner / Actions */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            {customerMode ? "My Invoices" : "Invoices & Billing"}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            {customerMode
              ? "View and download your recurring subscription invoices and payment receipts."
              : "Generate recurring invoices, review dry-runs, and manage customer billing."}
          </p>
        </div>

        {!customerMode && isStaffOrAdmin && (
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => setIsDryRunOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl border border-indigo-200 bg-indigo-50/60 px-4 py-2 text-sm font-semibold text-indigo-700 shadow-xs hover:bg-indigo-100 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Dry-Run Preview
            </button>
            <button
              type="button"
              onClick={() => setIsDryRunOpen(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-indigo-700 transition-colors"
            >
              Run Billing
            </button>
          </div>
        )}
      </div>

      {actionNotice && (
        <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200">
          {actionNotice}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Total Invoices</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">{data?.total ?? 0}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Page Volume</div>
          <div className="mt-1 text-2xl font-bold text-indigo-600">{inr(totalAmount.toFixed(2))}</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Overdue Invoices</div>
          <div className={`mt-1 text-2xl font-bold ${overdueCount > 0 ? "text-amber-600" : "text-slate-900"}`}>
            {overdueCount}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-xs">
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Paid Invoices</div>
          <div className="mt-1 text-2xl font-bold text-emerald-600">{paidCount}</div>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-xs sm:flex-row sm:items-center sm:justify-between">
        {/* Status Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {(["ALL", "CONFIRMED", "PAID", "DRAFT", "CANCELLED"] as const).map((status) => (
            <button
              key={status}
              type="button"
              onClick={() => {
                setSelectedStatus(status);
                setPage(1);
              }}
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-colors ${
                selectedStatus === status
                  ? "bg-indigo-600 text-white shadow-xs"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
              }`}
            >
              {status}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="w-full sm:w-72">
          <input
            type="text"
            placeholder="Search invoice number or customer..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Invoices Table */}
      <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Invoice Number</th>
                {!customerMode && <th className="px-5 py-3">Customer</th>}
                <th className="px-5 py-3">Issue Date</th>
                <th className="px-5 py-3">Due Date</th>
                <th className="px-5 py-3 text-right">Total Amount</th>
                <th className="px-5 py-3 text-right">Balance Due</th>
                <th className="px-5 py-3 text-center">Status</th>
                <th className="px-5 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr>
                  <td colSpan={customerMode ? 7 : 8} className="py-12 text-center text-sm text-slate-400">
                    Loading invoices...
                  </td>
                </tr>
              ) : invoices.length === 0 ? (
                <tr>
                  <td colSpan={customerMode ? 7 : 8} className="py-12 text-center text-sm text-slate-400">
                    No invoices found matching the current filter.
                  </td>
                </tr>
              ) : (
                invoices.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-4 font-semibold text-slate-900">
                      <Link
                        to={customerMode ? `/my/invoices/${inv.id}` : `/invoices/${inv.id}`}
                        className="text-indigo-600 hover:text-indigo-800 hover:underline"
                      >
                        {inv.number}
                      </Link>
                    </td>
                    {!customerMode && (
                      <td className="px-5 py-4 font-medium text-slate-800">
                        {inv.customer?.name ?? `Customer #${inv.customer_id}`}
                      </td>
                    )}
                    <td className="px-5 py-4 text-slate-500">{inv.issue_date}</td>
                    <td className="px-5 py-4">
                      <span className={inv.is_overdue ? "font-semibold text-rose-600" : "text-slate-500"}>
                        {inv.due_date}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right font-semibold text-slate-900">{inr(inv.amount_total)}</td>
                    <td className="px-5 py-4 text-right">
                      <span className={Number(inv.amount_due) > 0 ? "font-semibold text-rose-600" : "text-emerald-600"}>
                        {inr(inv.amount_due)}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-center">
                      <span className={invoiceStatusBadge(inv.status, inv.is_overdue)}>
                        {inv.is_overdue && inv.status !== "PAID" ? "OVERDUE" : inv.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link
                          to={customerMode ? `/my/invoices/${inv.id}` : `/invoices/${inv.id}`}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                        >
                          View
                        </Link>
                        <a
                          href={`/api/billing/invoices/${inv.id}/render`}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-100"
                        >
                          PDF
                        </a>
                        {!customerMode && isStaffOrAdmin && inv.status === "DRAFT" && (
                          <button
                            type="button"
                            onClick={() => confirmMutation.mutate(inv.id)}
                            className="rounded-lg bg-blue-50 px-2.5 py-1 text-xs font-semibold text-blue-700 hover:bg-blue-100"
                          >
                            Confirm
                          </button>
                        )}
                        {!customerMode && isStaffOrAdmin && (
                          <button
                            type="button"
                            onClick={() => sendMutation.mutate(inv.id)}
                            className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-200"
                          >
                            Send
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && data.pages > 1 && (
          <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-5 py-3 text-xs text-slate-600">
            <div>
              Showing page <span className="font-semibold">{data.page}</span> of{" "}
              <span className="font-semibold">{data.pages}</span> ({data.total} total)
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={data.page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={data.page >= data.pages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Dry Run Modal */}
      <DryRunModal
        isOpen={isDryRunOpen}
        onClose={() => setIsDryRunOpen(false)}
        onRunSuccess={() => {
          refetch();
          setActionNotice("Billing run completed successfully.");
          setTimeout(() => setActionNotice(null), 3000);
        }}
      />
    </div>
  );
}

