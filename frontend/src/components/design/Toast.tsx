"use client";

import { useEffect, useState } from "react";

export function PushToTestButton({
  label = "Push to test campaign",
}: {
  label?: string;
}) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (!shown) return;
    const id = setTimeout(() => setShown(false), 3200);
    return () => clearTimeout(id);
  }, [shown]);
  return (
    <>
      <button
        type="button"
        className="btn primary"
        onClick={() => setShown(true)}
      >
        {label}
      </button>
      {shown && (
        <div className="toast" role="status">
          Queued to Smadex test campaign · budget $500 · 72h hold
        </div>
      )}
    </>
  );
}
