export function formatPct(value: number, fractionDigits = 2): string {
  if (!Number.isFinite(value)) return "–";
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatRoas(value: number): string {
  if (!Number.isFinite(value)) return "–";
  return `${value.toFixed(2)}×`;
}

export function formatCurrency(value: number, opts?: { compact?: boolean }): string {
  if (!Number.isFinite(value)) return "–";
  if (opts?.compact) {
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}k`;
    return `$${value.toFixed(0)}`;
  }
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

export function formatCount(value: number, opts?: { compact?: boolean }): string {
  if (!Number.isFinite(value)) return "–";
  if (opts?.compact) {
    if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
    if (value >= 1_000) return `${(value / 1_000).toFixed(1)}k`;
    return value.toLocaleString();
  }
  return value.toLocaleString();
}

export function formatDays(value: number): string {
  if (!Number.isFinite(value)) return "–";
  return `${value}d`;
}
