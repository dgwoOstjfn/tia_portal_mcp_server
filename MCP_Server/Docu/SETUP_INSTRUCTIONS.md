# TIA Portal MCP Server - Setup Instructions

This guide provides step-by-step instructions for setting up the TIA Portal MCP Server on a new PC.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Installation Steps](#installation-steps)
- [Configuration](#configuration)
- [Testing the Installation](#testing-the-installation)
- [Troubleshooting](#troubleshooting)
- [Quick Start Guide](#quick-start-guide)

## Prerequisites

### System Requirements
- **Operating System**: Windows 10/11 (64-bit)
- **Python**: 3.9 or higher (3.11 recommended)
- **TIA Portal**: V15.1, V16, V17, V18, V19, or V20
- **RAM**: Minimum 8GB (16GB recommended)
- **Disk Space**: 500MB for MCP server + space for projects

### Required Software
1. **TIA Portal with Openness API**
   - Install TIA Portal (any version from V15.1 to V20)
   - Ensure TIA Portal Openness is activated in your license

2. **Python Installation**
   ```bash
   # Download Python from https://www.python.org/downloads/
   # During installation, check "Add Python to PATH"
   ```

3. **Git (Optional)**
   ```bash
   # For cloning the repository
   # Download from https://git-scm.com/downloads
   ```

## Installation Steps

### Step 1: Download/Clone the MCP Server

#### Option A: Download ZIP
1. Download the MCP_Server folder
2. Extract to your desired location (e.g., `C:\MCP_Server`)

#### Option B: Clone Repository
```bash
git clone [repository-url]
cd MCP_Server
```

### Step 2: Set Up Python Environment

1. **Open Command Prompt as Administrator**
2. **Navigate to MCP_Server directory**
   ```bash
   cd C:\MCP_Server
   ```

3. **Create Virtual Environment**
   ```bash
   python -m venv venv
   ```

4. **Activate Virtual Environment**
   ```bash
   # Windows Command Prompt
   venv\Scripts\activate
   
   # Windows PowerShell
   venv\Scripts\Activate.ps1
   ```

5. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Step 3: Verify TIA Portal Installation

1. **Check TIA Portal Path**
   ```bash
   # Default installation paths:
   # V17: C:\Program Files\Siemens\Automation\Portal V17
   # V18: C:\Program Files\Siemens\Automation\Portal V18
   ```

2. **Verify Openness DLL**
   ```bash
   # Check if file exists:
   # C:\Program Files\Siemens\Automation\Portal V17\PublicAPI\V17\Siemens.Engineering.dll
   ```

### Step 4: Configure the MCP Server

1. **Update Configuration File**
   
   Edit `src/config.py` if TIA Portal is not in default location:
   ```python
   TIA_PORTAL_PATH = r"C:\Program Files\Siemens\Automation\Portal V17"
   TIA_OPENNESS_DLL = r"C:\Program Files\Siemens\Automation\Portal V17\PublicAPI\V17\Siemens.Engineering.dll"
   ```

2. **Configure MCP Client (Claude Desktop)**
   
   Create/Edit `.mcp.json` in your project root:
   ```json
   {
     "mcpServers": {
       "tia-portal": {
         "command": "python",
         "args": ["MCP_Server/start_server.py"],
         "cwd": "C:\\Your\\Project\\Path",
         "env": {
           "PYTHONPATH": "C:\\Your\\Project\\Path\\MCP_Server\\src;C:\\Your\\Project\\Path\\MCP_Server",
           "PYTHONUNBUFFERED": "1",
           "TIA_SESSION_TIMEOUT": "3600",
           "TIA_MAX_SESSIONS": "3"
         }
       }
     }
   }
   ```

   Or for Claude Desktop, edit `%APPDATA%\Claude\claude_desktop_config.json`:
   ```json
   {
     "mcpServers": {
       "tia-portal": {
         "command": "python",
         "args": ["C:/MCP_Server/start_server.py"],
         "cwd": "C:/MCP_Server",
         "env": {
           "PYTHONPATH": "C:/MCP_Server/src",
           "PYTHONUNBUFFERED": "1"
         }
       }
     }
   }
   ```

## Testing the Installation

### Step 1: Test Server Startup

1. **Run Server Test**
   ```bash
   cd C:\MCP_Server
   venv\Scripts\activate
   python src/server.py test
   ```
   
   Expected output:
   ```
   2025-XX-XX XX:XX:XX - INFO - Initialized tia-portal-server v1.0.0
   2025-XX-XX XX:XX:XX - INFO - Server test completed successfully
   ```

2. **Start Server Manually**
   ```bash
   python start_server.py
   ```
   
   The server should start and wait for connections.

### Step 2: Test with MCP Client

1. **Using Claude Desktop**
   - Restart Claude Desktop after configuration
   - The TIA Portal server should appear in available MCP servers
   - Try a simple command: "List available TIA Portal sessions"

2. **Using Test Script**
   ```python
   # Run from another terminal
   cd C:\MCP_Server
   venv\Scripts\activate
   python tests/test_tools_simple.py
   ```

### Step 3: Verify TIA Portal Connection

1. **Open TIA Portal** (can be done automatically by MCP)
2. **Test Project Operations**
   ```python
   # Create a test session
   # Open a test project
   # List blocks
   # Close session
   ```

## Troubleshooting

### Common Issues and Solutions

#### 1. Python Not Found
```bash
# Solution: Add Python to PATH
# Windows Settings > Environment Variables > Path
# Add: C:\Python311\Scripts\ and C:\Python311\
```

#### 2. DLL Not Found Error
```python
# Error: Could not find Siemens.Engineering.dll
# Solution: Update TIA_OPENNESS_DLL path in config.py
```

#### 3. Permission Denied
```bash
# Solution: Run Command Prompt as Administrator
# Or grant full permissions to MCP_Server folder
```

#### 4. Import Error for pythonnet
```bash
# Solution: Install .NET Framework
# Download from Microsoft website
# Then reinstall pythonnet:
pip uninstall pythonnet
pip install pythonnet
```

#### 5. TIA Portal Won't Start
```bash
# Solution: Check Windows Firewall
# Add exception for TIA Portal and Python
# Ensure TIA Portal license is valid
```

#### 6. MCP Connection Failed
```bash
# Check error log:
# C:\Users\%USERNAME%\AppData\Local\claude-cli-nodejs\Cache\*\mcp-logs-tia-portal\*.txt

# Common fixes:
# - Verify server is running
# - Check .mcp.json configuration
# - Ensure paths use forward slashes or escaped backslashes
```

### Log Files Location
- **MCP Server Logs**: `MCP_Server/logs/`
- **Claude Desktop Logs**: `%APPDATA%\Local\claude-cli-nodejs\Cache\`
- **TIA Portal Logs**: Check TIA Portal installation directory

## Quick Start Guide

### For Developers
1. **Quick Setup Script** (create `setup.bat`):
   ```batch
   @echo off
   echo Setting up TIA Portal MCP Server...
   python -m venv venv
   call venv\Scripts\activate
   pip install -r requirements.txt
   echo Setup complete! Run 'start_server.bat' to start the server.
   pause
   ```

2. **Start Server Script** (create `start_server.bat`):
   ```batch
   @echo off
   call venv\Scripts\activate
   python start_server.py
   pause
   ```

### For End Users
1. Download the MCP_Server folder
2. Run `setup.bat` (one time only)
3. Run `start_server.bat` to start the server
4. Configure your MCP client to connect

## Environment Variables (Optional)

You can set these environment variables for custom configuration:

```bash
# Windows Command Prompt
set TIA_PORTAL_PATH=C:\Custom\Path\To\TIA
set TIA_SESSION_TIMEOUT=7200
set TIA_MAX_SESSIONS=5
set TIA_DEBUG=1

# Windows PowerShell
$env:TIA_PORTAL_PATH = "C:\Custom\Path\To\TIA"
$env:TIA_SESSION_TIMEOUT = "7200"
$env:TIA_MAX_SESSIONS = "5"
$env:TIA_DEBUG = "1"
```

## Security Considerations

1. **Firewall Configuration**
   - The MCP server runs locally only
   - No external network access required
   - Add exceptions if Windows Defender blocks

2. **User Permissions**
   - Run with standard user rights
   - Administrator only needed for installation
   - TIA Portal may require specific user permissions

3. **Project Access**
   - Ensure user has read/write access to project folders
   - Set appropriate permissions for export/import directories

## Support and Resources

- **Documentation**: See `API_METHOD_INSTRUCTIONS.md` for API reference
- **Test Projects**: Available in `Test_Material/` folder
- **Examples**: Check `tests/` folder for usage examples
- **Issues**: Report issues in the project repository

## Version Compatibility

| TIA Portal Version | Python Version | Status |
|-------------------|---------------|---------|
| V15.1             | 3.9+          | ✅ Supported |
| V16               | 3.9+          | ✅ Supported |
| V17               | 3.9+          | ✅ Supported |
| V18               | 3.10+         | ✅ Supported |
| V19               | 3.10+         | ✅ Supported |
| V20               | 3.11+         | ✅ Supported |

## Next Steps

After successful installation:
1. Review `API_METHOD_INSTRUCTIONS.md` for available methods
2. Try example scripts in `tests/` folder
3. Open test projects from `Test_Material/`
4. Start automating your TIA Portal workflows!