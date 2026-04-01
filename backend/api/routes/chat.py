"""
POST /api/chat — AI chat powered by OpenAI gpt-4o.
The system prompt is seeded with live brand sentiment data so the model
can answer questions grounded in the platform's actual data.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from openai import OpenAI
from dotenv import load_dotenv

from backend.db.database import get_db
from backend.api.models import Brand, SentimentScore, TrendTheme

load_dotenv()

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []   # [{"role": "user"|"assistant", "content": str}]


def _build_system_prompt(db: Session) -> str:
    """Snapshot current DB state into the system prompt."""
    brands = db.query(Brand).order_by(Brand.name).all()
    lines = ["You are a fashion intelligence analyst. Answer questions about luxury fashion trends, brand sentiment, and runway collections using the data below.\n"]
    lines.append("## Brand Sentiment Summary (Jan 2026–present)\n")

    for b in brands:
        row = (
            db.query(func.avg(SentimentScore.score), func.count(SentimentScore.id))
            .filter(SentimentScore.brand_id == b.id)
            .first()
        )
        avg_score, count = row
        if count and count > 0:
            avg_str = f"{avg_score:+.2f}"
            lines.append(f"- {b.name}: avg sentiment {avg_str} ({count} mentions)")
        else:
            lines.append(f"- {b.name}: no data yet")

    themes = db.query(TrendTheme).all()
    if themes:
        lines.append("\n## Current Trend Themes\n")
        for t in themes:
            lines.append(f"- {t.label} ({t.trajectory}): {t.description}")

    lines.append("\nAnswer concisely and professionally. If asked about data not in the summary, say so honestly.")
    return "\n".join(lines)


@router.post("")
def chat(body: ChatRequest, db: Session = Depends(get_db)):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    client = OpenAI(api_key=api_key)
    system_prompt = _build_system_prompt(db)

    messages = [{"role": "system", "content": system_prompt}]
    for h in body.history[-10:]:   # cap history to last 10 turns
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": body.message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=600,
            temperature=0.4,
        )
        reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {e}")

    return {"reply": reply}
