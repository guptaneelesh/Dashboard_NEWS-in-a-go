#!/usr/bin/env python3
"""
News aggregator for the dashboard.

Pulls RSS feeds from international and Indian sources, classifies each item
into a category, deduplicates near-identical stories by keyword overlap,
assigns a priority score, and writes data/news.json which the static page reads.

Intentionally has no AI dependency — keyword matching only.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import feedparser
import requests

# ---------------------------------------------------------------------------
# Feed registry
# ---------------------------------------------------------------------------
# Each feed has: name, url, region (intl|india), default_category (used as a hint;
# the classifier can still override). Only RSS feeds publicly offered by the
# outlets — no scraping.

FEEDS: list[dict] = [
    # International — general / world
    {"name": "BBC World",           "url": "https://feeds.bbci.co.uk/news/world/rss.xml",                 "region": "intl",  "default": "world"},
    {"name": "Reuters World",       "url": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",  "region": "intl",  "default": "world"},
    {"name": "Al Jazeera",          "url": "https://www.aljazeera.com/xml/rss/all.xml",                  "region": "intl",  "default": "world"},
    {"name": "Sky News World",      "url": "https://feeds.skynews.com/feeds/rss/world.xml",              "region": "intl",  "default": "world"},
    {"name": "France 24",           "url": "https://www.france24.com/en/rss",                            "region": "intl",  "default": "world"},
    {"name": "Deutsche Welle",      "url": "https://rss.dw.com/rdf/rss-en-all",                          "region": "intl",  "default": "world"},
    {"name": "NHK World",           "url": "https://www3.nhk.or.jp/nhkworld/en/news/feeds/",             "region": "intl",  "default": "world"},
    {"name": "NPR World",           "url": "https://feeds.npr.org/1004/rss.xml",                         "region": "intl",  "default": "world"},
    {"name": "AP Top News",         "url": "https://news.google.com/rss/search?q=when:1d+source:apnews.com&hl=en-US&gl=US&ceid=US:en",  "region": "intl",  "default": "world"},
    {"name": "AFP via Google News", "url": "https://news.google.com/rss/search?q=when:1d+source:afp.com&hl=en-US&gl=US&ceid=US:en",     "region": "intl",  "default": "world"},

    # International — business / markets
    {"name": "CNBC Top News",       "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",  "region": "intl",  "default": "business"},
    {"name": "Bloomberg via Google","url": "https://news.google.com/rss/search?q=when:1d+source:bloomberg.com&hl=en-US&gl=US&ceid=US:en", "region": "intl",  "default": "business"},
    {"name": "Reuters Business",    "url": "https://www.reutersagency.com/feed/?best-topics=business-finance&post_type=best",       "region": "intl",  "default": "business"},
    {"name": "BBC Business",        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",             "region": "intl",  "default": "business"},

    # International — tech / AI
    {"name": "BBC Tech",            "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",           "region": "intl",  "default": "technology"},
    {"name": "TechCrunch",          "url": "https://techcrunch.com/feed/",                               "region": "intl",  "default": "technology"},
    {"name": "The Verge",           "url": "https://www.theverge.com/rss/index.xml",                     "region": "intl",  "default": "technology"},
    {"name": "Ars Technica",        "url": "https://feeds.arstechnica.com/arstechnica/index",            "region": "intl",  "default": "technology"},
    {"name": "MIT Tech Review",     "url": "https://www.technologyreview.com/feed/",                     "region": "intl",  "default": "technology"},

    # International — science / health / environment
    {"name": "BBC Science",         "url": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "region": "intl", "default": "science"},
    {"name": "BBC Health",          "url": "https://feeds.bbci.co.uk/news/health/rss.xml",               "region": "intl",  "default": "health"},
    {"name": "Reuters Health",      "url": "https://www.reutersagency.com/feed/?best-topics=health&post_type=best",  "region": "intl",  "default": "health"},
    {"name": "NASA Breaking News",  "url": "https://www.nasa.gov/news-release/feed/",                    "region": "intl",  "default": "science"},

    # International — sports / entertainment
    {"name": "BBC Sport",           "url": "https://feeds.bbci.co.uk/sport/rss.xml",                     "region": "intl",  "default": "sports"},
    {"name": "BBC Entertainment",   "url": "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml", "region": "intl", "default": "entertainment"},
    {"name": "Variety",             "url": "https://variety.com/feed/",                                  "region": "intl",  "default": "entertainment"},

    # India — general
    {"name": "NDTV Top Stories",    "url": "https://feeds.feedburner.com/ndtvnews-top-stories",          "region": "india", "default": "india"},
    {"name": "NDTV India (Hindi)",  "url": "https://khabar.ndtv.com/rss/news",                           "region": "india", "default": "india"},
    {"name": "The Hindu National",  "url": "https://www.thehindu.com/news/national/feeder/default.rss",  "region": "india", "default": "india"},
    {"name": "Indian Express India","url": "https://indianexpress.com/section/india/feed/",              "region": "india", "default": "india"},
    {"name": "India Today",         "url": "https://www.indiatoday.in/rss/1206578",                      "region": "india", "default": "india"},
    {"name": "Times of India Top",  "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "region": "india", "default": "india"},
    {"name": "Scroll.in",           "url": "https://feeds.feedburner.com/ScrollinArticles.rss",          "region": "india", "default": "india"},
    {"name": "Hindustan Times India","url": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "region": "india", "default": "india"},

    # India — business / markets
    {"name": "Moneycontrol Business","url": "https://www.moneycontrol.com/rss/business.xml",             "region": "india", "default": "business"},
    {"name": "Moneycontrol Markets", "url": "https://www.moneycontrol.com/rss/marketreports.xml",        "region": "india", "default": "markets"},
    {"name": "ET Markets",          "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", "region": "india", "default": "markets"},
    {"name": "Business Standard",   "url": "https://www.business-standard.com/rss/latest.rss",           "region": "india", "default": "business"},
    {"name": "Livemint Top",        "url": "https://www.livemint.com/rss/news",                          "region": "india", "default": "business"},

    # India — tech / education
    {"name": "ET Tech",             "url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", "region": "india", "default": "technology"},
    {"name": "The Hindu Education", "url": "https://www.thehindu.com/education/feeder/default.rss",      "region": "india", "default": "education"},

    # India — sports / entertainment
    {"name": "NDTV Sports",         "url": "https://feeds.feedburner.com/ndtvsports-latest",             "region": "india", "default": "sports"},
    {"name": "Bollywood Hungama",   "url": "https://www.bollywoodhungama.com/rss/news.xml",              "region": "india", "default": "bollywood"},

    # Quirky / offbeat
    {"name": "BBC Odd News (Google)","url": "https://news.google.com/rss/search?q=when:1d+weird+OR+bizarre+OR+unusual&hl=en-US&gl=US&ceid=US:en", "region": "intl", "default": "quirky"},
]

# ---------------------------------------------------------------------------
# Category classifier — keyword sets per category, scored on title+summary
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "war":           ["war", "ceasefire", "missile", "airstrike", "invasion", "troops", "soldiers killed", "military strike", "combat", "frontline", "shelling", "drone strike"],
    "politics":      ["election", "parliament", "president", "prime minister", "minister", "modi", "biden", "trump", "putin", "xi jinping", "congress", "bjp", "policy", "bill passed", "lok sabha", "rajya sabha", "vote"],
    "government":    ["government", "cabinet", "ministry", "regulator", "regulation", "summit", "diplomatic", "treaty", "sanctions", "tariff"],
    "education":     ["education", "school", "university", "college", "exam", "neet", "jee", "cbse", "icse", "ugc", "students", "teacher", "syllabus"],
    "ai":            ["ai ", "artificial intelligence", "chatgpt", "openai", "anthropic", "claude", "gemini", "llm", "generative ai", "machine learning", "deep learning", "neural network", "copilot"],
    "technology":    ["tech", "software", "startup", "cybersecurity", "hack", "data breach", "cloud", "saas", "smartphone", "gadget", "iphone", "android", "samsung", "google", "apple", "microsoft", "meta", "nvidia", "chip", "semiconductor"],
    "markets":       ["sensex", "nifty", "nse", "bse", "stock", "shares", "ipo", "market cap", "wall street", "nasdaq", "dow jones", "rupee", "dollar", "bond yield", "fed", "rbi", "interest rate"],
    "business":      ["business", "company", "earnings", "revenue", "profit", "merger", "acquisition", "ceo", "layoff", "funding round"],
    "economy":       ["economy", "gdp", "inflation", "recession", "unemployment", "trade deficit", "fiscal", "budget", "imf", "world bank"],
    "health":        ["health", "covid", "virus", "vaccine", "hospital", "disease", "outbreak", "who ", "fda", "drug", "patient", "doctor", "mental health", "cancer", "diabetes"],
    "science":       ["research", "study finds", "scientists", "discovery", "nasa", "isro", "spacex", "space", "satellite", "mars", "moon", "telescope", "physics", "biology", "experiment"],
    "environment":   ["climate", "global warming", "emissions", "carbon", "wildfire", "flood", "drought", "heatwave", "biodiversity", "pollution", "renewable", "solar", "wind energy", "cyclone", "earthquake"],
    "sports":        ["cricket", "ipl", "world cup", "olympic", "football", "fifa", "tennis", "wimbledon", "f1", "formula 1", "match", "tournament", "league", "champion", "kohli", "messi", "ronaldo"],
    "bollywood":     ["bollywood", "shah rukh", "salman", "deepika", "ranveer", "alia", "ranbir", "khan", "filmfare", "box office", "hindi film"],
    "hollywood":     ["hollywood", "oscar", "academy awards", "netflix", "disney", "marvel", "warner", "sequel", "premiere", "blockbuster"],
    "entertainment": ["film", "movie", "music", "album", "celebrity", "actor", "actress", "concert", "festival", "tv series", "streaming"],
    "fashion":       ["fashion", "couture", "runway", "designer", "vogue", "milan fashion", "paris fashion", "trend"],
    "quirky":        ["bizarre", "weird", "unusual", "strange", "world record", "guinness", "viral", "freak", "oddity", "rare phenomenon"],
}

# Category display order on the UI (also defines priority weight tiebreak)
CATEGORY_ORDER = [
    "war", "politics", "government", "economy", "markets", "business",
    "ai", "technology", "science", "health", "environment", "education",
    "sports", "bollywood", "hollywood", "entertainment", "fashion", "quirky",
    "world", "india",
]

# Words/phrases that bump priority — high-impact signals
PRIORITY_HIGH = {
    "global": ["world", "global", "international", "un ", "united nations", "g20", "g7", "nato"],
    "crisis": ["crisis", "war", "attack", "killed", "dead", "explosion", "outbreak", "pandemic", "collapse", "crash", "breaking"],
    "india":  ["india", "indian", "modi", "delhi", "mumbai", "rbi", "sensex", "nifty"],
    "econ":   ["recession", "inflation", "rate hike", "rate cut", "tariff", "sanctions", "default"],
}

# Hindi detection: presence of Devanagari range
DEVANAGARI = re.compile(r"[\u0900-\u097F]")

# Stopwords for keyword extraction (used in dedup)
STOPWORDS = {
    "the","a","an","and","or","but","of","in","on","at","to","for","with","by","from","as","is","are","was","were","be","been","being","it","its","this","that","these","those","he","she","they","them","their","his","her","we","our","you","your","i","my","me","said","says","say","will","has","have","had","not","no","do","does","did","new","news","over","after","before","one","two","three","first","last","day","year","week","month","more","most","than","into","also","may","might","could","would","should","can","cannot","amid","via","update","updates","latest","top","report","reports","reportedly","reuters","bbc","ap","afp",
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Article:
    id: str
    title: str
    title_hindi: str | None
    summary: str
    link: str
    source: str
    source_domain: str
    region: str           # intl | india
    category: str
    published_iso: str    # ISO 8601 UTC
    published_ts: int     # unix seconds
    has_hindi: bool
    priority: int
    keywords: list[str] = field(default_factory=list)
    anchors: list[str] = field(default_factory=list)
    related_sources: list[dict] = field(default_factory=list)  # other sources covering the same story

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_text(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)         # strip HTML
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_ts(entry) -> tuple[str, int]:
    """Return (iso, unix_ts) from a feedparser entry; fallback to now."""
    for key in ("published", "updated", "pubDate", "created"):
        val = entry.get(key)
        if val:
            try:
                dt = parsedate_to_datetime(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                dt_utc = dt.astimezone(timezone.utc)
                return dt_utc.isoformat(), int(dt_utc.timestamp())
            except Exception:
                pass
    # parsed_published_parsed struct_time
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                ts = int(time.mktime(val))
                dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
                return dt_utc.isoformat(), ts
            except Exception:
                pass
    now = datetime.now(tz=timezone.utc)
    return now.isoformat(), int(now.timestamp())


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def classify(title: str, summary: str, default: str) -> str:
    """Pick the best category by keyword hit count; fall back to default."""
    text = f"{title} {summary}".lower()
    best_cat, best_score = default, 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text)
        if score > best_score:
            best_cat, best_score = cat, score
    return best_cat


def compute_priority(title: str, summary: str, region: str, category: str) -> int:
    """Score 0–100. Higher = more important / front-page."""
    text = f"{title} {summary}".lower()
    score = 0
    for kw in PRIORITY_HIGH["global"]:
        if kw in text: score += 8
    for kw in PRIORITY_HIGH["crisis"]:
        if kw in text: score += 10
    for kw in PRIORITY_HIGH["india"]:
        if kw in text: score += 6
    for kw in PRIORITY_HIGH["econ"]:
        if kw in text: score += 7
    if category in {"war", "politics", "economy", "markets", "ai"}:
        score += 5
    if category == "quirky":
        score -= 8
    return max(0, min(100, score))


def extract_keywords(title: str, summary: str, k: int = 8) -> list[str]:
    text = f"{title} {summary}".lower()
    # words = letters only, length >= 4
    words = re.findall(r"[a-z]{4,}", text)
    words = [w for w in words if w not in STOPWORDS]
    most = [w for w, _ in Counter(words).most_common(k)]
    return most


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


# "Anchor" tokens are proper nouns and other content-bearing words in the title.
# Two articles covering the same story almost always share several anchors
# (Israel/Hamas/ceasefire; Sensex/RBI; Modi/Maharashtra) even when the rest of
# the wording differs. We extract them from the original-case title so we keep
# the capitalization signal.
def extract_anchors(title: str) -> set[str]:
    # capitalized words >= 4 chars (Israel, Sensex, Modi, OpenAI)
    caps = re.findall(r"\b[A-Z][A-Za-z]{3,}\b", title)
    # all-caps abbreviations of length >= 2 (RBI, NSE, GPT, US)
    abbr = re.findall(r"\b[A-Z]{2,}\b", title)
    # numbers with units / context (500, 2026)
    nums = re.findall(r"\b\d{2,}\b", title)
    anchors = {w.lower() for w in caps + abbr + nums}
    anchors -= STOPWORDS
    return anchors


def make_id(title: str, link: str) -> str:
    h = hashlib.sha1(f"{title}|{link}".encode("utf-8")).hexdigest()
    return h[:12]


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_feed(feed: dict) -> list[Article]:
    """Fetch one RSS feed and turn its entries into Articles."""
    try:
        # feedparser handles redirects and most weird XML; set a UA to look polite
        headers = {"User-Agent": "NewsDashboard/1.0 (+https://github.com)"}
        resp = requests.get(feed["url"], headers=headers, timeout=20)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"[warn] {feed['name']}: {e}", file=sys.stderr)
        return []

    out: list[Article] = []
    for entry in parsed.entries[:40]:  # cap per feed
        title = clean_text(entry.get("title", ""))
        if not title:
            continue
        summary = clean_text(entry.get("summary", "") or entry.get("description", ""))[:600]
        link = entry.get("link", "").strip()
        if not link:
            continue
        iso, ts = to_ts(entry)
        has_hindi = bool(DEVANAGARI.search(title) or DEVANAGARI.search(summary))
        category = classify(title, summary, feed["default"])
        priority = compute_priority(title, summary, feed["region"], category)
        article = Article(
            id=make_id(title, link),
            title=title,
            title_hindi=title if has_hindi else None,
            summary=summary,
            link=link,
            source=feed["name"],
            source_domain=domain_of(link) or domain_of(feed["url"]),
            region=feed["region"],
            category=category,
            published_iso=iso,
            published_ts=ts,
            has_hindi=has_hindi,
            priority=priority,
            keywords=extract_keywords(title, summary),
            anchors=sorted(extract_anchors(title)),
        )
        out.append(article)
    print(f"[ok]   {feed['name']}: {len(out)} items", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Deduplication: cluster articles that share substantial keyword overlap
# ---------------------------------------------------------------------------

def dedupe(articles: list[Article]) -> list[Article]:
    """Cluster near-duplicate stories. Match criterion: two articles describe the
    same event if they share enough named-entity "anchors" in their titles.
    The strongest article in each cluster (priority, then recency) becomes
    canonical; the rest attach as `related_sources`."""
    # Sort by priority desc, then recency desc — strongest claim wins canonical
    articles.sort(key=lambda a: (a.priority, a.published_ts), reverse=True)
    keep: list[Article] = []
    anchor_sets: list[set] = []
    kw_sets: list[set] = []
    for art in articles:
        anc = set(art.anchors)
        kw = set(art.keywords)
        merged = False
        for i, existing_anc in enumerate(anchor_sets):
            shared_anc = len(anc & existing_anc)
            smaller = min(len(anc), len(existing_anc)) or 1
            coverage = shared_anc / smaller
            kj = jaccard(kw, kw_sets[i])
            # Match if: (a) very strong anchor overlap, or
            # (b) 2+ shared anchors that cover most of the smaller title's anchors, or
            # (c) 2+ shared anchors with decent keyword overlap as a fallback.
            if shared_anc >= 3 or (shared_anc >= 2 and coverage >= 0.6) or (shared_anc >= 2 and kj >= 0.20):
                canonical = keep[i]
                if art.source_domain and art.source_domain != canonical.source_domain:
                    if not any(r["domain"] == art.source_domain for r in canonical.related_sources):
                        canonical.related_sources.append({
                            "name": art.source,
                            "domain": art.source_domain,
                            "link": art.link,
                        })
                if art.published_ts > canonical.published_ts:
                    canonical.published_ts = art.published_ts
                    canonical.published_iso = art.published_iso
                merged = True
                break
        if not merged:
            keep.append(art)
            anchor_sets.append(anc)
            kw_sets.append(kw)
    return keep


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_articles: list[Article] = []
    for feed in FEEDS:
        all_articles.extend(fetch_feed(feed))

    print(f"[info] total fetched: {len(all_articles)}", file=sys.stderr)

    # Drop articles older than 8 days — the UI's longest filter is 7d
    cutoff = int(time.time()) - (8 * 24 * 3600)
    fresh = [a for a in all_articles if a.published_ts >= cutoff]
    print(f"[info] within 8-day window: {len(fresh)}", file=sys.stderr)

    deduped = dedupe(fresh)
    print(f"[info] after dedup: {len(deduped)}", file=sys.stderr)

    # Bump priority by number of corroborating sources (multi-source = bigger story)
    for art in deduped:
        bonus = min(15, len(art.related_sources) * 3)
        art.priority = min(100, art.priority + bonus)

    # Final sort: priority desc, then recency desc
    deduped.sort(key=lambda a: (a.priority, a.published_ts), reverse=True)

    # Cap output — UI doesn't need more than ~400 stories
    deduped = deduped[:400]

    # Counts by category & region — handy for the UI to show badges
    cat_counts = Counter(a.category for a in deduped)
    region_counts = Counter(a.region for a in deduped)

    payload = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "generated_ts": int(time.time()),
        "total": len(deduped),
        "category_counts": dict(cat_counts),
        "region_counts": dict(region_counts),
        "category_order": CATEGORY_ORDER,
        "articles": [asdict(a) for a in deduped],
    }

    out_path = Path(__file__).resolve().parent.parent / "data" / "news.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] wrote {out_path} ({len(deduped)} articles)", file=sys.stderr)


if __name__ == "__main__":
    main()
