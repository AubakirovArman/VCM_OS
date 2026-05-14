import functools
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from vcm_os.config import DATA_DIR, EMBEDDING_BATCH_SIZE, EMBEDDING_DEVICE, EMBEDDING_MODEL


class VectorIndex:
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        self.model_name = model_name or EMBEDDING_MODEL
        self.device = device or EMBEDDING_DEVICE
        self._model: Optional[SentenceTransformer] = None
        self._vectors: Optional[np.ndarray] = None
        self._ids: List[str] = []
        self._index_map: Dict[str, int] = {}
        self._dirty = False
        self._save_path = Path(DATA_DIR) / "vector_index.pkl"
        self._load()

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.model.get_sentence_embedding_dimension()), dtype=np.float32)
        return self._cached_encode(tuple(texts))

    @functools.lru_cache(maxsize=4096)
    def _cached_encode(self, texts: tuple) -> np.ndarray:
        return self.model.encode(list(texts), batch_size=EMBEDDING_BATCH_SIZE, convert_to_numpy=True, show_progress_bar=False)

    def add(self, memory_id: str, text: str, vector: Optional[np.ndarray] = None) -> None:
        if vector is None:
            vector = self.encode([text])[0]
        if memory_id in self._index_map:
            idx = self._index_map[memory_id]
            self._vectors[idx] = vector
        else:
            self._index_map[memory_id] = len(self._ids)
            self._ids.append(memory_id)
            if self._vectors is None:
                self._vectors = vector.reshape(1, -1)
            else:
                self._vectors = np.vstack([self._vectors, vector])
        self._dirty = True

    def add_batch(self, items: List[Tuple[str, str]]) -> None:
        if not items:
            return
        ids, texts = zip(*items)
        vectors = self.encode(list(texts))
        for i, mid in enumerate(ids):
            if mid in self._index_map:
                self._vectors[self._index_map[mid]] = vectors[i]
            else:
                self._index_map[mid] = len(self._ids)
                self._ids.append(mid)
                if self._vectors is None:
                    self._vectors = vectors[i].reshape(1, -1)
                else:
                    self._vectors = np.vstack([self._vectors, vectors[i]])
        self._dirty = True

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        if self._vectors is None or len(self._ids) == 0:
            return []
        qvec = self.encode([query])[0]
        # cosine similarity
        norms = np.linalg.norm(self._vectors, axis=1)
        qnorm = np.linalg.norm(qvec)
        if qnorm == 0:
            return []
        sims = np.dot(self._vectors, qvec) / (norms * qnorm + 1e-10)
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [(self._ids[i], float(sims[i])) for i in top_idx]

    def search_by_vector(self, vector: np.ndarray, top_k: int = 10) -> List[Tuple[str, float]]:
        if self._vectors is None or len(self._ids) == 0:
            return []
        norms = np.linalg.norm(self._vectors, axis=1)
        qnorm = np.linalg.norm(vector)
        if qnorm == 0:
            return []
        sims = np.dot(self._vectors, vector) / (norms * qnorm + 1e-10)
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [(self._ids[i], float(sims[i])) for i in top_idx]

    def remove(self, memory_id: str) -> None:
        if memory_id not in self._index_map:
            return
        idx = self._index_map[memory_id]
        del self._ids[idx]
        self._vectors = np.delete(self._vectors, idx, axis=0)
        # Rebuild index map
        self._index_map = {mid: i for i, mid in enumerate(self._ids)}
        self._dirty = True

    def get_stats(self) -> Dict[str, int]:
        return {
            "entries": len(self._ids),
            "dimension": self._vectors.shape[1] if self._vectors is not None else 0,
        }

    def save(self) -> None:
        if not self._dirty:
            return
        data = {
            "ids": self._ids,
            "vectors": self._vectors,
            "index_map": self._index_map,
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
            self._ids = data.get("ids", [])
            self._vectors = data.get("vectors", None)
            self._index_map = data.get("index_map", {})
        except Exception:
            pass
