import { statusToTone, statusToVerb } from "@/lib/status";

export function StatusPill({
  status,
  dense = false,
}: {
  status: string | null | undefined;
  dense?: boolean;
}) {
  const tone = statusToTone(status);
  const verb = statusToVerb(status);
  return (
    <span className={`status-pill ${tone}${dense ? " dense" : ""}`}>
      <span className="seed" />
      {verb}
    </span>
  );
}
