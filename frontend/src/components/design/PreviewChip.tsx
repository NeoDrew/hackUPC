export function PreviewChip({ label = "preview" }: { label?: string }) {
  return (
    <span className="preview-chip" title="Visual stub · not yet backed by real analysis">
      {label}
    </span>
  );
}
