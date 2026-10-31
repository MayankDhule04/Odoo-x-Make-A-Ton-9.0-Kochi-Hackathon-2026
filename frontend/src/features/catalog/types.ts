/* Catalog domain types (Member 2). Mirror the backend read schemas.
   Money arrives as a string like "1560.00". */

export type ProductType = "SERVICE" | "SOFTWARE" | "ADDON" | "PHYSICAL";
export type BillingPeriod = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
export type TaxAppliesTo = "PRODUCT" | "CATEGORY";
export type DiscountType = "FIXED" | "PERCENTAGE";
export type DiscountTarget = "PRODUCT" | "SUBSCRIPTION";

export type ProductAttribute = {
  id: number;
  name: string;
};

export type ProductVariant = {
  id: number;
  value: string;
  price_extra: string;
  attribute_id: number | null;
  effective_price: string;
};

export type Product = {
  id: number;
  name: string;
  type: ProductType;
  sales_price: string;
  cost_price: string;
  notes: string;
  margin: string;
  attributes: ProductAttribute[];
  variants: ProductVariant[];
};

export type Plan = {
  id: number;
  name: string;
  price: string;
  billing_period: BillingPeriod;
  min_quantity: number;
  available_from: string;
  available_to: string;
  auto_close: boolean;
  allow_early_close: boolean;
  allow_pause: boolean;
  allow_renew: boolean;
};

export type Tax = {
  id: number;
  name: string;
  percentage: string;
  applies_to: TaxAppliesTo;
  inclusive: boolean;
};

export type Discount = {
  id: number;
  name: string;
  type: DiscountType;
  value: string;
  min_purchase_amount: string;
  min_quantity: number;
  start_date: string;
  end_date: string;
  usage_limit: number;
  usage_count: number;
  target: DiscountTarget;
  product_ids: number[];
};

export const PRODUCT_TYPES: ProductType[] = ["SERVICE", "SOFTWARE", "ADDON", "PHYSICAL"];
export const BILLING_PERIODS: BillingPeriod[] = ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"];

export function inr(amount: string | number): string {
  return `₹${amount}`;
}

/* Shared Tailwind class strings so the forms stay consistent. */
export const inputClass =
  "rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none";
export const primaryBtn =
  "rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50";
export const secondaryBtn =
  "rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50";
export const cardClass =
  "rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200";
export const tableWrap =
  "overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200";
