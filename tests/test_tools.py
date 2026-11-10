import os
import pytest
from pathlib import Path

# --- Fixtures ---

@pytest.fixture
def tmp(tmp_path):
    """Base temp directory for all tests."""
    return tmp_path


@pytest.fixture
def py_file(tmp):
    """A simple Python source file."""
    f = tmp / "sample.py"
    f.write_text(
        "import os\n"
        "from pathlib import Path\n"
        "\n"
        "class MyClass:\n"
        "    def greet(self):\n"
        "        return 'hello'\n"
        "\n"
        "def standalone():\n"
        "    pass\n"
    )
    return f


@pytest.fixture
def js_file(tmp):
    """A simple JS source file with arrow and regular functions."""
    f = tmp / "sample.js"
    f.write_text(
        "import fs from 'fs';\n"
        "\n"
        "function regularFn() {}\n"
        "\n"
        "const arrowFn = () => {};\n"
        "\n"
        "class MyService {}\n"
    )
    return f


# ============================================================
# tools/filesystem.py
# ============================================================

from tools.filesystem import (
    list_directory,
    read_file,
    write_file,
    delete_file,
    move_file,
    search_files,
)


class TestListDirectory:
    def test_lists_contents(self, tmp):
        (tmp / "a.py").write_text("x")
        (tmp / "sub").mkdir()
        result = list_directory(str(tmp))
        assert result["count"] == 2
        names = {i["name"] for i in result["items"]}
        assert "a.py" in names
        assert "sub" in names

    def test_file_and_dir_types(self, tmp):
        (tmp / "f.py").write_text("")
        (tmp / "d").mkdir()
        result = list_directory(str(tmp))
        types = {i["name"]: i["type"] for i in result["items"]}
        assert types["f.py"] == "file"
        assert types["d"] == "directory"

    def test_nonexistent_path(self, tmp):
        result = list_directory(str(tmp / "nope"))
        assert "error" in result

    def test_file_instead_of_dir(self, tmp):
        f = tmp / "file.txt"
        f.write_text("x")
        result = list_directory(str(f))
        assert "error" in result


class TestReadFile:
    def test_reads_content(self, tmp):
        f = tmp / "hello.txt"
        f.write_text("line1\nline2\n")
        result = read_file(str(f))
        assert result["content"] == "line1\nline2\n"
        assert result["lines"] == 3

    def test_nonexistent_file(self, tmp):
        result = read_file(str(tmp / "missing.txt"))
        assert "error" in result

    def test_directory_instead_of_file(self, tmp):
        result = read_file(str(tmp))
        assert "error" in result


class TestWriteFile:
    def test_creates_file(self, tmp):
        path = str(tmp / "new.txt")
        result = write_file(path, "hello")
        assert Path(path).read_text() == "hello"
        assert result["bytes_written"] == 5

    def test_creates_parent_dirs(self, tmp):
        path = str(tmp / "a" / "b" / "c.txt")
        write_file(path, "deep")
        assert Path(path).exists()

    def test_overwrites_existing_file(self, tmp):
        f = tmp / "existing.txt"
        f.write_text("old")
        write_file(str(f), "new")
        assert f.read_text() == "new"

    def test_bytes_written_multibyte(self, tmp):
        path = str(tmp / "emoji.txt")
        result = write_file(path, "😀")
        assert result["bytes_written"] == 4  # emoji is 4 bytes in UTF-8


class TestDeleteFile:
    def test_moves_to_trash(self, tmp, monkeypatch):
        monkeypatch.setenv("TRASH_DIR", str(tmp / ".trash"))
        import tools.filesystem as fs
        fs._TRASH_DIR = str(tmp / ".trash")

        f = tmp / "todelete.txt"
        f.write_text("bye")
        result = delete_file(str(f))
        assert not f.exists()
        assert Path(result["moved_to"]).exists()

    def test_nonexistent_file(self, tmp):
        result = delete_file(str(tmp / "ghost.txt"))
        assert "error" in result

    def test_collision_adds_timestamp(self, tmp, monkeypatch):
        trash = tmp / ".trash"
        trash.mkdir()
        monkeypatch.setenv("TRASH_DIR", str(trash))
        import tools.filesystem as fs
        fs._TRASH_DIR = str(trash)

        # pre-place a file with the same name in trash
        (trash / "dup.txt").write_text("existing")

        f = tmp / "dup.txt"
        f.write_text("new")
        result = delete_file(str(f))
        moved = Path(result["moved_to"])
        assert moved.name != "dup.txt"  # timestamp was appended
        assert moved.exists()


