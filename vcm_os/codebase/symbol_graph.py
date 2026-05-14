from typing import Dict, List, Optional, Set, Tuple

from vcm_os.codebase.ast_index import PythonASTIndexer, SymbolInfo


class SymbolGraph:
    def __init__(self, indexer: PythonASTIndexer):
        self.indexer = indexer

    def find_affected_symbols(self, changed_file: str, changed_lines: List[int]) -> List[SymbolInfo]:
        """Find symbols in a file that overlap with changed line ranges."""
        affected = []
        for key in self.indexer.file_symbols.get(changed_file, []):
            sym = self.indexer.symbols.get(key)
            if not sym:
                continue
            for line in changed_lines:
                if sym.line_start <= line <= sym.line_end:
                    affected.append(sym)
                    break
        return affected

    def find_transitive_affected(self, seed_symbols: List[SymbolInfo], max_hops: int = 3) -> List[SymbolInfo]:
        """Find all symbols transitively affected via call graph."""
        visited: Set[str] = set()
        frontier = [f"{s.file_path}::{s.name}" for s in seed_symbols]
        all_affected: List[SymbolInfo] = []

        for hop in range(max_hops):
            next_frontier: List[str] = []
            for key in frontier:
                if key in visited:
                    continue
                visited.add(key)
                sym = self.indexer.symbols.get(key)
                if sym:
                    all_affected.append(sym)
                    # Follow callers (upstream) and callees (downstream)
                    for caller in self.indexer.get_callers(sym.name):
                        ck = f"{caller.file_path}::{caller.name}"
                        if ck not in visited:
                            next_frontier.append(ck)
                    for callee in self.indexer.get_callees(key):
                        ck = f"{callee.file_path}::{callee.name}"
                        if ck not in visited:
                            next_frontier.append(ck)
            frontier = next_frontier
            if not frontier:
                break

        return all_affected

    def get_dependency_chain(self, symbol_name: str) -> Dict[str, List[str]]:
        """Get upstream and downstream dependencies for a symbol."""
        upstream = []
        downstream = []
        for key, sym in self.indexer.symbols.items():
            if sym.name == symbol_name:
                upstream = [c.name for c in self.indexer.get_callers(symbol_name)]
                downstream = [c.name for c in self.indexer.get_callees(key)]
                break
        return {"upstream": upstream, "downstream": downstream}

    def to_dot(self) -> str:
        """Generate Graphviz DOT representation of call graph."""
        lines = ["digraph SymbolGraph {"]
        for key, sym in self.indexer.symbols.items():
            if sym.symbol_type in ("function", "method"):
                node_id = key.replace("/", "_").replace(".", "_")
                lines.append(f'  "{node_id}" [label="{sym.name}"];')
                for call in sym.calls:
                    lines.append(f'  "{node_id}" -> "{call}";')
        lines.append("}")
        return "\n".join(lines)
