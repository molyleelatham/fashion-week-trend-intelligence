"""
Seeds all 15 brands. Called automatically on startup if DB is empty.
Can also be run standalone: python -m backend.db.seed
"""
from backend.db.database import engine, SessionLocal, Base
from backend.api.models import Brand

BRANDS = [
    {"name": "Chanel",            "slug": "chanel",            "country": "France",  "city": "Paris",     "founded_year": 1910, "tier": "haute-couture"},
    {"name": "Dior",              "slug": "dior",              "country": "France",  "city": "Paris",     "founded_year": 1946, "tier": "haute-couture"},
    {"name": "Louis Vuitton",     "slug": "louis-vuitton",     "country": "France",  "city": "Paris",     "founded_year": 1854, "tier": "luxury"},
    {"name": "Givenchy",          "slug": "givenchy",          "country": "France",  "city": "Paris",     "founded_year": 1952, "tier": "luxury"},
    {"name": "Saint Laurent",     "slug": "saint-laurent",     "country": "France",  "city": "Paris",     "founded_year": 1961, "tier": "luxury"},
    {"name": "Prada",             "slug": "prada",             "country": "Italy",   "city": "Milan",     "founded_year": 1913, "tier": "luxury"},
    {"name": "Gucci",             "slug": "gucci",             "country": "Italy",   "city": "Florence",  "founded_year": 1921, "tier": "luxury"},
    {"name": "Bottega Veneta",    "slug": "bottega-veneta",    "country": "Italy",   "city": "Milan",     "founded_year": 1966, "tier": "luxury"},
    {"name": "Versace",           "slug": "versace",           "country": "Italy",   "city": "Milan",     "founded_year": 1978, "tier": "luxury"},
    {"name": "Miu Miu",           "slug": "miu-miu",           "country": "Italy",   "city": "Milan",     "founded_year": 1993, "tier": "luxury"},
    {"name": "Maison Margiela",   "slug": "maison-margiela",   "country": "Belgium", "city": "Paris",     "founded_year": 1988, "tier": "avant-garde"},
    {"name": "Rick Owens",        "slug": "rick-owens",        "country": "USA",     "city": "Paris",     "founded_year": 1994, "tier": "avant-garde"},
    {"name": "Burberry",          "slug": "burberry",          "country": "UK",      "city": "London",    "founded_year": 1856, "tier": "luxury"},
    {"name": "Alexander McQueen", "slug": "alexander-mcqueen", "country": "UK",      "city": "London",    "founded_year": 1992, "tier": "luxury"},
    {"name": "Alexander Wang",    "slug": "alexander-wang",    "country": "USA",     "city": "New York",  "founded_year": 2005, "tier": "luxury"},
]


def init_db():
    Base.metadata.create_all(bind=engine)


def seed_brands(db):
    if db.query(Brand).count() > 0:
        return
    for b in BRANDS:
        db.add(Brand(**b))
    db.commit()
    print(f"Seeded {len(BRANDS)} brands.")


def seed():
    init_db()
    db = SessionLocal()
    try:
        seed_brands(db)
        rows = db.query(Brand).order_by(Brand.id).all()
        print(f"\n{'ID':<4} {'Name':<22} {'Country':<10} {'City':<12} {'Founded':<9} Tier")
        print("-" * 70)
        for r in rows:
            print(f"{r.id:<4} {r.name:<22} {r.country:<10} {r.city:<12} {r.founded_year:<9} {r.tier}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
