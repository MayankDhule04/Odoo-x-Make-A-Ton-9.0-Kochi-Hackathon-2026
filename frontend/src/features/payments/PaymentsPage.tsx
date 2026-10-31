import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  PAYMENT_METHODS,
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type DunningAttempt,
  type InvoicePick,
  type Payment,
  type PaymentMethod,
  type PaymentStatusSummary,
  type RevenueAtRisk,
} from "./types.js";

type Tab = "payments" | "risk" | "dunning";

/* ---------------- Summary cards ---------------- */

function SummaryCards() {
  const { data } = useQuery({
    queryKey: ["payment-summary"],
    queryFn: () => api.get<PaymentStatusSummary>("/api/payments/summary"),
  });
  if (!data) return null;
  const cards = [
    { label: "Paid", value: String(data.paid) },
    { label: "Partially paid", value: String(data.partially_paid) },
    { label: "Outstanding", value: inr(data.total_outstanding) },
    { label: "Overdue", value: inr(data.total_overdue) },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((c) => (
        <div key={c.label} className={cardClass}>
          <p className="text-xs uppercase text-slate-400">{c.label}</p>
          <p className="text-xl font-semibold text-slate-900">{c.value}</p>
        </div>
      ))}
    </div>
  );
}

/* ---------------- Payments tab ---------------- */

function RecordPaymentForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [invoiceId, setInvoiceId] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("UPI");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const invoices = useQuery({
    queryKey: ["invoices", "payable"],
    queryFn: () => api.get<Page<InvoicePick>>("/api/invoices", { status: "CONFIRMED", page_size: "100" }),
  });

  const mutation = useMutation({
    mutationFn: (body: unknown) => api.post<Payment>("/api/payments", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["payments"] });
      void queryClient.invalidateQueries({ queryKey: ["payment-summary"] });
      void queryClient.invalidateQueries({ queryKey: ["invoices"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed to record payment"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      invoice_id: Number(invoiceId),
      amount,
      method,
      ...(note ? { note } : {}),
    });
  }

  const payable = (invoices.data?.items ?? []).filter((i) => Number(i.amount_due) > 0);

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">Record Payment</h2>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-slate-600">
          Invoice
          <select
            required
            value={invoiceId}
            onChange={(e) => setInvoiceId(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          >
            <option value="">Select…</option>
            {payable.map((i) => (
              <option key={i.id} value={i.id}>
                {i.number} · due {inr(i.amount_due)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-600">
          Amount (₹)
          <input
            type="number"
            min="0.01"
            step="0.01"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Method
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value as PaymentMethod)}
            className={`mt-1 w-full ${inputClass}`}
          >
            {PAYMENT_METHODS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-600">
          Note
          <input value={note} onChange={(e) => setNote(e.target.value)} className={`mt-1 w-full ${inputClass}`} />
        </label>
      </div>
      <div className="flex gap-2">
        <button type="submit" disabled={mutation.isPending} className={primaryBtn}>
          {mutation.isPending ? "Recording…" : "Record"}
        </button>
        <button type="button" onClick={onClose} className={secondaryBtn}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function PaymentsTab() {
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: ["payments"],
    queryFn: () => api.get<Page<Payment>>("/api/payments", { page_size: "100" }),
  });

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button type="button" onClick={() => setShowForm((v) => !v)} className={primaryBtn}>
          {showForm ? "Close" : "Record Payment"}
        </button>
      </div>
      {showForm && <RecordPaymentForm onClose={() => setShowForm(false)} />}
      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No payments yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Method</th>
                <th className="px-4 py-3">Paid on</th>
                <th className="px-4 py-3">Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3 text-slate-700">#{p.invoice_id}</td>
                  <td className="px-4 py-3 text-slate-800">{inr(p.amount)}</td>
                  <td className="px-4 py-3 text-slate-600">{p.method}</td>
                  <td className="px-4 py-3 text-slate-600">{p.paid_at}</td>
                  <td className="px-4 py-3 text-slate-500">{p.note ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/* ---------------- Revenue-at-risk tab ---------------- */

function RiskTab() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["revenue-at-risk"],
    queryFn: () => api.get<RevenueAtRisk>("/api/payments/revenue-at-risk"),
  });
  const remind = useMutation({
    mutationFn: (sid: number) => api.post(`/api/payments/revenue-at-risk/${sid}/remind`),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["dunning"] });
    },
  });

  return (
    <div className="space-y-4">
      {data && (
        <div className={cardClass}>
          <p className="text-xs uppercase text-slate-400">Total at risk</p>
          <p className="text-2xl font-semibold text-red-600">{inr(data.total_at_risk)}</p>
        </div>
      )}
      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">Nothing overdue. 🎉</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Subscription</th>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Overdue amount</th>
                <th className="px-4 py-3">Days late</th>
                <th className="px-4 py-3">Invoices</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((i) => (
                <tr key={i.subscription_id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{i.subscription_number}</td>
                  <td className="px-4 py-3 text-slate-600">{i.customer_name}</td>
                  <td className="px-4 py-3 font-semibold text-red-600">{inr(i.overdue_amount)}</td>
                  <td className="px-4 py-3 text-slate-600">{i.days_overdue}</td>
                  <td className="px-4 py-3 text-slate-600">{i.invoice_count}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => remind.mutate(i.subscription_id)}
                      disabled={remind.isPending}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      Send reminder
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/* ---------------- Dunning tab ---------------- */

function DunningTab() {
  const queryClient = useQueryClient();
  const [msg, setMsg] = useState<string | null>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["dunning"],
    queryFn: () => api.get<Page<DunningAttempt>>("/api/payments/dunning", { page_size: "100" }),
  });
  const run = useMutation({
    mutationFn: () => api.post<{ reminders_sent: number; suspensions: number; invoices_processed: number }>(
      "/api/payments/dunning/run",
      {},
    ),
    onSuccess: (r) => {
      setMsg(
        `Processed ${r.invoices_processed} invoice(s): ${r.reminders_sent} reminder(s), ${r.suspensions} suspension(s).`,
      );
      void queryClient.invalidateQueries({ queryKey: ["dunning"] });
      void queryClient.invalidateQueries({ queryKey: ["revenue-at-risk"] });
      void queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Reminders go out on days 1, 3, 5, 7 after the due date; the subscription is
          suspended after the final notice.
        </p>
        <button type="button" onClick={() => run.mutate()} disabled={run.isPending} className={primaryBtn}>
          {run.isPending ? "Running…" : "Run dunning now"}
        </button>
      </div>
      {msg && <div className="rounded-lg bg-indigo-50 p-3 text-sm text-indigo-900">{msg}</div>}
      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No dunning activity yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Kind</th>
                <th className="px-4 py-3">Attempt</th>
                <th className="px-4 py-3">Days overdue</th>
                <th className="px-4 py-3">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3 text-slate-700">#{d.invoice_id}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        d.kind === "SUSPENSION" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {d.kind}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{d.attempt_number || "—"}</td>
                  <td className="px-4 py-3 text-slate-600">{d.days_overdue}</td>
                  <td className="px-4 py-3 text-slate-500">{new Date(d.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/* ---------------- Page ---------------- */

const TABS: { id: Tab; label: string }[] = [
  { id: "payments", label: "Payments" },
  { id: "risk", label: "Revenue at risk" },
  { id: "dunning", label: "Dunning" },
];

export default function PaymentsPage() {
  const [tab, setTab] = useState<Tab>("payments");
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold text-slate-900">Payments</h1>
      <SummaryCards />

      <div className="flex gap-1 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.id
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "payments" && <PaymentsTab />}
      {tab === "risk" && <RiskTab />}
      {tab === "dunning" && <DunningTab />}
    </div>
  );
}
