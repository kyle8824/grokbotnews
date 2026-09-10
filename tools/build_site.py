#!/usr/bin/env python3
"""Regenerate index.html, story pages, and sitemap.xml from data/."""
from __future__ import annotations

import json
import re
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

HOME_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>'
    "</svg>"
)
SEARCH_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M15.5 14h-.79l-.28-.27A6.47 6.47 0 0 0 16 9.5 '
    "6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 "
    '5L20.49 19l-5-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 '
    '14 7.01 14 9.5 11.99 14 9.5 14z"/>'
    "</svg>"
)
MENU_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z"/>'
    "</svg>"
)
X_ICON = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 '
    "21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 "
    '17.52h1.833L7.084 4.126H5.117z"/>'
    "</svg>"
)


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
    cut = dek.split(". ")[0]
    if len(cut) > 110:
        cut = cut[:107].rstrip() + "…"
    elif cut and not cut.endswith("."):
        cut = cut + "."
    return cut


def short_dek(story: dict, limit: int = 220) -> str:
    dek = (story.get("dek") or "").strip()
    if not dek:
        return stack_blurb(story)
    # Prefer first 1–2 sentences
    parts = re.split(r"(?<=\.)\s+", dek)
    out = parts[0]
    if len(parts) > 1 and len(out) + 1 + len(parts[1]) <= limit:
        out = out + " " + parts[1]
    if len(out) > limit:
        out = out[: limit - 1].rstrip() + "…"
    return out


def read_mins(story: dict) -> int:
    text = " ".join(
        [
            story.get("dek") or "",
            (story.get("frames") or {}).get("cl", {}).get("body") or "",
            (story.get("frames") or {}).get("cr", {}).get("body") or "",
        ]
    )
    words = max(1, len(text.split()))
    return max(2, min(8, round(words / 180)))


def nav_category(story: dict) -> tuple[str, str]:
    """Return (LABEL, css-slug) for mock-style category kickers."""
    kicker = (story.get("kicker") or "").lower()
    section = (story.get("section") or "").lower()
    article = (story.get("article_section") or "").lower()
    blob = f"{kicker} {section} {article} {story.get('slug', '')}"

    if any(x in blob for x in ("trade", "tariff", "business", "markets")):
        return "BUSINESS", "business"
    if any(
        x in blob
        for x in ("energy", "hormuz", "houthi", "saudi", "oil", "gas", "weather")
    ):
        return "ENERGY", "energy"
    if section == "world" or any(
        x in blob for x in ("diplomacy", "ukraine", "world", "iran", "persian")
    ):
        # tanker / hormuz already caught as energy; remaining gulf/world
        if any(x in blob for x in ("hormuz", "houthi", "saudi energy")):
            return "ENERGY", "energy"
        return "WORLD", "world"
    if any(
        x in blob
        for x in (
            "midterm",
            "politics",
            "supreme",
            "justice",
            "homeland",
            "senate",
            "congress",
            "ballot",
            "voter",
            "redistrict",
            "ice",
            "doj",
        )
    ):
        return "POLITICS", "politics"
    if any(x in blob for x in ("tech", "ai", "amazon")):
        # miami amazon crash is accident/us, not tech product news
        if "miami" in blob or "cargo" in blob:
            return "U.S.", "us"
        return "TECH", "tech"
    if section in ("us", "lead") or "u.s" in article:
        return "U.S.", "us"
    return "U.S.", "us"


def fonts_and_css(*, root_absolute: bool = False) -> str:
    css = "/css/site.css" if root_absolute else "css/site.css"
    return f"""  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{css}">"""


def favicons() -> str:
    return """  <link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/img/favicon.ico" sizes="any">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">"""


