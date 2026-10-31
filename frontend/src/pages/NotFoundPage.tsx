import { Link } from "react-router";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-slate-900">404</h1>
        <p className="mt-3 text-slate-500">
          The page you're looking for doesn't exist.
        </p>
        <Link
          to="/"
          className="mt-6 inline-block rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
