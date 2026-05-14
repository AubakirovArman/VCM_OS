from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SymbolInfo:
    name: str
    symbol_type: str  # function, class, method, variable, import
    file_path: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parent: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
