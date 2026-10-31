/* Payments domain types (Member 3). Money arrives as strings. */

export type PaymentMethod = "CARD" | "BANK_TRANSFER" | "UPI" | "CASH" | "CHEQUE";
export const PAYMENT_METHODS: PaymentMethod[] = ["CARD", "BANK_TRANSFER", "UPI", "CASH", "CHEQUE"];

export type Payment = {
  id: number;
  invoice_id: number;
  customer_id: number;
  amount: string;
  method: PaymentMethod;
  paid_at: string;
  note: string | null;
  created_at: string;
};

export type PaymentStatusSummary = {
  paid: number;
  partially_paid: number;
  outstanding: number;
  overdue: number;
  total_outstanding: string;
  total_overdue: string;
};

export type DunningKind = "REMINDER" | "SUSPENSION";

export type DunningAttempt = {
  id: number;
  invoice_id: number;
  subscription_id: number | null;
  attempt_number: number;
  kind: DunningKind;
  days_overdue: number;
  note: string | null;
  created_at: string;
};

export type RevenueAtRiskItem = {
  subscription_id: number;
  subscription_number: string;
  customer_id: number;
  customer_name: string;
  overdue_amount: string;
  days_overdue: number;
  invoice_count: number;
};

export type RevenueAtRisk = {
  total_at_risk: string;
  items: RevenueAtRiskItem[];
};

/* Minimal invoice shape for the payment picker. */
export type InvoicePick = {
  id: number;
  number: string;
  status: string;
  amount_total: string;
  amount_due: string;
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
