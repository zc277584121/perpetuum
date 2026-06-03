#!/usr/bin/env python3
"""
style_score.py — frozen oracle for style-distill perpetuum task.

This file is part of the contract: it is the EVALUATOR and should not be
modified during a run. Modifying it invalidates score comparisons across
cycles.

USAGE:
  python style_score.py <target_corpus_dir> <draft_file>

OUTPUT:
  a single float on stdout (higher = closer to target)

PLACEHOLDER IMPLEMENTATION:
  This uses a simple cosine-similarity-of-tfidf approach as a starting
  point. Replace with a more sophisticated metric for production use:
  - sentence-embedding cosine (sbert)
  - style classifier probability (fine-tune a small model)
  - composite (similarity + LLM judge)

WARNING:
  Beware reward hacking. A score function that the agent can game without
  actually matching style is worse than no score function. Validate
  manually every 10 cycles or so.
"""

import sys
import re
from pathlib import Path
from collections import Counter

# Improvement threshold. Score deltas smaller than this are noise.
EPSILON = 0.005


def tokenize(text: str) -> list[str]:
    text = text.lower()
    return re.findall(r"[a-zA-Z一-鿿]+", text)


def tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts = Counter(tokens)
    total = sum(counts.values())
    return {t: c / total for t, c in counts.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    num = sum(a[k] * b[k] for k in keys)
    da = sum(v * v for v in a.values()) ** 0.5
    db = sum(v * v for v in b.values()) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def style_features(text: str) -> dict[str, float]:
    """
    Composite stylometric features beyond raw tf.
    """
    tokens = tokenize(text)
    sents = re.split(r"[.!?。！？]+", text)
    sents = [s.strip() for s in sents if s.strip()]
    sent_lens = [len(tokenize(s)) for s in sents] or [0]
    return {
        "_avg_sent_len": sum(sent_lens) / max(1, len(sent_lens)),
        "_sent_count": len(sents),
        "_token_count": len(tokens),
        "_long_word_ratio": (
            sum(1 for t in tokens if len(t) >= 8) / max(1, len(tokens))
        ),
        "_punct_density": (
            sum(text.count(p) for p in ",;:—()") / max(1, len(text))
        ),
    }


def score(target_dir: Path, draft_path: Path) -> float:
    """
    Composite score: tfidf cosine + stylometric L1 closeness.
    Higher = closer to target. Range roughly 0..1.
    """
    target_texts = [p.read_text() for p in target_dir.glob("*.md")]
    target_texts += [p.read_text() for p in target_dir.glob("*.txt")]
    if not target_texts:
        raise SystemExit(f"no .md or .txt files in {target_dir}")

    target_blob = "\n\n".join(target_texts)
    target_tf = tf(tokenize(target_blob))
    target_style = style_features(target_blob)

    draft_text = draft_path.read_text()
    draft_tf = tf(tokenize(draft_text))
    draft_style = style_features(draft_text)

    tf_sim = cosine(target_tf, draft_tf)

    # Stylometric L1 distance, normalized into similarity [0,1]
    style_dist = 0.0
    for k, v in target_style.items():
        dv = draft_style.get(k, 0)
        if abs(v) + abs(dv) > 0:
            style_dist += abs(v - dv) / (abs(v) + abs(dv) + 1e-9)
    style_dist /= max(1, len(target_style))
    style_sim = 1.0 - min(1.0, style_dist)

    # Weighted composite
    return 0.6 * tf_sim + 0.4 * style_sim


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python style_score.py <target_corpus_dir> <draft_file>")
    target_dir = Path(sys.argv[1])
    draft_path = Path(sys.argv[2])
    print(f"{score(target_dir, draft_path):.6f}")
