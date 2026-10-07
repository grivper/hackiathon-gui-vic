# TVN sitemap history ingestion

## Scope
Build the news history from TVN's public monthly sitemaps (listed in robots.txt: `https://tvn-2.com/tvn_sitemap_index.xml`), because the RSS only keeps ~150 recent items and GDELT DOC only covers ~90 days (and is rate-limited from this IP).

## Findings (explored read-only)
- Index has 233 sitemaps; `tvn_sitemap_contents_YYYY_MM.xml` exists for 2008..2026-10 (22 files from 2025-03 on).
- Each `<url>` has `loc`, `lastmod` and `image:title` (an image/headline title, not guaranteed to be the headline). Oct 2026 has 607 URLs.
- robots.txt disallows only `/api/`, `/buscador/`, `/tag/`. Sitemaps are allowed. Redirect `tvn-2.com` -> `www.tvn-2.com` needs `-L`.
- No article page is fetched: metadata only (title, URL, date), per the challenge rules.

## Decisions
- Date caveat: `lastmod` is the last modification, not the publication date. Store it as `fecha_deteccion`, leave `fecha_publicacion` empty (same contract choice as GDELT `seendate`). Title falls back to a readable slug from the URL when `image:title` is missing. Document in the manifest.
- Origin tag: `origen = tvn_sitemap`. Deduplicate by normalized URL, keeping the RSS row when both exist.
- Raw sitemap XML stays out of git (`data/raw/tvn_sitemap/`).
- Politeness: 1 request per ~2 s, identifiable User-Agent, fetch each monthly sitemap at most once per run, skip months already downloaded unless `--refrescar`.

## Tasks
- [ ] T1 Downloader: months in a configurable window (default 2025-10 .. current month) into raw/tvn_sitemap/
- [ ] T2 Processing: parse into the news contract, dedupe with RSS/GDELT, manifest/catalog entry
- [ ] T3 Tests with a small fixture (no network)
- [ ] T4 Real run, check counts and date coverage
- [ ] T5 README + commit
