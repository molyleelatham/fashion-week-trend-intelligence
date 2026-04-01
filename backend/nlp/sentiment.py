"""
Sentiment analysis using cardiffnlp/twitter-roberta-base-sentiment-latest.
Scores are mapped to a -1.0 to +1.0 float:
  negative → negative score, neutral → 0.0, positive → positive score.
"""
import re
from transformers import pipeline, AutoTokenizer
from loguru import logger

MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"

_pipe = None
_tokenizer = None


def _get_pipeline():
    global _pipe, _tokenizer
    if _pipe is None:
        logger.info(f"Loading sentiment model: {MODEL}")
        _tokenizer = AutoTokenizer.from_pretrained(MODEL)
        _pipe = pipeline(
            "sentiment-analysis",
            model=MODEL,
            tokenizer=_tokenizer,
            top_k=None,          # return all label scores
            truncation=True,
            max_length=512,
        )
        logger.info("Sentiment model loaded.")
    return _pipe


def _clean(text: str) -> str:
    """Basic text cleanup before inference."""
    text = re.sub(r"http\S+", "", text)          # strip URLs
    text = re.sub(r"@\w+", "@user", text)        # anonymise mentions
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1000]                            # model cap


def _label_to_score(label: str, confidence: float) -> float:
    """Convert label + confidence to a signed float in [-1, +1]."""
    label = label.lower()
    if "positive" in label:
        return round(confidence, 4)
    if "negative" in label:
        return round(-confidence, 4)
    return 0.0   # neutral


def analyze(text: str) -> dict:
    """
    Run sentiment analysis on text.

    Returns:
        {
            "label": "positive" | "neutral" | "negative",
            "score": float,        # -1.0 to +1.0
            "confidence": float,   # raw probability of winning label
        }
    """
    if not text or not text.strip():
        return {"label": "neutral", "score": 0.0, "confidence": 0.0}

    pipe = _get_pipeline()
    cleaned = _clean(text)
    results = pipe(cleaned)[0]   # list of {label, score} dicts

    # Pick the label with highest score
    best = max(results, key=lambda x: x["score"])
    label = best["label"].lower()
    # Normalise label to positive/neutral/negative
    if "positive" in label:
        norm_label = "positive"
    elif "negative" in label:
        norm_label = "negative"
    else:
        norm_label = "neutral"

    confidence = round(best["score"], 4)
    signed_score = _label_to_score(norm_label, confidence)

    return {
        "label": norm_label,
        "score": signed_score,
        "confidence": confidence,
    }
