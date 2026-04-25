import { CreativeDetail as CreativeDetailT } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { QuadrantBadge } from "./QuadrantBadge";

const HIDDEN_KEYS = new Set(["asset_file", "quadrant"]);

export function CreativeDetail({ creative }: { creative: CreativeDetailT }) {
  // Render every scalar field on the creative as a <dl> so judges (and the
  // team) can see the full attribute surface; styling comes later. Structured
  // sub-objects (quadrant, …) get their own components above.
  const entries = Object.entries(creative).filter(
    ([k]) => !HIDDEN_KEYS.has(k),
  );
  return (
    <article data-card="creative-detail">
      <img
        src={creativeImageUrl(creative.creative_id)}
        alt={`creative ${creative.creative_id}`}
        width={360}
        height={640}
      />
      <div data-detail-body>
        {creative.quadrant ? <QuadrantBadge quadrant={creative.quadrant} /> : null}
        <dl>
          {entries.map(([k, v]) => (
            <div key={k}>
              <dt>{k}</dt>
              <dd>{formatValue(v)}</dd>
            </div>
          ))}
        </dl>
      </div>
    </article>
  );
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "–";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(4);
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "true" : "false";
  return JSON.stringify(v);
}
