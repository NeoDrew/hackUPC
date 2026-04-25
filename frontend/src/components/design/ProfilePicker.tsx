"use client";

import { useTransition } from "react";

import type { Advertiser } from "@/lib/api";
import { setActiveAdvertiser } from "@/lib/advertiserScopeActions";

function initials(name: string): string {
  const cleaned = name.trim();
  if (!cleaned) return "??";
  const parts = cleaned.split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function ProfilePicker({
  advertisers,
  activeId,
}: {
  advertisers: Advertiser[];
  activeId: number | null;
}) {
  const [isPending, startTransition] = useTransition();

  if (advertisers.length === 0) {
    return <span className="avatar" title="No advertisers loaded">??</span>;
  }

  const onChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const next = Number.parseInt(e.target.value, 10);
    if (!Number.isFinite(next) || next === activeId) return;
    const fd = new FormData();
    fd.set("advertiser_id", String(next));
    startTransition(() => {
      setActiveAdvertiser(fd);
    });
  };

  const active =
    advertisers.find((a) => a.advertiser_id === activeId) ?? advertisers[0];

  return (
    <label className={`profile-picker${isPending ? " pending" : ""}`}>
      <span className="profile-avatar" aria-hidden>
        {initials(active.advertiser_name)}
      </span>
      <span className="profile-text">
        <span className="profile-label">Viewing as</span>
        <span className="profile-name">{active.advertiser_name}</span>
      </span>
      <select
        className="profile-select"
        value={active.advertiser_id}
        onChange={onChange}
        disabled={isPending}
        aria-label="Switch advertiser profile"
      >
        {advertisers.map((a) => (
          <option key={a.advertiser_id} value={a.advertiser_id}>
            {a.advertiser_name}
          </option>
        ))}
      </select>
    </label>
  );
}
