"""Tests for multi-language code indexer."""
import tempfile
from pathlib import Path

import pytest

from vcm_os.codebase.ast_index.multi_lang import MultiLangIndexer


def _write_file(root: Path, rel_path: str, content: str) -> None:
    fp = root / rel_path
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(content)


def test_index_python():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "foo.py", "class Foo:\n    def bar(self): pass\ndef baz(): pass")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "foo.py"))
        assert len(idx.symbols) == 3
        names = {s.name for s in idx.symbols.values()}
        assert names == {"Foo", "bar", "baz"}


def test_index_javascript():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "app.js", "class App {}\nfunction init() {}\nconst run = () => {}")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "app.js"))
        names = {s.name for s in idx.symbols.values()}
        assert "App" in names
        assert "init" in names
        assert "run" in names


def test_index_typescript():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "api.ts", "interface User {}\nclass ApiClient {}\nfunction fetch() {}")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "api.ts"))
        names = {s.name for s in idx.symbols.values()}
        assert "User" in names
        assert "ApiClient" in names
        assert "fetch" in names


def test_index_rust():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "main.rs", "struct Point;\nenum Status;\nfn main() {}\nimpl Point {}")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "main.rs"))
        names = {s.name for s in idx.symbols.values()}
        assert "Point" in names
        assert "Status" in names
        assert "main" in names


def test_index_go():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "main.go", "type Config struct{}\ntype Reader interface{}\nfunc main() {}")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "main.go"))
        names = {s.name for s in idx.symbols.values()}
        assert "Config" in names
        assert "Reader" in names
        assert "main" in names


def test_index_java():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "App.java", "public class App {}\ninterface Service {}\npublic void run() {}")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "App.java"))
        names = {s.name for s in idx.symbols.values()}
        assert "App" in names
        assert "Service" in names
        assert "run" in names


def test_index_cpp():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "main.cpp", "class Engine {};\nint start() {}")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "main.cpp"))
        names = {s.name for s in idx.symbols.values()}
        assert "Engine" in names
        assert "start" in names


def test_index_directory():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "a.py", "def f(): pass")
        _write_file(root, "b.js", "function g() {}")
        _write_file(root, "c.rs", "fn h() {}")
        idx = MultiLangIndexer()
        idx.index_directory(str(root))
        names = {s.name for s in idx.symbols.values()}
        assert names == {"f", "g", "h"}


def test_search_symbol():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "mod.py", "class AuthService:\n    def login(self): pass")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "mod.py"))
        results = idx.search_symbol("Auth")
        assert len(results) == 1
        assert results[0].name == "AuthService"


def test_get_file_symbols():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "mod.py", "class A:\n    def b(self): pass")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "mod.py"))
        syms = idx.get_file_symbols(str(root / "mod.py"))
        assert len(syms) == 2


def test_to_memory_objects():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write_file(root, "mod.py", "def foo(): pass")
        idx = MultiLangIndexer()
        idx.index_file(str(root / "mod.py"))
        objs = idx.to_memory_objects("proj1")
        assert len(objs) == 1
        assert objs[0]["memory_type"] == "code_change"
        assert "foo" in objs[0]["summary"]
