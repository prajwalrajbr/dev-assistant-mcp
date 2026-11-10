from mcp.server.mcpserver import MCPServer
from tools.filesystem import list_directory, read_file, write_file, delete_file, move_file, search_files
from tools.code_intelligence import find_symbol, get_symbols, get_references, get_imports, run_tests, get_lint_errors

mcp = MCPServer("dev-assistant")

# --- File System Tools ---
mcp.tool()(list_directory)
mcp.tool()(read_file)
mcp.tool()(write_file)
mcp.tool()(delete_file)
mcp.tool()(move_file)
mcp.tool()(search_files)

# --- Code Intelligence Tools ---
mcp.tool()(find_symbol)
mcp.tool()(get_symbols)
mcp.tool()(get_references)
mcp.tool()(get_imports)
mcp.tool()(run_tests)
mcp.tool()(get_lint_errors)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="dev-assistant MCP server")
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    mcp.run(transport=args.transport, port=args.port)
