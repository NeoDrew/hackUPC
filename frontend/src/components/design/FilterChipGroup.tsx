import Link from "next/link";

export interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

export function FilterChipGroup({
  label,
  paramKey,
  options,
  currentValue,
  buildHref,
}: {
  label: string;
  paramKey: string;
  options: FilterOption[];
  currentValue?: string;
  buildHref: (paramKey: string, value: string | undefined) => string;
}) {
  return (
    <div className="col gap-2">
      <span className="t-overline">{label}</span>
      <div className="row gap-2" style={{ flexWrap: "wrap" }}>
        <Link
          href={buildHref(paramKey, undefined)}
          className={`filter-chip${!currentValue ? " active" : ""}`}
        >
          All
        </Link>
        {options.map((opt) => (
          <Link
            key={opt.value}
            href={buildHref(paramKey, opt.value)}
            className={`filter-chip${currentValue === opt.value ? " active" : ""}`}
          >
            {opt.label}
            {opt.count !== undefined ? (
              <span className="muted" style={{ marginLeft: 4 }}>
                {opt.count}
              </span>
            ) : null}
          </Link>
        ))}
      </div>
    </div>
  );
}