def render_masthead(*, home: bool) -> str:
    brand_href = "/" if not home else "#hero"
    home_href = "#hero" if home else "/"
    top = "#top-stories" if home else "/#top-stories"
    us = "#latest" if home else "/#latest"
    world = "#featured" if home else "/#featured"
    politics = "#hero" if home else "/"
    business = "#latest" if home else "/#latest"
    energy = "#featured" if home else "/#featured"
    # Chrome-only destinations for categories we do not currently section
    tech = top
    entertainment = top
    sports = top
    opinion = "#featured" if home else "/#featured"

    return f"""  <header class="masthead">
    <div class="masthead-inner">
      <a class="brand" href="{brand_href}">
        <img class="brand-mark" src="/img/brand-mark.png" width="52" height="52" alt="">
        <span class="brand-text">
          <span class="brand-name">GROK BOT</span>
          <span class="brand-news">NEWS</span>
        </span>
      </a>
      <p class="tagline">REAL NEWS <span class="slash">/</span> REAL VIEWS <span class="slash">/</span> SAME WEIGHT</p>
    </div>
  </header>
  <nav class="nav-bar" aria-label="Sections">
    <div class="nav">
      <a class="nav-home" href="{home_href}" aria-label="Home">{HOME_ICON}</a>
      <a class="nav-link" href="{top}">Top Stories</a>
      <a class="nav-link" href="{us}">U.S.</a>
      <a class="nav-link" href="{world}">World</a>
      <a class="nav-link" href="{politics}">Politics</a>
      <a class="nav-link" href="{business}">Business</a>
      <a class="nav-link" href="{energy}">Energy</a>
      <a class="nav-link" href="{tech}">Tech</a>
      <a class="nav-link" href="{entertainment}">Entertainment</a>
      <a class="nav-link" href="{sports}">Sports</a>
      <a class="nav-link" href="{opinion}">Opinion</a>
      <div class="nav-utils">
        <button type="button" class="nav-util" aria-label="Search" disabled title="Search coming soon">{SEARCH_ICON}</button>
        <button type="button" class="nav-util" aria-label="Menu" disabled title="Menu">{MENU_ICON}</button>
      </div>
    </div>
  </nav>"""


def render_footer(site: dict, *, story: bool = False) -> str:
    method_key = "story_footer_method" if story else "footer_method"
    legal_key = "story_footer_legal" if story else "footer_legal"
    method = site.get(method_key) or site.get("footer_method", "")
    legal = site.get(legal_key) or site.get("footer_legal", "")
    return f"""  <footer class="site-footer" id="method">
    <div class="foot-inner">
      <div class="foot-top">
        <a class="foot-brand" href="/">
          <img class="brand-mark" src="/img/brand-mark.png" width="44" height="44" alt="">
          <span>
            <span class="brand-name" style="font-size:20px">GROK BOT</span>
            <span class="brand-news" style="display:flex">NEWS</span>
            <p class="foot-tagline">REAL NEWS <span class="slash">/</span> REAL VIEWS <span class="slash">/</span> SAME WEIGHT</p>
          </span>
        </a>
        <div class="foot-social">
          <a href="https://x.com/grokbotnews" rel="noopener" aria-label="Grok Bot News on X">{X_ICON} <span>X</span></a>
        </div>
      </div>
      <p class="method">{esc(method)}</p>
      <p class="legal">{esc(legal)}</p>
      <div class="foot-bottom">
        <div class="foot-links">
          <a href="/#method">About</a>
          <a href="https://x.com/grokbotnews" rel="noopener">Contact</a>
        </div>
        <div>© 2026 Grok Bot News. All rights reserved.</div>
      </div>
    </div>
  </footer>"""


def render_hero(story: dict) -> str:
    slug = story["slug"]
    label, css = nav_category(story)
    return f"""      <article class="hero-story">
        <img class="hero-bg" src="{esc(img_src(story["image"]))}" alt="{esc(story.get("alt", ""))}">
        <div class="hero-copy">
          <span class="cat-kicker cat-{css}">{esc(label)}</span>
          <h1 class="hero-hed"><a href="/stories/{esc(slug)}">{esc(story["hed"])}</a></h1>
          <p class="hero-dek">{esc(short_dek(story))}</p>
          <p class="hero-meta">{esc(story["stamp"])}</p>
          <a class="btn-read" href="/stories/{esc(slug)}">Read full story →</a>
        </div>
      </article>"""


