# dev-assistant-mcp

An MCP server that gives AI assistants developer superpowers — browse files, read/write code, find symbol definitions, trace call sites, list imports, run tests, and catch lint errors. Built on tree-sitter for accurate Python, JavaScript, TypeScript, and Java AST analysis with a smart cache that stays fresh as files change.

---

## Requirements

- Python 3.11+
- `pip install -r requirements.txt`
- Node.js + npm (for JS/TS linting via ESLint)
- Java + Maven (for Java test running)
- Checkstyle (for Java linting) — `brew install checkstyle`

---

## Setup

```bash
git clone https://github.com/prajwalrajbr/dev-assistant-mcp.git
cd dev-assistant-mcp
pip install -r requirements.txt
cp .env.example .env   # configure as needed
```

---

## Running the Server

**stdio** (default — for Claude Desktop):
```bash
python server.py
```

**SSE** (HTTP — for remote or multi-client use):
```bash
python server.py --transport sse
python server.py --transport sse --port 9090
```

---

## Configuration

Copy `.env.example` to `.env` and adjust values:

| Variable | Default | Description |
|---|---|---|
| `AST_MAX_DEPTH` | `100` | Max AST traversal depth. Increase for deeply nested code. |
| `TEST_TIMEOUT` | `60` | Timeout in seconds for `run_tests`. |
| `TRASH_DIR` | `.trash` | Folder where deleted files are moved instead of being permanently removed. |
| `CHECKSTYLE_CONFIG` | `/google_checks.xml` | Checkstyle config path. `/google_checks.xml` and `/sun_checks.xml` are bundled in the Checkstyle JAR. |

---

## Claude Desktop Configuration

