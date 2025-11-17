#!/usr/bin/env python3
"""
TIA Portal MCP Server Startup Script
Clean production entry point for the MCP server

This script automatically configures Python path to find all required modules,
eliminating the need for PYTHONPATH environment variable in MCP configuration.
"""
import sys
import os
from pathlib import Path

# Get the MCP_Server directory (parent of this script)
mcp_server_dir = Path(__file__).parent.resolve()

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
        print(f"Error importing server: {e}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Script location: {Path(__file__).parent}")
        print(f"Python path: {sys.path[:3]}...")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)