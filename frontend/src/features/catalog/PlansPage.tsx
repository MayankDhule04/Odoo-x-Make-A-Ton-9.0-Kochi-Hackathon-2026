import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  BILLING_PERIODS,
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type BillingPeriod,
  type Plan,
} from "./types.js";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function plusDays(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

const FLAGS = [
  { key: "auto_close", label: "Auto-close when it ends" },
  { key: "allow_early_close", label: "Allow early close" },
  { key: "allow_pause", label: "Allow pause" },
  { key: "allow_renew", label: "Allow renew" },
] as const;

type FlagKey = (typeof FLAGS)[number]["key"];

function PlanForm({ editing, onClose }: { editing: Plan | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [price, setPrice] = useState("0.00");
  const [billingPeriod, setBillingPeriod] = useState<BillingPeriod>("MONTHLY");
  const [minQty, setMinQty] = useState("1");
  const [availableFrom, setAvailableFrom] = useState(today());
  const [availableTo, setAvailableTo] = useState(plusDays(365));
  const [flags, setFlags] = useState<Record<FlagKey, boolean>>({
    auto_close: true,
    allow_early_close: true,
    allow_pause: true,
    allow_renew: true,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editing) {
      setName(editing.name);
      setPrice(editing.price);
      setBillingPeriod(editing.billing_period);
      setMinQty(String(editing.min_quantity));
      setAvailableFrom(editing.available_from);
      setAvailableTo(editing.available_to);
      setFlags({
        auto_close: editing.auto_close,
        allow_early_close: editing.allow_early_close,
        allow_pause: editing.allow_pause,
        allow_renew: editing.allow_renew,
      });
    }
  }, [editing]);

  const mutation = useMutation({
    mutationFn: (body: unknown) =>
      editing
        ? api.patch<Plan>(`/api/plans/${editing.id}`, body)
        : api.post<Plan>("/api/plans", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["plans"] });
      onClose();
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed to save plan"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      name,
      price,
      billing_period: billingPeriod,
      min_quantity: Number(minQty) || 1,
      available_from: availableFrom,
      available_to: availableTo,
      ...flags,
    });
  }

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">{editing ? "Edit" : "New"} Plan</h2>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="text"
          placeholder="Name *"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
        />
        <label className="text-sm text-slate-600">
          Price (₹)
          <input
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <select
          value={billingPeriod}
          onChange={(e) => setBillingPeriod(e.target.value as BillingPeriod)}
          className={inputClass}
        >
          {BILLING_PERIODS.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <label className="text-sm text-slate-600">
          Minimum quantity
          <input
            type="number"
            min="1"
            value={minQty}
            onChange={(e) => setMinQty(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Available from
          <input
            type="date"
            value={availableFrom}
            onChange={(e) => setAvailableFrom(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Available to
          <input
            type="date"
            value={availableTo}
            onChange={(e) => setAvailableTo(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {FLAGS.map((f) => (
          <label key={f.key} className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={flags[f.key]}
              onChange={(e) => setFlags((prev) => ({ ...prev, [f.key]: e.target.checked }))}
              className="h-4 w-4 rounded border-slate-300"
            />
            {f.label}
          </label>
        ))}
      </div>

      <div className="flex gap-2">
        <button type="submit" disabled={mutation.isPending} className={primaryBtn}>
          {mutation.isPending ? "Saving…" : editing ? "Save" : "Create"}
        </button>
        <button type="button" onClick={onClose} className={secondaryBtn}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function PlansPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Plan | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["plans"],
    queryFn: () => api.get<Page<Plan>>("/api/plans", { page_size: "100" }),
  });

  const selectableQuery = useQuery({
    queryKey: ["plans", "selectable"],
    queryFn: () => api.get<Plan[]>("/api/plans/selectable"),
  });
  const selectableIds = new Set((selectableQuery.data ?? []).map((p) => p.id));

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/plans/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["plans"] }),
  });

  function startEdit(plan: Plan) {
    setEditing(plan);
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Plans</h1>
          <p className="text-sm text-slate-500">
            A plan outside its availability window can't be used for new subscriptions.
          </p>
        </div>
        <button
          type="button"
          onClick={() => (showForm ? closeForm() : setShowForm(true))}
          className={primaryBtn}
        >
          {showForm ? "Close" : "Add Plan"}
        </button>
      </div>

      {showForm && <PlanForm editing={editing} onClose={closeForm} />}

      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load plans.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No plans yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Period</th>
                <th className="px-4 py-3">Min qty</th>
                <th className="px-4 py-3">Window</th>
                <th className="px-4 py-3">Flags</th>
                <th className="px-4 py-3">Selectable now</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((p) => (
                <tr key={p.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{p.name}</td>
                  <td className="px-4 py-3 text-slate-700">{inr(p.price)}</td>
                  <td className="px-4 py-3 text-slate-600">{p.billing_period}</td>
                  <td className="px-4 py-3 text-slate-600">{p.min_quantity}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {p.available_from} → {p.available_to}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {[
                      p.auto_close && "auto-close",
                      p.allow_early_close && "early-close",
                      p.allow_pause && "pause",
                      p.allow_renew && "renew",
                    ]
                      .filter(Boolean)
                      .join(", ") || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        selectableIds.has(p.id)
                          ? "bg-emerald-100 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {selectableIds.has(p.id) ? "Yes" : "No"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => startEdit(p)}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Delete plan "${p.name}"?`)) deleteMutation.mutate(p.id);
                      }}
                      className="ml-3 text-sm font-medium text-red-600 hover:text-red-700"
                    >
                      Delete
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