class TestMoveFile:
    def test_moves_file(self, tmp):
        src = tmp / "src.txt"
        src.write_text("data")
        dst = str(tmp / "dst.txt")
        result = move_file(str(src), dst)
        assert not src.exists()
        assert Path(dst).exists()
        assert "error" not in result

    def test_creates_parent_dirs(self, tmp):
        src = tmp / "src.txt"
        src.write_text("x")
        dst = str(tmp / "sub" / "dst.txt")
        move_file(str(src), dst)
        assert Path(dst).exists()

    def test_nonexistent_source(self, tmp):
        result = move_file(str(tmp / "nope.txt"), str(tmp / "dst.txt"))
        assert "error" in result

    def test_destination_already_exists(self, tmp):
        src = tmp / "src.txt"
        dst = tmp / "dst.txt"
        src.write_text("s")
        dst.write_text("d")
        result = move_file(str(src), str(dst))
        assert "error" in result


class TestSearchFiles:
    def test_finds_match(self, tmp):
        (tmp / "a.py").write_text("def foo():\n    pass\n")
        result = search_files(str(tmp), r"def foo")
        assert result["count"] == 1
        assert result["matches"][0]["line"] == 1

    def test_no_match(self, tmp):
        (tmp / "a.py").write_text("x = 1\n")
        result = search_files(str(tmp), r"def foo")
        assert result["count"] == 0

    def test_invalid_regex(self, tmp):
        result = search_files(str(tmp), r"[unclosed")
        assert "error" in result

    def test_nonexistent_directory(self, tmp):
        result = search_files(str(tmp / "nope"), r"foo")
        assert "error" in result

    def test_extension_filter(self, tmp):
        (tmp / "a.py").write_text("match here\n")
        (tmp / "b.js").write_text("match here\n")
        result = search_files(str(tmp), r"match", extensions=[".py"])
        assert result["count"] == 1
        assert result["matches"][0]["file"].endswith(".py")

    def test_skips_binary_files(self, tmp):
        binary = tmp / "data.bin"
        binary.write_bytes(b"\x00\x01\x02match\x00")
        result = search_files(str(tmp), r"match")
        assert result["count"] == 0

    def test_skips_node_modules(self, tmp):
        nm = tmp / "node_modules"
        nm.mkdir()
        (nm / "lib.js").write_text("match here\n")
        result = search_files(str(tmp), r"match")
        assert result["count"] == 0

    def test_multiple_matches_across_files(self, tmp):
        (tmp / "a.py").write_text("foo\nfoo\n")
        (tmp / "b.py").write_text("foo\n")
        result = search_files(str(tmp), r"foo")
        assert result["count"] == 3


# ============================================================
# tools/code_intelligence.py
# ============================================================

from tools.code_intelligence import (
    find_symbol,
    get_symbols,
    get_references,
    get_imports,
    get_lint_errors,
)


class TestFindSymbol:
    def test_finds_function(self, py_file):
        result = find_symbol(str(py_file), "standalone")
        assert result["count"] == 1
        assert result["results"][0]["type"] == "function"
        assert result["results"][0]["line"] == 8

    def test_finds_class(self, py_file):
        result = find_symbol(str(py_file), "MyClass")
        assert result["count"] == 1
        assert result["results"][0]["type"] == "class"

    def test_finds_method(self, py_file):
        result = find_symbol(str(py_file), "greet")
        assert result["count"] == 1

    def test_symbol_not_found(self, py_file):
        result = find_symbol(str(py_file), "nonexistent")
        assert result["count"] == 0

    def test_nonexistent_file(self, tmp):
        result = find_symbol(str(tmp / "nope.py"), "foo")
        assert "error" in result

    def test_unsupported_extension(self, tmp):
        f = tmp / "file.rb"
        f.write_text("def foo; end")
        result = find_symbol(str(f), "foo")
        assert "error" in result

    def test_finds_js_arrow_function(self, js_file):
        result = find_symbol(str(js_file), "arrowFn")
        assert result["count"] == 1
        assert result["results"][0]["type"] == "arrow_function"

    def test_finds_js_regular_function(self, js_file):
        result = find_symbol(str(js_file), "regularFn")
        assert result["count"] == 1
        assert result["results"][0]["type"] == "function"


