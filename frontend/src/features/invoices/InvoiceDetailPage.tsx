import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router";

import { api } from "../../api/client.js";
import { useAuth } from "../../lib/auth-context.js";
import type { InvoiceDetail } from "./types.js";
import { inr, invoiceStatusBadge } from "./types.js";

type Props = {
  customerMode?: boolean;
};

export default function InvoiceDetailPage({ customerMode = false }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const isStaffOrAdmin = user?.role === "ADMIN" || user?.role === "STAFF";

  const [notification, setNotification] = useState<string | null>(null);

  const { data: invoice, isLoading, error } = useQuery<InvoiceDetail>({
    queryKey: ["invoice-detail", id],
    queryFn: () => api.get<InvoiceDetail>(`/api/billing/invoices/${id}`),
    enabled: !!id,
  });

  const confirmMutation = useMutation({
    mutationFn: () => api.post<InvoiceDetail>(`/api/billing/invoices/${id}/confirm`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice-detail", id] });
      setNotification("Invoice has been confirmed.");
      setTimeout(() => setNotification(null), 3000);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (reason: string) =>
      api.post<InvoiceDetail>(`/api/billing/invoices/${id}/cancel`, { note: reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice-detail", id] });
      setNotification("Invoice has been cancelled.");
      setTimeout(() => setNotification(null), 3000);
    },
  });

  const sendMutation = useMutation({
    mutationFn: () => api.post<{ message: string }>(`/api/billing/invoices/${id}/send`),
    onSuccess: (res) => {
      setNotification(res.message);
      setTimeout(() => setNotification(null), 3000);
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-500">
        Loading invoice details...
      </div>
    );
  }

  if (error || !invoice) {
    return (
      <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-center">
        <h2 className="text-base font-bold text-rose-800">Invoice not found</h2>
        <p className="mt-1 text-sm text-rose-600">
          The requested invoice does not exist or you do not have permission to view it.
        </p>
        <Link
          to={customerMode ? "/my/invoices" : "/invoices"}
          className="mt-4 inline-block text-sm font-semibold text-rose-700 underline"
        >
          Return to invoices
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      {/* Top Action Bar */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(customerMode ? "/my/invoices" : "/invoices")}
            className="rounded-xl border border-slate-200 bg-white p-2 text-slate-600 shadow-xs hover:bg-slate-50"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">{invoice.number}</h1>
              <span className={invoiceStatusBadge(invoice.status, invoice.is_overdue)}>
                {invoice.is_overdue && invoice.status !== "PAID" ? "OVERDUE" : invoice.status}
              </span>
            </div>
            <p className="text-xs text-slate-500">Issued on {invoice.issue_date}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <a
            href={`/api/billing/invoices/${invoice.id}/render`}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50"
          >
            <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Print / PDF
          </a>

          {!customerMode && isStaffOrAdmin && (
            <>
              <button
                type="button"
                disabled={sendMutation.isPending}
                onClick={() => sendMutation.mutate()}
                className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 shadow-xs hover:bg-slate-50 disabled:opacity-50"
              >
                <svg className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {sendMutation.isPending ? "Sending..." : "Send Email"}
              </button>

              {invoice.status === "DRAFT" && (
                <button
                  type="button"
                  disabled={confirmMutation.isPending}
                  onClick={() => confirmMutation.mutate()}
                  className="rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-blue-700 disabled:opacity-50"
                >
                  Confirm Invoice
                </button>
              )}

              {invoice.status !== "CANCELLED" && invoice.status !== "PAID" && (
                <button
                  type="button"
                  disabled={cancelMutation.isPending}
                  onClick={() => {
                    if (window.confirm("Are you sure you want to cancel this invoice?")) {
                      cancelMutation.mutate("Cancelled by user");
                    }
                  }}
                  className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                >
                  Cancel
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {notification && (
        <div className="rounded-xl bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-800 ring-1 ring-emerald-200">
          {notification}
        </div>
      )}

      {/* Invoice Document Box */}
      <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-xs sm:p-10">
        {/* Document Header */}
        <div className="flex flex-col gap-6 border-b border-slate-100 pb-8 sm:flex-row sm:justify-between">
          <div>
            <div className="text-xl font-extrabold text-indigo-600">Brightloop Subscriptions</div>
            <p className="text-xs text-slate-500">Automated Subscription & Billing Engine</p>
          </div>

          <div className="text-left sm:text-right">
            <div className="font-mono text-xl font-bold text-slate-900">{invoice.number}</div>
            <div className="mt-1 text-xs text-slate-500">
              Payment Terms: <span className="font-semibold text-slate-700">{invoice.subscription_id ? "Recurring" : "Standard"}</span>
            </div>
            {invoice.subscription_id && (
              <div className="mt-0.5 text-xs text-slate-500">
                Subscription:{" "}
                <Link
                  to={`/subscriptions/${invoice.subscription_id}`}
                  className="font-semibold text-indigo-600 hover:underline"
                >
                  View Subscription #{invoice.subscription_id}
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Customer & Dates Grid */}
        <div className="grid grid-cols-1 gap-6 py-8 sm:grid-cols-2">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Billed To</div>
            <div className="mt-2 text-base font-bold text-slate-900">
              {invoice.customer?.name ?? `Customer #${invoice.customer_id}`}
            </div>
            <div className="text-sm text-slate-600">{invoice.customer?.email}</div>
            {invoice.customer?.billing_address && (
              <div className="mt-1 text-sm text-slate-500 whitespace-pre-line">
                {invoice.customer.billing_address}
              </div>
            )}
          </div>

          <div className="space-y-2 text-left sm:text-right">
            <div>
              <span className="text-xs text-slate-400">Issue Date:</span>{" "}
              <span className="text-sm font-semibold text-slate-800">{invoice.issue_date}</span>
            </div>
            <div>
              <span className="text-xs text-slate-400">Due Date:</span>{" "}
              <span className={`text-sm font-semibold ${invoice.is_overdue ? "text-rose-600" : "text-slate-800"}`}>
                {invoice.due_date}
              </span>
            </div>
            {invoice.period_start && invoice.period_end && (
              <div>
                <span className="text-xs text-slate-400">Billing Period:</span>{" "}
                <span className="text-xs font-medium text-slate-600">
                  {invoice.period_start} to {invoice.period_end}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Line Items Table */}
        <div className="overflow-x-auto rounded-2xl border border-slate-100">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <tr>
                <th className="px-5 py-3">Item Description</th>
                <th className="px-5 py-3 text-center">Qty</th>
                <th className="px-5 py-3 text-right">Unit Price</th>
                <th className="px-5 py-3 text-right">Tax</th>
                <th className="px-5 py-3 text-right">Discount</th>
                <th className="px-5 py-3 text-right">Line Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {invoice.lines.map((line) => (
                <tr key={line.id} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3.5 font-medium text-slate-900">{line.description}</td>
                  <td className="px-5 py-3.5 text-center text-slate-600">{line.quantity}</td>
                  <td className="px-5 py-3.5 text-right text-slate-600">{inr(line.unit_price)}</td>
                  <td className="px-5 py-3.5 text-right text-slate-600">{inr(line.tax_amount)}</td>
                  <td className="px-5 py-3.5 text-right text-emerald-600">
                    {Number(line.discount_amount) > 0 ? `-${inr(line.discount_amount)}` : "—"}
                  </td>
                  <td className="px-5 py-3.5 text-right font-semibold text-slate-900">{inr(line.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Totals Summary */}
        <div className="mt-8 flex justify-end">
          <div className="w-full max-w-xs space-y-2 text-sm">
            <div className="flex justify-between text-slate-600">
              <span>Subtotal:</span>
              <span className="font-medium text-slate-800">{inr(invoice.amount_subtotal)}</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>Tax Total:</span>
              <span className="font-medium text-slate-800">{inr(invoice.amount_tax)}</span>
            </div>
            {Number(invoice.amount_discount) > 0 && (
              <div className="flex justify-between text-emerald-600">
                <span>Discount Total:</span>
                <span className="font-medium">-{inr(invoice.amount_discount)}</span>
              </div>
            )}
            <div className="flex justify-between border-t border-slate-200 pt-3 text-base font-bold text-slate-900">
              <span>Total Amount:</span>
              <span>{inr(invoice.amount_total)}</span>
            </div>
            <div className="flex justify-between text-xs text-slate-500">
              <span>Amount Paid:</span>
              <span>{inr(invoice.amount_paid)}</span>
            </div>
            <div className="flex justify-between border-t border-slate-100 pt-2 font-bold">
              <span className="text-slate-900">Balance Due:</span>
              <span className={Number(invoice.amount_due) > 0 ? "text-rose-600" : "text-emerald-600"}>
                {inr(invoice.amount_due)}
              </span>
            </div>
          </div>
        </div>

        {/* Notes */}
        {invoice.notes && (
          <div className="mt-8 rounded-xl bg-slate-50 p-4 text-xs text-slate-600">
            <span className="font-bold text-slate-700">Notes:</span> {invoice.notes}
          </div>
        )}
      </div>
    </div>
  );
}

