# Fashion Intelligence Platform

A full-stack data science dashboard tracking high fashion runway shows, editorial sentiment, and trend forecasting across the 2026 fashion weeks (NYFW, LFW, MFW, PFW). Scrapes Vogue Runway, Business of Fashion, and Reddit; runs NLP sentiment analysis and BERTopic theme extraction; and surfaces insights through a Next.js dashboard with an AI chat interface powered by OpenAI.

## Stack

| Layer | Tech |
|-------|------|
| Backend API | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| Scrapers | httpx, BeautifulSoup, PRAW |
| NLP | HuggingFace Transformers, BERTopic, sentence-transformers |
| Frontend | Next.js 14 (App Router), Tailwind CSS, Recharts |
| AI Chat | OpenAI API (gpt-4o) |

## Brand Scope (SS2026 & AW2026)

| Region | Houses |
|--------|--------|
| French | Chanel, Dior, Louis Vuitton, Givenchy, Saint Laurent |
| Italian | Prada, Gucci, Bottega Veneta, Versace, Miu Miu |
| Belgian | Maison Margiela, Rick Owens |
| British | Burberry, Alexander McQueen |
| American | Alexander Wang |

## Quickstart

```bash
git clone https://github.com/molyleelatham/fashionintelligence.git
cd fashionintelligence

# Backend
cp .env.example .env        # fill in your API keys
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

- API: http://localhost:8000
- Dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs

## Checkpoints

### Checkpoint 1 — Scaffold ✅
Folder structure, `.env.example`, `requirements.txt`, `.gitignore`, `README.md`

### Checkpoint 2 — Database + seed data
SQLite schema (Brand, Collection, Article, SentimentScore, TrendTheme, ThemeScore) + all 15 brands seeded

### Checkpoint 3 — Scrapers
Vogue Runway, Business of Fashion, Reddit scrapers with rate limiting and retry logic

### Checkpoint 4 — NLP pipeline
Sentiment analysis (cardiffnlp/twitter-roberta-base-sentiment-latest) + BERTopic theme extraction

### Checkpoint 5 — FastAPI backend
All routes: /api/brands, /api/trends, /api/feed, /api/chat (GPT-4o-powered)

### Checkpoint 6 — Next.js dashboard
Overview, Brands, Trends, Feed, AI Chat pages with dark editorial design
