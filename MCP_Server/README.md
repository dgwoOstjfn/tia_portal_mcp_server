# TIA Portal MCP Server

MCP (Model Context Protocol) server for Siemens TIA Portal automation. Provides AI assistants with structured access to TIA Portal operations including project management, block operations, compilation, PLC tag export, and UDT (User-Defined Types) management.

## Features

### Core Operations
- **Session Management**: Create, manage, and close TIA Portal sessions
- **Project Operations**: Open, save, close, and get project information
- **Block Operations**: Import/export blocks from/to XML files, list all blocks
- **Compilation**: Compile entire projects, specific devices, or individual blocks
- **Error Handling**: Get compilation errors and warnings

### PLC Tag Operations (NEW)
- **Export All Tag Tables**: Export all PLC tag tables to XML files
- **Export Specific Tag Tables**: Export selected tag tables by name
- **List Tag Tables**: Get information about all available tag tables
- **Get Tag Details**: Retrieve detailed information about specific tag tables including individual tags

### UDT Operations (NEW)
- **Discover All UDTs**: Recursively discover all User-Defined Types in nested groups
- **Export All UDTs**: Export all UDTs to XML files maintaining folder structure
- **Export Specific UDTs**: Export selected UDTs by name
- **Generate UDT Source**: Generate SCL source code from UDTs with dependency management

### File Conversion
- **XML ↔ JSON**: Bidirectional conversion between XML and JSON formats
- **JSON ↔ SCL**: Convert JSON to SCL and SCL to JSON
- **XML ↔ SCL**: Convert XML to SCL and SCL to XML (via JSON)
- **PLC Tag Conversions**: Convert PLC tag XML to Excel format and vice versa
- **UDT Conversions**: Convert UDT XML to .udt format and vice versa

## Setup

1. Create virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure paths in `tia_portal_mcp.json` (automatically created with defaults on first run)

## Usage

### Start the Server
```bash
# Production start
python start_server.py

# Or directly
python src/server.py
```

### Test the Server
```bash
# Run basic functionality tests
python start_server.py test

# Run comprehensive tests
python tests/test_tools_simple.py
```

### Example MCP Tool Usage

#### Session Management
```python
# Create a new session
{
    "tool": "create_session",
    "arguments": {
        "metadata": {"description": "My automation session"}
    }
}

# Open a project
{
    "tool": "open_project", 
    "arguments": {
        "project_path": "D:/Projects/MyProject/MyProject.ap17",
        "session_id": "your-session-id"
    }
}
```

#### PLC Tag Operations
```python
# List all tag tables
{
    "tool": "list_tag_tables",
    "arguments": {
        "session_id": "your-session-id"
    }
}

# Export all tag tables
{
    "tool": "export_all_tag_tables",
    "arguments": {
        "session_id": "your-session-id",
        "output_path": "./exports/tags"
    }
}

# Export specific tag tables
{
    "tool": "export_specific_tag_tables",
    "arguments": {
        "session_id": "your-session-id",
        "table_names": ["PLC_1_Tags", "Safety_Tags"],
        "output_path": "./exports/tags"
    }
}
```

#### UDT Operations
```python
# Discover all UDTs
{
    "tool": "discover_all_udts",
    "arguments": {
        "session_id": "your-session-id"
    }
}

# Export all UDTs
{
    "tool": "export_all_udts",
    "arguments": {
        "session_id": "your-session-id",
        "output_path": "./exports/udts",
        "export_all": false  # Only exportable UDTs
    }
}

# Generate SCL source from UDTs
{
    "tool": "generate_udt_source",
    "arguments": {
        "session_id": "your-session-id",
        "udt_names": ["MyUDT1", "MyUDT2"],
        "output_path": "./generated/udts.scl",
        "with_dependencies": true
    }
}
```

#### Specialized File Conversions
```python
# Convert PLC tag XML to Excel format
{
    "tool": "convert_plc_tag_xml_to_excel",
    "arguments": {
        "xml_file_path": "./exports/MachineSettingsConstants.xml",
        "output_path": "./converted/MachineSettings.xlsx"
    }
}

# Convert Excel back to PLC tag XML
{
    "tool": "convert_excel_to_plc_tag_xml", 
    "arguments": {
        "excel_file_path": "./converted/MachineSettings.xlsx",
        "output_path": "./converted/MachineSettingsConstants.xml"
    }
}

# Convert UDT XML to .udt format
{
    "tool": "convert_udt_xml_to_udt",
    "arguments": {
        "xml_file_path": "./exports/UDT_ButtonStructure.xml",
        "output_path": "./converted/UDT_ButtonStructure.udt"
    }
}

# Convert .udt back to UDT XML
{
    "tool": "convert_udt_to_xml",
    "arguments": {
        "udt_file_path": "./converted/UDT_ButtonStructure.udt", 
        "output_path": "./converted/UDT_ButtonStructure.xml"
    }
}
```

