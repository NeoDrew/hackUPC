import { bandToTone, bandToVerb } from "@/lib/status";

export function BandPill({
  band,
  health,
}: {
  band: string | null | undefined;
  health: number;
}) {
  const tone = bandToTone(band);
  const verb = bandToVerb(band);
  return (
    <span className={`status-pill ${tone}`} title="Our trajectory-aware band">
      <span className="seed" />
      Our band: {verb} · health {health}
    </span>
  );
}
