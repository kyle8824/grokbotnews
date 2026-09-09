# Grok Bot News static builder

Stories live as JSON. `tools/build_site.py` regenerates `index.html`, `stories/<slug>.html`, and `sitemap.xml`.

## Layout

- `data/site.json` — utility timestamp/markets, breaking line, homepage `order` (first = lead), `stack` rail, section groupings, ticker, markets, archive sitemap entries
- `data/stories/<slug>.json` — one file per framed story (hed, dek, image, both frames + sources)

Keep `css/site.css` and `js/views.js` unless a tiny fix is required. Do not reuse the same `img/` file across two live ordered framed stories.

## Add a story

1. Add a unique image under `img/`.
2. Create `data/stories/my-slug.json` (copy an existing file). Required fields:

```json
{
  "slug": "my-slug",
  "kicker": "Place",
  "hed": "Event-only headline",
  "stamp": "NEW · Wed. 9 a.m. EDT",
  "dek": "Event summary…",
  "image": "img/my-unique.jpg",
  "alt": "…",
  "caption": "…",
  "credit": "…",
  "byline": "Event summary from public reporting and named outlets",
  "section": "us",
  "updated": "2026-09-09",
  "stack_blurb": "Short stack line.",
  "seo_description": "Meta description…",
  "frames": {
    "cl": {"body": "…", "sources": [{"name": "Outlet", "url": "https://…"}]},
    "cr": {"body": "…", "sources": [{"name": "Outlet", "url": "https://…"}]}
  }
}
```

3. Put the slug first in `data/site.json` → `order` to make it the lead (or elsewhere in `order` / `section_labels` / `stack`).
4. Update utility/breaking/ticker/markets text in `site.json` as needed.
5. From the repo root:

```bash
python3 tools/build_site.py
```

The builder fails loudly if two ordered stories share an image path.

6. Commit the data + regenerated HTML/sitemap and push `main`.

## Hourly refresh

Edit or add story JSON → reorder `site.json` → run the builder → commit/push. No hand-rewrites of `index.html`.
