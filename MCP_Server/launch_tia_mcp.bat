@echo off
REM TIA Portal MCP Server Launcher for Claude Code
REM This script launches the TIA Portal MCP Server for use with Claude Code

REM Set the working directory to the MCP Server location
cd /d "E:\OneDrive\VS_Code_Worspace\100_Dist\MCP_Server"

REM Set environment variables for better debugging
set PYTHONUNBUFFERED=1
set TIA_DEBUG=0

REM Launch the MCP server
python src\server.py

REM Pause on error for debugging (only if not called from Claude Code)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo MCP Server exited with error code %ERRORLEVEL%
    echo Check the logs above for details.
    pause
)