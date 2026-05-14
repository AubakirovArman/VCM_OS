from fastapi import FastAPI

from vcm_os.app.lifespan import lifespan
from vcm_os.app.routers import (
    admin,
    codebase,
    context,
    dashboard,
    events,
    gateway,
    memory,
    project,
    query,
    session,
    summaries,
    verify,
)

app = FastAPI(title="VCM-OS", version="0.5.0", lifespan=lifespan)

app.include_router(events.router)
app.include_router(memory.router)
app.include_router(context.router)
app.include_router(session.router)
app.include_router(project.router)
app.include_router(query.router)
app.include_router(codebase.router)
app.include_router(verify.router)
app.include_router(summaries.router)
app.include_router(admin.router)
app.include_router(dashboard.router)
app.include_router(gateway.router)
