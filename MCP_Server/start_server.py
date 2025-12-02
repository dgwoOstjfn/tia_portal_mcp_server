#!/usr/bin/env python3
"""
TIA Portal MCP Server Startup Script
Clean production entry point for the MCP server

This script automatically:
1. Detects and switches to the project root directory (eliminates need for 'cwd' in MCP config)
2. Configures Python path to find all required modules (eliminates need for PYTHONPATH)

This allows the simplest possible MCP configuration - only 'command' needs an absolute path.
"""
import sys
import os
from pathlib import Path

# Get the MCP_Server directory (parent of this script)
mcp_server_dir = Path(__file__).parent.resolve()

# Get the project root directory (parent of MCP_Server)
project_root = mcp_server_dir.parent

# Change to project root directory
# This ensures relative paths in config files work correctly
# and allows cwd in .mcp.json to be omitted or set to any value
os.chdir(project_root)

# Add both MCP_Server and MCP_Server/src to Python path
# This allows imports like: from src.server import main, and import lib.tia_portal
for path in [str(mcp_server_dir), str(mcp_server_dir / "src")]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import and run the server
if __name__ == "__main__":
    try:
        from src.server import main
        main()
    except ImportError as e:
        sys.stderr.write(f"Error importing server: {e}\n")
        sys.stderr.write(f"Current working directory: {os.getcwd()}\n")
        sys.stderr.write(f"Script location: {Path(__file__).parent}\n")
        sys.stderr.write(f"Python path: {sys.path[:3]}...\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"Error starting server: {e}\n")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)