# TIA Portal MCP Server - API Method Instructions

## Table of Contents
- [Overview](#overview)
- [Session Management](#session-management)
- [Project Operations](#project-operations)
- [Block Operations](#block-operations)
- [Compilation Operations](#compilation-operations)
- [File Conversion Operations](#file-conversion-operations)
- [PLC Tag Operations](#plc-tag-operations)
- [UDT Operations](#udt-operations)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Quick Reference](#quick-reference)

## Overview

This document provides comprehensive instructions for using all available MCP tools/methods in the TIA Portal MCP Server. Each method includes interface descriptions, parameters, types, practical examples, and expected responses.

The server provides **30 MCP tools** organized into 7 categories:
- **Session Management** (3 tools)
- **Project Operations** (4 tools)
- **Block Operations** (4 tools)
- **Compilation Operations** (4 tools)
- **File Conversion Operations** (10 tools)
- **PLC Tag Operations** (4 tools)
- **UDT Operations** (4 tools)

---

## Session Management

### 1. create_session

Creates a new TIA Portal session for managing project operations.

**Parameters:**
- `metadata` (optional): `object` - Additional session metadata for tracking

**Interface:**
```json
{
  "name": "create_session",
  "arguments": {
    "metadata": {
      "user": "engineer",
      "project_type": "automation"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "uuid-string-12345",
  "created_at": 1754061968.424
}
```

**Example Usage:**
```python
# Create a basic session
session = await call_tool("create_session", {})

# Create session with metadata
session = await call_tool("create_session", {
    "metadata": {
        "user": "john_doe",
        "department": "automation",
        "project_category": "production"
    }
})
```

### 2. close_session

Closes an active TIA Portal session and cleans up resources.

**Parameters:**
- `session_id` (required): `string` - Session ID to close

**Interface:**
```json
{
  "name": "close_session",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Session closed successfully"
}
```

**Example Usage:**
```python
# Close a specific session
result = await call_tool("close_session", {
    "session_id": "uuid-string-12345"
})
```

### 3. list_sessions

Lists all currently active sessions with their status information.

**Parameters:** None

**Interface:**
```json
{
  "name": "list_sessions",
  "arguments": {}
}
```

**Response:**
```json
{
  "success": true,
  "sessions": {
    "session-uuid-1": {
      "session_id": "session-uuid-1",
      "created_at": "2025-08-01T23:03:54.343046",
      "last_activity": "2025-08-01T23:03:54.343046",
      "current_project": "Test_Project",
      "project_modified": false,
      "age_seconds": 120.5,
      "idle_seconds": 30.2,
      "metadata": {"user": "engineer"}
    }
  },
  "count": 1
}
```

**Example Usage:**
```python
# List all active sessions
sessions = await call_tool("list_sessions", {})
print(f"Active sessions: {sessions['count']}")
for session_id, info in sessions['sessions'].items():
    print(f"Session {session_id}: {info['current_project']}")
```

---

## Project Operations

### 4. open_project

Opens a TIA Portal project file for operations.

**Parameters:**
- `project_path` (required): `string` - Path to project file (.ap*) or directory
- `project_name` (optional): `string` - Project name if path is directory
- `session_id` (optional): `string` - Existing session ID, creates new if not provided

**Interface:**
```json
{
  "name": "open_project",
  "arguments": {
    "project_path": "D:\\Projects\\MyProject\\MyProject.ap17",
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "project_name": "MyProject",
  "store_path": "D:\\Projects\\MyProject",
  "is_modified": false,
  "session_id": "uuid-string-12345"
}
```

**Example Usage:**
```python
# Open project with existing session
project = await call_tool("open_project", {
    "project_path": "D:\\Projects\\AutomationProject\\AutomationProject.ap17",
    "session_id": session_id
})

# Open project and create new session
project = await call_tool("open_project", {
    "project_path": "E:\\TIA_Projects\\TestProject.ap17"
})

# Open project from directory
project = await call_tool("open_project", {
    "project_path": "D:\\Projects\\MyProject",
    "project_name": "MyProject"
})
```

### 5. save_project

Saves the currently open project.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "save_project",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Project saved successfully"
}
```

**Example Usage:**
```python
# Save current project
result = await call_tool("save_project", {
    "session_id": session_id
})
```

### 6. close_project

Closes the currently open project.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "close_project",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Project closed successfully"
}
```

**Example Usage:**
```python
# Close current project
result = await call_tool("close_project", {
    "session_id": session_id
})
```

### 7. get_project_info

Retrieves information about the currently open project.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "get_project_info",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "project_info": {
    "name": "MyProject",
    "is_modified": false,
    "path": "D:\\Projects\\MyProject"
  }
}
```

**Example Usage:**
```python
# Get project information
info = await call_tool("get_project_info", {
    "session_id": session_id
})

if info["success"]:
    project_name = info["project_info"]["name"]
    is_modified = info["project_info"]["is_modified"]
    print(f"Project: {project_name}, Modified: {is_modified}")
```

---

## Block Operations

### 8. list_blocks

Lists all blocks in the current project with their details.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "list_blocks",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "blocks": [
    {
      "name": "Main",
      "type": "OB",
      "path": "/Program blocks/"
    },
    {
      "name": "FB_Motor",
      "type": "FB",
      "path": "/Program blocks/Motors/"
    }
  ],
  "count": 2
}
```

**Example Usage:**
```python
# List all blocks
blocks = await call_tool("list_blocks", {
    "session_id": session_id
})

print(f"Found {blocks['count']} blocks:")
for block in blocks['blocks']:
    print(f"- {block['name']} ({block['type']}) in {block['path']}")
```

### 9. import_blocks

Imports blocks from XML files into the project.

**Parameters:**
- `xml_paths` (required): `array[string]` - List of XML file paths to import
- `session_id` (required): `string` - Session ID
- `target_folder` (optional): `string` - Target folder in PLC software
- `preserve_structure` (optional): `boolean` - Preserve folder structure (default: true)

**Interface:**
```json
{
  "name": "import_blocks",
  "arguments": {
    "xml_paths": [
      "./blocks/Main.xml",
      "./blocks/FB_Motor.xml"
    ],
    "target_folder": "ImportedBlocks",
    "preserve_structure": true,
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "imported": [
    {
      "path": "./blocks/Main.xml",
      "block_name": "Main",
      "folder": "ImportedBlocks",
      "subfolder": null
    }
  ],
  "errors": [],
  "summary": {
    "total": 2,
    "imported": 1,
    "failed": 1
  }
}
```

**Example Usage:**
```python
# Import specific blocks
import_result = await call_tool("import_blocks", {
    "xml_paths": [
        "D:\\Backups\\Main.xml",
        "D:\\Backups\\FB_Motor.xml"
    ],
    "target_folder": "BackupBlocks",
    "session_id": session_id
})

print(f"Imported {import_result['summary']['imported']} blocks")
for block in import_result['imported']:
    print(f"- {block['block_name']} from {block['path']}")
```

### 10. export_blocks

Exports blocks from the project to XML files.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `block_names` (optional): `array[string]` - List of block names to export (empty for all)
- `output_path` (optional): `string` - Output directory path (default: "./exports")
- `export_all` (optional): `boolean` - Export all blocks (default: false)

**Interface:**
```json
{
  "name": "export_blocks",
  "arguments": {
    "block_names": ["Main", "FB_Motor"],
    "output_path": "./block_exports",
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "exported": [
    {
      "block_name": "Main",
      "file_path": "./block_exports/Main.xml"
    }
  ],
  "errors": [],
  "output_path": "./block_exports",
  "summary": {
    "total": 2,
    "exported": 1,
    "failed": 1
  }
}
```

**Example Usage:**
```python
# Export specific blocks
export_result = await call_tool("export_blocks", {
    "block_names": ["Main", "FB_Conveyor", "FC_Initialize"],
    "output_path": "./project_backup",
    "session_id": session_id
})

# Export all blocks
export_all = await call_tool("export_blocks", {
    "export_all": true,
    "output_path": "./full_backup",
    "session_id": session_id
})
```

### 11. create_block_from_scl

Creates a TIA Portal block directly from SCL source code string. This tool accepts SCL code as a string parameter, converts it to TIA Portal XML format, and imports it into the project. This eliminates the need for file system access from MCP clients (e.g., Claude Desktop's sandboxed Linux environment).

**Parameters:**
- `session_id` (required): `string` - Session ID
- `scl_content` (required): `string` - SCL source code as string (complete block definition including FUNCTION_BLOCK, VAR sections, and BEGIN...END_FUNCTION_BLOCK)
- `target_folder` (optional): `string` - Target folder in PLC software
- `block_name` (optional): `string` - Block name override (extracted from SCL if not provided)

**Interface:**
```json
{
  "name": "create_block_from_scl",
  "arguments": {
    "session_id": "uuid-string-12345",
    "scl_content": "FUNCTION_BLOCK \"FB_Motor\"\nVAR_INPUT\n    Enable : Bool;\nEND_VAR\nBEGIN\n    // Motor control logic\nEND_FUNCTION_BLOCK",
    "target_folder": "Motors"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully created block 'FB_Motor' from SCL",
  "block_name": "FB_Motor",
  "target_folder": "Motors",
  "import_result": {
    "success": true,
    "imported": [
      {
        "path": "C:\\temp\\FB_Motor.xml",
        "block_name": "FB_Motor",
        "folder": "Motors",
        "subfolder": null
      }
    ],
    "errors": [],
    "summary": {
      "total": 1,
      "imported": 1,
      "failed": 0
    }
  }
}
```

**Example Usage:**
```python
# Create a function block from SCL code
scl_code = '''FUNCTION_BLOCK "FB_Conveyor"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1

VAR_INPUT
    Start : Bool;
    Stop : Bool;
    Speed : Real;
END_VAR

VAR_OUTPUT
    Running : Bool;
    CurrentSpeed : Real;
END_VAR

VAR
    internalState : Int;
END_VAR

BEGIN
    IF #Start AND NOT #Stop THEN
        #Running := TRUE;
        #CurrentSpeed := #Speed;
        #internalState := 1;
    ELSIF #Stop THEN
        #Running := FALSE;
        #CurrentSpeed := 0.0;
        #internalState := 0;
    END_IF;
END_FUNCTION_BLOCK
'''

result = await call_tool("create_block_from_scl", {
    "session_id": session_id,
    "scl_content": scl_code,
    "target_folder": "Conveyors"
})

if result["success"]:
    print(f"Created block: {result['block_name']}")
else:
    print(f"Failed: {result.get('error', 'Unknown error')}")

# Create block with explicit name override
result = await call_tool("create_block_from_scl", {
    "session_id": session_id,
    "scl_content": scl_code,
    "block_name": "FB_ConveyorV2",
    "target_folder": "Conveyors/Version2"
})
```

**Notes:**
- The SCL content must be a complete block definition
- Block name is automatically extracted from `FUNCTION_BLOCK "BlockName"` if not provided
- Supports FUNCTION_BLOCK (FB) type blocks
- All temporary files are automatically cleaned up after import
- The block is compiled after import to verify syntax

---

## Compilation Operations

### 11. compile_project

Compiles the entire project.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "compile_project",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "compilation_result": true,
  "message": "Project compilation completed"
}
```

**Example Usage:**
```python
# Compile entire project
compile_result = await call_tool("compile_project", {
    "session_id": session_id
})

if compile_result["compilation_result"]:
    print("Project compiled successfully")
else:
    print("Project compilation completed with issues")
```

### 12. compile_device

Compiles a specific device or PLC.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `device_name` (optional): `string` - Name of device to compile (uses first if not provided)

**Interface:**
```json
{
  "name": "compile_device",
  "arguments": {
    "session_id": "uuid-string-12345",
    "device_name": "PLC_1"
  }
}
```

**Response:**
```json
{
  "success": true,
  "compilation_result": true,
  "device_name": "PLC_1",
  "message": "Device compilation completed for PLC_1"
}
```

**Example Usage:**
```python
# Compile specific device
device_result = await call_tool("compile_device", {
    "session_id": session_id,
    "device_name": "MainPLC"
})

# Compile first device
device_result = await call_tool("compile_device", {
    "session_id": session_id
})
```

### 13. compile_block

Compiles a specific block.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `block_name` (required): `string` - Name of block to compile

**Interface:**
```json
{
  "name": "compile_block",
  "arguments": {
    "session_id": "uuid-string-12345",
    "block_name": "Main"
  }
}
```

**Response:**
```json
{
  "success": true,
  "compilation_result": true,
  "block_name": "Main",
  "message": "Block compilation completed for 'Main'"
}
```

**Example Usage:**
```python
# Compile specific block
block_result = await call_tool("compile_block", {
    "session_id": session_id,
    "block_name": "FB_Motor"
})
```

### 14. get_compilation_errors

Retrieves compilation errors and warnings from the project.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "get_compilation_errors",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "compilation_info": {
    "errors": [
      {
        "message": "Variable 'temp' not declared",
        "block": "FB_Motor",
        "line": 15
      }
    ],
    "warnings": [
      {
        "message": "Unused variable 'counter'",
        "block": "Main",
        "line": 8
      }
    ],
    "device_status": [
      {
        "name": "PLC_1",
        "status": "Compilation successful"
      }
    ]
  },
  "error_count": 1,
  "warning_count": 1
}
```

**Example Usage:**
```python
# Check compilation status
errors = await call_tool("get_compilation_errors", {
    "session_id": session_id
})

if errors["error_count"] > 0:
    print(f"Found {errors['error_count']} errors:")
    for error in errors["compilation_info"]["errors"]:
        print(f"- {error['message']} in {error['block']}")
        
if errors["warning_count"] > 0:
    print(f"Found {errors['warning_count']} warnings")
```

---

## File Conversion Operations

### 15. convert_xml_to_json

Converts XML files to JSON format.

**Parameters:**
- `xml_file_path` (required): `string` - Path to input XML file
- `output_path` (optional): `string` - Path for output JSON file

**Interface:**
```json
{
  "name": "convert_xml_to_json",
  "arguments": {
    "xml_file_path": "./blocks/Main.xml",
    "output_path": "./json/Main.json"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\Main.json",
  "message": "Successfully converted XML to JSON: D:\\absolute\\path\\to\\Main.json"
}
```

### 16. convert_json_to_xml

Converts JSON files to XML format.

**Parameters:**
- `json_file_path` (required): `string` - Path to input JSON file
- `output_path` (optional): `string` - Path for output XML file

**Interface:**
```json
{
  "name": "convert_json_to_xml",
  "arguments": {
    "json_file_path": "./json/Main.json",
    "output_path": "./xml/Main.xml"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\Main.xml",
  "message": "Successfully converted JSON to XML: D:\\absolute\\path\\to\\Main.xml"
}
```

### 17. convert_json_to_scl

Converts JSON files to SCL (Structured Control Language) format.

**Parameters:**
- `json_file_path` (required): `string` - Path to input JSON file
- `output_path` (optional): `string` - Path for output SCL file

**Interface:**
```json
{
  "name": "convert_json_to_scl",
  "arguments": {
    "json_file_path": "./json/FB_Motor.json",
    "output_path": "./scl/FB_Motor.scl"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\FB_Motor.scl",
  "message": "Successfully converted JSON to SCL: D:\\absolute\\path\\to\\FB_Motor.scl"
}
```

### 18. convert_scl_to_json

Converts SCL files to JSON format.

**Parameters:**
- `scl_file_path` (required): `string` - Path to input SCL file
- `output_path` (optional): `string` - Path for output JSON file

**Interface:**
```json
{
  "name": "convert_scl_to_json",
  "arguments": {
    "scl_file_path": "./scl/FB_Motor.scl",
    "output_path": "./json/FB_Motor.json"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\FB_Motor.json",
  "message": "Successfully converted SCL to JSON: D:\\absolute\\path\\to\\FB_Motor.json"
}
```

### 19. convert_xml_to_scl

Converts XML files to SCL format (via intermediate JSON conversion).

**Parameters:**
- `xml_file_path` (required): `string` - Path to input XML file
- `output_path` (optional): `string` - Path for output SCL file
- `temp_dir` (optional): `string` - Directory for temporary files

**Interface:**
```json
{
  "name": "convert_xml_to_scl",
  "arguments": {
    "xml_file_path": "./blocks/FB_Pump.xml",
    "output_path": "./scl/FB_Pump.scl",
    "temp_dir": "./temp"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\FB_Pump.scl",
  "message": "Successfully converted XML to SCL: D:\\absolute\\path\\to\\FB_Pump.scl"
}
```

### 20. convert_scl_to_xml

Converts SCL files to XML format (via intermediate JSON conversion).

**Parameters:**
- `scl_file_path` (required): `string` - Path to input SCL file
- `output_path` (optional): `string` - Path for output XML file
- `temp_dir` (optional): `string` - Directory for temporary files

**Interface:**
```json
{
  "name": "convert_scl_to_xml",
  "arguments": {
    "scl_file_path": "./scl/FB_Pump.scl",
    "output_path": "./xml/FB_Pump.xml",
    "temp_dir": "./temp"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\FB_Pump.xml",
  "message": "Successfully converted SCL to XML: D:\\absolute\\path\\to\\FB_Pump.xml"
}
```

### 21. convert_plc_tag_xml_to_excel

Converts PLC tag table XML files to Excel format with multiple sheets.

**Parameters:**
- `xml_file_path` (required): `string` - Path to input PLC tag XML file
- `output_path` (optional): `string` - Path for output Excel file

**Interface:**
```json
{
  "name": "convert_plc_tag_xml_to_excel",
  "arguments": {
    "xml_file_path": "./tags/IO_Tags.xml",
    "output_path": "./excel/IO_Tags.xlsx"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\IO_Tags.xlsx",
  "message": "Successfully converted PLC tag XML to Excel: D:\\absolute\\path\\to\\IO_Tags.xlsx"
}
```

### 22. convert_excel_to_plc_tag_xml

Converts Excel files back to PLC tag table XML format.

**Parameters:**
- `excel_file_path` (required): `string` - Path to input Excel file  
- `output_path` (optional): `string` - Path for output XML file
- `table_name` (optional): `string` - Name for the tag table

**Interface:**
```json
{
  "name": "convert_excel_to_plc_tag_xml",
  "arguments": {
    "excel_file_path": "./excel/IO_Tags.xlsx",
    "output_path": "./tags/IO_Tags_converted.xml",
    "table_name": "IO_Tags"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\IO_Tags_converted.xml",
  "message": "Successfully converted Excel to PLC tag XML: D:\\absolute\\path\\to\\IO_Tags_converted.xml"
}
```

### 23. convert_udt_xml_to_udt

Converts UDT XML files to .udt SCL-like format.

**Parameters:**
- `xml_file_path` (required): `string` - Path to input UDT XML file
- `output_path` (optional): `string` - Path for output .udt file

**Interface:**
```json
{
  "name": "convert_udt_xml_to_udt", 
  "arguments": {
    "xml_file_path": "./udts/UDT_Motor.xml",
    "output_path": "./scl/UDT_Motor.udt"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\UDT_Motor.udt",
  "message": "Successfully converted UDT XML to .udt: D:\\absolute\\path\\to\\UDT_Motor.udt"
}
```

### 24. convert_udt_to_xml

Converts .udt files to UDT XML format.

**Parameters:**
- `udt_file_path` (required): `string` - Path to input .udt file
- `output_path` (optional): `string` - Path for output XML file

**Interface:**
```json
{
  "name": "convert_udt_to_xml",
  "arguments": {
    "udt_file_path": "./scl/UDT_Motor.udt",
    "output_path": "./udts/UDT_Motor_converted.xml"
  }
}
```

**Response:**
```json
{
  "success": true,
  "output_file": "D:\\absolute\\path\\to\\UDT_Motor_converted.xml", 
  "message": "Successfully converted .udt to UDT XML: D:\\absolute\\path\\to\\UDT_Motor_converted.xml"
}
```

**Example Usage:**
```python
# Convert XML to JSON
conversion = await call_tool("convert_xml_to_json", {
    "xml_file_path": "D:\\Blocks\\Main.xml",
    "output_path": "D:\\JSON\\Main.json"
})

# Chain conversions: XML -> JSON -> SCL
json_result = await call_tool("convert_xml_to_json", {
    "xml_file_path": "source.xml"
})
if json_result["success"]:
    scl_result = await call_tool("convert_json_to_scl", {
        "json_file_path": json_result["output_file"],
        "output_path": "converted.scl"
    })

# Direct XML to SCL conversion
scl_direct = await call_tool("convert_xml_to_scl", {
    "xml_file_path": "source.xml",
    "output_path": "direct_converted.scl"
})

# PLC Tag conversions
tag_excel = await call_tool("convert_plc_tag_xml_to_excel", {
    "xml_file_path": "D:\\Tags\\IO_Tags.xml",
    "output_path": "D:\\Excel\\IO_Tags.xlsx"
})

# Convert Excel back to XML
tag_xml = await call_tool("convert_excel_to_plc_tag_xml", {
    "excel_file_path": "D:\\Excel\\IO_Tags.xlsx",
    "output_path": "D:\\Tags\\IO_Tags_converted.xml",
    "table_name": "IO_Tags"
})

# UDT conversions  
udt_file = await call_tool("convert_udt_xml_to_udt", {
    "xml_file_path": "D:\\UDTs\\UDT_Motor.xml",
    "output_path": "D:\\SCL\\UDT_Motor.udt"
})

# Convert UDT back to XML
udt_xml = await call_tool("convert_udt_to_xml", {
    "udt_file_path": "D:\\SCL\\UDT_Motor.udt", 
    "output_path": "D:\\UDTs\\UDT_Motor_converted.xml"
})
```

---

## PLC Tag Operations

### 21. export_all_tag_tables

Exports all PLC tag tables to XML files.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `output_path` (optional): `string` - Output directory path (default: "./exports")

**Interface:**
```json
{
  "name": "export_all_tag_tables",
  "arguments": {
    "session_id": "uuid-string-12345",
    "output_path": "./tag_exports"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tag table export completed: 3/3 successful",
  "details": {
    "output_path": "./tag_exports",
    "tables_found": 3,
    "tables_exported": 3,
    "total_size_bytes": 15680,
    "exported_tables": [
      {
        "name": "PLC_Tags",
        "path": "./tag_exports/PLC_Tags.xml",
        "size_bytes": 8192,
        "status": "success"
      }
    ]
  }
}
```

### 22. export_specific_tag_tables

Exports specific PLC tag tables to XML files.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `table_names` (required): `array[string]` - List of tag table names to export
- `output_path` (optional): `string` - Output directory path (default: "./exports")

**Interface:**
```json
{
  "name": "export_specific_tag_tables",
  "arguments": {
    "session_id": "uuid-string-12345",
    "table_names": ["PLC_Tags", "HMI_Tags"],
    "output_path": "./selected_tags"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Specific tag table export completed: 2/2 successful",
  "details": {
    "output_path": "./selected_tags",
    "tables_requested": ["PLC_Tags", "HMI_Tags"],
    "tables_exported": 2,
    "total_size_bytes": 12288,
    "exported_tables": [
      {
        "name": "PLC_Tags",
        "path": "./selected_tags/PLC_Tags.xml",
        "size_bytes": 8192,
        "status": "success"
      }
    ]
  }
}
```

### 23. list_tag_tables

Lists all available PLC tag tables in the project.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "list_tag_tables",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Found 3 tag tables",
  "details": {
    "tag_tables": [
      {
        "name": "PLC_Tags",
        "type": "TagTable",
        "tag_count": 25
      },
      {
        "name": "HMI_Tags",
        "type": "TagTable",
        "tag_count": 15
      }
    ],
    "total_count": 2
  }
}
```

### 24. get_tag_table_details

Gets detailed information about a specific tag table including individual tags.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `table_name` (required): `string` - Name of the tag table

**Interface:**
```json
{
  "name": "get_tag_table_details",
  "arguments": {
    "session_id": "uuid-string-12345",
    "table_name": "PLC_Tags"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved details for tag table 'PLC_Tags'",
  "details": {
    "table_name": "PLC_Tags",
    "tag_count": 3,
    "tags": [
      {
        "name": "Motor1_Start",
        "data_type": "Bool",
        "logical_address": "%M0.0",
        "comment": "Motor 1 start signal",
        "external_accessible": true,
        "external_visible": true,
        "external_writable": false
      },
      {
        "name": "Temperature_Sensor",
        "data_type": "Real",
        "logical_address": "%MD4",
        "comment": "Temperature reading"
      }
    ]
  }
}
```

**Example Usage:**
```python
# List all tag tables
tables = await call_tool("list_tag_tables", {
    "session_id": session_id
})

# Get details for specific table
details = await call_tool("get_tag_table_details", {
    "session_id": session_id,
    "table_name": "PLC_Tags"
})

# Export all tag tables
export_all = await call_tool("export_all_tag_tables", {
    "session_id": session_id,
    "output_path": "./tag_backup"
})

# Export specific tables
export_specific = await call_tool("export_specific_tag_tables", {
    "session_id": session_id,
    "table_names": ["Critical_Tags", "Safety_Tags"],
    "output_path": "./critical_backup"
})
```

---

## UDT Operations

### 25. discover_all_udts

Discovers all User-Defined Types (UDTs) in the project using recursive nested group exploration.

**Parameters:**
- `session_id` (required): `string` - Session ID

**Interface:**
```json
{
  "name": "discover_all_udts",
  "arguments": {
    "session_id": "uuid-string-12345"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "UDT discovery completed: 15 UDTs found",
  "details": {
    "total_udts": 15,
    "exportable_udts": 12,
    "protected_udts": 2,
    "inconsistent_udts": 1,
    "categories": {
      "Motors": [
        {
          "name": "UDT_Motor",
          "path": "Motors",
          "exportable": true,
          "consistent": true
        }
      ],
      "Sensors": [
        {
          "name": "UDT_TemperatureSensor",
          "path": "Sensors",
          "exportable": true,
          "consistent": true
        }
      ]
    },
    "all_udts": [
      {
        "name": "UDT_Motor",
        "path": "Motors",
        "is_know_how_protected": false,
        "is_consistent": true,
        "creation_date": "2024-01-15T10:30:00",
        "modified_date": "2024-02-20T14:15:00"
      }
    ]
  }
}
```

### 26. export_all_udts

Exports all UDTs to XML files maintaining folder structure.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `output_path` (optional): `string` - Base output directory (default: "./exports")
- `export_all` (optional): `boolean` - Whether to export all UDTs or only exportable ones (default: false)

**Interface:**
```json
{
  "name": "export_all_udts",
  "arguments": {
    "session_id": "uuid-string-12345",
    "output_path": "./udt_exports",
    "export_all": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "UDT export completed: 12/15 UDTs exported successfully",
  "details": {
    "output_path": "./udt_exports",
    "total_found": 15,
    "total_exported": 12,
    "total_failed": 1,
    "total_skipped": 2,
    "total_size_bytes": 45678,
    "export_results": [
      {
        "name": "UDT_Motor",
        "path": "Motors",
        "export_path": "./udt_exports/Motors/UDT_Motor.xml",
        "size_bytes": 2048,
        "status": "success",
        "is_consistent": true
      },
      {
        "name": "UDT_Protected",
        "path": "System",
        "status": "skipped",
        "reason": "Know-how protected"
      }
    ]
  }
}
```

### 27. export_specific_udts

Exports specific UDTs by name.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `udt_names` (required): `array[string]` - List of UDT names to export
- `output_path` (optional): `string` - Output directory (default: "./exports")

**Interface:**
```json
{
  "name": "export_specific_udts",
  "arguments": {
    "session_id": "uuid-string-12345",
    "udt_names": ["UDT_Motor", "UDT_Valve"],
    "output_path": "./selected_udts"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Specific UDT export completed: 2/2 successful",
  "details": {
    "output_path": "./selected_udts",
    "udts_requested": ["UDT_Motor", "UDT_Valve"],
    "udts_exported": 2,
    "total_size_bytes": 4096,
    "export_results": [
      {
        "name": "UDT_Motor",
        "path": "Motors",
        "export_path": "./selected_udts/UDT_Motor.xml",
        "size_bytes": 2048,
        "status": "success",
        "is_consistent": true
      },
      {
        "name": "UDT_Valve",
        "path": "Valves",
        "export_path": "./selected_udts/UDT_Valve.xml",
        "size_bytes": 2048,
        "status": "success",
        "is_consistent": true
      }
    ]
  }
}
```

### 28. generate_udt_source

Generates SCL source code from UDTs.

**Parameters:**
- `session_id` (required): `string` - Session ID
- `udt_names` (required): `array[string]` - List of UDT names to generate source for
- `output_path` (required): `string` - Output SCL file path
- `with_dependencies` (optional): `boolean` - Whether to include dependencies (default: true)

**Interface:**
```json
{
  "name": "generate_udt_source",
  "arguments": {
    "session_id": "uuid-string-12345",
    "udt_names": ["UDT_Motor", "UDT_Pump"],
    "output_path": "./source/Motor_Types.scl",
    "with_dependencies": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "SCL source generated successfully",
  "details": {
    "output_path": "./source/Motor_Types.scl",
    "udt_names": ["UDT_Motor", "UDT_Pump"],
    "with_dependencies": true,
    "file_size_bytes": 8192
  }
}
```

**Example Usage:**
```python
# Discover all UDTs
discovery = await call_tool("discover_all_udts", {
    "session_id": session_id
})

# Export all exportable UDTs
export_all = await call_tool("export_all_udts", {
    "session_id": session_id,
    "output_path": "./udt_backup",
    "export_all": false  # Only exportable ones
})

# Export specific UDTs
export_specific = await call_tool("export_specific_udts", {
    "session_id": session_id,
    "udt_names": ["UDT_Motor", "UDT_Conveyor"],
    "output_path": "./motor_udts"
})

# Generate SCL source code
generate_source = await call_tool("generate_udt_source", {
    "session_id": session_id,
    "udt_names": ["UDT_Motor", "UDT_Valve"],
    "output_path": "./source/equipment_types.scl",
    "with_dependencies": true
})
```

---

## Response Format

All MCP tools return responses in a consistent format:

### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": { /* operation-specific data */ },
  "details": { /* additional details */ }
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "code": "ERROR_CODE",
  "details": { /* error context */ }
}
```

### Common Response Fields
- `success`: Boolean indicating operation success
- `message`: Human-readable description of the result
- `error`: Error description (only in error responses)
- `code`: Error code for programmatic handling (optional)
- `data`: Primary operation result data
- `details`: Additional information and metadata

---

## Error Handling

### Common Error Types

1. **SESSION_NOT_FOUND**
   - Session ID is invalid or expired
   - Solution: Create a new session

2. **PROJECT_NOT_FOUND**
   - Project file doesn't exist at specified path
   - Solution: Verify project path and file existence

3. **BLOCK_NOT_FOUND**
   - Specified block doesn't exist in project
   - Solution: Use `list_blocks` to verify available blocks

4. **COMPILATION_FAILED**
   - Project/device/block compilation encountered errors
   - Solution: Use `get_compilation_errors` to diagnose issues

5. **IMPORT_FAILED**
   - Block import failed due to conflicts or invalid XML
   - Solution: Check XML format and resolve naming conflicts

6. **EXPORT_FAILED**
   - Block/tag/UDT export failed
   - Solution: Check permissions and disk space

7. **CONVERSION_FAILED**
   - File format conversion failed
   - Solution: Verify input file format and content

### Error Handling Best Practices

```python
async def safe_operation(tool_name, arguments):
    try:
        result = await call_tool(tool_name, arguments)
        
        if not result.get("success", False):
            print(f"Operation failed: {result.get('error', 'Unknown error')}")
            return None
            
        return result
        
    except Exception as e:
        print(f"Tool execution failed: {e}")
        return None

# Example usage
result = await safe_operation("compile_project", {"session_id": session_id})
if result:
    if result["compilation_result"]:
        print("Compilation successful")
    else:
        # Check for compilation errors
        errors = await safe_operation("get_compilation_errors", {"session_id": session_id})
        if errors and errors["error_count"] > 0:
            print(f"Found {errors['error_count']} compilation errors")
```

### Retry Strategies

1. **Session Timeouts**: Create new session and retry
2. **File Conflicts**: Use different output paths or cleanup existing files
3. **TIA Portal Busy**: Wait and retry with exponential backoff
4. **Compilation Errors**: Fix dependencies and retry

---

## Quick Reference

### Tool Categories Summary

| Category | Tools | Description |
|----------|-------|-------------|
| **Session** | `create_session`, `close_session`, `list_sessions` | Manage TIA Portal sessions |
| **Project** | `open_project`, `save_project`, `close_project`, `get_project_info` | Project lifecycle management |
| **Blocks** | `list_blocks`, `import_blocks`, `export_blocks`, `create_block_from_scl` | Block operations and management |
| **Compilation** | `compile_project`, `compile_device`, `compile_block`, `get_compilation_errors` | Compilation and error checking |
| **Conversion** | `convert_xml_to_json`, `convert_json_to_xml`, `convert_json_to_scl`, `convert_scl_to_json`, `convert_xml_to_scl`, `convert_scl_to_xml` | File format conversions |
| **Tags** | `export_all_tag_tables`, `export_specific_tag_tables`, `list_tag_tables`, `get_tag_table_details` | PLC tag table operations |
| **UDTs** | `discover_all_udts`, `export_all_udts`, `export_specific_udts`, `generate_udt_source` | User-Defined Type operations |

### Common Workflows

#### 1. Basic Project Operation
```python
# 1. Create session → 2. Open project → 3. List blocks → 4. Save project → 5. Close session
session = await call_tool("create_session", {})
project = await call_tool("open_project", {"project_path": "project.ap17", "session_id": session["session_id"]})
blocks = await call_tool("list_blocks", {"session_id": session["session_id"]})
await call_tool("save_project", {"session_id": session["session_id"]})
await call_tool("close_session", {"session_id": session["session_id"]})
```

#### 2. Export and Backup Workflow
```python
# Export blocks, tags, and UDTs for complete backup
await call_tool("export_blocks", {"export_all": True, "session_id": session_id})
await call_tool("export_all_tag_tables", {"session_id": session_id})
await call_tool("export_all_udts", {"session_id": session_id})
```

#### 3. Compilation and Error Check
```python
# Compile project and check for issues
compile_result = await call_tool("compile_project", {"session_id": session_id})
if not compile_result["compilation_result"]:
    errors = await call_tool("get_compilation_errors", {"session_id": session_id})
```

#### 4. File Format Conversion Chain
```python
# Convert XML → JSON → SCL
json_result = await call_tool("convert_xml_to_json", {"xml_file_path": "block.xml"})
scl_result = await call_tool("convert_json_to_scl", {"json_file_path": json_result["output_file"]})
```

#### 5. Create Block from SCL Code (AI-Assisted Development)
```python
# Generate and create a new function block directly from SCL code
# This is ideal for AI-assisted development where blocks are generated programmatically
scl_code = '''FUNCTION_BLOCK "FB_GeneratedBlock"
VAR_INPUT
    Enable : Bool;
    SetPoint : Real;
END_VAR
VAR_OUTPUT
    Active : Bool;
    ProcessValue : Real;
END_VAR
BEGIN
    IF #Enable THEN
        #Active := TRUE;
        #ProcessValue := #SetPoint * 1.0;
    ELSE
        #Active := FALSE;
    END_IF;
END_FUNCTION_BLOCK
'''

result = await call_tool("create_block_from_scl", {
    "session_id": session_id,
    "scl_content": scl_code,
    "target_folder": "Generated"
})

# Compile the new block to verify
if result["success"]:
    await call_tool("compile_block", {
        "session_id": session_id,
        "block_name": result["block_name"]
    })
```

This comprehensive API reference provides developers with all necessary information to effectively use the TIA Portal MCP Server tools for automation and integration tasks.