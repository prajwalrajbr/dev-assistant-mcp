from mcp.server.fastmcp import FastMCP
from tools.filesystem import list_directory, read_file, write_file, delete_file, move_file, search_files
from tools.code_intelligence import find_symbol, get_references, get_imports, run_tests, get_lint_errors

mcp = FastMCP("dev-assistant")

# --- File System Tools ---
mcp.tool()(list_directory)
mcp.tool()(read_file)
mcp.tool()(write_file)
mcp.tool()(delete_file)
mcp.tool()(move_file)
mcp.tool()(search_files)

# --- Code Intelligence Tools ---
mcp.tool()(find_symbol)
mcp.tool()(get_references)
mcp.tool()(get_imports)
mcp.tool()(run_tests)
mcp.tool()(get_lint_errors)

if __name__ == "__main__":
    mcp.run()