Add the following to your Claude Desktop config file:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "dev-assistant": {
      "command": "python",
      "args": ["/absolute/path/to/dev-assistant-mcp/server.py"],
      "env": {
        "AST_MAX_DEPTH": "100",
        "TEST_TIMEOUT": "60",
        "TRASH_DIR": ".trash",
        "CHECKSTYLE_CONFIG": "/google_checks.xml"
      }
    }
  }
}
```

For SSE transport (remote server already running):
```json
{
  "mcpServers": {
    "dev-assistant": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## Tools

### File System

| Tool | Description |
|---|---|
| `list_directory` | List files and subdirectories inside a directory |
| `read_file` | Read the full text content of a file |
| `write_file` | Write content to a file, creating parent directories if needed |
| `delete_file` | Safely move a file to the trash folder instead of permanently deleting it |
| `move_file` | Move or rename a file, creating destination directories if needed |
| `search_files` | Regex-search across all text files in a directory, with optional extension filter |

### Code Intelligence

| Tool | Description |
|---|---|
| `get_symbols` | List all functions, classes, and arrow functions defined in a file |
| `find_symbol` | Find where a specific function or class is defined in a file |
| `get_references` | Find all call sites of a function across all supported files in a directory |
| `get_imports` | List all import statements in a file |
| `run_tests` | Run tests using the appropriate test runner (pytest / Jest / Maven / Gradle) |
| `get_lint_errors` | Lint a file and return structured errors (flake8 / ESLint / Checkstyle) |

---

### File System

#### `list_directory`
List contents of a directory.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the directory |

```json
{
  "path": "./src",
  "items": [
    {"name": "index.py", "type": "file", "path": "src/index.py"},
    {"name": "utils",    "type": "directory", "path": "src/utils"}
  ],
  "count": 2
}
```

---

#### `read_file`
Read the full contents of a file.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the file |

```json
{"path": "src/index.py", "content": "...", "lines": 42}
```

---

#### `write_file`
Write content to a file, creating parent directories if needed. Overwrites existing files.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the file |
| `content` | `str` | Content to write |

```json
{"path": "src/index.py", "bytes_written": 1024}
```

---

#### `delete_file`
Moves a file to the trash folder (`TRASH_DIR`) instead of permanently deleting it. Appends a timestamp to avoid name collisions.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the file to delete |

```json
{"original": "src/old.py", "moved_to": ".trash/old.py", "trash_dir": ".trash"}
```

---

#### `move_file`
Move or rename a file. Creates destination parent directories if needed. Fails if destination already exists.

| Parameter | Type | Description |
|---|---|---|
| `src` | `str` | Source file path |
| `dst` | `str` | Destination file path |

```json
{"src": "src/old.py", "dst": "src/new.py"}
```

---

#### `search_files`
Search for a regex pattern across all text files in a directory. Skips binaries and noise directories (`.git`, `node_modules`, `__pycache__`, `.venv`, `dist`, `build`, `target`, `.trash`).

| Parameter | Type | Description |
|---|---|---|
| `directory` | `str` | Root directory to search |
| `pattern` | `str` | Python regex pattern |
| `extensions` | `list[str]` _(optional)_ | Only search files with these extensions e.g. `[".py", ".ts"]` |

```json
{
  "pattern": "def process_",
  "matches": [
    {"file": "src/order.py", "line": 12, "content": "def process_order(self):"}
  ],
  "count": 1
}
```

---

### Code Intelligence

Supported languages: **Python** (`.py`), **JavaScript** (`.js`), **TypeScript** (`.ts`), **Java** (`.java`)

---

#### `get_symbols`
List all functions, classes, and arrow functions defined in a file, sorted by line number.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the source file |

```json
{
  "file": "src/utils.ts",
  "symbols": [
    {"type": "class",          "name": "OrderService", "line": 3},
    {"type": "function",       "name": "processOrder", "line": 12},
    {"type": "arrow_function", "name": "handleClick",  "line": 28}
  ],
  "count": 3
}
```

---

#### `find_symbol`
Find where a specific function or class is defined in a file.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the source file |
| `name` | `str` | Symbol name to find |

```json
{
  "symbol": "processOrder",
  "results": [
    {"type": "function", "name": "processOrder", "line": 12, "file": "src/order.py"}
  ],
  "count": 1
}
```

---

#### `get_references`
Find all call sites of a function or method across all supported files in a directory. Handles plain calls (`foo()`), attribute calls (`obj.foo()`), and Java constructor calls (`new Foo()`).

| Parameter | Type | Description |
|---|---|---|
| `directory` | `str` | Directory to search |
| `name` | `str` | Function/method name to find |

```json
{
  "symbol": "processOrder",
  "references": [
    {"file": "src/checkout.py",   "line": 42, "call": "processOrder"},
    {"file": "src/api/orders.py", "line": 17, "call": "self.processOrder"}
  ],
  "count": 2
}
```

---

#### `get_imports`
List all import statements in a file, sorted by line number.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the source file |

```json
{
  "file": "src/order.py",
  "imports": [
    {"type": "import_statement",      "statement": "import os",               "line": 1},
    {"type": "import_from_statement", "statement": "from pathlib import Path", "line": 2}
  ],
  "count": 2
}
```

---

#### `run_tests`
Run tests using the appropriate test runner detected from the file/directory type. Times out after `TEST_TIMEOUT` seconds.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | File or directory to test |

| File/Directory | Runner used |
|---|---|
| `.py` file or directory | `pytest` |
| `.js` / `.ts` or has `package.json` | `jest` |
| `.java` or has `pom.xml` | `mvn test` |
| has `build.gradle` | `./gradlew test` |

```json
{
  "path": "tests/",
  "runner": "python",
  "passed": true,
  "exit_code": 0,
  "output": "3 passed in 0.12s",
  "errors": ""
}
```

---

#### `get_lint_errors`
Run a linter on a source file and return structured errors.

| Parameter | Type | Description |
|---|---|---|
| `path` | `str` | Path to the source file |

| Extension | Linter |
|---|---|
| `.py` | flake8 |
| `.js` / `.ts` | ESLint (via `npx`) |
| `.java` | Checkstyle |

```json
{
  "file": "src/order.py",
  "linter": "flake8",
  "errors": [
    {"line": 12, "col": 5, "code": "E302", "message": "expected 2 blank lines, got 1"}
  ],
  "count": 1
}
```

---

## Project Structure

```
dev-assistant-mcp/
├── server.py              # MCP server entry point
├── core/
│   ├── ast_parser.py      # tree-sitter parsing, traversal, language grammars
│   └── index.py           # mtime-based AST cache (thread-safe)
├── tools/
│   ├── __init__.py        # shared helpers (check_path)
│   ├── filesystem.py      # file system tools
│   └── code_intelligence.py  # AST-based code tools
├── .env.example           # configuration reference
└── requirements.txt
```
