/* Subscription domain types (Member 2). Money/amount arrive as strings. */

export type SubscriptionStatus =
  | "DRAFT"
  | "QUOTATION"
  | "CONFIRMED"
  | "ACTIVE"
  | "PAUSED"
  | "CLOSED";

export type PaymentTerms = "IMMEDIATE" | "NET_15" | "NET_30";

export const PAYMENT_TERMS: PaymentTerms[] = ["IMMEDIATE", "NET_15", "NET_30"];

export type SubscriptionLine = {
  id: number;
  product_id: number;
  variant_id: number | null;
  tax_id: number | null;
  quantity: number;
  unit_price: string;
  amount: string;
};

export type Subscription = {
  id: number;
  number: string;
  customer_id: number;
  plan_id: number;
  start_date: string;
  expiry_date: string;
  next_billing_date: string | null;
  payment_terms: PaymentTerms;
  status: SubscriptionStatus;
  amount_total: string;
  lines: SubscriptionLine[];
};

export type SubscriptionHistoryEntry = {
  id: number;
  from_status: SubscriptionStatus | null;
  to_status: SubscriptionStatus;
  actor_id: number | null;
  note: string | null;
  created_at: string;
};

export type SubscriptionDetail = Subscription & {
  history: SubscriptionHistoryEntry[];
};

export type TemplateLine = {
  id: number;
  product_id: number;
  variant_id: number | null;
  quantity: number;
  unit_price: string | null;
};

export type Template = {
  id: number;
  name: string;
  plan_id: number;
  validity_days: number;
  notes: string;
  lines: TemplateLine[];
};

/* Minimal shapes for pickers (from catalog endpoints). */
export type PickCustomer = { id: number; name: string };
export type PickPlan = { id: number; name: string };
export type PickProduct = { id: number; name: string };

export const STATUS_COLOR: Record<SubscriptionStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-600",
  QUOTATION: "bg-amber-100 text-amber-700",
  CONFIRMED: "bg-blue-100 text-blue-700",
  ACTIVE: "bg-emerald-100 text-emerald-700",
  PAUSED: "bg-orange-100 text-orange-700",
  CLOSED: "bg-slate-200 text-slate-500",
};

export function inr(amount: string | number): string {
  return `₹${amount}`;
}

export const inputClass =
  "rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none";
export const primaryBtn =
  "rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50";
export const secondaryBtn =
  "rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50";
export const cardClass = "rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200";
export const tableWrap = "overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200";

export function statusBadgeClass(status: SubscriptionStatus): string {
  return `inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[status]}`;
}
