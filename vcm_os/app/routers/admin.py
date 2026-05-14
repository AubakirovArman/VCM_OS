from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.app.models import RetentionIn
from vcm_os.health.dashboard import MemoryHealthDashboard

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}


@router.get("/health/dashboard")
async def health_dashboard():
    dashboard = MemoryHealthDashboard(state.store)
    return dashboard.snapshot()


@router.get("/metrics")
async def metrics():
    stats = state.store.get_stats()
    return {
        "store": stats,
        "vector_index": state.vector_index.get_stats() if hasattr(state.vector_index, "get_stats") else {},
        "sparse_index": state.sparse_index.get_stats() if hasattr(state.sparse_index, "get_stats") else {},
    }


@router.post("/admin/retention")
async def run_retention(body: RetentionIn):
    state.store.apply_retention(body.max_age_days, body.max_memories_per_project)
    state.vector_index.save()
    state.sparse_index.save()
    return {"status": "ok", "applied": True}
