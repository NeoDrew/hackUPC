# Smadex frontend

Next.js 16 (App Router, Tailwind 4, TS, src-dir). Skeleton MVP — pure data browser.

## Run

```
pnpm install
pnpm dev
```

Listens on `http://localhost:3000`. Expects the backend at the URL in `.env.local` (default `http://127.0.0.1:8001`).

## Type generation

After backend schema changes, with the backend running:

```
pnpm gen:types
```

Regenerates `src/types/api.ts` from the FastAPI OpenAPI document.
