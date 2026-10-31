import { useQuery } from "@tanstack/react-query";

type Health = {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
};

async function fetchHealth(): Promise<Health> {
  const response = await fetch("/api/health");
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return (await response.json()) as Health;
}

// Placeholder home page. It only proves the web -> API -> database chain works;
// the shared shell (routing, layout, navigation) replaces it.
export default function App() {
  const health = useQuery({ queryKey: ["health"], queryFn: fetchHealth, retry: false });

  let statusText = "Checking the API…";
  let statusClass = "text-slate-500";
  if (health.isSuccess) {
    statusText = "API and database are up";
    statusClass = "text-emerald-600";
  } else if (health.isError) {
    statusText = `API unavailable: ${health.error.message}`;
    statusClass = "text-red-600";
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="text-center">
        <h1 className="text-3xl font-semibold text-slate-900">Brightloop Subscriptions</h1>
        <p className={`mt-3 text-sm ${statusClass}`} role="status">
          {statusText}
        </p>
      </div>
    </main>
  );
}
