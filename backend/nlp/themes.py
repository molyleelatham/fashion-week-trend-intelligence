"""
Theme extraction using BERTopic + sentence-transformers/all-MiniLM-L6-v2.
Produces a list of named themes and maps each brand to the themes it appears in.
"""
from __future__ import annotations

import re
from collections import defaultdict

from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from loguru import logger

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MIN_TOPIC_SIZE = 2   # lower bound so small corpora still produce topics
MIN_DOCS = 4         # need at least this many docs to run BERTopic


def _clean(text: str) -> str:
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_themes(
    docs: list[str],
    doc_brands: list[list[str]],
) -> list[dict]:
    """
    Run BERTopic over docs and return a list of theme dicts.

    Args:
        docs:       List of text strings (one per article/collection).
        doc_brands: Parallel list; each entry is the list of brand slugs
                    associated with that doc.

    Returns:
        [
            {
                "label": str,            # keyword-based topic label
                "description": str,      # top keywords joined
                "trajectory": str,       # always "peaking" — updated downstream
                "season": str | None,
                "brand_scores": {slug: float, ...},
            },
            ...
        ]
    """
    cleaned = [_clean(d) for d in docs]
    non_empty = [(d, b) for d, b in zip(cleaned, doc_brands) if d]
    if len(non_empty) < MIN_DOCS:
        logger.warning(f"Only {len(non_empty)} docs — skipping BERTopic run")
        return []

    texts, brands_per_doc = zip(*non_empty)
    texts = list(texts)
    brands_per_doc = list(brands_per_doc)

    logger.info(f"Fitting BERTopic on {len(texts)} docs...")
    embedding_model = SentenceTransformer(EMBED_MODEL)
    topic_model = BERTopic(
        embedding_model=embedding_model,
        min_topic_size=MIN_TOPIC_SIZE,
        verbose=False,
    )
    topics, _ = topic_model.fit_transform(texts)

    topic_info = topic_model.get_topic_info()

    theme_list = []
    for _, row in topic_info.iterrows():
        tid = row["Topic"]
        if tid == -1:
            continue   # BERTopic outlier cluster

        topic_words = topic_model.get_topic(tid)
        if not topic_words:
            continue

        keywords = [w for w, _ in topic_words[:8]]
        label = " / ".join(keywords[:3])
        description = ", ".join(keywords)

        # Collect brand → doc-count for this topic
        brand_counts: dict[str, int] = defaultdict(int)
        total = 0
        for doc_idx, t in enumerate(topics):
            if t == tid:
                for slug in brands_per_doc[doc_idx]:
                    brand_counts[slug] += 1
                total += 1

        # Normalise to [0, 1]
        brand_scores = {
            slug: round(count / total, 4)
            for slug, count in brand_counts.items()
        }

        theme_list.append({
            "label": label,
            "description": description,
            "trajectory": "peaking",
            "season": None,
            "brand_scores": brand_scores,
        })

    logger.info(f"Extracted {len(theme_list)} themes")
    return theme_list
