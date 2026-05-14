# Backward-compatible shim — re-exports from modular sub-package
from vcm_os.codebase.ast_index.types import SymbolInfo
from vcm_os.codebase.ast_index.indexer import PythonASTIndexer

__all__ = ["SymbolInfo", "PythonASTIndexer"]
