import type { Advertiser } from "@/lib/api";
import { PeriodPicker } from "./PeriodPicker";
import { ProfilePicker } from "./ProfilePicker";
import { SearchInput } from "./SearchInput";

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
      <div className="brand">
        <span className="mark">S</span>
        <span>Smadex</span>
        <span className="crumb">/ Creative Twin Copilot</span>
      </div>
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
