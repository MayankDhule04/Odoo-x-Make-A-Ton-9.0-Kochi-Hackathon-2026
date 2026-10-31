import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  PAYMENT_TERMS,
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  statusBadgeClass,
  tableWrap,
  type PaymentTerms,
  type PickCustomer,
  type PickPlan,
  type PickProduct,
  type Subscription,
  type Template,
} from "./types.js";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function plusDays(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

type LineInput = { product_id: string; quantity: string };

function usePickers() {
  const customers = useQuery({
    queryKey: ["customers", "pick"],
    queryFn: () => api.get<Page<PickCustomer>>("/api/customers", { page_size: "100" }),
  });
  const plans = useQuery({
    queryKey: ["plans", "pick"],
    queryFn: () => api.get<Page<PickPlan>>("/api/plans", { page_size: "100" }),
  });
  const products = useQuery({
    queryKey: ["products", "pick"],
    queryFn: () => api.get<Page<PickProduct>>("/api/products", { page_size: "100" }),
  });
  const templates = useQuery({
    queryKey: ["quotation-templates", "pick"],
    queryFn: () => api.get<Page<Template>>("/api/quotation-templates", { page_size: "100" }),
  });
  return {
    customers: customers.data?.items ?? [],
    plans: plans.data?.items ?? [],
    products: products.data?.items ?? [],
    templates: templates.data?.items ?? [],
  };
}

function CreatePanel({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const { customers, plans, products, templates } = usePickers();
  const [mode, setMode] = useState<"manual" | "template">("manual");
  const [error, setError] = useState<string | null>(null);

  const [customerId, setCustomerId] = useState("");
  const [planId, setPlanId] = useState("");
  const [startDate, setStartDate] = useState(today());
  const [expiryDate, setExpiryDate] = useState(plusDays(30));
  const [paymentTerms, setPaymentTerms] = useState<PaymentTerms>("IMMEDIATE");
  const [lines, setLines] = useState<LineInput[]>([{ product_id: "", quantity: "1" }]);
  const [templateId, setTemplateId] = useState("");

  const mutation = useMutation({
    mutationFn: (body: { url: string; payload: unknown }) =>
      api.post<Subscription>(body.url, body.payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
      onClose();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Failed to create subscription"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "template") {
      mutation.mutate({
        url: "/api/subscriptions/from-template",
        payload: {
          template_id: Number(templateId),
          customer_id: Number(customerId),
          start_date: startDate,
          payment_terms: paymentTerms,
        },
      });
    } else {
      mutation.mutate({
        url: "/api/subscriptions",
        payload: {
          customer_id: Number(customerId),
          plan_id: Number(planId),
          start_date: startDate,
          expiry_date: expiryDate,
          payment_terms: paymentTerms,
          lines: lines
            .filter((l) => l.product_id)
            .map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity) || 1 })),
        },
      });
    }
  }

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <div className="flex items-center gap-2">
        <h2 className="font-medium text-slate-900">New Subscription</h2>
        <div className="ml-auto flex gap-1 rounded-lg bg-slate-100 p-0.5 text-sm">
          <button
            type="button"
            onClick={() => setMode("manual")}
            className={`rounded px-3 py-1 ${mode === "manual" ? "bg-white shadow-sm" : "text-slate-500"}`}
          >
            Manual
          </button>
          <button
            type="button"
            onClick={() => setMode("template")}
            className={`rounded px-3 py-1 ${mode === "template" ? "bg-white shadow-sm" : "text-slate-500"}`}
          >
            From template
          </button>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm text-slate-600">
          Customer
          <select
            required
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          >
            <option value="">Select…</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>

        {mode === "manual" ? (
          <label className="text-sm text-slate-600">
            Plan
            <select
              required
              value={planId}
              onChange={(e) => setPlanId(e.target.value)}
              className={`mt-1 w-full ${inputClass}`}
            >
              <option value="">Select…</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="text-sm text-slate-600">
            Template
            <select
              required
              value={templateId}
              onChange={(e) => setTemplateId(e.target.value)}
              className={`mt-1 w-full ${inputClass}`}
            >
              <option value="">Select…</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="text-sm text-slate-600">
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        {mode === "manual" && (
          <label className="text-sm text-slate-600">
            Expiry date
            <input
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
              className={`mt-1 w-full ${inputClass}`}
            />
          </label>
        )}
        <label className="text-sm text-slate-600">
          Payment terms
          <select
            value={paymentTerms}
            onChange={(e) => setPaymentTerms(e.target.value as PaymentTerms)}
            className={`mt-1 w-full ${inputClass}`}
          >
            {PAYMENT_TERMS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
      </div>

      {mode === "manual" && (
        <div className="rounded-lg bg-slate-50 p-3">
          <p className="mb-2 text-sm font-medium text-slate-700">Lines</p>
          <div className="space-y-2">
            {lines.map((l, i) => (
              <div key={i} className="flex gap-2">
                <select
                  value={l.product_id}
                  onChange={(e) =>
                    setLines((ls) => ls.map((x, idx) => (idx === i ? { ...x, product_id: e.target.value } : x)))
                  }
                  className={`flex-1 ${inputClass}`}
                >
                  <option value="">Product…</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min="1"
                  value={l.quantity}
                  onChange={(e) =>
                    setLines((ls) => ls.map((x, idx) => (idx === i ? { ...x, quantity: e.target.value } : x)))
                  }
                  className={`w-24 ${inputClass}`}
                />
                <button
                  type="button"
                  onClick={() => setLines((ls) => ls.filter((_, idx) => idx !== i))}
                  className="rounded-lg px-2 text-slate-400 hover:text-red-600"
                  aria-label="Remove line"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <button
            type="button"
            onClick={() => setLines((ls) => [...ls, { product_id: "", quantity: "1" }])}
            className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            + Add line
          </button>
        </div>
      )}

      <div className="flex gap-2">
        <button type="submit" disabled={mutation.isPending} className={primaryBtn}>
          {mutation.isPending ? "Creating…" : "Create"}
        </button>
        <button type="button" onClick={onClose} className={secondaryBtn}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function SubscriptionsPage() {
  const navigate = useNavigate();
  const [showForm, setShowForm] = useState(false);
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["subscriptions", page],
    queryFn: () =>
      api.get<Page<Subscription>>("/api/subscriptions", {
        page: String(page),
        page_size: "25",
      }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Subscriptions</h1>
        <button type="button" onClick={() => setShowForm((v) => !v)} className={primaryBtn}>
          {showForm ? "Close" : "New Subscription"}
        </button>
      </div>

      {showForm && <CreatePanel onClose={() => setShowForm(false)} />}

      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load subscriptions.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No subscriptions yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Number</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Start</th>
                <th className="px-4 py-3">Expiry</th>
                <th className="px-4 py-3">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((s) => (
                <tr
                  key={s.id}
                  className="cursor-pointer hover:bg-slate-50"
                  onClick={() => navigate(`/subscriptions/${s.id}`)}
                >
                  <td className="px-4 py-3 font-medium text-indigo-700">{s.number}</td>
                  <td className="px-4 py-3">
                    <span className={statusBadgeClass(s.status)}>{s.status}</span>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{s.start_date}</td>
                  <td className="px-4 py-3 text-slate-600">{s.expiry_date}</td>
                  <td className="px-4 py-3 text-slate-700">{inr(s.amount_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">
            Page {data.page} of {data.pages} ({data.total} total)
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className={secondaryBtn}
            >
              Previous
            </button>
            <button
              type="button"
              disabled={page >= data.pages}
              onClick={() => setPage((p) => p + 1)}
              className={secondaryBtn}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
