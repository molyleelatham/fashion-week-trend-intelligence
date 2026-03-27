"""
Business of Fashion scraper — brand articles from Jan 2026 via RSS feed.
Run: python -m backend.scrapers.bof
Saves: backend/data/raw/bof/{YYYY-MM-DD}.jsonl

Note: BoF's search page is JavaScript-rendered so we use their RSS feed
(/feed) and filter by brand mentions. Article bodies require a subscription,
so we extract whatever is publicly available (title, excerpt, metadata).
"""
import json
import re
import time
from datetime import datetime, date
from pathlib import Path
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup
from loguru import logger

logger.add("backend/data/raw/bof/scraper.log", rotation="10 MB", level="INFO")

BRANDS = [
    "Chanel", "Dior", "Louis Vuitton", "Givenchy", "Saint Laurent",
    "Prada", "Gucci", "Bottega Veneta", "Versace", "Miu Miu",
    "Maison Margiela", "Rick Owens", "Burberry", "Alexander McQueen", "Alexander Wang",
]

BRAND_SLUG_MAP = {
    "Chanel": "chanel", "Dior": "dior", "Louis Vuitton": "louis-vuitton",
    "Givenchy": "givenchy", "Saint Laurent": "saint-laurent", "Prada": "prada",
    "Gucci": "gucci", "Bottega Veneta": "bottega-veneta", "Versace": "versace",
    "Miu Miu": "miu-miu", "Maison Margiela": "maison-margiela", "Rick Owens": "rick-owens",
    "Burberry": "burberry", "Alexander McQueen": "alexander-mcqueen", "Alexander Wang": "alexander-wang",
}

MIN_DATE = date(2026, 1, 1)
RSS_FEED = "https://www.businessoffashion.com/feed"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}
RATE_LIMIT = 2.0
MAX_RETRIES = 3
OUT_DIR = Path("backend/data/raw/bof")


def fetch_with_retry(client: httpx.Client, url: str) -> httpx.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, timeout=15)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (403, 429, 401):
                logger.warning(f"Blocked ({resp.status_code}) on {url} — attempt {attempt}/{MAX_RETRIES}")
                time.sleep(2 ** attempt)
            else:
                logger.warning(f"HTTP {resp.status_code} on {url}")
                return None
        except httpx.RequestError as e:
            logger.warning(f"Request error: {e} — attempt {attempt}/{MAX_RETRIES}")
            time.sleep(2 ** attempt)
    logger.error(f"Giving up on {url} after {MAX_RETRIES} attempts")
    return None


def detect_brand_mentions(text: str) -> list[str]:
    text_lower = text.lower()
    return [BRAND_SLUG_MAP[b] for b in BRANDS if b.lower() in text_lower]


def parse_date(date_str: str) -> date | None:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def fetch_article_excerpt(client: httpx.Client, url: str) -> str:
    """Fetch whatever body text is publicly visible (excerpt before paywall)."""
    resp = fetch_with_retry(client, url)
    if not resp:
        return ""
    soup = BeautifulSoup(resp.text, "html.parser")

    # Try to get the lead paragraph / open excerpt
    for selector in [
        "div.article-body p",
        "div[class*='ArticleBody'] p",
        "div[class*='body'] p",
        "article p",
        "main p",
    ]:
        paragraphs = soup.select(selector)
        if paragraphs:
            text = " ".join(p.get_text(strip=True) for p in paragraphs[:4])
            if len(text) > 100:
                return text[:2000]

    # Fallback: meta description
    meta = soup.select_one("meta[name='description'], meta[property='og:description']")
    if meta:
        return meta.get("content", "")[:500]

    return ""


def parse_rss_feed(xml_text: str) -> list[dict]:
    """Parse RSS feed and return all items as dicts."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as e:
        logger.error(f"Failed to parse RSS XML: {e}")
        return []

    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    items = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        url = (item.findtext("link") or "").strip()
        pub_date_str = (item.findtext("pubDate") or "").strip()
        description = (item.findtext("description") or "").strip()

        # Strip HTML from description
        if description:
            description = BeautifulSoup(description, "html.parser").get_text(strip=True)

        published_date = parse_date(pub_date_str)

        items.append({
            "title": title,
            "url": url,
            "published_at": pub_date_str,
            "published_date": published_date,
            "excerpt": description,
        })

    return items


def scrape():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_file = OUT_DIR / f"{today}.jsonl"
    total_saved = 0
    seen_urls: set[str] = set()

    logger.info("Fetching BoF RSS feed...")
    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        resp = fetch_with_retry(client, RSS_FEED)
        if resp is None:
            logger.error("Could not fetch BoF RSS feed — aborting")
            print("BoF RSS feed unavailable. Skipping.")
            return

        items = parse_rss_feed(resp.text)
        logger.info(f"Parsed {len(items)} items from RSS feed")

        # Filter to Jan 2026+ and brand mentions
        for item in items:
            pub = item.get("published_date")
            if pub and pub < MIN_DATE:
                continue

            combined_text = (item["title"] or "") + " " + (item["excerpt"] or "")
            brand_mentions = detect_brand_mentions(combined_text)

            if not brand_mentions:
                continue

            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])

            # Fetch article excerpt
            logger.info(f"Fetching article: {item['title'][:60]}")
            time.sleep(RATE_LIMIT)
            body = fetch_article_excerpt(client, item["url"])

            # Re-detect brands with full body
            all_mentions = detect_brand_mentions(combined_text + " " + body)

            record = {
                "title": item["title"],
                "url": item["url"],
                "published_at": item["published_at"],
                "body_text": body or item["excerpt"],
                "brand_mentions": all_mentions or brand_mentions,
                "source": "bof",
                "scraped_at": datetime.utcnow().isoformat(),
                "status": "ok",
            }

            with open(out_file, "a") as f:
                f.write(json.dumps(record) + "\n")
            total_saved += 1
            logger.info(f"Saved: {item['title'][:60]} | brands: {all_mentions}")

    logger.info(f"BoF scraper done. {total_saved} articles saved to {out_file}")
    print(f"Done: {total_saved} articles saved to {out_file}")


if __name__ == "__main__":
    scrape()
