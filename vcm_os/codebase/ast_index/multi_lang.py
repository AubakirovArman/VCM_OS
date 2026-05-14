"""Multi-language symbol indexer using regex (lightweight, no tree-sitter)."""
import re
from pathlib import Path
from typing import Dict, List, Set

from vcm_os.codebase.ast_index.types import SymbolInfo


_LANG_PATTERNS = {
    "py": {
        "class": re.compile(r"^class\s+(\w+)"),
        "function": re.compile(r"^def\s+(\w+)"),
        "method": re.compile(r"^\s+def\s+(\w+)"),
    },
    "js": {
        "class": re.compile(r"^class\s+(\w+)"),
        "function": re.compile(r"^function\s+(\w+)|^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function"),
        "arrow_function": re.compile(r"^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
        "method": re.compile(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*{"),
    },
    "ts": {
        "class": re.compile(r"^class\s+(\w+)"),
        "interface": re.compile(r"^interface\s+(\w+)"),
        "function": re.compile(r"^function\s+(\w+)|^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?function"),
        "arrow_function": re.compile(r"^(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\("),
        "method": re.compile(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:\{]"),
    },
    "rs": {
        "struct": re.compile(r"^struct\s+(\w+)"),
        "enum": re.compile(r"^enum\s+(\w+)"),
        "trait": re.compile(r"^trait\s+(\w+)"),
        "function": re.compile(r"^fn\s+(\w+)"),
        "impl": re.compile(r"^impl\s+(?:\w+\s+for\s+)?(\w+)"),
        "method": re.compile(r"^\s+fn\s+(\w+)"),
    },
    "go": {
        "function": re.compile(r"^func\s+(?:\([^)]*\)\s+)?(\w+)"),
        "struct": re.compile(r"^type\s+(\w+)\s+struct"),
        "interface": re.compile(r"^type\s+(\w+)\s+interface"),
        "method": re.compile(r"^func\s+\([^)]*\*?(\w+)\)\s+(\w+)"),
    },
    "java": {
        "class": re.compile(r"^(?:public\s+|private\s+|protected\s+)?class\s+(\w+)"),
        "interface": re.compile(r"^(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)"),
        "method": re.compile(r"^(?:public\s+|private\s+|protected\s+)?(?:static\s+)?\w+\s+(\w+)\s*\("),
    },
    "c": {
        "function": re.compile(r"^\w+\s+\*?\s*(\w+)\s*\([^)]*\)\s*\{"),
        "struct": re.compile(r"^typedef\s+struct\s+\{?[^}]*\}?\s*(\w+)"),
    },
    "cpp": {
        "class": re.compile(r"^class\s+(\w+)"),
        "function": re.compile(r"^\w+\s+\*?\s*(\w+)\s*\([^)]*\)\s*\{"),
        "method": re.compile(r"^\s+\w+\s+\*?\s*(\w+)\s*\([^)]*\)\s*\{"),
    },
}


class MultiLangIndexer:
    """Index symbols across multiple languages using regex."""

    def __init__(self):
        self.symbols: Dict[str, SymbolInfo] = {}
        self.file_symbols: Dict[str, List[str]] = {}
        self.call_graph: Dict[str, Set[str]] = {}

    def index_directory(self, root_path: str) -> None:
        root = Path(root_path)
        for ext in ("*.py", "*.js", "*.ts", "*.rs", "*.go", "*.java", "*.c", "*.cpp", "*.h", "*.hpp"):
            for file_path in root.rglob(ext):
                if "node_modules" in str(file_path) or "target" in str(file_path) or "__pycache__" in str(file_path):
                    continue
                self.index_file(str(file_path))

    def index_file(self, file_path: str) -> None:
        ext = Path(file_path).suffix.lstrip(".")
        lang = "c" if ext in ("h", "c") else "cpp" if ext in ("hpp", "cpp") else ext
        patterns = _LANG_PATTERNS.get(lang)
        if not patterns:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, OSError):
            return

        self.file_symbols[file_path] = []
        calls = []

        for i, line in enumerate(lines, 1):
            for sym_type, pat in patterns.items():
                m = pat.match(line)
                if m:
                    name = next((g for g in m.groups() if g), None)
                    if name:
                        sym = SymbolInfo(
                            name=name,
                            file_path=file_path,
                            symbol_type=sym_type,
                            line_start=i,
                            line_end=i,
                            calls=calls,
                        )
                        key = f"{file_path}::{name}"
                        self.symbols[key] = sym
                        self.file_symbols[file_path].append(key)
                        # Extract simple calls from surrounding lines (naive)
                        call_pat = re.compile(r"\b(\w+)\s*\(")
                        for j in range(max(0, i - 1), min(len(lines), i + 5)):
                            for cm in call_pat.finditer(lines[j]):
                                cname = cm.group(1)
                                if cname != name and not cname.startswith("_"):
                                    calls.append(cname)
                        sym.calls = list(set(calls))
                        self.call_graph[key] = set(sym.calls)
                    break

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
