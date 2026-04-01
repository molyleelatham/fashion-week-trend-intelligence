"""
GET /api/trends   — all trend themes with brand associations
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.api.models import TrendTheme, ThemeScore, Brand

router = APIRouter()


@router.get("")
def list_trends(db: Session = Depends(get_db)):
    themes = db.query(TrendTheme).order_by(TrendTheme.id).all()
    result = []
    for theme in themes:
        scores = (
            db.query(ThemeScore, Brand)
            .join(Brand, ThemeScore.brand_id == Brand.id)
            .filter(ThemeScore.theme_id == theme.id)
            .order_by(ThemeScore.score.desc())
            .all()
        )
        brands = [
            {"slug": b.slug, "name": b.name, "score": ts.score}
            for ts, b in scores
        ]
        result.append({
            "id": theme.id,
            "label": theme.label,
            "description": theme.description,
            "trajectory": theme.trajectory,
            "season": theme.season,
            "brands": brands,
        })
    return result
