from typing import Dict, List, Optional, Set

from vcm_os.schemas import MemoryObject
from vcm_os.storage.sqlite_store import SQLiteStore


class GraphExpander:
    def __init__(self, store: SQLiteStore):
        self.store = store

    def expand(
        self,
        seed_memory_ids: List[str],
        max_hops: int = 2,
        relation_types: Optional[List[str]] = None,
    ) -> List[MemoryObject]:
        visited: Set[str] = set()
        frontier = list(seed_memory_ids)
        all_memories: Dict[str, MemoryObject] = {}

        for hop in range(max_hops):
            next_frontier: List[str] = []
            for mid in frontier:
                if mid in visited:
                    continue
                visited.add(mid)
                mem = self.store.get_memory(mid)
                if mem:
                    all_memories[mid] = mem
                    # Follow links from this node
                    links = self.store.get_linked(mid)
                    links += self.store.get_reverse_linked(mid)
                    for target_id, rel_type, conf in links:
                        if relation_types and rel_type not in relation_types:
                            continue
                        if target_id not in visited:
                            next_frontier.append(target_id)
            frontier = next_frontier
            if not frontier:
                break

        # Also follow dependency_links and contradiction_links stored in memory object
        for mid, mem in list(all_memories.items()):
            for dep in mem.dependency_links:
                if dep not in visited:
                    dep_mem = self.store.get_memory(dep)
                    if dep_mem:
                        all_memories[dep] = dep_mem
                        visited.add(dep)
            for cont in mem.contradiction_links:
                if cont not in visited:
                    cont_mem = self.store.get_memory(cont)
                    if cont_mem:
                        all_memories[cont] = cont_mem
                        visited.add(cont)

        return list(all_memories.values())

    def get_neighbors(self, memory_id: str) -> List[MemoryObject]:
        mem = self.store.get_memory(memory_id)
        if not mem:
            return []
        ids: Set[str] = set()
        for target_id, _, _ in self.store.get_linked(memory_id):
            ids.add(target_id)
        for source_id, _, _ in self.store.get_reverse_linked(memory_id):
            ids.add(source_id)
        for dep in mem.dependency_links:
            ids.add(dep)
        for cont in mem.contradiction_links:
            ids.add(cont)
        return [self.store.get_memory(mid) for mid in ids if mid and self.store.get_memory(mid)]
