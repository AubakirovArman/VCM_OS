import ast
from typing import List, Optional, Tuple

from vcm_os.codebase.ast_index.types import SymbolInfo


class _SymbolVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, source: str):
        self.file_path = file_path
        self.source = source
        self.symbols: List[SymbolInfo] = []
        self._current_class: Optional[str] = None
        self._lines = source.splitlines()

    def _get_source_lines(self, node: ast.AST) -> Tuple[int, int]:
        return (getattr(node, "lineno", 1), getattr(node, "end_lineno", getattr(node, "lineno", 1)))

    def _get_docstring(self, node: ast.AST) -> Optional[str]:
        doc = ast.get_docstring(node)
        return doc[:500] if doc else None

    def _get_decorators(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> List[str]:
        decs = []
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decs.append(d.id)
            elif isinstance(d, ast.Call) and isinstance(d.func, ast.Name):
                decs.append(d.func.id)
        return decs

    def _extract_calls(self, node: ast.AST) -> List[str]:
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute) and isinstance(child.func.value, ast.Name):
                    calls.append(child.func.attr)
        return calls

    def _extract_signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation and isinstance(arg.annotation, ast.Name):
                arg_str += f": {arg.annotation.id}"
            args.append(arg_str)
        return f"def {node.name}({', '.join(args)})"

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        old_class = self._current_class
        self._current_class = node.name
        line_start, line_end = self._get_source_lines(node)
        sym = SymbolInfo(
            name=node.name,
            symbol_type="class",
            file_path=self.file_path,
            line_start=line_start,
            line_end=line_end,
            docstring=self._get_docstring(node),
            decorators=self._get_decorators(node),
            calls=self._extract_calls(node),
        )
        self.symbols.append(sym)
        self.generic_visit(node)
        self._current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node, is_async=True)

    def _process_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        line_start, line_end = self._get_source_lines(node)
        prefix = "async " if is_async else ""
        name = node.name
        if self._current_class:
            name = f"{self._current_class}.{name}"
        sym = SymbolInfo(
            name=name,
            symbol_type="method" if self._current_class else "function",
            file_path=self.file_path,
            line_start=line_start,
            line_end=line_end,
            signature=self._extract_signature(node),
            docstring=self._get_docstring(node),
            parent=self._current_class,
            decorators=self._get_decorators(node),
            calls=self._extract_calls(node),
        )
        self.symbols.append(sym)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            sym = SymbolInfo(
                name=alias.name,
                symbol_type="import",
                file_path=self.file_path,
                line_start=getattr(node, "lineno", 1),
                line_end=getattr(node, "lineno", 1),
            )
            self.symbols.append(sym)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            sym = SymbolInfo(
                name=f"{module}.{alias.name}" if module else alias.name,
                symbol_type="import",
                file_path=self.file_path,
                line_start=getattr(node, "lineno", 1),
                line_end=getattr(node, "lineno", 1),
            )
            self.symbols.append(sym)
