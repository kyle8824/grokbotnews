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
MARK_HTML = """        <span class="mark" aria-hidden="true">
          <img src="/img/brand-mark-v4.png" width="54" height="54" alt="">
        </span>"""

X_ICON = (
    '<svg class="x-glyph" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">'
    '<path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817'
    "L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 "
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

    explicit = {
        "sports": ("SPORTS", "sports"),
        "tech": ("TECH", "tech"),
        "entertainment": ("ENTERTAINMENT", "entertainment"),
        "business": ("BUSINESS", "business"),
        "energy": ("ENERGY", "energy"),
        "world": ("WORLD", "world"),
        "politics": ("POLITICS", "politics"),
        "opinion": ("OPINION", "opinion"),
        "us": ("U.S.", "us"),
    }
    if section in explicit:
        return explicit[section]

    if any(x in blob for x in ("sports", "nfl", "mlb", "nba", "tennis", "us-open", "seahawks", "ohtani")):
        return "SPORTS", "sports"
    if any(x in blob for x in ("entertainment", "hollywood", "emmy", "film", "venice", "television")):
        return "ENTERTAINMENT", "entertainment"
    if any(x in blob for x in ("tech", "siri", "ai", "google", "apple", "software", "dreambeans")):
        if "miami" in blob or "cargo" in blob:
            return "U.S.", "us"
        return "TECH", "tech"
    if any(x in blob for x in ("energy", "hormuz", "houthi", "saudi", "oil", "gas", "brent", "weather")):
        return "ENERGY", "energy"
    if any(x in blob for x in ("trade", "tariff", "business", "markets", "dividend")):
        return "BUSINESS", "business"
    if section == "world" or any(x in blob for x in ("diplomacy", "ukraine", "world", "iran", "persian")):
        if any(x in blob for x in ("hormuz", "houthi", "saudi energy")):
            return "ENERGY", "energy"
        return "WORLD", "world"
    if any(
        x in blob
        for x in (
            "midterm", "politics", "supreme", "justice", "homeland", "senate",
            "congress", "ballot", "voter", "redistrict", "ice", "doj", "census",
        )
    ):
        return "POLITICS", "politics"
    if section in ("us", "lead") or "u.s" in article:
        return "U.S.", "us"
    return "U.S.", "us"


def fonts_and_css(*, root_absolute: bool = False) -> str:
    css = "/css/site.css?v=navfull1" if root_absolute else "css/site.css?v=navfull1"
    return f"""  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@400;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{css}">"""


def favicons() -> str:
    return """  <link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="/img/favicon.ico" sizes="any">
  <link rel="apple-touch-icon" href="/img/apple-touch-icon.png">"""


def render_masthead(*, home: bool, nav: dict[str, str] | None = None) -> str:
    nav = nav or {}
    def n(key: str, fallback: str) -> str:
        return nav.get(key) or fallback

    brand_href = "/"
    home_href = "/"
    top = n("top", "#top") if home else "/#top"
    us = n("us", "#us") if home else "/#us"
    world = n("world", "#world") if home else "/#world"
    politics = n("politics", "#politics") if home else "/#politics"
    business = n("business", "#business") if home else "/#business"
    energy = n("energy", "#energy") if home else "/#energy"
    tech = n("tech", "#tech") if home else "/#tech"
    entertainment = n("entertainment", "#entertainment") if home else "/#entertainment"
    sports = n("sports", "#sports") if home else "/#sports"
    opinion = n("opinion", "#opinion") if home else "/#opinion"

    return f"""  <header class="topbar">
    <div class="topbar-grid" aria-hidden="true"></div>
    <span class="slash slash-l1" aria-hidden="true"></span>
    <span class="slash slash-l2" aria-hidden="true"></span>
    <span class="slash slash-r1" aria-hidden="true"></span>
    <span class="slash slash-r2" aria-hidden="true"></span>
    <div class="topbar-inner">
      <a class="brand" href="{brand_href}">
{MARK_HTML}
        <span class="word">
          <span class="row1">GROK BOT</span>
          <span class="row2"><span class="news-word">NEWS</span></span>
        </span>
      </a>
      <p class="tagline">Real News <span>/</span> Real Views <span>/</span> Same Weight</p>
    </div>
  </header>
  <nav class="nav" aria-label="Sections">
    <div class="nav-inner">
      <a class="home" href="{home_href}" aria-label="Home">{HOME_ICON}</a>
      <a class="active" href="{top}">Top Stories</a>
      <a href="{us}">U.S.</a>
      <a href="{world}">World</a>
      <a href="{politics}">Politics</a>
      <a href="{business}">Business</a>
      <a href="{energy}">Energy</a>
      <a href="{tech}">Tech</a>
      <a href="{entertainment}">Entertainment</a>
      <a href="{sports}">Sports</a>
      <a href="{opinion}">Opinion</a>
      <div class="nav-tools">
        <a class="icon" href="/search.html" aria-label="Search">{SEARCH_ICON}</a>
        <a class="icon" href="#menu" aria-label="Menu" data-menu-open>{MENU_ICON}</a>
      </div>
    </div>
  </nav>
"""


def render_footer(site: dict, *, story: bool = False) -> str:
    method_key = "story_footer_method" if story else "footer_method"
    method = site.get(method_key) or site.get("footer_method", "")
    return f"""  <footer class="foot">
    <div class="topbar-grid" aria-hidden="true"></div>
    <span class="slash slash-l1" aria-hidden="true"></span>
    <span class="slash slash-l2" aria-hidden="true"></span>
    <span class="slash slash-r1" aria-hidden="true"></span>
    <span class="slash slash-r2" aria-hidden="true"></span>
    <div class="foot-top">
      <a class="brand" href="/">
        <span class="mark" aria-hidden="true">
          <img src="/img/brand-mark-v4.png" width="54" height="54" alt="">
        </span>
        <span class="word">
          <span class="row1">GROK BOT</span>
          <span class="row2"><span class="news-word">NEWS</span></span>
        </span>
      </a>
      <p class="tagline">Real News <span>/</span> Real Views <span>/</span> Same Weight</p>
      <div class="social">
        <a class="x-link" href="https://x.com/grokbotnews" rel="noopener" target="_blank" aria-label="Grok Bot News on X">
          {X_ICON}
        </a>
      </div>
    </div>
    <div class="foot-bot">
      <nav>
        <a href="/about.html">About</a>
        <a href="/contact.html">Contact</a>
        <a href="/privacy.html">Privacy Policy</a>
        <a href="/terms.html">Terms of Service</a>
      </nav>
      <div class="foot-copy">© 2026 Grok Bot News. All rights reserved.</div>
    </div>
    <p class="method">{esc(method)}</p>
  </footer>
"""


def render_hero(story: dict) -> str:
    slug = story["slug"]
    label, _css = nav_category(story)
    # Prefer mock capitol hero when present for lead chrome parity
    img = "img/hero-capitol.jpg" if (ROOT / "img" / "hero-capitol.jpg").exists() else img_src(story["image"])
    return f"""      <article class="hero" id="politics">
        <img src="/{esc(img)}" alt="{esc(story.get("alt", ""))}">
        <div class="hero-scrim"></div>
        <div class="hero-copy">
          <span class="pill">{esc(label)}</span>
          <h1>{esc(story["hed"])}</h1>
          <p>{esc(short_dek(story))}</p>
          <div class="updated">{esc(story["stamp"])}</div>
          <a class="btn" href="/stories/{esc(slug)}">Read Full Story →</a>
        </div>
      </article>
"""


def render_trending(slugs: list[str], stories: dict[str, dict], claimed: set[str] | None = None) -> str:
    claimed = claimed if claimed is not None else set()
    items = []
    for i, slug in enumerate(slugs, start=1):
        s = stories[slug]
        label, _ = nav_category(s)
        sid = section_id_for_story(slug, stories, claimed)
        items.append(
            f"""          <li{sid}>
            <span class="num">{i}</span>
            <div>
              <h3><a href="/stories/{esc(slug)}">{esc(s["hed"])}</a></h3>
              <div class="meta">{esc(label)} · {esc(s["stamp"])}</div>
            </div>
          </li>"""
        )
    return f"""      <aside class="trend" aria-label="Trending now">
        <h2>Trending Now</h2>
        <ol>
{chr(10).join(items)}
        </ol>
      </aside>
"""


def render_top_cards(slugs: list[str], stories: dict[str, dict], claimed: set[str] | None = None) -> str:
    claimed = claimed if claimed is not None else set()
    cards = []
    for slug in slugs:
        s = stories[slug]
        label, _ = nav_category(s)
        sid = section_id_for_story(slug, stories, claimed)
        cards.append(
            f"""      <article class="card"{sid}>
        <div class="card-photo">
          <a href="/stories/{esc(slug)}"><img src="/{esc(img_src(s["image"]))}" alt="{esc(s.get("alt", ""))}"></a>
          <span class="pill">{esc(label)}</span>
        </div>
        <div class="body">
          <h3><a href="/stories/{esc(slug)}">{esc(s["hed"])}</a></h3>
          <p>{esc(stack_blurb(s))}</p>
          <div class="stamp">{esc(s["stamp"])}</div>
        </div>
      </article>"""
        )
    return (
        '    <h2 class="section-head" id="top">Top Stories</h2>\n'
        '    <div class="grid-3">\n'
        + "\n".join(cards)
        + "\n    </div>\n"
    )


def render_latest(slugs: list[str], stories: dict[str, dict], claimed: set[str] | None = None) -> str:
    claimed = claimed if claimed is not None else set()
    items = []
    for slug in slugs:
        s = stories[slug]
        label, _ = nav_category(s)
        sid = section_id_for_story(slug, stories, claimed)
        items.append(
            f"""        <article class="latest-item"{sid}>
          <a href="/stories/{esc(slug)}"><img src="/{esc(img_src(s["image"]))}" alt="{esc(s.get("alt", ""))}"></a>
          <div>
            <div class="meta">{esc(label)}</div>
            <h4><a href="/stories/{esc(slug)}">{esc(s["hed"])}</a></h4>
            <div class="stamp">{esc(s["stamp"])}</div>
          </div>
        </article>"""
        )
    return (
        '      <aside class="latest" id="latest" aria-label="Latest">\n'
        '        <h2 class="section-head">Latest</h2>\n'
        + "\n".join(items)
        + "\n      </aside>\n"
    )


def render_featured(slugs: list[str], stories: dict[str, dict], claimed: set[str] | None = None) -> str:
    if not slugs:
        return ""
    claimed = claimed if claimed is not None else set()
    main = stories[slugs[0]]
    main_label, _ = nav_category(main)
    main_sid = section_id_for_story(main["slug"], stories, claimed)
    minis = []
    for slug in slugs[1:]:
        s = stories[slug]
        label, _ = nav_category(s)
        sid = section_id_for_story(slug, stories, claimed)
        minis.append(
            f"""            <article class="mini"{sid}>
              <a href="/stories/{esc(slug)}"><img src="/{esc(img_src(s["image"]))}" alt="{esc(s.get("alt", ""))}"></a>
              <div>
                <span class="pill">{esc(label)}</span>
                <h4><a href="/stories/{esc(slug)}">{esc(s["hed"])}</a></h4>
                <div class="stamp">{esc(s["stamp"])}</div>
              </div>
            </article>"""
        )
    return f"""      <section aria-label="Featured analysis">
        <h2 class="section-head" id="opinion">Featured Analysis</h2>
        <div class="feat-grid" id="analysis">
          <div class="feat-lead"{main_sid}>
            <div class="feat-photo">
              <a href="/stories/{esc(main["slug"])}"><img src="/{esc(img_src(main["image"]))}" alt="{esc(main.get("alt", ""))}"></a>
              <span class="pill">{esc(main_label)}</span>
            </div>
            <div class="feat-copy">
              <h3><a href="/stories/{esc(main["slug"])}">{esc(main["hed"])}</a></h3>
              <p>{esc(stack_blurb(main))}</p>
              <div class="stamp">{esc(main["stamp"])}</div>
            </div>
          </div>
          <div class="feat-minis">
{chr(10).join(minis)}
          </div>
        </div>
      </section>
"""


def render_views_layer(*, root_absolute: bool = False) -> str:
    script = "/js/views.js" if root_absolute else "js/views.js"
    return f"""  <div class="views-layer" id="views-layer" hidden>
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
  <script src="{script}" defer></script>"""


def render_views_layer_abs() -> str:
    return render_views_layer(root_absolute=True)



NAV_CLAIM_KEYS = {
    "business", "energy", "world", "us", "tech", "entertainment", "sports",
}


def homepage_nav_targets(order: list[str], stories: dict[str, dict]) -> dict[str, str]:
    """First on-page anchor for each nav label; defaults to #top when absent."""
    targets = {
        "home": "/",
        "top": "#top",
        "politics": "#politics",
        "opinion": "#opinion",
        "us": "#top",
        "world": "#top",
        "business": "#top",
        "energy": "#top",
        "tech": "#top",
        "entertainment": "#top",
        "sports": "#top",
    }
    seen: set[str] = set()
    for slug in order:
        _label, css = nav_category(stories[slug])
        if css == "politics":
            seen.add("politics")
            continue
        if css not in NAV_CLAIM_KEYS or css in seen:
            continue
        targets[css] = f"#{css}"
        seen.add(css)
    return targets


def section_id_for_story(slug: str, stories: dict[str, dict], claimed: set[str]) -> str:
    """Return id="us" etc. the first time that category appears (skip politics/lead)."""
    _label, css = nav_category(stories[slug])
    if css not in NAV_CLAIM_KEYS or css in claimed:
        return ""
    claimed.add(css)
    return f' id="{css}"'


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

    claimed: set[str] = set()
    nav = homepage_nav_targets(order, stories)
    trending_html = render_trending(buckets["trending"], stories, claimed)
    top_html = render_top_cards(buckets["top"], stories, claimed)
    featured_html = render_featured(buckets["featured"], stories, claimed)
    latest_html = render_latest(buckets["latest"], stories, claimed)

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

{render_masthead(home=True, nav=nav)}

  <main id="main" class="wrap">
    <section class="hero-row">
{render_hero(lead)}

{trending_html}
    </section>

{top_html}

    <div class="lower">
{featured_html}

{latest_html}
    </div>
  </main>

{render_footer(site, story=False)}
{render_menu_panel(home=True)}
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
{VIEWS_BTN}
{frames_html(story, indent="      ")}
    </article>
  </main>
{render_footer(site, story=True)}
{render_views_layer_abs()}
{render_menu_panel(home=False)}
</body>
</html>
"""



def render_menu_panel(*, home: bool = True) -> str:
    prefix = "" if home else "/"
    return f"""  <div class="menu-layer" id="menu" hidden>
    <div class="menu-backdrop" data-menu-close></div>
    <div class="menu-sheet" role="dialog" aria-modal="true" aria-label="Site menu">
      <div class="menu-head">
        <h2>Menu</h2>
        <button type="button" class="menu-close" data-menu-close aria-label="Close menu">Close</button>
      </div>
      <nav class="menu-nav" aria-label="All sections">
        <a href="{prefix}#top">Top Stories</a>
        <a href="{prefix}#us">U.S.</a>
        <a href="{prefix}#world">World</a>
        <a href="{prefix}#politics">Politics</a>
        <a href="{prefix}#business">Business</a>
        <a href="{prefix}#energy">Energy</a>
        <a href="{prefix}#tech">Tech</a>
        <a href="{prefix}#entertainment">Entertainment</a>
        <a href="{prefix}#sports">Sports</a>
        <a href="{prefix}#opinion">Opinion</a>
        <hr>
        <a href="/search.html">Search</a>
        <a href="/about.html">About</a>
        <a href="/contact.html">Contact</a>
        <a href="/privacy.html">Privacy Policy</a>
        <a href="/terms.html">Terms of Service</a>
      </nav>
    </div>
  </div>
  <script>
  (function(){{
    var layer=document.getElementById('menu');
    if(!layer) return;
    function open(){{layer.hidden=false;document.body.classList.add('menu-open');}}
    function close(){{layer.hidden=true;document.body.classList.remove('menu-open');}}
    document.addEventListener('click',function(e){{
      if(e.target.closest('[data-menu-open]')){{e.preventDefault();open();return;}}
      if(e.target.closest('[data-menu-close]')){{close();}}
    }});
    document.addEventListener('keydown',function(e){{if(e.key==='Escape'&&!layer.hidden)close();}});
    if(location.hash==='#menu'){{open();}}
  }})();
  </script>
"""


def build_utility_page(site: dict, *, slug: str, title: str, heading: str, body_html: str) -> str:
    canon = f"https://www.grokbotnews.com/{slug}.html"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — GROK BOT NEWS</title>
  <meta name="description" content="{esc(heading)}">
{favicons()}
  <link rel="canonical" href="{esc(canon)}">
  <meta property="og:site_name" content="GROK BOT NEWS">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)} — GROK BOT NEWS">
  <meta property="og:url" content="{esc(canon)}">
{fonts_and_css(root_absolute=True)}
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
{render_masthead(home=False)}
  <main id="main" class="wrap utility-page">
    <p><a class="back-home" href="/">← Home</a></p>
    <article>
      <h1>{esc(heading)}</h1>
{body_html}
    </article>
  </main>
{render_footer(site, story=False)}
{render_menu_panel(home=False)}
</body>
</html>
"""


def build_search_page(site: dict, stories: dict[str, dict]) -> str:
    order = site.get("order") or []
    items = []
    for slug in order:
        s = stories[slug]
        label, _ = nav_category(s)
        items.append(
            {
                "slug": slug,
                "hed": s.get("hed") or "",
                "label": label,
                "stamp": s.get("stamp") or "",
                "dek": s.get("stack_blurb") or stack_blurb(s),
            }
        )
    payload = json.dumps(items, ensure_ascii=False)
    body = f"""      <p class="dek">Search today’s framed headlines. Type a word from a hed, section, or blurb.</p>
      <form class="search-form" id="search-form" action="/search.html" method="get" role="search">
        <label class="sr-only" for="q">Search stories</label>
        <input id="q" name="q" type="search" placeholder="Search headlines…" autocomplete="off">
        <button type="submit">Search</button>
      </form>
      <p class="search-meta" id="search-meta"></p>
      <ul class="search-results" id="search-results"></ul>
      <script type="application/json" id="search-index">{payload}</script>
      <script>
      (function(){{
        var data=[];
        try {{ data=JSON.parse(document.getElementById('search-index').textContent||'[]'); }} catch(e) {{ data=[]; }}
        var input=document.getElementById('q');
        var list=document.getElementById('search-results');
        var meta=document.getElementById('search-meta');
        function escHtml(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}}
        function render(q){{
          q=(q||'').trim().toLowerCase();
          var rows=!q?data:data.filter(function(it){{
            return (it.hed+' '+it.label+' '+it.dek).toLowerCase().indexOf(q)!==-1;
          }});
          meta.textContent=rows.length+' stor'+(rows.length===1?'y':'ies')+(q?' matching “'+q+'”':'');
          list.innerHTML=rows.map(function(it){{
            return '<li><a href="/stories/'+escHtml(it.slug)+'"><span class="pill">'+escHtml(it.label)+'</span><strong>'+escHtml(it.hed)+'</strong><span class="stamp">'+escHtml(it.stamp)+'</span></a></li>';
          }}).join('');
        }}
        var params=new URLSearchParams(location.search);
        if(params.get('q')) input.value=params.get('q');
        render(input.value);
        input.addEventListener('input', function(){{ render(input.value); }});
        document.getElementById('search-form').addEventListener('submit', function(e){{
          e.preventDefault();
          var url=new URL(location.href); url.searchParams.set('q', input.value); history.replaceState(null,'',url);
          render(input.value);
        }});
      }})();
      </script>
"""
    return build_utility_page(
        site,
        slug="search",
        title="Search",
        heading="Search",
        body_html=body,
    )


def utility_bodies(site: dict) -> dict[str, tuple[str, str, str]]:
    method = esc(site.get("footer_method") or "")
    legal = esc(site.get("footer_legal") or "")
    return {
        "about": (
            "About",
            "About Grok Bot News",
            f"""      <p>Grok Bot News publishes event-only headlines with two equal-weight viewpoint blocks — typical center-left and typical center-right — at the same size, with named outlets and outbound links. The site does not declare a winner in the headline.</p>
      <p>{method}</p>
      <p>{legal}</p>
      <p>Follow updates on <a href="https://x.com/grokbotnews" rel="noopener" target="_blank">X @grokbotnews</a>.</p>""",
        ),
        "contact": (
            "Contact",
            "Contact",
            """      <p>Editorial and corrections: <a href="mailto:news@grokbotnews.com">news@grokbotnews.com</a></p>
      <p>Press and partnership notes: <a href="mailto:hello@grokbotnews.com">hello@grokbotnews.com</a></p>
      <p>We do not host public comments or user accounts. For source corrections on a framed story, include the story URL and the outlet link you believe is missing or wrong.</p>""",
        ),
        "privacy": (
            "Privacy Policy",
            "Privacy Policy",
            """      <p>Grok Bot News is a static news site. We do not require accounts, and we do not run a comment system.</p>
      <p><strong>What we may collect.</strong> Standard web server and CDN logs (IP address, user agent, referrer, pages requested) may be processed by our host (currently Vercel) to operate and secure the site. Aggregated analytics, if enabled by the host, may include page views.</p>
      <p><strong>Cookies.</strong> We do not set first-party advertising cookies. The host or embedded fonts provider may set strictly technical cookies or local cache entries required to deliver the page.</p>
      <p><strong>Outbound links.</strong> Viewpoint blocks link to third-party news sites. Their privacy practices are their own.</p>
      <p><strong>Contact.</strong> Privacy questions: <a href="mailto:hello@grokbotnews.com">hello@grokbotnews.com</a>.</p>
      <p>Last updated: September 10, 2026.</p>""",
        ),
        "terms": (
            "Terms of Service",
            "Terms of Service",
            """      <p>By using grokbotnews.com you agree to these terms.</p>
      <p><strong>Nature of the service.</strong> Stories summarize publicly reported events and present two sourced viewpoint frames. Summaries are original and short. Full third-party articles are not reproduced. Headlines state the event only.</p>
      <p><strong>No affiliation.</strong> Grok Bot News is an independent staging page. It is not affiliated with any broadcast or cable news company, and the wordmark is original.</p>
      <p><strong>Photographs.</strong> News-file and stock photographs are used for layout and are not claimed as original field work by this site. Image credits appear on story pages when available.</p>
      <p><strong>Disclaimer.</strong> Content is provided for informational purposes without warranties. Links to external sources do not imply endorsement.</p>
      <p><strong>Changes.</strong> We may update these terms by posting a new version on this page.</p>
      <p>Last updated: September 10, 2026.</p>""",
        ),
    }



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
    for util in ("about", "contact", "privacy", "terms", "search"):
        lines.append(
            f"  <url><loc>https://www.grokbotnews.com/{util}.html</loc>"
            f"<lastmod>{newest}</lastmod></url>"
        )
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

    for slug, (title, heading, body) in utility_bodies(site).items():
        page = build_utility_page(site, slug=slug, title=title, heading=heading, body_html=body)
        (ROOT / f"{slug}.html").write_text(page, encoding="utf-8")
    print("wrote about/contact/privacy/terms")

    (ROOT / "search.html").write_text(build_search_page(site, stories), encoding="utf-8")
    print("wrote search.html")
    print("OK")


if __name__ == "__main__":
    main()