def render_trending(slugs: list[str], stories: dict[str, dict]) -> str:
    items = []
    for i, slug in enumerate(slugs, start=1):
        s = stories[slug]
        label, _ = nav_category(s)
        items.append(
            f"""        <li>
          <span class="trend-num">{i}</span>
          <div class="trend-body">
            <a href="/stories/{esc(slug)}">{esc(s["hed"])}</a>
            <div class="trend-meta"><span class="cat">{esc(label)}</span>{esc(s["stamp"])}</div>
          </div>
        </li>"""
        )
    return f"""      <aside class="trending" aria-label="Trending now">
        <div class="section-head"><span class="bar" aria-hidden="true"></span><h2>Trending Now</h2></div>
        <ol class="trend-list">
{chr(10).join(items)}
        </ol>
      </aside>"""


def render_top_cards(slugs: list[str], stories: dict[str, dict]) -> str:
    cards = []
    for slug in slugs:
        s = stories[slug]
        label, css = nav_category(s)
        mins = read_mins(s)
        cards.append(
            f"""        <a class="story-card" href="/stories/{esc(slug)}">
          <img src="{esc(img_src(s["image"]))}" alt="{esc(s.get("alt", ""))}">
          <div class="story-card-body">
            <span class="cat-kicker cat-{css}">{esc(label)}</span>
            <h3>{esc(s["hed"])}</h3>
            <p>{esc(stack_blurb(s))}</p>
            <div class="card-meta">{esc(s["stamp"])}<span class="sep">·</span>{mins} MIN READ</div>
          </div>
        </a>"""
        )
    return (
        '      <section id="top-stories">\n'
        '        <div class="band-head"><span class="bar" aria-hidden="true"></span><h2>Top Stories</h2></div>\n'
        '        <div class="top-cards">\n'
        + "\n".join(cards)
        + "\n        </div>\n      </section>"
    )


def render_latest(slugs: list[str], stories: dict[str, dict]) -> str:
    items = []
    for slug in slugs:
        s = stories[slug]
        label, _ = nav_category(s)
        items.append(
            f"""        <li>
          <a href="/stories/{esc(slug)}"><img src="{esc(img_src(s["image"]))}" alt="{esc(s.get("alt", ""))}"></a>
          <div>
            <div class="latest-meta"><span class="cat">{esc(label)}</span>{esc(s["stamp"])}</div>
            <a class="hed" href="/stories/{esc(slug)}">{esc(s["hed"])}</a>
          </div>
        </li>"""
        )
    return (
        '      <aside class="latest-rail" id="latest" aria-label="Latest">\n'
        '        <div class="band-head"><span class="bar" aria-hidden="true"></span><h2>Latest</h2></div>\n'
        '        <ul class="latest-list">\n'
        + "\n".join(items)
        + "\n        </ul>\n      </aside>"
    )


def render_featured(slugs: list[str], stories: dict[str, dict]) -> str:
    if not slugs:
        return ""
    main = stories[slugs[0]]
    main_label, main_css = nav_category(main)
    side_html = []
    for slug in slugs[1:]:
        s = stories[slug]
        label, css = nav_category(s)
        side_html.append(
            f"""        <a href="/stories/{esc(slug)}">
          <img src="{esc(img_src(s["image"]))}" alt="{esc(s.get("alt", ""))}">
          <div>
            <span class="cat-kicker cat-{css}">{esc(label)}</span>
            <h3>{esc(s["hed"])}</h3>
          </div>
        </a>"""
        )
    side_block = ""
    if side_html:
        side_block = (
            '      <div class="featured-side">\n'
            + "\n".join(side_html)
            + "\n      </div>"
        )
    return f"""    <section class="featured" id="featured">
      <div class="band-head"><span class="bar" aria-hidden="true"></span><h2>Featured Analysis</h2></div>
      <div class="featured-grid">
        <a class="featured-main" href="/stories/{esc(main["slug"])}">
          <img src="{esc(img_src(main["image"]))}" alt="{esc(main.get("alt", ""))}">
          <div>
            <span class="cat-kicker cat-{main_css}">{esc(main_label)}</span>
            <h3>{esc(main["hed"])}</h3>
            <p>{esc(stack_blurb(main))}</p>
          </div>
        </a>
{side_block}
      </div>
    </section>"""


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


