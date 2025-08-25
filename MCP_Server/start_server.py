#!/usr/bin/env python3
"""
TIA Portal MCP Server Startup Script
Clean production entry point for the MCP server
"""
import sys
import os
from pathlib import Path

# Ensure src is in Python path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

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