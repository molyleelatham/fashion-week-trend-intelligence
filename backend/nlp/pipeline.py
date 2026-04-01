"""
NLP pipeline — loads all raw JSONL, runs sentiment + theme extraction, writes to DB.
Run: python -m backend.nlp.pipeline
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy.orm import Session

from backend.db.database import SessionLocal
from backend.db.seed import seed_brands
from backend.api.models import Brand, Article, Collection, SentimentScore, TrendTheme, ThemeScore
from backend.nlp import sentiment as sent_mod
from backend.nlp import themes as theme_mod

logger.add("backend/data/raw/nlp_pipeline.log", rotation="10 MB", level="INFO")

RAW_DIR = Path("backend/data/raw")
VOGUE_DIR = RAW_DIR / "vogue"
BOF_DIR = RAW_DIR / "bof"
REDDIT_DIR = RAW_DIR / "reddit"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    records = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return records


def _get_brand(db: Session, slug: str) -> Brand | None:
    return db.query(Brand).filter(Brand.slug == slug).first()


def _upsert_article(db: Session, record: dict) -> Article | None:
    """Insert article if URL not already present; return the Article row."""
    url = record.get("url", "").strip()
    if not url:
        return None

    existing = db.query(Article).filter(Article.url == url).first()
    if existing:
        return existing

    source = record.get("source", "unknown")
    title = record.get("title", "")
    body = record.get("body_text") or record.get("body") or record.get("excerpt") or ""

    # Parse published_at
    pub_str = record.get("published_at") or record.get("created_utc") or ""
    pub_dt = None
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            pub_dt = datetime.strptime(pub_str.strip(), fmt)
            break
        except (ValueError, AttributeError):
            continue

    brand_tags = record.get("brand_mentions") or (
        [record["brand"]] if record.get("brand") else []
    )

    article = Article(
        source=source,
        url=url,
        title=title,
        published_at=pub_dt,
        body=body[:5000],
        brand_tags=brand_tags,
        scraped_at=datetime.utcnow(),
    )
    db.add(article)
    db.flush()   # get article.id without committing
    return article


def _upsert_collection(db: Session, record: dict) -> tuple[Collection | None, Brand | None]:
    """Insert collection row from a Vogue JSONL record."""
    brand_slug = record.get("brand")
    season = record.get("season")
    if not brand_slug or not season:
        return None, None

    brand = _get_brand(db, brand_slug)
    if not brand:
        logger.warning(f"Brand not found: {brand_slug}")
        return None, None

    existing = (
        db.query(Collection)
        .filter(Collection.brand_id == brand.id, Collection.season == season)
        .first()
    )
    if existing:
        return existing, brand

    year = 2026
    show_date = None
    if record.get("show_date"):
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%B %d, %Y"):
            try:
                show_date = datetime.strptime(record["show_date"].strip(), fmt).date()
                break
            except (ValueError, AttributeError):
                continue

    col = Collection(
        brand_id=brand.id,
        season=season,
        year=year,
        show_date=show_date,
        review_text=record.get("review_text", "")[:5000],
        source_url=record.get("url", ""),
    )
    db.add(col)
    db.flush()
    return col, brand


# ---------------------------------------------------------------------------
# Sentiment pass
# ---------------------------------------------------------------------------

def run_sentiment(db: Session):
    """Score every Article against each brand it tags."""
    logger.info("=== Sentiment pass ===")
    articles = db.query(Article).all()
    total = 0

    for article in articles:
        text = article.body or article.title or ""
        if not text.strip():
            continue

        result = sent_mod.analyze(text)

        for slug in (article.brand_tags or []):
            brand = _get_brand(db, slug)
            if not brand:
                continue

            already = (
                db.query(SentimentScore)
                .filter(
                    SentimentScore.article_id == article.id,
                    SentimentScore.brand_id == brand.id,
                )
                .first()
            )
            if already:
                continue

            ss = SentimentScore(
                article_id=article.id,
                brand_id=brand.id,
                score=result["score"],
                label=result["label"],
                confidence=result["confidence"],
            )
            db.add(ss)
            total += 1

    db.commit()
    logger.info(f"Sentiment pass done — {total} scores written")


# ---------------------------------------------------------------------------
# Theme pass
# ---------------------------------------------------------------------------

def run_themes(db: Session):
    """Extract themes from all text and write TrendTheme + ThemeScore rows."""
    logger.info("=== Theme pass ===")

    docs: list[str] = []
    doc_brands: list[list[str]] = []

    # Include articles
    for article in db.query(Article).all():
        text = article.body or article.title or ""
        if text.strip():
            docs.append(text)
            doc_brands.append(article.brand_tags or [])

    # Include Vogue collection reviews (richer text)
    for col in db.query(Collection).all():
        text = col.review_text or ""
        if text.strip():
            brand_slug = col.brand.slug if col.brand else None
            docs.append(text)
            doc_brands.append([brand_slug] if brand_slug else [])

    if not docs:
        logger.warning("No documents for theme extraction — skipping")
        return

    themes = theme_mod.extract_themes(docs, doc_brands)

    # Clear old theme data so re-runs stay idempotent
    db.query(ThemeScore).delete()
    db.query(TrendTheme).delete()
    db.commit()

    for theme_data in themes:
        trend = TrendTheme(
            label=theme_data["label"],
            description=theme_data["description"],
            trajectory=theme_data["trajectory"],
            season=theme_data.get("season"),
        )
        db.add(trend)
        db.flush()

        for slug, score in theme_data["brand_scores"].items():
            brand = _get_brand(db, slug)
            if not brand:
                continue
            ts = ThemeScore(
                theme_id=trend.id,
                brand_id=brand.id,
                score=score,
            )
            db.add(ts)

    db.commit()
    logger.info(f"Theme pass done — {len(themes)} themes written")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def ingest_raw(db: Session):
    """Load all JSONL files and write Article / Collection rows."""
    logger.info("=== Ingestion pass ===")

    # --- Vogue collections ---
    for jsonl_file in sorted(VOGUE_DIR.glob("*.jsonl")):
        for record in _load_jsonl(jsonl_file):
            if record.get("status") != "ok":
                continue
            _upsert_collection(db, record)
    db.commit()
    logger.info("Vogue collections ingested")

    # --- BoF articles ---
    for jsonl_file in sorted(BOF_DIR.glob("*.jsonl")):
        for record in _load_jsonl(jsonl_file):
            if record.get("status") != "ok":
                continue
            _upsert_article(db, record)
    db.commit()
    logger.info("BoF articles ingested")

    # --- Reddit posts ---
    for jsonl_file in sorted(REDDIT_DIR.glob("*.jsonl")):
        for record in _load_jsonl(jsonl_file):
            if record.get("status") != "ok":
                continue
            # Reddit records have a body field and brand (single slug)
            record.setdefault("source", "reddit")
            record.setdefault("body_text", record.get("body", ""))
            _upsert_article(db, record)
    db.commit()
    logger.info("Reddit posts ingested")


def main():
    db = SessionLocal()
    try:
        seed_brands(db)
        ingest_raw(db)
        run_sentiment(db)
        run_themes(db)
        logger.info("=== Pipeline complete ===")
        print("Pipeline complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
