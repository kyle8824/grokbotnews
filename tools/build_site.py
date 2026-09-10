#!/usr/bin/env python3
"""Regenerate index.html, story pages, and sitemap.xml from data/."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STORIES_DIR = DATA / "stories"
SITE_PATH = DATA / "site.json"

VIEWS_BTN = """        <p class="views-row">
          <button type="button" class="views-btn" data-open-views>
            <span class="views-btn-kicker">Equal weight</span>
            <span class="views-btn-label">Open both views</span>
            <span class="views-btn-sub">Center-left and center-right. Same size. Named sources. You decide.</span>
          </button>
        </p>"""


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def esc(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def load_site() -> dict:
    if not SITE_PATH.exists():
        die(f"missing {SITE_PATH}")
    return json.loads(SITE_PATH.read_text(encoding="utf-8"))


def load_stories() -> dict[str, dict]:
    stories = {}
    for path in sorted(STORIES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        slug = data.get("slug") or path.stem
        if slug != path.stem:
            die(f"{path.name}: slug {slug!r} != filename stem {path.stem!r}")
        data["slug"] = slug
        stories[slug] = data
    if not stories:
        die(f"no story JSON in {STORIES_DIR}")
    return stories


def validate_unique_images(order: list[str], stories: dict[str, dict]) -> None:
    seen: dict[str, str] = {}
    for slug in order:
        if slug not in stories:
            die(f"order slug missing from data/stories: {slug}")
        img = stories[slug].get("image") or ""
        if not img:
            die(f"{slug}: missing image")
        img_norm = img.lstrip("/")
        if img_norm in seen:
            die(
                f"duplicate image among ordered framed stories: {img_norm} "
                f"used by {seen[img_norm]} and {slug}"
            )
        seen[img_norm] = slug


def sources_html(sources: list[dict], indent: str = "              ") -> str:
    parts = []
    for i, src in enumerate(sources or []):
        name = esc(src.get("name", ""))
        url = esc(src.get("url", ""))
        sep = " ·\n" if i < len(sources) - 1 else ""
        parts.append(f'{indent}<a href="{url}" rel="noopener">{name}</a>{sep}')
    return "\n".join(parts)


def frames_html(story: dict, indent: str = "        ") -> str:
    cl = story["frames"]["cl"]
    cr = story["frames"]["cr"]
    return f"""{indent}<div class="frames">
{indent}  <div class="frame cl">
{indent}    <h3>Center-left view</h3>
{indent}    <p>{esc(cl["body"])}</p>
{indent}    <p class="sources">Sources:
{sources_html(cl.get("sources", []), indent + "      ")}
{indent}    </p>
{indent}  </div>
{indent}  <div class="frame cr">
{indent}    <h3>Center-right view</h3>
{indent}    <p>{esc(cr["body"])}</p>
{indent}    <p class="sources">Sources:
{sources_html(cr.get("sources", []), indent + "      ")}
{indent}    </p>
{indent}  </div>
{indent}</div>"""


def img_src(path: str, *, absolute: bool = False, root_absolute: bool = False) -> str:
    p = (path or "").lstrip("/")
    if absolute:
        return f"https://www.grokbotnews.com/{p}"
    if root_absolute:
        return f"/{p}"
    return p


def stack_blurb(story: dict) -> str:
    if story.get("stack_blurb"):
        return story["stack_blurb"]
    dek = story.get("dek") or ""
    # short fallback: first sentence-ish
    cut = dek.split(". ")[0]
    if len(cut) > 110:
        cut = cut[:107].rstrip() + "…"
    elif cut and not cut.endswith("."):
        cut = cut + "."
    return cut


def render_utility(site: dict) -> str:
    return f"""  <div class="utility">
    <div class="utility-inner">
      <div class="utility-live"><span class="live-dot" aria-hidden="true"></span> Live <span class="sep">·</span> {esc(site["utility_live"])}</div>
      <div class="utility-mkts">{esc(site["utility_markets"])}</div>
    </div>
  </div>"""


def render_masthead(*, home: bool) -> str:
    brand_href = "#lead" if home else "/"
    top = "#lead" if home else "/"
    us = "#us" if home else "/#us"
    world = "#world" if home else "/#world"
    politics = "#politics" if home else "/#politics"
    energy = "#energy" if home else "/#energy"
    method = "#method" if home else "/#method"
    return f"""  <header class="masthead">
    <div class="masthead-inner">
      <a class="brand" href="{brand_href}">
        <img class="brand-mark" src="/img/brand-mark.png" width="56" height="56" alt="">
        <span class="wordmark">GROK BOT NEWS</span>
      </a>
      <p class="tagline">Event first. Two views. Same weight.</p>
    </div>
    <nav class="nav" aria-label="Sections">
      <a href="{top}">Top</a>
      <a href="{us}">U.S.</a>
      <a href="{world}">World</a>
      <a href="{politics}">Politics</a>
      <a href="{energy}">Energy</a>
      <a href="{method}">Method</a>
    </nav>
  </header>"""


def render_lead(story: dict) -> str:
    slug = story["slug"]
    return f"""      <article>
        <p class="kicker">{esc(story["kicker"])}</p>
        <h1 class="lead-hed"><a href="/stories/{esc(slug)}">{esc(story["hed"])}</a></h1>
        <p class="stamp">{esc(story["stamp"])}</p>
        <p class="dek">{esc(story["dek"])}</p>
        <div class="photo-wrap">
          <img src="{esc(img_src(story["image"]))}" alt="{esc(story.get("alt", ""))}">
        </div>
        <p class="caption">{esc(story.get("caption", ""))}</p>
        <p class="credit">{esc(story.get("credit", ""))}</p>
        <p class="byline">{esc(story.get("byline", "Event summary from public reporting and named outlets"))}</p>

