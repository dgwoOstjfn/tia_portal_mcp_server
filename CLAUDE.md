# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Model Context Protocol (MCP) server** that enables AI assistants to interact with Siemens TIA Portal automation engineering software. It bridges MCP clients (like Claude Desktop) with TIA Portal's Openness API, providing structured access to PLC programming, project management, compilation, and engineering workflows.

**Key Technology Stack:**
- Python 3.9+ with asyncio
- MCP protocol (stdio transport, JSON-RPC)
- pythonnet (clr) for .NET/COM interop
- TIA Portal Openness API (Siemens.Engineering.dll)

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server
```bash
# Production mode (stdio transport for MCP)
python MCP_Server/start_server.py

# Test mode (runs diagnostic tests)
python MCP_Server/start_server.py test
```

### Testing
```bash
# Run test mode to verify server functionality
python MCP_Server/start_server.py test

# Individual handler testing (most handlers support this)
cd MCP_Server/src/handlers
python -m pytest test_*.py
```

### Configuration
- **Main config**: `tia_portal_mcp.json` (auto-created on first run)
- **MCP client config**: `.mcp.json` (project) or `~/.claude.json` (user)
- **Simplified setup**: Only ONE absolute path required
  - `command`: `<PROJECT_ROOT>\launch_mcp.bat` - launcher script that auto-detects all paths
  - `args`: Not needed - launcher handles everything
  - `cwd`: Not needed - launcher auto-detects and switches to project root
  - No PYTHONPATH needed - all paths configured automatically
- **How it works**:
  - `launch_mcp.bat` uses `%~dp0` to detect its own location (project root)
  - Automatically derives paths to virtual environment and startup script
  - Works from any directory without additional configuration
- **Example**: See `.mcp.example.json` for a template configuration

## Architecture

### High-Level Structure
```
MCP Client (Claude Desktop)
    ↓ stdio (JSON-RPC)
TIAPortalMCPServer (src/server.py)
    ↓ routes to handlers
Handlers (session-based or stateless)
    ↓ uses async/sync bridge
TIAClientWrapper (async → ThreadPoolExecutor)
    ↓ COM calls on STA thread
tia_portal library (lib/tia_portal)
    ↓ pythonnet (clr)
Siemens.Engineering.dll (TIA Portal Openness API)
```

### Key Components

**1. Server Core** (`src/server.py`, ~1176 lines)
- Main MCP protocol handler
- Tool registration (30+ tools)
- Request routing to handlers
- Resource management

**2. Session Manager** (`src/session/session_manager.py`)
- Multi-session lifecycle management
- UUID-based session IDs
- Automatic timeout/cleanup (default 30 min)
- Concurrent session limits

**3. TIA Client Wrapper** (`src/tia_client_wrapper.py`)
- **Critical**: Async/sync bridge for COM operations
- TIA Portal API requires STA (Single-Threaded Apartment)
- Uses `ThreadPoolExecutor(max_workers=1)` for thread affinity
- All TIA operations must go through `execute_sync()` method

**4. Handlers** (`src/handlers/`)
- `block_handlers.py`: Block import/export/list
- `compilation_handlers.py`: Project/device/block compilation
- `tag_handlers.py`: PLC tag table operations
- `udt_handlers.py`: User-Defined Type operations
- `conversion_handlers.py`: File format conversions (stateless)

**5. TIA Portal Library** (`lib/tia_portal/`)
- Python wrapper for Openness API
- `__init__.py` contains main `Client` class (~2300 lines)
- Object-oriented interface to TIA Portal
- Handles version compatibility (V15.1-V20)

**6. Converters** (`lib/converters/`)
- Stateless file format converters
- XML ↔ JSON ↔ SCL transformations
- PLC tag and UDT specialized formats

## Critical Design Patterns

### Async/Sync Bridge Pattern
```python
# In TIAClientWrapper
async def my_operation(self):
    def _sync_operation():
        # TIA Portal COM API calls (must be synchronous)
        return self.project.get_plcs()

    # Execute on dedicated STA thread
    result = await self.execute_sync(_sync_operation)
    return result
```

**Why**: TIA Portal's COM objects require STA threading. Cannot be called directly from async code.

### Handler Response Pattern
All tools return standardized response format:
```python
{
    "success": bool,
    "message": str,           # Human-readable summary
    "details": {...},         # Detailed results
    "error": str              # Only if success=False
}
```

### Tool Dependency Chain
```
Level 0: list_sessions, create_session, convert_* (no dependencies)
Level 1: create_session → open_project
Level 2: open_project → list_blocks, compile_*, export_*
Level 3: list_blocks → export_blocks
```

**Important**: Always validate session existence and project state before operations.

## Code Organization

```
MCP_Server/
├── src/                           # Application code
│   ├── server.py                  # Main MCP server
│   ├── mcp_config.py              # Configuration loader
│   ├── tia_client_wrapper.py     # Async/sync bridge
│   ├── handlers/                  # Tool implementations
│   └── session/                   # Session management
├── lib/                           # Self-contained libraries
│   ├── tia_portal/               # Openness API wrapper
│   └── converters/               # Format converters
├── start_server.py               # Entry point
├── requirements.txt              # Dependencies
└── tia_portal_mcp.json          # Configuration (auto-created)
```

