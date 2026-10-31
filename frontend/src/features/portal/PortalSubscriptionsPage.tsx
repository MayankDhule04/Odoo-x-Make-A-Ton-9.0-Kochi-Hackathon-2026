import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  STATUS_COLOR,
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type PortalProduct,
  type PortalSubscription,
  type Preview,
  type SubStatus,
} from "./types.js";

function actionsFor(status: SubStatus): { label: string; path: string }[] {
  switch (status) {
    case "ACTIVE":
      return [
        { label: "Pause", path: "pause" },
        { label: "Cancel", path: "close" },
      ];
    case "PAUSED":
      return [
        { label: "Resume", path: "resume" },
        { label: "Cancel", path: "close" },
      ];
    case "CLOSED":
      return [{ label: "Renew", path: "renew" }];
    default:
      return [];
  }
}

type LineInput = { product_id: string; quantity: string };

function ChangePanel({ sub, onDone }: { sub: PortalSubscription; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [lines, setLines] = useState<LineInput[]>(
    sub.lines.map((l) => ({ product_id: String(l.product_id), quantity: String(l.quantity) })),
  );
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const products = useQuery({
    queryKey: ["portal-products"],
    queryFn: () => api.get<Page<PortalProduct>>("/api/products", { page_size: "100" }),
  });

  function payload() {
    return {
      lines: lines
        .filter((l) => l.product_id)
        .map((l) => ({ product_id: Number(l.product_id), quantity: Number(l.quantity) || 1 })),
    };
  }

  const previewMut = useMutation({
    mutationFn: () => api.post<Preview>(`/api/subscriptions/${sub.id}/change/preview`, payload()),
    onSuccess: (p) => {
      setPreview(p);
      setError(null);
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Preview failed"),
  });
  const applyMut = useMutation({
    mutationFn: () => api.post(`/api/subscriptions/${sub.id}/change`, payload()),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["portal-subscriptions"] });
      onDone();
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Change failed"),
  });

  return (
    <div className={`mt-3 space-y-3 ${cardClass}`}>
      <p className="font-medium text-slate-900">Change plan / quantity</p>
      {error && <div className="rounded-lg bg-red-50 p-2 text-sm text-red-600">{error}</div>}
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
          </div>
        ))}
      </div>
      {preview && (
        <div className="rounded-lg bg-indigo-50 p-3 text-sm text-indigo-900">
          New total {inr(preview.new_total)} · credit {inr(preview.credit)} · charge {inr(preview.charge)} ·
          <span className="font-semibold"> pay now {inr(preview.net)}</span>
        </div>
      )}
      <div className="flex gap-2">
        <button type="button" onClick={() => previewMut.mutate()} className={secondaryBtn}>
          Preview
        </button>
        <button type="button" onClick={() => applyMut.mutate()} className={primaryBtn}>
          Confirm change
        </button>
        <button type="button" onClick={onDone} className={secondaryBtn}>
          Close
        </button>
      </div>
    </div>
  );
}

export default function PortalSubscriptionsPage() {
  const queryClient = useQueryClient();
  const [changingId, setChangingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["portal-subscriptions"],
    queryFn: () => api.get<Page<PortalSubscription>>("/api/subscriptions", { page_size: "100" }),
  });

  const action = useMutation({
    mutationFn: ({ id, path }: { id: number; path: string }) =>
      api.post(`/api/subscriptions/${id}/${path}`, {}),
    onSuccess: () => {
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["portal-subscriptions"] });
    },
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Action failed"),
  });

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900">My Subscriptions</h1>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}
      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load subscriptions.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">You have no subscriptions yet.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {data?.items.map((sub) => (
              <div key={sub.id} className="p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-medium text-slate-800">{sub.number}</span>
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[sub.status]}`}>
                    {sub.status}
                  </span>
                  <span className="text-sm text-slate-500">
                    {sub.start_date} → {sub.expiry_date} · {inr(sub.amount_total)}
                  </span>
                  <div className="ml-auto flex gap-2">
                    {actionsFor(sub.status).map((a) => (
                      <button
                        key={a.path}
                        type="button"
                        onClick={() => action.mutate({ id: sub.id, path: a.path })}
                        className={secondaryBtn}
                      >
                        {a.label}
                      </button>
                    ))}
                    {sub.status === "ACTIVE" && (
                      <button
                        type="button"
                        onClick={() => setChangingId(changingId === sub.id ? null : sub.id)}
                        className={primaryBtn}
                      >
                        Change
                      </button>
                    )}
                  </div>
                </div>
                {changingId === sub.id && <ChangePanel sub={sub} onDone={() => setChangingId(null)} />}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