## Available MCP Tools

### Session Management
- `create_session` - Create a new TIA Portal session
- `close_session` - Close an existing session
- `list_sessions` - List all active sessions

### Project Operations  
- `open_project` - Open a TIA Portal project
- `save_project` - Save the current project
- `close_project` - Close the current project
- `get_project_info` - Get information about the current project

### Block Operations
- `import_blocks` - Import blocks from XML files
- `export_blocks` - Export blocks to XML files
- `list_blocks` - List all blocks in the current project

### Compilation
- `compile_project` - Compile the entire project
- `compile_device` - Compile a specific device
- `compile_block` - Compile a specific block
- `get_compilation_errors` - Get compilation errors and warnings

### PLC Tag Operations
- `export_all_tag_tables` - Export all PLC tag tables to XML files
- `export_specific_tag_tables` - Export specific tag tables by name
- `list_tag_tables` - List all available PLC tag tables
- `get_tag_table_details` - Get detailed information about a specific tag table

### UDT Operations
- `discover_all_udts` - Discover all UDTs using recursive nested group exploration
- `export_all_udts` - Export all UDTs to XML files maintaining folder structure
- `export_specific_udts` - Export specific UDTs by name
- `generate_udt_source` - Generate SCL source code from UDTs

### File Conversion
- `convert_xml_to_json` - Convert XML file to JSON format
- `convert_json_to_xml` - Convert JSON file to XML format
- `convert_json_to_scl` - Convert JSON file to SCL format
- `convert_scl_to_json` - Convert SCL file to JSON format
- `convert_xml_to_scl` - Convert XML file to SCL format (via JSON)
- `convert_scl_to_xml` - Convert SCL file to XML format (via JSON)
- `convert_plc_tag_xml_to_excel` - Convert PLC tag XML to Excel format with multiple sheets
- `convert_excel_to_plc_tag_xml` - Convert Excel file back to PLC tag XML format
- `convert_udt_xml_to_udt` - Convert UDT XML to .udt SCL format
- `convert_udt_to_xml` - Convert .udt file back to UDT XML format

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Test server functionality
python src/server.py test

