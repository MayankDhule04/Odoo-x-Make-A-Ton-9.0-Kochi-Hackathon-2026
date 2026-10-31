import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  statusBadgeClass,
  tableWrap,
  type PickProduct,
  type SubscriptionDetail,
  type SubscriptionLine,
  type SubscriptionStatus,
} from "./types.js";

type Action = { label: string; url: string; body?: unknown; style?: "primary" | "secondary" };

function actionsFor(id: number, status: SubscriptionStatus): Action[] {
  switch (status) {
    case "DRAFT":
      return [{ label: "Submit as quotation", url: `/api/subscriptions/${id}/submit` }];
    case "QUOTATION":
      return [
        { label: "Confirm", url: `/api/subscriptions/${id}/confirm` },
        {
          label: "Back to draft",
          url: `/api/subscriptions/${id}/transition`,
          body: { to_status: "DRAFT" },
          style: "secondary",
        },
      ];
    case "CONFIRMED":
      return [
        { label: "Activate", url: `/api/subscriptions/${id}/activate` },
        { label: "Close", url: `/api/subscriptions/${id}/close`, style: "secondary" },
      ];
    case "ACTIVE":
      return [
        { label: "Pause", url: `/api/subscriptions/${id}/pause`, style: "secondary" },
        { label: "Close", url: `/api/subscriptions/${id}/close`, style: "secondary" },
      ];
    case "PAUSED":
      return [
        { label: "Resume", url: `/api/subscriptions/${id}/resume` },
        { label: "Close", url: `/api/subscriptions/${id}/close`, style: "secondary" },
      ];
    case "CLOSED":
      return [{ label: "Renew", url: `/api/subscriptions/${id}/renew` }];
    default:
      return [];
  }
}

type Preview = {
  remaining_fraction: string;
  old_total: string;
  new_total: string;
  credit: string;
  charge: string;
  net: string;
};

type LineInput = { product_id: string; quantity: string };

