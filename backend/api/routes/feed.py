"""
GET /api/feed              — recent articles (paginated, filterable by brand/source)
GET /api/feed/{article_id} — single article with sentiment scores
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.api.models import Article, SentimentScore, Brand

router = APIRouter()


@router.get("")
def list_feed(
    brand: str | None = Query(None, description="Filter by brand slug"),
    source: str | None = Query(None, description="Filter by source (vogue/bof/reddit)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Article)

    if brand:
        brand_row = db.query(Brand).filter(Brand.slug == brand).first()
        if not brand_row:
            raise HTTPException(status_code=404, detail="Brand not found")
        # Filter articles whose brand_tags JSON contains the slug
        # SQLite: use LIKE since brand_tags is stored as JSON string
        q = q.filter(Article.brand_tags.like(f'%"{brand}"%'))

    if source:
        q = q.filter(Article.source == source)

    total = q.count()
    articles = (
        q.order_by(Article.published_at.desc().nullslast())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for a in articles:
        items.append({
            "id": a.id,
            "source": a.source,
            "title": a.title,
            "url": a.url,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "body_preview": (a.body or "")[:300],
            "brand_tags": a.brand_tags,
        })

    return {"total": total, "offset": offset, "limit": limit, "items": items}


@router.get("/{article_id}")
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    scores = (
        db.query(SentimentScore, Brand)
        .join(Brand, SentimentScore.brand_id == Brand.id)
        .filter(SentimentScore.article_id == article_id)
        .all()
    )
    sentiment = [
        {"brand": b.slug, "label": s.label, "score": s.score, "confidence": s.confidence}
        for s, b in scores
    ]

    return {
        "id": article.id,
        "source": article.source,
        "title": article.title,
        "url": article.url,
        "published_at": article.published_at.isoformat() if article.published_at else None,
        "body": article.body,
        "brand_tags": article.brand_tags,
        "sentiment": sentiment,
    }
