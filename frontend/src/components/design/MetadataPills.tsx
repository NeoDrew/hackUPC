import type { CreativeDetail } from "@/lib/api";

const FIELDS: Array<{ key: string; label: string }> = [
  { key: "theme", label: "Theme" },
  { key: "hook_type", label: "Hook" },
  { key: "emotional_tone", label: "Tone" },
  { key: "cta_text", label: "CTA" },
  { key: "dominant_color", label: "Color" },
  { key: "duration_sec", label: "Duration (s)" },
  { key: "text_density", label: "Text density" },
  { key: "clutter_score", label: "Clutter" },
  { key: "novelty_score", label: "Novelty" },
  { key: "has_discount_badge", label: "Discount" },
  { key: "has_ugc_style", label: "UGC style" },
  { key: "faces_count", label: "Faces" },
];

export function MetadataPills({ creative }: { creative: CreativeDetail }) {
  // CreativeDetail allows extra keys; access generically via index.
  const data = creative as unknown as Record<string, unknown>;
  return (
    <div className="meta-pills">
      {FIELDS.map((f) => {
        const raw = data[f.key];
        return (
          <div key={f.key} className="meta-pill">
            <span className="k">{f.label}</span>
            <span className="v">{formatValue(raw)}</span>
          </div>
        );
      })}
    </div>
  );
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}
