import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  cardClass,
  inputClass,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type Tax,
  type TaxAppliesTo,
} from "./types.js";

function TaxForm({ editing, onClose }: { editing: Tax | null; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [percentage, setPercentage] = useState("18.000");
  const [appliesTo, setAppliesTo] = useState<TaxAppliesTo>("PRODUCT");
  const [inclusive, setInclusive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (editing) {
      setName(editing.name);
      setPercentage(editing.percentage);
      setAppliesTo(editing.applies_to);
      setInclusive(editing.inclusive);
    }
  }, [editing]);

  const mutation = useMutation({
    mutationFn: (body: unknown) =>
      editing
        ? api.patch<Tax>(`/api/taxes/${editing.id}`, body)
        : api.post<Tax>("/api/taxes", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["taxes"] });
      onClose();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Failed to save tax"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate({ name, percentage, applies_to: appliesTo, inclusive });
  }

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">{editing ? "Edit" : "New"} Tax Rule</h2>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="text"
          placeholder="Name * (e.g. GST 18%)"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
        />
        <label className="text-sm text-slate-600">
          Percentage
          <input
            type="number"
            min="0"
            step="0.001"
            value={percentage}
            onChange={(e) => setPercentage(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <select
          value={appliesTo}
          onChange={(e) => setAppliesTo(e.target.value as TaxAppliesTo)}
          className={inputClass}
        >
          <option value="PRODUCT">Applies to: Product</option>
          <option value="CATEGORY">Applies to: Category</option>
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input
            type="checkbox"
            checked={inclusive}
            onChange={(e) => setInclusive(e.target.checked)}
            className="h-4 w-4 rounded border-slate-300"
          />
          Tax inclusive
        </label>
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

export default function TaxesPanel() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Tax | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["taxes"],
    queryFn: () => api.get<Page<Tax>>("/api/taxes", { page_size: "100" }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/taxes/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["taxes"] }),
  });

  function startEdit(tax: Tax) {
    setEditing(tax);
    setShowForm(true);
  }

  function closeForm() {
    setShowForm(false);
    setEditing(null);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Admin-defined tax rules. Billing applies these per invoice line.
        </p>
        <button
          type="button"
          onClick={() => (showForm ? closeForm() : setShowForm(true))}
          className={primaryBtn}
        >
          {showForm ? "Close" : "Add Tax"}
        </button>
      </div>

      {showForm && <TaxForm editing={editing} onClose={closeForm} />}

      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load taxes.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No tax rules yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Percentage</th>
                <th className="px-4 py-3">Applies to</th>
                <th className="px-4 py-3">Inclusive</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((t) => (
                <tr key={t.id}>
                  <td className="px-4 py-3 font-medium text-slate-800">{t.name}</td>
                  <td className="px-4 py-3 text-slate-700">{t.percentage}%</td>
                  <td className="px-4 py-3 text-slate-600">{t.applies_to}</td>
                  <td className="px-4 py-3 text-slate-600">{t.inclusive ? "Yes" : "No"}</td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => startEdit(t)}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Delete tax "${t.name}"?`)) deleteMutation.mutate(t.id);
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
