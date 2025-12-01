# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Note**: For comprehensive documentation, see the root-level [../CLAUDE.md](../CLAUDE.md) which covers the entire tia_mcp repository including this MCP server component.

## Quick Reference for MCP Server Development

### Commands

```bash
# From tia_portal_mcp_server directory
venv\Scripts\activate
python MCP_Server/start_server.py test    # Run diagnostic tests
python MCP_Server/start_server.py         # Production mode (stdio)
```

### Key Files

| File | Purpose |
|------|---------|
| `MCP_Server/src/server.py` | Main MCP server, tool registration, request routing |
| `MCP_Server/src/handlers/*.py` | Tool implementations (blocks, tags, compilation, etc.) |
| `MCP_Server/src/tia_client_wrapper.py` | Async/sync bridge for COM operations |
| `MCP_Server/lib/tia_portal/__init__.py` | TIA Portal Openness API wrapper |
| `tia_portal_mcp.json` | Server configuration (auto-created) |

### Critical Pattern: Async/Sync Bridge

All TIA Portal API calls must go through `execute_sync()`:

```python
async def my_handler(session, ...):
    def _sync_operation():
        # TIA Portal COM API calls here (sync only)
        return session.client_wrapper.project.get_plcs()

    result = await session.client_wrapper.execute_sync(_sync_operation)
    return {"success": True, "data": result}
```

**Why**: TIA Portal's COM objects require STA (Single-Threaded Apartment) threading.

### Adding New Tools

1. Register in `server.py` → `handle_list_tools()`
2. Implement in `handlers/*.py`
3. Route in `server.py` → `_execute_tool()`

See root CLAUDE.md for detailed examples.
