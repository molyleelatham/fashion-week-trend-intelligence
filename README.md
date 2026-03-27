# Fashion Intelligence Platform

A data science dashboard that tracks high fashion runway shows, editorial sentiment, and trend forecasting across the 2026 fashion weeks (NYFW, LFW, MFW, PFW). The platform scrapes editorial coverage from Vogue Runway, Business of Fashion, and Reddit; runs NLP sentiment analysis and BERTopic theme extraction; exposes a FastAPI backend; and surfaces insights through an interactive Next.js dashboard with an AI chat interface powered by Claude.

---

## Brand Scope (v1 — 2026 seasons only)

| Region   | Houses |
|----------|--------|
| French   | Chanel, Dior, Louis Vuitton, Givenchy, Saint Laurent (YSL) |
| Italian  | Prada, Gucci, Bottega Veneta, Versace, Miu Miu |
| Belgian  | Maison Margiela, Rick Owens |
| British  | Burberry, Alexander McQueen |
| American | Alexander Wang |

**Seasons:** SS2026 and AW2026 only

---

## Quickstart

```bash
git clone https://github.com/molyleelatham/fashionintelligence.git
cd fashionintelligence
cp .env.example .env
# Fill in credentials in .env
docker-compose up
```

- Backend API: http://localhost:8000
- Frontend dashboard: http://localhost:3000
- API docs: http://localhost:8000/docs

---

## Checkpoints

### Checkpoint 1 — Repo scaffold + environment
Folder structure, `.env.example`, `requirements.txt`, `docker-compose.yml`, `.gitignore`, `README.md`.

### Checkpoint 2 — Database schema + seed data
_(coming soon)_

### Checkpoint 3 — Scrapers
_(coming soon)_

### Checkpoint 4 — NLP pipeline
_(coming soon)_

### Checkpoint 5 — FastAPI backend
_(coming soon)_

### Checkpoint 6 — Next.js dashboard
_(coming soon)_

---

## Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **NLP:** HuggingFace Transformers, BERTopic, sentence-transformers
- **Frontend:** Next.js 14 (app router), Recharts, Tailwind CSS
- **Infra:** Docker + docker-compose
