from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.app.models import QueryRewriteIn

router = APIRouter()


@router.post("/query/rewrite")
async def query_rewrite(body: QueryRewriteIn):
    queries = await state.rewriter.expand(body.query, body.task_type)
    return {"original": body.query, "rewritten": queries}
