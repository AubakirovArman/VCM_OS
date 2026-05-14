from fastapi import APIRouter

import vcm_os.app.state as state
from vcm_os.app.models import AffectedSymbolsIn, CodebaseIndexIn, SymbolQueryIn
from vcm_os.schemas import MemoryObject

router = APIRouter()


@router.post("/codebase/index")
async def codebase_index(body: CodebaseIndexIn):
    state.ast_indexer.index_directory(body.directory)
    payloads = state.ast_indexer.to_memory_objects(body.project_id)
    for p in payloads:
        mem = MemoryObject(
            project_id=body.project_id,
            memory_type=p["memory_type"],
            source_type="file_snapshot",
            raw_text=p["summary"],
            compressed_summary=p["summary"],
            file_references=p["file_references"],
            entities=[{"type": e["type"], "name": e["name"]} for e in p["entities"]],
            importance_score=p["importance"],
            confidence_score=p["confidence"],
        )
        state.store.insert_memory(mem)
    return {
        "status": "ok",
        "files_indexed": len(state.ast_indexer.file_symbols),
        "symbols_found": len(state.ast_indexer.symbols),
    }


@router.post("/codebase/symbols/search")
async def symbol_search(body: SymbolQueryIn):
    results = state.ast_indexer.search_symbol(body.name)
    return {"symbols": [r.__dict__ for r in results]}


@router.post("/codebase/symbols/affected")
async def affected_symbols(body: AffectedSymbolsIn):
    affected = state.symbol_graph.find_affected_symbols(body.file_path, body.changed_lines)
    return {"affected": [s.__dict__ for s in affected]}


@router.post("/codebase/symbols/dependency_chain")
async def symbol_dependency_chain(name: str):
    chain = state.symbol_graph.get_dependency_chain(name)
    return chain
