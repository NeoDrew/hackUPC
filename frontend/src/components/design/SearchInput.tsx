"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, type SearchHit } from "@/lib/api";
import { creativeImageUrl } from "@/lib/assetUrl";
import { statusToTone, statusToVerb } from "@/lib/status";

const DEBOUNCE_MS = 220;
const MIN_CHARS = 1;

export function SearchInput() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Debounced search.
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < MIN_CHARS) {
      setHits([]);
      setLoading(false);
      return;
    }
    const handle = setTimeout(async () => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      setLoading(true);
      try {
        const res = await api.search(trimmed, 8);
        if (!controller.signal.aborted) {
          setHits(res.hits);
          setActiveIdx(0);
        }
      } catch {
        // Network errors swallowed; UI shows "no matches" state.
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => clearTimeout(handle);
  }, [query]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (!containerRef.current) return;
      if (!containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const showDropdown = open && query.trim().length >= MIN_CHARS;

  const navigate = (cid: number) => {
    setOpen(false);
    setQuery("");
    setHits([]);
    inputRef.current?.blur();
    router.push(`/creatives/${cid}`);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
      return;
    }
    if (!showDropdown || hits.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => (i + 1) % hits.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => (i - 1 + hits.length) % hits.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const target = hits[activeIdx] ?? hits[0];
      if (target) navigate(target.creative_id);
    }
  };

  return (
    <div className="search-wrap" ref={containerRef}>
      <input
        ref={inputRef}
        className="search"
        type="text"
        placeholder="Search creatives, advertisers, themes…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        spellCheck={false}
        aria-label="Search creatives"
      />
      {showDropdown ? (
        <div className="search-dropdown" role="listbox">
          {loading && hits.length === 0 ? (
            <div className="search-empty">Searching…</div>
          ) : hits.length === 0 ? (
            <div className="search-empty">No matches.</div>
          ) : (
            hits.map((hit, i) => (
              <SearchRow
                key={hit.creative_id}
                hit={hit}
                active={i === activeIdx}
                onHover={() => setActiveIdx(i)}
                onSelect={() => navigate(hit.creative_id)}
              />
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

function SearchRow({
  hit,
  active,
  onHover,
  onSelect,
}: {
  hit: SearchHit;
  active: boolean;
  onHover: () => void;
  onSelect: () => void;
}) {
  const tone = statusToTone(hit.status);
  return (
    <Link
      href={`/creatives/${hit.creative_id}`}
      className={`search-row${active ? " active" : ""}`}
      onMouseEnter={onHover}
      onMouseDown={(e) => {
        // mousedown fires before input blur, so we navigate before the
        // blur-induced close can happen.
        e.preventDefault();
        onSelect();
      }}
      role="option"
      aria-selected={active}
    >
      <img
        src={creativeImageUrl(hit.creative_id)}
        alt=""
        loading="lazy"
        width={36}
        height={36}
      />
      <div className="search-row-text">
        <span className="search-row-headline">
          {hit.headline || `Creative ${hit.creative_id}`}
        </span>
        <span className="search-row-meta">
          {hit.advertiser_name} · {hit.vertical} · {hit.format} · #{hit.creative_id}
        </span>
      </div>
      <span className={`status-pill ${tone} dense`}>
        <span className="seed" />
        {statusToVerb(hit.status)}
      </span>
    </Link>
  );
}