## Common Tasks

### Adding a New MCP Tool

1. **Register tool** in `src/server.py`:
```python
async def handle_list_tools(self) -> list[types.Tool]:
    return [
        # ... existing tools ...
        types.Tool(
            name="my_new_tool",
            description="What this tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "Session ID"},
                    "param1": {"type": "string", "description": "Parameter description"}
                },
                "required": ["session_id", "param1"]
            }
        )
    ]
```

2. **Implement handler** in appropriate `src/handlers/*.py`:
```python
@staticmethod
async def my_new_tool(session, param1: str) -> Dict[str, Any]:
    if not session.client_wrapper.project:
        return {"success": False, "error": "No project is open"}

    def _operation():
        # TIA Portal API calls here
        return result

    result = await session.client_wrapper.execute_sync(_operation)
    return {"success": True, "data": result}
```

3. **Route tool** in `src/server.py`:
```python
async def _execute_tool(self, tool_name: str, arguments: Dict) -> Dict:
    # ... existing tools ...
    elif tool_name == "my_new_tool":
        session = await self.session_manager.get_session(arguments["session_id"])
        if not session:
            return {"success": False, "error": "Session not found"}
        result = await MyHandlers.my_new_tool(session, arguments["param1"])
        session.update_activity()
        return result
```

### Modifying TIA Portal API Wrapper

The wrapper in `lib/tia_portal/__init__.py` uses composition pattern:
- Each TIA Portal object type has a Python wrapper class
- Wrappers hold reference to underlying COM object in `.value`
- Methods delegate to COM API calls
- Collections use `Composition` base class

Example pattern:
```python
class MyTIAObject:
    def __init__(self, value):
        self.value = value  # COM object

    def my_method(self, param):
        return self.value.MyMethod(param)  # Delegate to COM
```

## Known Issues

### Critical Bug in tag_handlers.py
**Location**: `src/handlers/tag_handlers.py`
**Issue**: Attempts to access non-existent `session.client_wrapper.session_manager`
**Pattern to fix**: Should access `session.client_wrapper.project.devices` directly
**Impact**: Tag table operations may fail

### Session Timeout Behavior
- Default timeout: 1800 seconds (30 minutes)
- Background cleanup runs every 5 minutes
- Sessions auto-close when timeout expires
- Unsaved project changes may be lost

## Threading and Concurrency

**COM STA Requirement**:
- All TIA Portal API calls MUST occur on the same thread
- Use `TIAClientWrapper.execute_sync()` for all TIA operations
- Never call TIA API directly from async code

**Session Concurrency**:
- `asyncio.Lock` protects session creation/destruction
- Max concurrent sessions configurable (default: 5)
- Each session has dedicated TIA Portal instance

## TIA Portal Version Compatibility

Supported versions: V15.1, V16, V17, V18, V19, V20

**Auto-detection logic**:
1. Check `tia_portal_mcp.json` for explicit path
2. Search common installation paths
3. Fall back to environment variable `TIA_PORTAL_PATH`

**DLL Path Pattern**:
```
C:\Program Files\Siemens\Automation\Portal V{XX}\PublicAPI\V{XX}\Siemens.Engineering.dll
```

## Configuration Management

### Configuration Hierarchy
1. **tia_portal_mcp.json** (primary, auto-created)
2. **Environment variables** (override)
   - `TIA_SESSION_TIMEOUT`
   - `TIA_MAX_SESSIONS`
   - `TIA_DEBUG`
3. **Hardcoded defaults** (fallback)

### Path Resolution
- Only ONE absolute path required in `.mcp.json` - the path to `launch_mcp.bat`
- `launch_mcp.bat` uses batch file variable `%~dp0` to auto-detect project root
- `start_server.py` configures `sys.path` for internal libraries automatically
- No need to set `PYTHONPATH` environment variable - everything is auto-configured
- Works from any directory - no `cwd` parameter needed

## Testing Checklist

Before committing changes:
1. Run `python MCP_Server/start_server.py test` - should pass all tests
2. Test with actual MCP client (Claude Desktop)
3. Verify session creation/cleanup
4. Test error handling paths
5. Check log output for warnings/errors

## Logging

Log files location:
- **MCP server logs**: Check stderr (MCP uses stdio transport)
- **Claude Desktop logs**: `%APPDATA%\Local\claude-cli-nodejs\Cache\C--Users-...\mcp-logs-tia-portal\`
- **Session manager**: Logs to stdout with timestamps

## Import Patterns

**From handlers to library**:
```python
import lib.tia_portal as tia_portal
from lib.converters.xml_to_json import convert_xml_to_json
```

**Within tia_portal library**:
```python
from .exceptions import TIAConnectionError
from .config import get_tia_version
```

**TIA Portal .NET imports**:
```python
import clr
clr.AddReference(dll_path)
import Siemens.Engineering as tia
```

## Performance Considerations

- TIA Portal operations can be slow (seconds for compilation)
- Session cleanup runs in background (non-blocking)
- File conversions are CPU-bound but fast
- COM calls have overhead - batch operations when possible

## Security Notes

- Server runs locally only (stdio transport)
- No network exposure
- File operations respect filesystem permissions
- TIA Portal license required for Openness API
