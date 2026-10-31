import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "../../api/client.js";
import type { Page } from "../../api/client.js";
import {
  PRODUCT_TYPES,
  cardClass,
  inputClass,
  inr,
  primaryBtn,
  secondaryBtn,
  tableWrap,
  type Product,
  type ProductType,
  type ProductVariant,
} from "./types.js";

const PAGE_SIZE = 25;

type VariantInput = { value: string; price_extra: string };

function emptyVariant(): VariantInput {
  return { value: "", price_extra: "0" };
}

/* ---------------- Create form ---------------- */

function AddProductForm({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [type, setType] = useState<ProductType>("SOFTWARE");
  const [salesPrice, setSalesPrice] = useState("0.00");
  const [costPrice, setCostPrice] = useState("0.00");
  const [notes, setNotes] = useState("");
  const [attributeName, setAttributeName] = useState("");
  const [variants, setVariants] = useState<VariantInput[]>([emptyVariant()]);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (body: unknown) => api.post<Product>("/api/products", body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products"] });
      onClose();
    },
    onError: (err) =>
      setError(err instanceof ApiError ? err.detail : "Failed to create product"),
  });

  function updateVariant(index: number, patch: Partial<VariantInput>) {
    setVariants((vs) => vs.map((v, i) => (i === index ? { ...v, ...patch } : v)));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    mutation.mutate({
      name,
      type,
      sales_price: salesPrice || "0",
      cost_price: costPrice || "0",
      notes,
      attributes: attributeName.trim() ? [{ name: attributeName.trim() }] : [],
      variants: variants
        .filter((v) => v.value.trim())
        .map((v) => ({ value: v.value.trim(), price_extra: v.price_extra || "0" })),
    });
  }

  return (
    <form onSubmit={handleSubmit} className={`mb-4 space-y-3 ${cardClass}`}>
      <h2 className="font-medium text-slate-900">New Product</h2>
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
        <select
          value={type}
          onChange={(e) => setType(e.target.value as ProductType)}
          className={inputClass}
        >
          {PRODUCT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <label className="text-sm text-slate-600">
          Sales price (₹)
          <input
            type="number"
            min="0"
            step="0.01"
            value={salesPrice}
            onChange={(e) => setSalesPrice(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Cost price (₹)
          <input
            type="number"
            min="0"
            step="0.01"
            value={costPrice}
            onChange={(e) => setCostPrice(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
      </div>

      <input
        type="text"
        placeholder="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className={`w-full ${inputClass}`}
      />

      <div className="rounded-lg bg-slate-50 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">Variants</span>
          <input
            type="text"
            placeholder="Attribute (e.g. Brand)"
            value={attributeName}
            onChange={(e) => setAttributeName(e.target.value)}
            className={`w-48 ${inputClass}`}
          />
        </div>
        <div className="space-y-2">
          {variants.map((v, i) => (
            <div key={i} className="flex gap-2">
              <input
                type="text"
                placeholder="Value (e.g. Odoo)"
                value={v.value}
                onChange={(e) => updateVariant(i, { value: e.target.value })}
                className={`flex-1 ${inputClass}`}
              />
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="Price extra"
                value={v.price_extra}
                onChange={(e) => updateVariant(i, { price_extra: e.target.value })}
                className={`w-32 ${inputClass}`}
              />
              <button
                type="button"
                onClick={() => setVariants((vs) => vs.filter((_, idx) => idx !== i))}
                className="rounded-lg px-2 text-slate-400 hover:text-red-600"
                aria-label="Remove variant"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setVariants((vs) => [...vs, emptyVariant()])}
          className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-700"
        >
          + Add variant
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

/* ---------------- Editor (scalar fields + variants + attributes) ---------------- */

function VariantRow({ productId, variant }: { productId: number; variant: ProductVariant }) {
  const queryClient = useQueryClient();
  const [value, setValue] = useState(variant.value);
  const [priceExtra, setPriceExtra] = useState(variant.price_extra);

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["product", productId] });
    void queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  const save = useMutation({
    mutationFn: () =>
      api.patch<ProductVariant>(`/api/products/${productId}/variants/${variant.id}`, {
        value,
        price_extra: priceExtra,
      }),
    onSuccess: invalidate,
  });
  const remove = useMutation({
    mutationFn: () => api.delete<void>(`/api/products/${productId}/variants/${variant.id}`),
    onSuccess: invalidate,
  });

  return (
    <div className="flex items-center gap-2">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className={`flex-1 ${inputClass}`}
      />
      <input
        type="number"
        min="0"
        step="0.01"
        value={priceExtra}
        onChange={(e) => setPriceExtra(e.target.value)}
        className={`w-28 ${inputClass}`}
      />
      <span className="w-28 text-sm text-slate-500">= {inr(variant.effective_price)}</span>
      <button
        type="button"
        onClick={() => save.mutate()}
        disabled={save.isPending}
        className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
      >
        Save
      </button>
      <button
        type="button"
        onClick={() => remove.mutate()}
        className="text-sm font-medium text-red-600 hover:text-red-700"
      >
        Delete
      </button>
    </div>
  );
}

function ProductEditor({ productId, onClose }: { productId: number; onClose: () => void }) {
  const queryClient = useQueryClient();
  const { data: product } = useQuery({
    queryKey: ["product", productId],
    queryFn: () => api.get<Product>(`/api/products/${productId}`),
  });

  const [name, setName] = useState("");
  const [type, setType] = useState<ProductType>("SOFTWARE");
  const [salesPrice, setSalesPrice] = useState("0.00");
  const [costPrice, setCostPrice] = useState("0.00");
  const [notes, setNotes] = useState("");
  const [newVariant, setNewVariant] = useState<VariantInput>(emptyVariant());
  const [newAttribute, setNewAttribute] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      setName(product.name);
      setType(product.type);
      setSalesPrice(product.sales_price);
      setCostPrice(product.cost_price);
      setNotes(product.notes);
    }
  }, [product]);

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["product", productId] });
    void queryClient.invalidateQueries({ queryKey: ["products"] });
  }

  const saveScalars = useMutation({
    mutationFn: () =>
      api.patch<Product>(`/api/products/${productId}`, {
        name,
        type,
        sales_price: salesPrice,
        cost_price: costPrice,
        notes,
      }),
    onSuccess: invalidate,
    onError: (err) => setError(err instanceof ApiError ? err.detail : "Failed to save"),
  });
  const addVariant = useMutation({
    mutationFn: () =>
      api.post<ProductVariant>(`/api/products/${productId}/variants`, {
        value: newVariant.value.trim(),
        price_extra: newVariant.price_extra || "0",
      }),
    onSuccess: () => {
      setNewVariant(emptyVariant());
      invalidate();
    },
  });
  const addAttribute = useMutation({
    mutationFn: () =>
      api.post(`/api/products/${productId}/attributes`, { name: newAttribute.trim() }),
    onSuccess: () => {
      setNewAttribute("");
      invalidate();
    },
  });
  const removeAttribute = useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/products/${productId}/attributes/${id}`),
    onSuccess: invalidate,
  });

  if (!product) {
    return <div className={`mb-4 ${cardClass}`}>Loading…</div>;
  }

  return (
    <div className={`mb-4 space-y-4 ${cardClass}`}>
      <div className="flex items-center justify-between">
        <h2 className="font-medium text-slate-900">Edit “{product.name}”</h2>
        <button type="button" onClick={onClose} className={secondaryBtn}>
          Close
        </button>
      </div>
      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600">{error}</div>}

      {/* Scalar fields */}
      <div className="grid gap-3 sm:grid-cols-2">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={inputClass}
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value as ProductType)}
          className={inputClass}
        >
          {PRODUCT_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <label className="text-sm text-slate-600">
          Sales price (₹)
          <input
            type="number"
            min="0"
            step="0.01"
            value={salesPrice}
            onChange={(e) => setSalesPrice(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
        <label className="text-sm text-slate-600">
          Cost price (₹)
          <input
            type="number"
            min="0"
            step="0.01"
            value={costPrice}
            onChange={(e) => setCostPrice(e.target.value)}
            className={`mt-1 w-full ${inputClass}`}
          />
        </label>
      </div>
      <input
        type="text"
        placeholder="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        className={`w-full ${inputClass}`}
      />
      <button
        type="button"
        onClick={() => saveScalars.mutate()}
        disabled={saveScalars.isPending}
        className={primaryBtn}
      >
        {saveScalars.isPending ? "Saving…" : "Save details"}
      </button>

      {/* Variants */}
      <div className="rounded-lg bg-slate-50 p-3">
        <p className="mb-2 text-sm font-medium text-slate-700">Variants</p>
        <div className="space-y-2">
          {product.variants.map((v) => (
            <VariantRow key={v.id} productId={productId} variant={v} />
          ))}
          {product.variants.length === 0 && (
            <p className="text-sm text-slate-400">No variants.</p>
          )}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <input
            type="text"
            placeholder="New variant value"
            value={newVariant.value}
            onChange={(e) => setNewVariant((v) => ({ ...v, value: e.target.value }))}
            className={`flex-1 ${inputClass}`}
          />
          <input
            type="number"
            min="0"
            step="0.01"
            placeholder="Price extra"
            value={newVariant.price_extra}
            onChange={(e) => setNewVariant((v) => ({ ...v, price_extra: e.target.value }))}
            className={`w-28 ${inputClass}`}
          />
          <button
            type="button"
            onClick={() => newVariant.value.trim() && addVariant.mutate()}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            + Add
          </button>
        </div>
      </div>

      {/* Attributes */}
      <div className="rounded-lg bg-slate-50 p-3">
        <p className="mb-2 text-sm font-medium text-slate-700">Attributes</p>
        <div className="flex flex-wrap gap-2">
          {product.attributes.map((a) => (
            <span
              key={a.id}
              className="inline-flex items-center gap-1 rounded-full bg-white px-3 py-1 text-sm text-slate-700 ring-1 ring-slate-200"
            >
              {a.name}
              <button
                type="button"
                onClick={() => removeAttribute.mutate(a.id)}
                className="text-slate-400 hover:text-red-600"
                aria-label={`Remove ${a.name}`}
              >
                ✕
              </button>
            </span>
          ))}
          {product.attributes.length === 0 && (
            <span className="text-sm text-slate-400">No attributes.</span>
          )}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <input
            type="text"
            placeholder="New attribute (e.g. Brand)"
            value={newAttribute}
            onChange={(e) => setNewAttribute(e.target.value)}
            className={`w-64 ${inputClass}`}
          />
          <button
            type="button"
            onClick={() => newAttribute.trim() && addAttribute.mutate()}
            className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
          >
            + Add
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Panel ---------------- */

export default function ProductsPanel() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["products", page],
    queryFn: () =>
      api.get<Page<Product>>("/api/products", {
        page: String(page),
        page_size: String(PAGE_SIZE),
      }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete<void>(`/api/products/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["products"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-500">
          Products, their variants and the effective price (base + variant extra).
        </p>
        <button
          type="button"
          onClick={() => {
            setEditingId(null);
            setShowForm((v) => !v);
          }}
          className={primaryBtn}
        >
          {showForm ? "Close" : "Add Product"}
        </button>
      </div>

      {showForm && <AddProductForm onClose={() => setShowForm(false)} />}
      {editingId !== null && (
        <ProductEditor productId={editingId} onClose={() => setEditingId(null)} />
      )}

      <div className={tableWrap}>
        {isLoading ? (
          <p className="p-6 text-sm text-slate-500">Loading…</p>
        ) : isError ? (
          <p className="p-6 text-sm text-red-600">Failed to load products.</p>
        ) : data && data.items.length === 0 ? (
          <p className="p-8 text-center text-sm text-slate-400">No products yet.</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Sales</th>
                <th className="px-4 py-3">Cost</th>
                <th className="px-4 py-3">Margin</th>
                <th className="px-4 py-3">Variants</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.items.map((p) => (
                <tr key={p.id} className="align-top">
                  <td className="px-4 py-3 font-medium text-slate-800">{p.name}</td>
                  <td className="px-4 py-3 text-slate-600">{p.type}</td>
                  <td className="px-4 py-3 text-slate-700">{inr(p.sales_price)}</td>
                  <td className="px-4 py-3 text-slate-700">{inr(p.cost_price)}</td>
                  <td className="px-4 py-3 text-emerald-700">{inr(p.margin)}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {p.variants.length === 0 ? (
                      "—"
                    ) : (
                      <ul className="space-y-0.5">
                        {p.variants.map((v) => (
                          <li key={v.id}>
                            {v.value}:{" "}
                            <span className="font-medium text-slate-800">
                              {inr(v.effective_price)}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right whitespace-nowrap">
                    <button
                      type="button"
                      onClick={() => {
                        setShowForm(false);
                        setEditingId(p.id);
                      }}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (confirm(`Delete product "${p.name}"?`)) deleteMutation.mutate(p.id);
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