{VIEWS_BTN}
{frames_html(story, indent="        ")}
      </article>"""


def render_stack(stack_slugs: list[str], stories: dict[str, dict]) -> str:
    items = []
    for slug in stack_slugs:
        s = stories[slug]
        items.append(
            f"""        <div class="stack-item">
          <p class="kicker">{esc(s["kicker"])}</p>
          <h2><a href="/stories/{esc(slug)}">{esc(s["hed"])}</a></h2>
          <p class="stamp">{esc(s["stamp"])}</p>
          <p>{esc(stack_blurb(s))}</p>
        </div>"""
        )
    return (
        '      <aside class="stack" aria-label="Headline stack">\n'
        + "\n".join(items)
        + "\n      </aside>"
    )


def render_body_story(story: dict, *, article_id: str | None = None) -> str:
    slug = story["slug"]
    id_attr = f' id="{esc(article_id)}"' if article_id else ""
    return f"""    <article class="story"{id_attr}>
      <div>
        <img src="{esc(img_src(story["image"]))}" alt="{esc(story.get("alt", ""))}">
        <p class="credit">{esc(story.get("credit", ""))}</p>
      </div>
      <div>
        <p class="kicker">{esc(story["kicker"])}</p>
        <h2 class="story-hed"><a href="/stories/{esc(slug)}">{esc(story["hed"])}</a></h2>
        <p class="dek">{esc(story["dek"])}</p>
{VIEWS_BTN}
{frames_html(story, indent="        ")}
      </div>
    </article>"""


def render_rail(site: dict) -> str:
    wire_parts = []
    for i, item in enumerate(site.get("rail_wire", [])):
        label = esc(item["label"])
        text = esc(item["text"])
        stamp = esc(item.get("stamp", ""))
        if i == 0:
            wire_parts.append(
                f"""        <p class="stack-item" style="border:0;padding-top:0">
          <strong>{label}</strong> {text}
          <span class="stamp">{stamp}</span>
        </p>"""
            )
        else:
            wire_parts.append(
                f"""        <p>
          <strong>{label}</strong> {text}
          <span class="stamp">{stamp}</span>
        </p>"""
            )
    markets = site.get("markets", {})
    rows = []
    for row in markets.get("rows", []):
        rows.append(
            f'        <div class="quote-row"><span>{esc(row["label"])}</span>'
            f'<span class="{esc(row.get("dir", "up"))}">{esc(row["value"])}</span></div>'
        )
    return f"""    <div class="rail">
      <div class="box">
        <h2>Also on the wire</h2>
{chr(10).join(wire_parts)}
      </div>
      <div class="box">
        <h2>{esc(markets.get("heading", "Markets"))}</h2>
{chr(10).join(rows)}
        <p class="credit" style="margin-top:10px">{esc(markets.get("credit", ""))}</p>
      </div>
    </div>"""


def render_ticker(site: dict) -> str:
    items = site.get("ticker", [])
    # duplicate for marquee loop as in original
    spans = []
    for entry in items + items:
        if "|" in entry:
            k, v = entry.split("|", 1)
        else:
            k, v = "", entry
        spans.append(f"      <span><b>{esc(k)}</b> {esc(v)}</span>")
    return (
        '  <div class="ticker" aria-label="Bottom ticker">\n'
        '    <div class="ticker-inner">\n'
        + "\n".join(spans)
        + "\n    </div>\n  </div>"
    )


def render_views_layer() -> str:
    return """  <div class="views-layer" id="views-layer" hidden>
    <div class="views-backdrop" data-views-close></div>
    <div class="views-sheet" role="dialog" aria-modal="true" aria-labelledby="views-title">
      <div class="views-head">
        <div>
          <p class="kicker" id="views-kicker"></p>
          <h2 id="views-title"></h2>
        </div>
        <button type="button" class="views-close" data-views-close aria-label="Close two views">Close</button>
      </div>
      <p class="views-note">Same story. Two frames. Same weight. You decide.</p>
      <div class="views-body" id="views-body"></div>
    </div>
  </div>
  <script src="js/views.js" defer></script>"""


def build_index(site: dict, stories: dict[str, dict]) -> str:
    order = site["order"]
    lead_slug = order[0]
    lead = stories[lead_slug]
    stack_slugs = site.get("stack") or order[1:8]

    for slug in stack_slugs:
        if slug not in stories:
            die(f"stack slug missing: {slug}")

    sections_html = []
    for sec in site.get("section_labels", []):
        label = sec["label"]
        sid = sec["id"]
        sections_html.append(
            f'    <h2 class="section-label" id="{esc(sid)}">{esc(label)}</h2>\n'
        )
        for i, slug in enumerate(sec.get("slugs", [])):
            if slug not in stories:
                die(f"section {sid} missing story {slug}")
            article_id = "politics" if slug == "missouri-redistricting-referendum" else None
            sections_html.append(render_body_story(stories[slug], article_id=article_id))
            sections_html.append("\n\n")

    ld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "GROK BOT NEWS",
            "url": site.get("site_url", "https://www.grokbotnews.com"),
            "description": "Event-only headlines with two equal sourced viewpoint blocks.",
        },
        ensure_ascii=False,
        separators=(",", ": "),
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(site["title"])}</title>
  <link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/img/favicon.ico" sizes="any">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
  <link rel="canonical" href="https://www.grokbotnews.com/">
  <meta property="og:site_name" content="GROK BOT NEWS">
  <meta property="og:type" content="website">
  <meta property="og:title" content="GROK BOT NEWS">
  <meta property="og:description" content="{esc(site.get("og_description", ""))}">
  <meta property="og:url" content="https://www.grokbotnews.com/">
  <meta property="og:image" content="https://www.grokbotnews.com/img/og-default.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="description" content="{esc(site.get("meta_description", ""))}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/site.css">
<script type="application/ld+json">{ld}</script>
</head>
<body>
  <a class="skip" href="#main">Skip to stories</a>

{render_utility(site)}

{render_masthead(home=True)}

  <div class="breaking">
    <div class="breaking-inner">
      <span class="breaking-kicker">Breaking</span>
      <p>{esc(site.get("breaking", ""))}</p>
    </div>
  </div>

  <main id="main" class="wrap">
    <section class="lead-grid" id="lead">
{render_lead(lead)}

{render_stack(stack_slugs, stories)}
    </section>

{"".join(sections_html)}
{render_rail(site)}
  </main>

{render_ticker(site)}

  <footer id="method">
    <div class="foot-inner">
      <p class="foot-mark">GROK BOT NEWS</p>
      <p class="method">{esc(site.get("footer_method", ""))}</p>
      <p class="legal">{esc(site.get("footer_legal", ""))}</p>
    </div>
  </footer>

{render_views_layer()}
</body>
</html>
"""


