/* Customer portal types (#8). Money/amounts arrive as strings. */

export type SubStatus = "DRAFT" | "QUOTATION" | "CONFIRMED" | "ACTIVE" | "PAUSED" | "CLOSED";

export type PortalLine = {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: string;
  amount: string;
};

export type PortalSubscription = {
  id: number;
  number: string;
  plan_id: number;
  status: SubStatus;
  start_date: string;
  expiry_date: string;
  next_billing_date: string | null;
  amount_total: string;
  lines: PortalLine[];
};

export type PortalInvoice = {
  id: number;
  number: string;
  status: string;
  issue_date: string;
  due_date: string;
  amount_total: string;
  amount_paid: string;
  amount_due: string;
  is_overdue: boolean;
};

export type PortalProduct = { id: number; name: string };

export type Preview = {
  remaining_fraction: string;
  old_total: string;
  new_total: string;
  credit: string;
  charge: string;
  net: string;
};

export type PaymentMethod = "CARD" | "BANK_TRANSFER" | "UPI" | "CASH" | "CHEQUE";
export const PAYMENT_METHODS: PaymentMethod[] = ["CARD", "BANK_TRANSFER", "UPI", "CASH", "CHEQUE"];

export const STATUS_COLOR: Record<SubStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-600",
  QUOTATION: "bg-amber-100 text-amber-700",
  CONFIRMED: "bg-blue-100 text-blue-700",
  ACTIVE: "bg-emerald-100 text-emerald-700",
  PAUSED: "bg-orange-100 text-orange-700",
  CLOSED: "bg-slate-200 text-slate-500",
};

export function inr(v: string | number): string {
  return `₹${v}`;
}

export const inputClass =
  "rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 focus:outline-none";
export const primaryBtn =
  "rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50";
export const secondaryBtn =
  "rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-50";
export const cardClass = "rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200";
export const tableWrap = "overflow-x-auto rounded-xl bg-white shadow-sm ring-1 ring-slate-200";