# Test tag and UDT integration
python test_tools_simple.py
```

## Configuration

The server uses a JSON configuration file (`tia_portal_mcp.json`) for all settings:

### Key Configuration Sections
- **paths.tia_portal**: TIA Portal installation and DLL paths
- **paths.project_defaults**: Default storage locations for projects, exports, imports
- **paths.test_materials**: Test project locations
- **paths.internal_libraries**: Internal library paths (self-contained)
- **settings**: Server behavior, logging, session management

### Configuration Example
```json
{
  "paths": {
    "tia_portal": {
      "installation_path": "C:\\Program Files\\Siemens\\Automation\\Portal V17",
      "dll_path": "C:\\Program Files\\Siemens\\Automation\\Portal V17\\PublicAPI\\V17\\Siemens.Engineering.dll"
    },
    "project_defaults": {
      "store_path": "./projects",
      "export_path": "./exports"
    }
  }
}
```

## Project Structure

```
MCP_Server/
├── src/
│   ├── server.py                    # Main MCP server
│   ├── mcp_config.py               # MCP configuration loader
│   ├── config.py                   # Legacy configuration (backward compatibility)
│   ├── handlers/
│   │   ├── block_handlers.py       # Block import/export operations
│   │   ├── compilation_handlers.py # Compilation operations
│   │   ├── conversion_handlers.py  # File conversion operations
│   │   ├── tag_handlers.py         # PLC tag operations (NEW)
│   │   └── udt_handlers.py         # UDT operations (NEW)
│   ├── session/
│   │   └── session_manager.py      # Session management
│   └── tia_client_wrapper.py       # TIA Portal client wrapper
├── lib/                            # Internal libraries (self-contained)
│   ├── tia_portal/                 # TIA Portal client library
│   ├── converters/                 # File conversion utilities
│   │   ├── plc_tag_converter.py   # PLC tag XML ↔ Excel conversion
│   │   └── udt_converter.py       # UDT XML ↔ .udt conversion
│   └── utils/                      # Utility functions
├── tests/                          # All test files consolidated here
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   ├── fixtures/                   # Test data
│   └── test_*.py                   # Test scripts
├── Docu/                           # All documentation consolidated here
│   ├── API_DOCUMENTATION.md
│   ├── CLAUDE_CODE_INTEGRATION.md
│   └── *.md                        # Other documentation files
├── ../Test_Material/               # Test projects and blocks (moved to parent directory)
├── tia_portal_mcp.json            # Main configuration file
├── start_server.py                 # Production startup script
├── README.md                       # This file
└── CLAUDE.md                       # Development guide
```

## Implementation Notes

### PLC Tag Export Integration
The PLC tag export functionality has been integrated from the proven `99_TIA_Client` implementation with the following features:

- **Complete Tag Discovery**: Finds all tag tables in PLC software
- **XML Export**: Exports tag tables to TIA Portal compatible XML format
- **Detailed Tag Information**: Retrieves individual tag details including data types, addresses, and properties
- **Error Handling**: Graceful handling of export failures with detailed error reporting

### UDT Export Integration  
The UDT export functionality uses the proven direct C# API approach that successfully exports UDTs:

- **Recursive UDT Discovery**: Traverses nested type groups to find all UDTs (71 UDTs discovered in test project)
- **Direct C# API Export**: Uses `udt.Export(FileInfo(path), tia.ExportOptions(0))` for reliable XML export
- **Folder Structure Preservation**: Maintains original TIA Portal folder hierarchy in exported files
- **Path Sanitization**: Handles special characters in folder names for filesystem compatibility
- **Protection Handling**: Properly identifies and handles know-how protected UDTs

### Message Format Consistency
All new tag and UDT tools maintain the same message format as existing MCP tools:

```python
{
    "success": bool,
    "message": str,           # Human readable summary
    "details": {              # Detailed results
        "operation_specific_data": "..."
    },
    "error": str              # Present only if success=False
}
```

## Production-Ready Features

### Self-Contained Distribution
- **Internal Libraries**: All dependencies packaged in `lib/` folder
- **Configurable Paths**: No hardcoded paths, everything configurable via JSON
- **Portable**: Easy to share and deploy without external dependencies

### Clean Project Structure
- **Organized Documentation**: All docs in `Docu/` subfolder
- **Consolidated Tests**: All test files in `tests/` directory
- **Essential Files Only**: Removed temporary and development files

### Configuration Management
- **JSON Configuration**: Single `tia_portal_mcp.json` file for all settings
- **Automatic Detection**: TIA Portal installation auto-detection
- **Flexible Paths**: Support for relative and absolute paths

## Recent Updates

### Version 1.3.0 - Specialized Conversions
- ✅ PLC tag XML to Excel conversion with Variables, User Constants, System Constants sheets
- ✅ Excel to PLC tag XML bidirectional conversion maintaining TIA Portal compatibility
- ✅ UDT XML to .udt SCL format conversion preserving comments and structure
- ✅ .udt to UDT XML bidirectional conversion with multilingual comment support
- ✅ Enhanced conversion handlers with specialized format support

### Version 1.2.0 - Production Ready
- ✅ Self-contained library structure
- ✅ JSON-based configuration system
- ✅ Clean project organization
- ✅ Internal path management
- ✅ Portable distribution

### Version 1.1.0 - Tag and UDT Integration
- ✅ Added 4 PLC tag operation tools
- ✅ Added 4 UDT operation tools  
- ✅ Integrated proven export functionality from `99_TIA_Client`
- ✅ Maintained consistent message format across all tools
- ✅ Added comprehensive error handling and logging
- ✅ Created integration tests for new functionality

### Testing Status
- ✅ Basic server functionality: **WORKING**
- ✅ Session management: **WORKING** 
- ✅ Project operations: **WORKING**
- ✅ Block operations: **WORKING**
- ✅ Tag and UDT tool integration: **VERIFIED**
- ✅ Tool execution paths: **CONFIRMED**

The MCP Server now provides comprehensive TIA Portal automation capabilities including the newly integrated PLC tag and UDT management features, making it suitable for production use with complex TIA Portal projects.