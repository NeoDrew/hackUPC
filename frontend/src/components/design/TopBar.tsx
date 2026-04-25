import Link from "next/link";
import type { Advertiser } from "@/lib/api";
import { PeriodPicker } from "./PeriodPicker";
import { ProfilePicker } from "./ProfilePicker";
import { SearchInput } from "./SearchInput";

function FryingPanIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="9" cy="12" r="6.25" />
      <rect x="13" y="10.75" width="9.5" height="2.5" rx="1.25" />
    </svg>
  );
}

export function TopBar({
  advertisers,
  activeAdvertiserId,
  totalWeeks,
  activeWeek,
}: {
  advertisers: Advertiser[];
  activeAdvertiserId: number | null;
  totalWeeks: number;
  activeWeek: number | null;
}) {
  return (
    <header className="topbar">
      <Link href="/" className="brand" aria-label="Smadex Cooking — home">
        <span className="mark" aria-hidden="true">
          <FryingPanIcon />
        </span>
        <span>Smadex Cooking</span>
      </Link>
      <SearchInput />
      <div className="right">
        <PeriodPicker totalWeeks={totalWeeks} activeWeek={activeWeek} />
        <ProfilePicker
          advertisers={advertisers}
          activeId={activeAdvertiserId}
        />
      </div>
    </header>
  );
}
