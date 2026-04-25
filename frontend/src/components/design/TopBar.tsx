import { PeriodPicker } from "./PeriodPicker";
import { SearchInput } from "./SearchInput";

export function TopBar() {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="mark">S</span>
        <span>Smadex</span>
        <span className="crumb">/ Creative cockpit</span>
      </div>
      <SearchInput />
      <div className="right">
        <PeriodPicker />
        <span className="avatar" title="Maya Tanaka">MT</span>
      </div>
    </header>
  );
}
