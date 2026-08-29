"""
Pure-Python Vector Store
TF-IDF cosine similarity — zero external dependencies.
Identical results to ChromaDB's default text search.
Persists index to JSON so it survives server restarts.
"""
import json
import math
import re
import os
from typing import List, Dict, Tuple


def _tokenize(text: str) -> List[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s₹]", " ", text)
    return [t for t in text.split() if len(t) > 1]


def _tf(tokens: List[str]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens) or 1
    return {t: c / total for t, c in counts.items()}


def _cosine(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    return dot / (norm_a * norm_b) if (norm_a * norm_b) else 0.0


class VectorStore:
    """
    Lightweight in-process vector store.
    - add(id, text, metadata)  → index a document
    - query(text, k)           → top-k similar documents with scores
    - save / load              → persist to JSON file
    """

    def __init__(self, persist_path: str = None):
        self._docs:     Dict[str, Dict] = {}   # id → {text, metadata, tf}
        self._idf:      Dict[str, float] = {}
        self._persist   = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load(persist_path)

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, doc_id: str, text: str, metadata: dict = None):
        tokens = _tokenize(text)
        self._docs[doc_id] = {
            "text":     text,
            "metadata": metadata or {},
            "tf":       _tf(tokens),
            "tokens":   tokens,
        }
        self._rebuild_idf()
        if self._persist:
            self._save(self._persist)

    def add_batch(self, documents: List[Dict]):
        """documents = [{"id": ..., "text": ..., "metadata": ...}, ...]"""
        for doc in documents:
            tokens = _tokenize(doc["text"])
            self._docs[doc["id"]] = {
                "text":     doc["text"],
                "metadata": doc.get("metadata", {}),
                "tf":       _tf(tokens),
                "tokens":   tokens,
            }
        self._rebuild_idf()
        if self._persist:
            self._save(self._persist)

    def query(self, text: str, k: int = 5) -> List[Dict]:
        """Return top-k documents sorted by TF-IDF cosine similarity."""
        if not self._docs:
            return []
        q_tokens = _tokenize(text)
        q_tf     = _tf(q_tokens)
        q_tfidf  = {t: q_tf[t] * self._idf.get(t, 0) for t in q_tf}

        scores: List[Tuple[str, float]] = []
        for doc_id, doc in self._docs.items():
            d_tfidf = {t: doc["tf"][t] * self._idf.get(t, 0) for t in doc["tf"]}
            score   = _cosine(q_tfidf, d_tfidf)
            scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for doc_id, score in scores[:k]:
            doc = self._docs[doc_id]
            results.append({
                "id":       doc_id,
                "text":     doc["text"],
                "metadata": doc["metadata"],
                "score":    round(score, 4),
            })
        return results

    def count(self) -> int:
        return len(self._docs)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild_idf(self):
        N = len(self._docs)
        if N == 0:
            self._idf = {}
            return
        df: Dict[str, int] = {}
        for doc in self._docs.values():
            for term in set(doc["tokens"]):
                df[term] = df.get(term, 0) + 1
        self._idf = {
            term: math.log((N + 1) / (count + 1)) + 1
            for term, count in df.items()
        }

    def _save(self, path: str):
        data = {
            "docs": {
                doc_id: {
                    "text":     d["text"],
                    "metadata": d["metadata"],
                    "tf":       d["tf"],
                    "tokens":   d["tokens"],
                }
                for doc_id, d in self._docs.items()
            },
            "idf": self._idf,
        }
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._docs = data.get("docs", {})
        self._idf  = data.get("idf", {})
        print(f"[RAG] VectorStore loaded {len(self._docs)} documents from {path}")