class TestGetSymbols:
    def test_lists_all_symbols(self, py_file):
        result = get_symbols(str(py_file))
        names = {s["name"] for s in result["symbols"]}
        assert "MyClass" in names
        assert "greet" in names
        assert "standalone" in names

    def test_sorted_by_line(self, py_file):
        result = get_symbols(str(py_file))
        lines = [s["line"] for s in result["symbols"]]
        assert lines == sorted(lines)

    def test_js_includes_arrow_functions(self, js_file):
        result = get_symbols(str(js_file))
        types = {s["type"] for s in result["symbols"]}
        assert "arrow_function" in types

    def test_nonexistent_file(self, tmp):
        result = get_symbols(str(tmp / "nope.py"))
        assert "error" in result

    def test_empty_file(self, tmp):
        f = tmp / "empty.py"
        f.write_text("")
        result = get_symbols(str(f))
        assert result["count"] == 0


class TestGetReferences:
    def test_finds_call(self, tmp):
        (tmp / "a.py").write_text("def target(): pass\n")
        (tmp / "b.py").write_text("target()\n")
        result = get_references(str(tmp), "target")
        assert result["count"] == 1
        assert result["references"][0]["line"] == 1

    def test_finds_attribute_call(self, tmp):
        (tmp / "a.py").write_text("obj.target()\n")
        result = get_references(str(tmp), "target")
        assert result["count"] == 1

    def test_no_references(self, tmp):
        (tmp / "a.py").write_text("x = 1\n")
        result = get_references(str(tmp), "target")
        assert result["count"] == 0

    def test_nonexistent_directory(self, tmp):
        result = get_references(str(tmp / "nope"), "foo")
        assert "error" in result

    def test_skips_unreadable_files(self, tmp):
        binary = tmp / "data.py"
        binary.write_bytes(b"\x00\x01\x02")
        result = get_references(str(tmp), "foo")
        assert "error" not in result  # should not crash


class TestGetImports:
    def test_finds_python_imports(self, py_file):
        result = get_imports(str(py_file))
        statements = [i["statement"] for i in result["imports"]]
        assert any("import os" in s for s in statements)
        assert any("from pathlib" in s for s in statements)

    def test_sorted_by_line(self, py_file):
        result = get_imports(str(py_file))
        lines = [i["line"] for i in result["imports"]]
        assert lines == sorted(lines)

    def test_js_imports(self, js_file):
        result = get_imports(str(js_file))
        assert result["count"] == 1
        assert "fs" in result["imports"][0]["statement"]

    def test_no_imports(self, tmp):
        f = tmp / "noimport.py"
        f.write_text("x = 1\n")
        result = get_imports(str(f))
        assert result["count"] == 0

    def test_nonexistent_file(self, tmp):
        result = get_imports(str(tmp / "nope.py"))
        assert "error" in result


class TestGetLintErrors:
    def test_clean_file_has_no_errors(self, tmp):
        f = tmp / "clean.py"
        f.write_text("x = 1\n")
        result = get_lint_errors(str(f))
        assert result["count"] == 0

    def test_detects_flake8_errors(self, tmp):
        f = tmp / "bad.py"
        # F401: imported but unused
        f.write_text("import os\nimport sys\n")
        result = get_lint_errors(str(f))
        assert result["linter"] == "flake8"
        assert result["count"] > 0
        assert all("line" in e for e in result["errors"] if "raw" not in e)

    def test_nonexistent_file(self, tmp):
        result = get_lint_errors(str(tmp / "nope.py"))
        assert "error" in result

    def test_unsupported_extension(self, tmp):
        f = tmp / "file.rb"
        f.write_text("def foo; end")
        result = get_lint_errors(str(f))
        assert "error" in result
