import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type Discount,
  type DiscountTarget,
  type DiscountType,
} from "./types.js";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function AddDiscountForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState<DiscountType>("PERCENTAGE");
  const [value, setValue] = useState("10.00");
  const [minPurchase, setMinPurchase] = useState("0.00");
  const [minQty, setMinQty] = useState("0");
  const [startDate, setStartDate] = useState(today());
  const [endDate, setEndDate] = useState(today());
  const [usageLimit, setUsageLimit] = useState("0");
  const [target, setTarget] = useState<DiscountTarget>("SUBSCRIPTION");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: unknown) => api.post<Discount>("/api/discounts", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["discounts"] });
      onClose();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Failed to create discount"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      name,
      type,
      value,
      min_purchase_amount: minPurchase || "0",
      min_quantity: Number(minQty) || 0,
      start_date: startDate,
      end_date: endDate,
      usage_limit: Number(usageLimit) || 0,
      target,
    });
  }

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">New Discount Rule</h2>
      {error && (
        <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>
      )}
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="text"
          placeholder="Name * (e.g. Launch 10%)"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value as DiscountType)}
          className={inputClass}
        >
          <option value="PERCENTAGE">Percentage</option>
          <option value="FIXED">Fixed amount</option>
        </select>
        <label className="text-sm text-slate-600">
          {type === "PERCENTAGE" ? "Percent" : "Amount (₹)"}
          <input
            type="number"
            min="0"
            step="0.01"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <select
          value={target}
          onChange={(e) => setTarget(e.target.value as DiscountTarget)}
          className={inputClass}
        >
          <option value="SUBSCRIPTION">Target: whole subscription</option>
          <option value="PRODUCT">Target: specific products</option>
        </select>
        <label className="text-sm text-slate-600">
          Min purchase (₹)
          <input
            type="number"
            min="0"
            step="0.01"
            value={minPurchase}
            onChange={(e) => setMinPurchase(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Min quantity
          <input
            type="number"
            min="0"
            value={minQty}
            onChange={(e) => setMinQty(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Start date
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          End date
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Usage limit (0 = unlimited)
          <input
            type="number"
            min="0"
            value={usageLimit}
            onChange={(e) => setUsageLimit(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
      </div>
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

export default function DiscountsPanel() {
  const [showForm, setShowForm] = useState(false);
  const { data, isLoading, isError } = useQuery({
    queryKey: ["discounts"],
    queryFn: () => api.get<Page<Discount>>("/api/discounts", { page_size: "100" }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Admin-only discount rules. They apply automatically on the next invoice and
          stop at expiry or the usage limit.
        </p>
        <button type="button" onClick={() => setShowForm((v) => !v)} className={primaryBtn}>
          {showForm ? "Close" : "Add Discount"}
        </button>
      </div>

      {showForm && <AddDiscountForm onClose={() => setShowForm(false)} />}

      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load discounts.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No discount rules yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Value</th>
                <th className="px-4 py-3">Window</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Usage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{d.name}</td>
                  <td className="px-4 py-3 text-slate-600">{d.type}</td>
                  <td className="px-4 py-3 text-slate-700">
                    {d.type === "PERCENTAGE" ? `${d.value}%` : inr(d.value)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {d.start_date} → {d.end_date}
                  </td>
                  <td className="px-4 py-3 text-slate-600">{d.target}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {d.usage_count}
                    {d.usage_limit > 0 ? ` / ${d.usage_limit}` : ""}
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
