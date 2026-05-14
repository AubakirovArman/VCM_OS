import json
import pickle
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi

from vcm_os.config import DATA_DIR


def tokenize(text: str) -> List[str]:
    # Simple tokenization: lowercase, split on non-alphanumeric, filter short
    tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return [t for t in tokens if len(t) > 1]


class SparseIndex:
    def __init__(self):
        self._corpus: Dict[str, str] = {}
        self._tokenized_corpus: List[List[str]] = []
        self._id_to_idx: Dict[str, int] = {}
        self._bm25: Optional[BM25Okapi] = None
        self._dirty = False
        self._save_path = Path(DATA_DIR) / "sparse_index.pkl"
        self._load()

    def add(self, memory_id: str, text: str) -> None:
        if memory_id in self._corpus:
            # Update existing
            idx = self._id_to_idx[memory_id]
            self._corpus[memory_id] = text
            self._tokenized_corpus[idx] = tokenize(text)
        else:
            idx = len(self._tokenized_corpus)
            self._id_to_idx[memory_id] = idx
            self._corpus[memory_id] = text
            self._tokenized_corpus.append(tokenize(text))
        self._bm25 = BM25Okapi(self._tokenized_corpus)
        self._dirty = True

    def add_batch(self, items: List[Tuple[str, str]]) -> None:
        for mid, text in items:
            if mid in self._corpus:
                idx = self._id_to_idx[mid]
                self._corpus[mid] = text
                self._tokenized_corpus[idx] = tokenize(text)
            else:
                idx = len(self._tokenized_corpus)
                self._id_to_idx[mid] = idx
                self._corpus[mid] = text
                self._tokenized_corpus.append(tokenize(text))
        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
        self._dirty = True

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self._bm25 is None or not self._tokenized_corpus:
            return []
        tokenized_query = tokenize(query)
        if not tokenized_query:
            return []
        scores = self._bm25.get_scores(tokenized_query)
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        # Map back to ids
        idx_to_id = {v: k for k, v in self._id_to_idx.items()}
        return [(idx_to_id[i], float(scores[i])) for i in top_idx if i in idx_to_id]

    def remove(self, memory_id: str) -> None:
        if memory_id not in self._corpus:
            return
        idx = self._id_to_idx[memory_id]
        del self._corpus[memory_id]
        self._tokenized_corpus.pop(idx)
        # Rebuild mappings
        self._id_to_idx = {}
        new_corpus = {}
        new_tokenized = []
        for mid, text in self._corpus.items():
            new_idx = len(new_tokenized)
            self._id_to_idx[mid] = new_idx
            new_corpus[mid] = text
            new_tokenized.append(tokenize(text))
        self._corpus = new_corpus
        self._tokenized_corpus = new_tokenized
        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus)
        else:
            self._bm25 = None
        self._dirty = True

    def get_stats(self) -> Dict[str, int]:
        return {
            "entries": len(self._corpus),
            "avg_tokens": sum(len(t) for t in self._tokenized_corpus) // max(len(self._tokenized_corpus), 1),
        }

    def save(self) -> None:
        if not self._dirty:
            return
        data = {
            "corpus": self._corpus,
            "tokenized_corpus": self._tokenized_corpus,
            "id_to_idx": self._id_to_idx,
        }
        with open(self._save_path, "wb") as f:
            pickle.dump(data, f)
        self._dirty = False

    def _load(self) -> None:
        if not self._save_path.exists():
            return
        try:
            with open(self._save_path, "rb") as f:
                data = pickle.load(f)
            self._corpus = data.get("corpus", {})
            self._tokenized_corpus = data.get("tokenized_corpus", [])
            self._id_to_idx = data.get("id_to_idx", {})
            if self._tokenized_corpus:
                self._bm25 = BM25Okapi(self._tokenized_corpus)
        except Exception:
            pass
