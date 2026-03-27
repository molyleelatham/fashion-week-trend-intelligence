"""
Reddit scraper — fashion subreddit posts mentioning our 15 brands, Jan 2026+.
Run: python -m backend.scrapers.reddit
Saves: backend/data/raw/reddit/{YYYY-MM-DD}.jsonl

Requires in .env:
  REDDIT_CLIENT_ID=
  REDDIT_CLIENT_SECRET=
  REDDIT_USER_AGENT=FashionIntelligence/1.0
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import praw
from dotenv import load_dotenv
from loguru import logger

load_dotenv()
logger.add("backend/data/raw/reddit/scraper.log", rotation="10 MB", level="INFO")

SUBREDDITS = ["HighFashion", "femalefashionadvice", "streetwear", "malefashionadvice"]

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

MIN_TIMESTAMP = datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp()
RATE_LIMIT = 2.0
OUT_DIR = Path("backend/data/raw/reddit")


def get_reddit_client() -> praw.Reddit | None:
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.getenv("REDDIT_USER_AGENT", "FashionIntelligence/1.0")

    if not client_id or not client_secret:
        logger.error("REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set in .env")
        return None

    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )


def scrape():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    out_file = OUT_DIR / f"{today}.jsonl"
    total_saved = 0
    seen_ids: set[str] = set()

    reddit = get_reddit_client()
    if reddit is None:
        logger.warning(
            "No Reddit credentials found. Writing placeholder file.\n"
            "Add REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to .env to enable real scraping."
        )
        placeholder = {
            "status": "no_credentials",
            "message": "Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env",
            "scraped_at": datetime.utcnow().isoformat(),
        }
        with open(out_file, "a") as f:
            f.write(json.dumps(placeholder) + "\n")
        print(f"No Reddit credentials — placeholder written to {out_file}")
        return

    for subreddit_name in SUBREDDITS:
        for brand in BRANDS:
            logger.info(f"Searching r/{subreddit_name} for '{brand}'")
            try:
                subreddit = reddit.subreddit(subreddit_name)
                results = subreddit.search(
                    brand,
                    sort="new",
                    time_filter="year",
                    limit=50,
                )

                for post in results:
                    if post.id in seen_ids:
                        continue
                    if post.created_utc < MIN_TIMESTAMP:
                        continue

                    seen_ids.add(post.id)
                    record = {
                        "id": post.id,
                        "title": post.title,
                        "body": post.selftext[:2000] if post.selftext else "",
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "created_utc": datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ).isoformat(),
                        "subreddit": subreddit_name,
                        "url": f"https://reddit.com{post.permalink}",
                        "brand": BRAND_SLUG_MAP[brand],
                        "source": "reddit",
                        "scraped_at": datetime.utcnow().isoformat(),
                        "status": "ok",
                    }

                    with open(out_file, "a") as f:
                        f.write(json.dumps(record) + "\n")
                    total_saved += 1

                time.sleep(RATE_LIMIT)

            except Exception as e:
                logger.error(f"Error searching r/{subreddit_name} for {brand}: {e}")
                time.sleep(RATE_LIMIT)
                continue

    logger.info(f"Reddit scraper done. {total_saved} posts saved to {out_file}")
    print(f"Done: {total_saved} posts saved to {out_file}")


if __name__ == "__main__":
    scrape()
