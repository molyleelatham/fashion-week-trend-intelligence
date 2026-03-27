import json
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, Date,
    ForeignKey, TypeDecorator
)
from sqlalchemy.orm import relationship
from backend.db.database import Base


class JSONList(TypeDecorator):
    """Stores a Python list as a JSON string in SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        return json.loads(value)


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    country = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    founded_year = Column(Integer)
    tier = Column(String(50))

    collections = relationship("Collection", back_populates="brand")
    sentiment_scores = relationship("SentimentScore", back_populates="brand")
    theme_scores = relationship("ThemeScore", back_populates="brand")


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    season = Column(String(10), nullable=False)   # SS2026 / AW2026
    year = Column(Integer, nullable=False)
    show_date = Column(Date)
    review_text = Column(Text)
    source_url = Column(String(1000))

    brand = relationship("Brand", back_populates="collections")


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    title = Column(String(500))
    published_at = Column(DateTime)
    body = Column(Text)
    brand_tags = Column(JSONList)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    sentiment_scores = relationship("SentimentScore", back_populates="article")


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    score = Column(Float, nullable=False)   # -1.0 to +1.0
    label = Column(String(20), nullable=False)  # positive / neutral / negative
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    article = relationship("Article", back_populates="sentiment_scores")
    brand = relationship("Brand", back_populates="sentiment_scores")


class TrendTheme(Base):
    __tablename__ = "trend_themes"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(200), nullable=False)
    description = Column(Text)
    trajectory = Column(String(20), nullable=False, default="peaking")  # rising/peaking/declining
    season = Column(String(10))
    created_at = Column(DateTime, default=datetime.utcnow)

    theme_scores = relationship("ThemeScore", back_populates="theme")


class ThemeScore(Base):
    __tablename__ = "theme_scores"

    id = Column(Integer, primary_key=True, index=True)
    theme_id = Column(Integer, ForeignKey("trend_themes.id"), nullable=False)
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=False)
    score = Column(Float, nullable=False)

    theme = relationship("TrendTheme", back_populates="theme_scores")
    brand = relationship("Brand", back_populates="theme_scores")
