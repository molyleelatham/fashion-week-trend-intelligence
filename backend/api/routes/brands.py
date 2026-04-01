"""
GET /api/brands          — all brands with aggregated sentiment
GET /api/brands/{slug}   — single brand with collections, sentiment history, themes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.api.models import Brand, Collection, SentimentScore, ThemeScore, TrendTheme

router = APIRouter()


def _sentiment_summary(db: Session, brand_id: int) -> dict:
    rows = (
        db.query(SentimentScore.label, func.count(SentimentScore.id), func.avg(SentimentScore.score))
        .filter(SentimentScore.brand_id == brand_id)
        .group_by(SentimentScore.label)
        .all()
    )
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    total_score = 0.0
    total_n = 0
    for label, n, avg in rows:
        counts[label] = n
        total_score += (avg or 0.0) * n
        total_n += n

    avg_score = round(total_score / total_n, 4) if total_n else 0.0
    return {
        "avg_score": avg_score,
        "total_mentions": total_n,
        "positive_count": counts["positive"],
        "neutral_count": counts["neutral"],
        "negative_count": counts["negative"],
    }


@router.get("")
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(Brand).order_by(Brand.name).all()
    result = []
    for b in brands:
        sentiment = _sentiment_summary(db, b.id)
        result.append({
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "country": b.country,
            "city": b.city,
            "founded_year": b.founded_year,
            "tier": b.tier,
            "sentiment": sentiment,
        })
    return result


@router.get("/{slug}")
def get_brand(slug: str, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.slug == slug).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")

    sentiment = _sentiment_summary(db, brand.id)

    # Sentiment over time (one point per article)
    scores = (
        db.query(SentimentScore)
        .filter(SentimentScore.brand_id == brand.id)
        .join(SentimentScore.article)
        .order_by(SentimentScore.article.property.mapper.class_.published_at)
        .all()
    )
    sentiment_history = [
        {
            "score": s.score,
            "label": s.label,
            "confidence": s.confidence,
            "published_at": s.article.published_at.isoformat() if s.article.published_at else None,
            "source": s.article.source,
            "title": s.article.title,
        }
        for s in scores
    ]

    # Collections
    collections = (
        db.query(Collection)
        .filter(Collection.brand_id == brand.id)
        .order_by(Collection.season)
        .all()
    )
    collections_out = [
        {
            "season": c.season,
            "year": c.year,
            "show_date": c.show_date.isoformat() if c.show_date else None,
            "review_text": c.review_text,
            "source_url": c.source_url,
        }
        for c in collections
    ]

    # Theme associations
    theme_scores = (
        db.query(ThemeScore, TrendTheme)
        .join(TrendTheme, ThemeScore.theme_id == TrendTheme.id)
        .filter(ThemeScore.brand_id == brand.id)
        .all()
    )
    themes_out = [
        {
            "label": t.label,
            "description": t.description,
            "trajectory": t.trajectory,
            "score": ts.score,
        }
        for ts, t in theme_scores
    ]

    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "country": brand.country,
        "city": brand.city,
        "founded_year": brand.founded_year,
        "tier": brand.tier,
        "sentiment": sentiment,
        "sentiment_history": sentiment_history,
        "collections": collections_out,
        "themes": themes_out,
    }
