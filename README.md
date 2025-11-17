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

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed development documentation.
