import ast
from pathlib import Path
from typing import Dict, List, Set

from vcm_os.codebase.ast_index.types import SymbolInfo
from vcm_os.codebase.ast_index.visitor import _SymbolVisitor


class PythonASTIndexer:
    def __init__(self):
        self.symbols: Dict[str, SymbolInfo] = {}
        self.file_symbols: Dict[str, List[str]] = {}
        self.call_graph: Dict[str, Set[str]] = {}

    def index_directory(self, root_path: str) -> None:
        root = Path(root_path)
        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            self.index_file(str(py_file))

    def index_file(self, file_path: str) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            return

        self.file_symbols[file_path] = []
        visitor = _SymbolVisitor(file_path, source)
        visitor.visit(tree)

        for sym in visitor.symbols:
            key = f"{file_path}::{sym.name}"
            self.symbols[key] = sym
            self.file_symbols[file_path].append(key)
            self.call_graph[key] = set(sym.calls)

    def search_symbol(self, name: str) -> List[SymbolInfo]:
        results = []
        for key, sym in self.symbols.items():
            if sym.name == name or name in sym.name:
                results.append(sym)
        return results

    def get_file_symbols(self, file_path: str) -> List[SymbolInfo]:
        keys = self.file_symbols.get(file_path, [])
        return [self.symbols[k] for k in keys if k in self.symbols]

    def get_callers(self, symbol_name: str) -> List[SymbolInfo]:
        callers = []
        for key, calls in self.call_graph.items():
            if symbol_name in calls:
                if key in self.symbols:
                    callers.append(self.symbols[key])
        return callers

    def get_callees(self, symbol_key: str) -> List[SymbolInfo]:
        if symbol_key not in self.call_graph:
            return []
        return [self.symbols[k] for k in self.call_graph[symbol_key] if k in self.symbols]

    def to_memory_objects(self, project_id: str) -> List[dict]:
        """Export symbols as memory object payloads."""
        objs = []
        for key, sym in self.symbols.items():
            objs.append({
                "memory_type": "code_change",
                "summary": f"{sym.symbol_type} {sym.name} in {sym.file_path}:{sym.line_start}",
                "file_references": [sym.file_path],
                "entities": [{"type": sym.symbol_type, "name": sym.name}],
                "importance": 0.6,
                "confidence": 0.9,
            })
        return objs
