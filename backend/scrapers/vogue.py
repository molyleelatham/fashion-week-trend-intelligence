"""
Vogue Runway scraper — SS2026 and AW2026 collection reviews.
Run: python -m backend.scrapers.vogue
Saves: backend/data/raw/vogue/{brand}-{season}.jsonl
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from loguru import logger

logger.add("backend/data/raw/vogue/scraper.log", rotation="10 MB", level="INFO")

BRANDS = [
    {"slug": "chanel",            "vogue_slug": "chanel"},
    {"slug": "dior",              "vogue_slug": "christian-dior"},
    {"slug": "louis-vuitton",     "vogue_slug": "louis-vuitton"},
    {"slug": "givenchy",          "vogue_slug": "givenchy"},
    {"slug": "saint-laurent",     "vogue_slug": "saint-laurent"},
    {"slug": "prada",             "vogue_slug": "prada"},
    {"slug": "gucci",             "vogue_slug": "gucci"},
    {"slug": "bottega-veneta",    "vogue_slug": "bottega-veneta"},
    {"slug": "versace",           "vogue_slug": "versace"},
    {"slug": "miu-miu",           "vogue_slug": "miu-miu"},
    {"slug": "maison-margiela",   "vogue_slug": "maison-margiela"},
    {"slug": "rick-owens",        "vogue_slug": "rick-owens"},
    {"slug": "burberry",          "vogue_slug": "burberry"},
    {"slug": "alexander-mcqueen", "vogue_slug": "alexander-mcqueen"},
    {"slug": "alexander-wang",    "vogue_slug": "alexander-wang"},
]

SEASONS = [
    {"label": "SS2026", "vogue_season": "spring-2026-ready-to-wear"},
    {"label": "AW2026", "vogue_season": "fall-2026-ready-to-wear"},
]

BASE_URL = "https://www.vogue.com/fashion-shows"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
RATE_LIMIT = 2.0  # seconds between requests
MAX_RETRIES = 3
OUT_DIR = Path("backend/data/raw/vogue")


def fetch_with_retry(client: httpx.Client, url: str) -> httpx.Response | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.get(url, timeout=15)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (403, 429):
                logger.warning(f"Blocked ({resp.status_code}) on {url} — attempt {attempt}/{MAX_RETRIES}")
                time.sleep(2 ** attempt)
            else:
                logger.warning(f"HTTP {resp.status_code} on {url}")
                return None
        except httpx.RequestError as e:
            logger.warning(f"Request error on {url}: {e} — attempt {attempt}/{MAX_RETRIES}")
            time.sleep(2 ** attempt)
    logger.error(f"Giving up on {url} after {MAX_RETRIES} attempts")
    return None


def parse_collection_page(html: str, brand_slug: str, season_label: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")

    # Review text — main body content
    review_text = ""
    for selector in ["div.body__inner-container", "div[data-testid='BodyWrapper']", "article", "main"]:
        el = soup.select_one(selector)
        if el:
            review_text = el.get_text(separator=" ", strip=True)
            break

    if not review_text:
        return None

    # Look count — try multiple patterns
    look_count = None
    for el in soup.select("span, div, p"):
        text = el.get_text(strip=True)
        if "look" in text.lower() and any(c.isdigit() for c in text):
            try:
                look_count = int("".join(filter(str.isdigit, text.split()[0])))
                break
            except (ValueError, IndexError):
                pass

    # Show date
    show_date = None
    for selector in ["time", "[datetime]", "span.date"]:
        el = soup.select_one(selector)
        if el:
            show_date = el.get("datetime") or el.get_text(strip=True)
            break

    # Show notes — typically a short intro paragraph
    show_notes = ""
    intro = soup.select_one("p.intro, div.intro, [data-testid='Lede']")
    if intro:
        show_notes = intro.get_text(strip=True)

    return {
        "brand": brand_slug,
        "season": season_label,
        "url": url,
        "review_text": review_text[:5000],  # cap at 5k chars
        "show_notes": show_notes,
        "look_count": look_count,
        "show_date": show_date,
        "scraped_at": datetime.utcnow().isoformat(),
    }


def scrape():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_saved = 0

    with httpx.Client(headers=HEADERS, follow_redirects=True) as client:
        for season in SEASONS:
            for brand in BRANDS:
                url = f"{BASE_URL}/{season['vogue_season']}/{brand['vogue_slug']}"
                out_file = OUT_DIR / f"{brand['slug']}-{season['label']}.jsonl"

                logger.info(f"Fetching {brand['slug']} {season['label']} → {url}")
                resp = fetch_with_retry(client, url)

                if resp is None:
                    logger.warning(f"Skipping {brand['slug']} {season['label']} — no response")
                    # Write a minimal record so downstream code knows we tried
                    record = {
                        "brand": brand["slug"],
                        "season": season["label"],
                        "url": url,
                        "review_text": "",
                        "show_notes": "",
                        "look_count": None,
                        "show_date": None,
                        "scraped_at": datetime.utcnow().isoformat(),
                        "status": "blocked",
                    }
                    with open(out_file, "a") as f:
                        f.write(json.dumps(record) + "\n")
                    time.sleep(RATE_LIMIT)
                    continue

                record = parse_collection_page(resp.text, brand["slug"], season["label"], url)
                if record:
                    record["status"] = "ok"
                    with open(out_file, "a") as f:
                        f.write(json.dumps(record) + "\n")
                    total_saved += 1
                    logger.info(f"Saved {brand['slug']} {season['label']} ({len(record['review_text'])} chars)")
                else:
                    logger.warning(f"Could not parse content for {brand['slug']} {season['label']}")

                time.sleep(RATE_LIMIT)

    logger.info(f"Vogue scraper done. {total_saved} records saved.")
    print(f"Done: {total_saved} records saved to {OUT_DIR}/")


if __name__ == "__main__":
    scrape()