def split_home_buckets(order: list[str]) -> dict[str, list[str]]:
    """Partition ordered stories into mock homepage regions without inventing content."""
    if not order:
        die("empty order")
    rest = order[1:]
    trending = rest[:5]
    top = rest[5:8]
    leftover = rest[8:]
    # Prefer 3 for featured (main + 2 side); rest go to Latest
    if len(leftover) >= 5:
        featured = leftover[-3:]
        latest = leftover[:-3]
    elif len(leftover) >= 3:
        featured = leftover[-3:]
        latest = leftover[:-3]
    else:
        featured = leftover
        latest = []
    return {
        "lead": [order[0]],
        "trending": trending,
        "top": top,
        "latest": latest,
        "featured": featured,
    }


def build_index(site: dict, stories: dict[str, dict]) -> str:
    order = site["order"]
    for slug in order:
        if slug not in stories:
            die(f"order slug missing: {slug}")

    buckets = split_home_buckets(order)
    lead = stories[buckets["lead"][0]]

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

    featured_html = render_featured(buckets["featured"], stories)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(site["title"])}</title>
{favicons()}
  <link rel="canonical" href="https://www.grokbotnews.com/">
  <meta property="og:site_name" content="GROK BOT NEWS">
  <meta property="og:type" content="website">
  <meta property="og:title" content="GROK BOT NEWS">
  <meta property="og:description" content="{esc(site.get("og_description", ""))}">
  <meta property="og:url" content="https://www.grokbotnews.com/">
  <meta property="og:image" content="https://www.grokbotnews.com/img/og-default.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="description" content="{esc(site.get("meta_description", ""))}">
{fonts_and_css()}
<script type="application/ld+json">{ld}</script>
</head>
<body>
  <a class="skip" href="#main">Skip to stories</a>

{render_masthead(home=True)}

  <section class="hero-band" id="hero">
    <div class="hero-grid">
{render_hero(lead)}

{render_trending(buckets["trending"], stories)}
    </div>
  </section>

  <main id="main" class="wrap">
    <div class="home-main">
{render_top_cards(buckets["top"], stories)}

{render_latest(buckets["latest"], stories)}
    </div>

{featured_html}
  </main>

{render_footer(site, story=False)}
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
    label, _ = nav_category(story)
    return label.title() if label != "U.S." else "U.S."


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
    label, css = nav_category(story)
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
{favicons()}
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
{fonts_and_css(root_absolute=True)}
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False, separators=(",", ": "))}</script>
</head>
<body>
  <a class="skip" href="#main">Skip to stories</a>
{render_masthead(home=False)}
  <main id="main" class="wrap story-page">
    <p><a class="back-home" href="/">← All stories</a></p>
    <article>
      <span class="cat-kicker cat-{css}">{esc(label)}</span>
      <h1 class="lead-hed">{esc(hed)}</h1>
      <p class="stamp">{esc(story["stamp"])}</p>
      <p class="dek">{esc(story["dek"])}</p>
      <div class="photo-wrap"><img src="{esc(img_page)}" alt="{esc(story.get("alt", ""))}"></div>{caption_html}{credit_html}
{frames_html(story, indent="      ")}
    </article>
  </main>
{render_footer(site, story=True)}
</body>
</html>
"""


def build_sitemap(site: dict, stories: dict[str, dict]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    newest = max((stories[s].get("updated") or "2026-09-09") for s in site["order"])
    lines.append(
        f"  <url><loc>https://www.grokbotnews.com/</loc><lastmod>{newest}</lastmod></url>"
    )
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