function ChangePanel({
  subscriptionId,
  currentLines,
}: {
  subscriptionId: number;
  currentLines: SubscriptionLine[];
}) {
  const queryClient = useQueryClient();
  const [lines, setLines] = useState<LineInput[]>(
    currentLines.map((l) => ({ product_id: String(l.product_id), quantity: String(l.quantity) })),
  );
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const products = useQuery({
    queryKey: ["products", "pick"],
    queryFn: () => api.get<Page<PickProduct>>("/api/products", { page_size: "100" }),
  });

  function payload() {
    return {
      lines: lines
        .filter((l) => l.product_id)
        .map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity) || 1 })),
    };
  }

  const previewMutation = useMutation({
    mutationFn: () => api.post<Preview>(`/api/subscriptions/${subscriptionId}/change/preview`, payload()),
    onSuccess: (p) => {
      setPreview(p);
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Preview failed"),
  });

  const applyMutation = useMutation({
    mutationFn: () => api.post(`/api/subscriptions/${subscriptionId}/change`, payload()),
    onSuccess: () => {
      setPreview(null);
      void queryClient.invalidateQueries({ queryKey: ["subscription", subscriptionId] });
      void queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Change failed"),
  });

  return (
    <div className={`space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">Change plan / quantity (prorated)</h2>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

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
              {(products.data?.items ?? []).map((p) => (
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
        className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
      >
        + Add line
      </button>

      {preview && (
        <div className="rounded-lg bg-indigo-50 p-3 text-sm text-indigo-900">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
            <span>Old total: {inr(preview.old_total)}</span>
            <span>New total: {inr(preview.new_total)}</span>
            <span>Credit: {inr(preview.credit)}</span>
            <span>Charge: {inr(preview.charge)}</span>
          </div>
          <p className="mt-1 font-semibold">
            Net now: {inr(preview.net)} ({(Number(preview.remaining_fraction) * 100).toFixed(1)}% of
            period remaining)
          </p>
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={() => previewMutation.mutate()}
          disabled={previewMutation.isPending}
          className={secondaryBtn}
        >
          {previewMutation.isPending ? "Previewing…" : "Preview"}
        </button>
        <button
          type="button"
          onClick={() => applyMutation.mutate()}
          disabled={applyMutation.isPending}
          className={primaryBtn}
        >
          {applyMutation.isPending ? "Applying…" : "Apply change"}
        </button>
      </div>
    </div>
  );
}

export default function SubscriptionDetailPage() {
  const { id } = useParams();
  const subscriptionId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const { data: sub, isLoading, isError } = useQuery({
    queryKey: ["subscription", subscriptionId],
    queryFn: () => api.get<SubscriptionDetail>(`/api/subscriptions/${subscriptionId}`),
  });

  const action = useMutation({
    mutationFn: (a: Action) => api.post(a.url, a.body ?? {}),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["subscription", subscriptionId] });
      void queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Action failed"),
  });

  if (isLoading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (isError || !sub) return <p className="text-sm text-red-600">Subscription not found.</p>;

  const actions = actionsFor(sub.id, sub.status);

  return (
    <div className="space-y-5">
      <button
        type="button"
        onClick={() => navigate("/subscriptions")}
        className="text-sm text-slate-500 hover:text-slate-700"
      >
        ← Back to subscriptions
      </button>

      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-slate-900">{sub.number}</h1>
        <span className={statusBadgeClass(sub.status)}>{sub.status}</span>
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Lifecycle actions */}
      {actions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {actions.map((a) => (
            <button
              key={a.label}
              type="button"
              disabled={action.isPending}
              onClick={() => action.mutate(a)}
              className={a.style === "secondary" ? secondaryBtn : primaryBtn}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}

      {/* Summary */}
      <div className={`grid gap-4 sm:grid-cols-2 lg:grid-cols-4 ${cardClass}`}>
        <div>
          <p className="text-xs uppercase text-slate-400">Start</p>
          <p className="text-slate-800">{sub.start_date}</p>
        </div>
        <div>
          <p className="text-xs uppercase text-slate-400">Expiry</p>
          <p className="text-slate-800">{sub.expiry_date}</p>
        </div>
        <div>
          <p className="text-xs uppercase text-slate-400">Next billing</p>
          <p className="text-slate-800">{sub.next_billing_date ?? "—"}</p>
        </div>
        <div>
          <p className="text-xs uppercase text-slate-400">Payment terms</p>
          <p className="text-slate-800">{sub.payment_terms}</p>
        </div>
      </div>

      {/* Lines */}
      <div className={tableWrap}>
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">Product</th>
              <th className="px-4 py-3">Variant</th>
              <th className="px-4 py-3">Qty</th>
              <th className="px-4 py-3">Unit price</th>
              <th className="px-4 py-3">Amount</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sub.lines.map((l) => (
              <tr key={l.id}>
                <td className="px-4 py-3 text-slate-700">#{l.product_id}</td>
                <td className="px-4 py-3 text-slate-600">{l.variant_id ? `#${l.variant_id}` : "—"}</td>
                <td className="px-4 py-3 text-slate-600">{l.quantity}</td>
                <td className="px-4 py-3 text-slate-700">{inr(l.unit_price)}</td>
                <td className="px-4 py-3 text-slate-700">{inr(l.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-slate-200">
              <td colSpan={4} className="px-4 py-3 text-right font-medium text-slate-600">
                Total
              </td>
              <td className="px-4 py-3 font-semibold text-slate-900">{inr(sub.amount_total)}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Mid-cycle change with proration (only while active) */}
      {sub.status === "ACTIVE" && (
        <ChangePanel subscriptionId={sub.id} currentLines={sub.lines} />
      )}

      {/* Timeline */}
      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Timeline</h2>
        <ol className="space-y-3">
          {sub.history.map((h) => (
            <li key={h.id} className="flex gap-3">
              <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-indigo-500" />
              <div className="text-sm">
                <p className="text-slate-800">
                  {h.from_status ? `${h.from_status} → ` : "Created · "}
                  <span className="font-medium">{h.to_status}</span>
                </p>
                <p className="text-xs text-slate-400">
                  {new Date(h.created_at).toLocaleString()}
                  {h.actor_id ? ` · user #${h.actor_id}` : ""}
                  {h.note ? ` · ${h.note}` : ""}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
