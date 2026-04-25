import type { VisionInsight } from "@/lib/api";

export function VisionInsightCard({ insight }: { insight: VisionInsight }) {
  return (
    <div className="vision-insight">
      <span className="badge">Vision insight · preview</span>
      <h3 className="t-section">{insight.headline}</h3>
      <p className="t-body">{insight.body}</p>
      <p className="t-micro muted">
        Confidence {(insight.confidence * 100).toFixed(0)}% · generated from attribute deltas.
      </p>
    </div>
  );
}
