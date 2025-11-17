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

Copy `.mcp.example.json` to `.mcp.json` and update the project root path:

```json
{
  "mcpServers": {
    "tia-portal": {
      "command": "C:\\path\\to\\your\\project\\venv\\Scripts\\python.exe",
      "args": ["MCP_Server\\start_server.py"],
      "cwd": "C:\\path\\to\\your\\project",
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
- Replace `<PROJECT_ROOT>` in both `command` and `cwd` with your actual project path
- `command` must be an absolute path (so it works from any directory)
- `args` uses relative path (relative to `cwd`)

### 3. Test the Server

```bash
venv\Scripts\python.exe MCP_Server\start_server.py test
```

## Configuration Explained

You only need to specify your project root path in **two places**:

1. **`command`**: `<PROJECT_ROOT>\venv\Scripts\python.exe`
   - Must be absolute path (MCP client resolves this before changing directory)

2. **`cwd`**: `<PROJECT_ROOT>`
   - Sets the working directory for the server process

3. **`args`**: `MCP_Server\start_server.py`
   - Relative path (automatically resolved from `cwd`)
   - No PYTHONPATH needed - `start_server.py` handles it automatically

## Why Both Paths Are Absolute?

When you run Claude Code from different directories:
- The MCP client tries to find the `command` executable from your **current directory**
- If `command` is relative, it will fail when you're not in the project directory
- Using absolute path ensures the server starts correctly from anywhere

## Supported TIA Portal Versions

- V15.1
- V16
- V17
- V18
- V19
- V20

## Documentation

See [CLAUDE.md](CLAUDE.md) for detailed development documentation.
