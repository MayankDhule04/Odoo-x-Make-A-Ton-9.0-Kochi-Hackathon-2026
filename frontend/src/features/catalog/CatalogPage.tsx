import { useState } from "react";

import DiscountsPanel from "./DiscountsPanel.js";
import ProductsPanel from "./ProductsPanel.js";
import TaxesPanel from "./TaxesPanel.js";

type Tab = "products" | "taxes" | "discounts";

const TABS: { id: Tab; label: string }[] = [
  { id: "products", label: "Products" },
  { id: "taxes", label: "Taxes" },
  { id: "discounts", label: "Discounts" },
];

export default function CatalogPage() {
  const [tab, setTab] = useState<Tab>("products");

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-semibold text-slate-900">Catalog</h1>

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

      {tab === "products" && <ProductsPanel />}
      {tab === "taxes" && <TaxesPanel />}
      {tab === "discounts" && <DiscountsPanel />}
    </div>
  );
}
