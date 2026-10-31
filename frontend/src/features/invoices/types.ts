/* Invoice & billing types (Member 3). */

export type InvoiceStatus = "DRAFT" | "CONFIRMED" | "PAID" | "CANCELLED";

export type InvoiceLine = {
  id: number;
  invoice_id: number;
  product_id: number | null;
  variant_id: number | null;
  tax_id: number | null;
  description: string;
  quantity: number;
  unit_price: string;
  tax_rate: string;
  tax_amount: string;
  discount_amount: string;
  amount: string;
  line_type: string;
};

export type InvoiceCustomer = {
  id: number;
  name: string;
  email: string;
  billing_address: string | null;
  phone: string | null;
};

export type Invoice = {
  id: number;
  number: string;
  customer_id: number;
  subscription_id: number | null;
  status: InvoiceStatus;
  issue_date: string;
  due_date: string;
  period_start: string | null;
  period_end: string | null;
  currency: string;
  amount_subtotal: string;
  amount_tax: string;
  amount_discount: string;
  amount_total: string;
  amount_paid: string;
  amount_due: string;
  is_overdue: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
  lines: InvoiceLine[];
  customer?: InvoiceCustomer;
};

export type InvoiceDetail = Invoice;

export type DryRunInvoiceItem = {
  subscription_id: number;
  subscription_number: string;
  customer_id: number;
  customer_name: string;
  period_start: string;
  period_end: string;
  due_date: string;
  amount_subtotal: string;
  amount_tax: string;
  amount_discount: string;
  amount_total: string;
  lines_count: number;
};

export type DryRunExceptionItem = {
  subscription_id: number;
  subscription_number: string;
  customer_id: number;
  customer_name: string;
  error_code: string;
  severity: "WARNING" | "BLOCKER";
  message: string;
  recommendation: string;
};

export type DryRunResponse = {
  as_of_date: string;
  projected_invoices_count: number;
  projected_total_amount: string;
  exceptions_count: number;
  projected_invoices: DryRunInvoiceItem[];
  exceptions: DryRunExceptionItem[];
};

export type BillingRunResponse = {
  as_of_date: string;
  created_count: number;
  skipped_count: number;
  total_amount: string;
  invoices: Invoice[];
};

export const INVOICE_STATUS_COLOR: Record<InvoiceStatus, string> = {
  DRAFT: "bg-slate-100 text-slate-700 border-slate-200",
  CONFIRMED: "bg-blue-50 text-blue-700 border-blue-200",
  PAID: "bg-emerald-50 text-emerald-700 border-emerald-200",
  CANCELLED: "bg-rose-50 text-rose-700 border-rose-200",
};

export function inr(amount: string | number | undefined): string {
  if (amount === undefined || amount === null) return "₹0.00";
  return `₹${amount}`;
}

export function invoiceStatusBadge(status: InvoiceStatus, isOverdue: boolean = false): string {
  if (isOverdue && status !== "PAID" && status !== "CANCELLED") {
    return "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300";
  }
  return `inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border ${INVOICE_STATUS_COLOR[status] ?? "bg-slate-100 text-slate-700"}`;
}
