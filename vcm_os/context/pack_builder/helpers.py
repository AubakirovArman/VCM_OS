from vcm_os.schemas import MemoryObject


def raw_hash(m: MemoryObject) -> str:
    rt = (m.raw_text or "").strip().lower()
    return " ".join(rt.split())[:120]


def sort_key(m: MemoryObject):
    return m.importance_score * 0.6 + m.recency_score * 0.4
