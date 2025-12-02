# TIA Portal MCP Server

Model Context Protocol (MCP) server for Siemens TIA Portal automation.

## Quick Start

### 1. Environment Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. MCP Configuration

Copy `.mcp.example.json` to `.mcp.json` and update the project root path in `command` only:

```json
{
  "mcpServers": {
    "tia-portal": {
      "command": "C:\\path\\to\\your\\project\\venv\\Scripts\\python.exe",
      "args": ["MCP_Server\\start_server.py"],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "TIA_SESSION_TIMEOUT": "3600",
        "TIA_MAX_SESSIONS": "3"
      }
    }
  }
}
```

**Important**:
- Only `command` needs an absolute path - replace with your actual project path
- `cwd` is optional - `start_server.py` auto-detects and switches to project root
- `args` uses relative path (works from any directory)

### 3. Test the Server

```bash
venv\Scripts\python.exe MCP_Server\start_server.py test
```

## Configuration Explained

You only need to specify your project root path **once** in the `command` field:

1. **`command`**: `<PROJECT_ROOT>\venv\Scripts\python.exe`
   - Must be absolute path (MCP client resolves this before starting the process)
   - This is the ONLY place you need to specify the full path

2. **`args`**: `MCP_Server\start_server.py`
   - Relative path - works from any directory
   - `start_server.py` auto-detects project root and switches to it

3. **`cwd`**: Optional (can be omitted)
   - `start_server.py` automatically changes to project root directory
   - No PYTHONPATH needed - all paths configured automatically

## How It Works

When you run Claude Code from any directory:
1. MCP client starts the Python interpreter using the absolute `command` path
2. `start_server.py` detects its own location
3. Script automatically switches working directory to project root
4. All relative paths in config files now work correctly

This design ensures the server works correctly regardless of where you run Claude Code from.

## Supported TIA Portal Versions

- V15.1
- V16
- V17
- V18
- V19
- V20

## Available Tools

The server provides **35+ MCP tools** organized into categories:

- **Session Management**: `create_session`, `close_session`, `list_sessions`
- **Project Operations**: `open_project`, `save_project`, `close_project`, `get_project_info`
- **Block Operations**: `list_blocks`, `import_blocks`, `export_blocks`, `create_block_from_scl`
- **Compilation**: `compile_project`, `compile_device`, `compile_block`, `get_compilation_errors`
- **File Conversions**: XML/JSON/SCL format conversions, PLC tag Excel conversions, UDT conversions
- **PLC Tags**: `list_tag_tables`, `export_all_tag_tables`, `export_specific_tag_tables`, `get_tag_table_details`
- **UDTs**: `discover_all_udts`, `export_all_udts`, `export_specific_udts`, `import_udt`

### Key Feature: Create Blocks from SCL String

The `create_block_from_scl` tool allows you to create TIA Portal blocks directly from SCL source code passed as a string parameter. This eliminates the need for file system access from MCP clients (e.g., Claude Desktop's sandboxed environment).

```python
# Example: Create a function block from SCL code
result = await call_tool("create_block_from_scl", {
    "session_id": "your-session-id",
    "scl_content": """FUNCTION_BLOCK "FB_MyBlock"
VAR_INPUT
    Enable : Bool;
    SetValue : Real;
END_VAR
VAR_OUTPUT
    Done : Bool;
END_VAR
BEGIN
    IF #Enable THEN
        #Done := TRUE;
    END_IF;
END_FUNCTION_BLOCK
""",
    "target_folder": "MyBlocks"  # Optional
})
```

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development documentation
- [MCP_Server/Docu/API_METHOD_INSTRUCTIONS.md](MCP_Server/Docu/API_METHOD_INSTRUCTIONS.md) - Complete API reference
