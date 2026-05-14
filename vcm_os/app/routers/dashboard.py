"""Dashboard API endpoints."""
from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.dashboard.metrics import DashboardMetrics

router = APIRouter()


@router.get("/dashboard")
async def dashboard_snapshot():
    metrics = DashboardMetrics(state.store, state.vector_index, state.sparse_index)
    return metrics.snapshot()


@router.get("/dashboard/health")
async def dashboard_health():
    from vcm_os.health.dashboard import MemoryHealthDashboard
    dash = MemoryHealthDashboard(state.store)
    return dash.snapshot()


@router.get("/dashboard/latency")
async def dashboard_latency():
    metrics = DashboardMetrics(state.store, state.vector_index, state.sparse_index)
    return metrics._latency_metrics()


@router.get("/dashboard/retrieval")
async def dashboard_retrieval():
    metrics = DashboardMetrics(state.store, state.vector_index, state.sparse_index)
    return metrics._retrieval_metrics()


@router.get("/dashboard/errors")
async def dashboard_errors():
    metrics = DashboardMetrics(state.store, state.vector_index, state.sparse_index)
    return metrics._error_metrics()
