import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, getAccessToken } from "../api/client.js";
import { useAuth } from "../lib/auth-context.js";

type DashboardSummary = {
  active_subscriptions: number;
  revenue_collected: string;
  amount_owed: string;
  overdue_count: number;
  overdue_amount: string;
  customers: number;
};

type WaterfallEntry = {
  month: string;
  new: string;
  expansion: string;
  contraction: string;
  churn: string;
  net: string;
};

type MrrAnalytics = {
  mrr: string;
  arr: string;
  arpu: string;
  active_subscriptions: number;
  active_customers: number;
  churn_rate: string;
  waterfall: WaterfallEntry[];
};

const card = "rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200";

function inr(v: string | number): string {
  return `₹${v}`;
}

async function downloadCsv(url: string, filename: string): Promise<void> {
  const token = getAccessToken();
  const res = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    credentials: "include",
  });
  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = href;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(href);
}

export default function DashboardPage() {
  const { user } = useAuth();

  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => api.get<DashboardSummary>("/api/reporting/dashboard"),
  });
  const mrr = useQuery({
    queryKey: ["dashboard-mrr"],
    queryFn: () => api.get<MrrAnalytics>("/api/reporting/mrr"),
  });

  const kpis = [
    { label: "Active Subscriptions", value: summary.data ? String(summary.data.active_subscriptions) : "—" },
    { label: "Revenue Collected", value: summary.data ? inr(summary.data.revenue_collected) : "—" },
    { label: "Amount Owed", value: summary.data ? inr(summary.data.amount_owed) : "—" },
    {
      label: "Overdue",
      value: summary.data ? `${inr(summary.data.overdue_amount)} (${summary.data.overdue_count})` : "—",
    },
    { label: "MRR", value: mrr.data ? inr(mrr.data.mrr) : "—" },
    { label: "ARR", value: mrr.data ? inr(mrr.data.arr) : "—" },
    { label: "ARPU", value: mrr.data ? inr(mrr.data.arpu) : "—" },
    { label: "Churn rate", value: mrr.data ? `${mrr.data.churn_rate}%` : "—" },
  ];

  const chartData = (mrr.data?.waterfall ?? []).map((w) => ({
    month: w.month,
    New: Number(w.new),
    Expansion: Number(w.expansion),
    Contraction: Number(w.contraction),
    Churn: Number(w.churn),
    Net: Number(w.net),
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Finance Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">Welcome, {user?.full_name}</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => downloadCsv("/api/reporting/invoices.csv", "invoices.csv")}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            Export invoices CSV
          </button>
          <button
            type="button"
            onClick={() => downloadCsv("/api/reporting/payments.csv", "payments.csv")}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            Export payments CSV
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className={card}>
            <p className="text-sm font-medium text-slate-500">{kpi.label}</p>
            <p className="mt-2 text-2xl font-semibold text-slate-900">{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className={card}>
        <h2 className="mb-4 text-lg font-semibold text-slate-900">
          MRR movement (New / Expansion / Contraction / Churn)
        </h2>
        {chartData.length === 0 ? (
          <p className="text-sm text-slate-400">No MRR data yet.</p>
        ) : (
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" fontSize={12} />
                <YAxis fontSize={12} />
                <Tooltip />
                <Legend />
                <Bar dataKey="New" fill="#10b981" />
                <Bar dataKey="Expansion" fill="#6366f1" />
                <Bar dataKey="Contraction" fill="#f59e0b" />
                <Bar dataKey="Churn" fill="#ef4444" />
                <Bar dataKey="Net" fill="#334155" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
