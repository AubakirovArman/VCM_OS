from typing import Dict, List, Optional

from vcm_os.schemas import MemoryObject
from vcm_os.storage.sqlite_store import SQLiteStore


class CodeIndex:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def index_file(self, project_id: str, file_path: str, content: str) -> MemoryObject:
        mem = MemoryObject(
            project_id=project_id,
            memory_type="code_change",
            source_type="file_snapshot",
            raw_text=content,
            compressed_summary=f"File: {file_path}",
            file_references=[file_path],
        )
        self.store.insert_memory(mem)
        return mem

    def search_by_path(self, project_id: str, path_fragment: str) -> List[MemoryObject]:
        mems = self.store.get_memories(project_id=project_id, memory_type="code_change", limit=200)
        return [m for m in mems if any(path_fragment in p for p in m.file_references)]
