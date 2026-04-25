export function TopBar() {
  return (
    <header className="topbar">
      <div className="brand">
        <span className="mark">S</span>
        <span>Smadex</span>
        <span className="crumb">/ Creative Twin Copilot</span>
      </div>
      <input
        className="search"
        placeholder="Search creatives, advertisers… (preview)"
        readOnly
      />
      <div className="right">
        <span className="filter-chip">
          <span className="muted">Period</span>
          <strong>Last 75 days</strong>
        </span>
        <span className="avatar" title="Maya Tanaka">MT</span>
      </div>
    </header>
  );
}