def seo_description(story: dict) -> str:
    if story.get("seo_description"):
        return story["seo_description"]
    dek = story.get("dek") or story.get("hed") or ""
    if len(dek) > 160:
        return dek[:157].rstrip() + "…"
    return dek


def iso_datetime(story: dict, field: str) -> str:
    if story.get(field):
        return story[field]
    updated = story.get("updated") or "2026-09-09"
    return f"{updated}T08:00:00-04:00"


def article_section_label(story: dict) -> str:
    if story.get("article_section"):
        return story["article_section"]
    mapping = {
        "lead": "Top",
        "us": "U.S.",
        "world": "World",
        "politics": "Politics",
        "weather": "Energy",
        "stack": "Top",
    }
    return mapping.get(story.get("section", ""), "News")


def build_story_page(site: dict, story: dict) -> str:
    slug = story["slug"]
    hed = story["hed"]
    title = f"{hed} — GROK BOT NEWS"
    desc = seo_description(story)
    img_abs = img_src(story["image"], absolute=True)
    img_page = img_src(story["image"], root_absolute=True)
    canon = f"https://www.grokbotnews.com/stories/{slug}"
    published = iso_datetime(story, "date_published")
    modified = iso_datetime(story, "date_modified")
    ld = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": hed,
        "description": desc,
        "image": [img_abs],
        "datePublished": published,
        "dateModified": modified,
        "author": {"@type": "Organization", "name": "GROK BOT NEWS"},
        "publisher": {
            "@type": "Organization",
            "name": "GROK BOT NEWS",
            "url": "https://www.grokbotnews.com",
        },
        "mainEntityOfPage": canon,
        "articleSection": article_section_label(story),
        "inLanguage": "en-US",
    }
    caption = story.get("caption") or ""
    caption_html = f'\n        <p class="caption">{esc(caption)}</p>' if caption else ""
    credit = story.get("credit") or ""
    credit_html = f'\n        <p class="credit">{esc(credit)}</p>' if credit else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(desc)}">
  <link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/img/favicon.ico" sizes="any">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
  <link rel="canonical" href="{esc(canon)}">
  <meta property="og:site_name" content="GROK BOT NEWS">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(desc)}">
  <meta property="og:url" content="{esc(canon)}">
  <meta property="og:image" content="{esc(img_abs)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(desc)}">
  <meta name="twitter:image" content="{esc(img_abs)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/site.css">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ": "))}</script>
