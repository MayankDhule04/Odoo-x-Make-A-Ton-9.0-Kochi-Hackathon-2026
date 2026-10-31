import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  cardClass,
  inputClass,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type PickPlan,
  type PickProduct,
  type Template,
} from "./types.js";

type LineInput = { product_id: string; quantity: string };

function CreateTemplateForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [planId, setPlanId] = useState("");
  const [validityDays, setValidityDays] = useState("30");
  const [lines, setLines] = useState<LineInput[]>([{ product_id: "", quantity: "1" }]);
  const [error, setError] = useState<string | null>(null);

  const plans = useQuery({
    queryKey: ["plans", "pick"],
    queryFn: () => api.get<Page<PickPlan>>("/api/plans", { page_size: "100" }),
  });
  const products = useQuery({
    queryKey: ["products", "pick"],
    queryFn: () => api.get<Page<PickProduct>>("/api/products", { page_size: "100" }),
  });

  const mutation = useMutation({
    mutationFn: (body: unknown) => api.post<Template>("/api/quotation-templates", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["quotation-templates"] });
      onClose();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Failed to create template"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      name,
      plan_id: Number(planId),
      validity_days: Number(validityDays) || 30,
      lines: lines
        .filter((l) => l.product_id)
        .map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity) || 1 })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">New Quotation Template</h2>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-3">
        <input
          type="text"
          placeholder="Name *"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
        />
        <select
          required
          value={planId}
          onChange={(e) => setPlanId(e.target.value)}
          className={inputClass}
        >
          <option value="">Plan…</option>
          {(plans.data?.items ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
        <label className="text-sm text-slate-600">
          Validity (days)
          <input
            type="number"
            min="1"
            value={validityDays}
            onChange={(e) => setValidityDays(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
      </div>

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
          className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          + Add line
        </button>
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

export default function QuotationTemplatesPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quotation-templates"],
    queryFn: () => api.get<Page<Template>>("/api/quotation-templates", { page_size: "100" }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/quotation-templates/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["quotation-templates"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Quotation Templates</h1>
          <p className="text-sm text-slate-500">
            Presets of a plan and product lines. Create a subscription from one in seconds.
          </p>
        </div>
        <button type="button" onClick={() => setShowForm((v) => !v)} className={primaryBtn}>
          {showForm ? "Close" : "New Template"}
        </button>
      </div>

      {showForm && <CreateTemplateForm onClose={() => setShowForm(false)} />}

      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load templates.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No templates yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Plan</th>
                <th className="px-4 py-3">Validity</th>
                <th className="px-4 py-3">Lines</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((t) => (
                <tr key={t.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{t.name}</td>
                  <td className="px-4 py-3 text-slate-600">#{t.plan_id}</td>
                  <td className="px-4 py-3 text-slate-600">{t.validity_days} days</td>
                  <td className="px-4 py-3 text-slate-600">{t.lines.length}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Delete template "${t.name}"?`)) deleteMutation.mutate(t.id);
                      }}
                      className="text-sm font-medium text-red-600 hover:text-red-700"
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
