type Props = {
  title: string;
  description?: string;
};

export default function PlaceholderPage({ title, description }: Props) {
  return (
    <div className="rounded-xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      {description && (
        <p className="mt-2 text-sm text-slate-500">{description}</p>
      )}
    </div>
  );
}
