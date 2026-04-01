"""
FastAPI application entry point.
Run: uvicorn backend.api.main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import engine
from backend.db.seed import seed_brands, init_db
from backend.db.database import SessionLocal
from backend.api.routes import brands, trends, feed, chat

app = FastAPI(
    title="Fashion Intelligence API",
    description="Luxury fashion sentiment and trend analysis platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    db = SessionLocal()
    try:
        seed_brands(db)
    finally:
        db.close()


app.include_router(brands.router, prefix="/api/brands", tags=["brands"])
app.include_router(trends.router, prefix="/api/trends", tags=["trends"])
app.include_router(feed.router,   prefix="/api/feed",   tags=["feed"])
app.include_router(chat.router,   prefix="/api/chat",   tags=["chat"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