</head>
<body>
  <a class="skip" href="#main">Skip to stories</a>
{render_utility(site)}
{render_masthead(home=False)}
  <main id="main" class="wrap story-page">
    <p><a class="back-home" href="/">← All stories</a></p>
    <article>
      <p class="kicker">{esc(story["kicker"])}</p>
      <h1 class="lead-hed">{esc(hed)}</h1>
      <p class="stamp">{esc(story["stamp"])}</p>
      <p class="dek">{esc(story["dek"])}</p>
      <div class="photo-wrap"><img src="{esc(img_page)}" alt="{esc(story.get("alt", ""))}"></div>{caption_html}{credit_html}
{frames_html(story, indent="      ")}
    </article>
  </main>
  <footer id="method">
    <div class="foot-inner">
      <p class="foot-mark">GROK BOT NEWS</p>
      <p class="method">{esc(site.get("story_footer_method", site.get("footer_method", "")))}</p>
      <p class="legal">{esc(site.get("story_footer_legal", site.get("footer_legal", "")))}</p>
    </div>
  </footer>
</body>
</html>
"""


def build_sitemap(site: dict, stories: dict[str, dict]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    # homepage lastmod = newest ordered story
    newest = max((stories[s].get("updated") or "2026-09-09") for s in site["order"])
    lines.append(
        f"  <url><loc>https://www.grokbotnews.com/</loc><lastmod>{newest}</lastmod></url>"
    )
    # live ordered stories first (homepage order), then any other data stories, then archive
    seen = set()
    for slug in site["order"]:
        st = stories[slug]
        lines.append(
            f"  <url><loc>https://www.grokbotnews.com/stories/{slug}</loc>"
            f"<lastmod>{st.get('updated', newest)}</lastmod></url>"
        )
        seen.add(slug)
    for slug in sorted(stories.keys()):
        if slug in seen:
            continue
        st = stories[slug]
        lines.append(
            f"  <url><loc>https://www.grokbotnews.com/stories/{slug}</loc>"
            f"<lastmod>{st.get('updated', newest)}</lastmod></url>"
        )
        seen.add(slug)
    for arch in site.get("archive", []):
        slug = arch["slug"]
        if slug in seen:
            continue
        lines.append(
            f"  <url><loc>https://www.grokbotnews.com/stories/{slug}</loc>"
            f"<lastmod>{arch.get('updated', newest)}</lastmod></url>"
        )
        seen.add(slug)
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> None:
    site = load_site()
    stories = load_stories()
    order = site.get("order") or []
    if not order:
        die("site.json order is empty")
    validate_unique_images(order, stories)

    index_html = build_index(site, stories)
    (ROOT / "index.html").write_text(index_html, encoding="utf-8")
    print(f"wrote index.html ({len(order)} ordered stories)")

    stories_out = ROOT / "stories"
    stories_out.mkdir(exist_ok=True)
    for slug, story in stories.items():
        page = build_story_page(site, story)
        (stories_out / f"{slug}.html").write_text(page, encoding="utf-8")
    print(f"wrote {len(stories)} story pages")

    sitemap = build_sitemap(site, stories)
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    print("wrote sitemap.xml")
    print("OK")


if __name__ == "__main__":
    main()
