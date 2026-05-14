from typing import List

from vcm_os.llm_client import LLMClient


class QueryRewriter:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def expand(self, query: str, task_type: str) -> List[str]:
        expanded = await self.llm.rewrite_query(query, task_type)
        # Always include original
        if query not in expanded:
            expanded.insert(0, query)
        return expanded[:4]  # max 4 queries

    def expand_simple(self, query: str, task_type: str) -> List[str]:
        # Fallback non-LLM expansion
        variants = [query]
        if task_type == "debugging":
            variants.append(f"error bug fix {query}")
            variants.append(f"traceback exception {query}")
        elif task_type == "architecture":
            variants.append(f"design decision ADR {query}")
        elif task_type == "feature":
            variants.append(f"implement requirement {query}")
        return variants
