import type { PasswordPolicy } from "../api/client.js";

type Props = {
  password: string;
  policy: PasswordPolicy;
};

export function PasswordChecklist({ password, policy }: Props) {
  const checks = [
    {
      label: `At least ${policy.min_length} characters`,
      passed: password.length >= policy.min_length,
    },
    {
      label: `At most ${policy.max_length} characters`,
      passed: password.length > 0 && password.length <= policy.max_length,
    },
    ...(policy.requires_uppercase
      ? [{ label: "Contains an uppercase letter", passed: /[A-Z]/.test(password) }]
      : []),
    ...(policy.requires_lowercase
      ? [{ label: "Contains a lowercase letter", passed: /[a-z]/.test(password) }]
      : []),
    ...(policy.requires_special
      ? [
          {
            label: "Contains a special character",
            passed: /[^A-Za-z0-9]/.test(password),
          },
        ]
      : []),
  ];

  return (
    <ul className="mt-2 space-y-1 text-sm" aria-label="Password requirements">
      {checks.map((c) => (
        <li key={c.label} className="flex items-center gap-2">
          <span className={c.passed ? "text-green-600" : "text-slate-400"}>
            {c.passed ? "✓" : "✗"}
          </span>
          <span className={c.passed ? "text-green-700" : "text-slate-500"}>
            {c.label}
          </span>
        </li>
      ))}
    </ul>
  );
}
