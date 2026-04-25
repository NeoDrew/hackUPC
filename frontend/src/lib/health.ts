export type HealthBand = "low" | "mid" | "high";

export function healthBand(value: number): HealthBand {
  if (value >= 70) return "high";
  if (value >= 40) return "mid";
  return "low";
}

export function healthColor(value: number): string {
  switch (healthBand(value)) {
    case "high":
      return "var(--health-high-b)";
    case "mid":
      return "var(--health-mid-a)";
    case "low":
      return "var(--health-low-a)";
  }
}
