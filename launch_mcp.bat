@echo off
REM TIA Portal MCP Server Launcher
REM This script automatically detects the project root and launches the MCP server
REM Usage: Simply specify the absolute path to this batch file in your .mcp.json

REM Get the directory where this batch file is located (project root)
set PROJECT_ROOT=%~dp0

REM Remove trailing backslash
if "%PROJECT_ROOT:~-1%"=="\" set PROJECT_ROOT=%PROJECT_ROOT:~0,-1%

REM Launch the MCP server with the virtual environment Python
"%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\MCP_Server\start_server.py" %*
