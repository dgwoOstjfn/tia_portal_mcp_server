# TIA Portal MCP Server - Method Dependencies Analysis

## Overview

This analysis documents the exact conditions required for each MCP method to succeed, based on systematic testing via the MCP protocol.

## Dependency Levels

### Level 0: No Dependencies Required
These methods work without any prerequisite calls:

| Method | Success | Condition |
|--------|---------|-----------|
| `list_sessions` | ✅ Always | No dependencies |
| `create_session` | ✅ Always | No dependencies |
| `convert_xml_to_json` | ❌ File Error | Requires valid XML file path |
| `convert_json_to_xml` | ❌ File Error | Requires valid JSON file path |
| `convert_json_to_scl` | ❌ File Error | Requires valid JSON file path |
| `convert_scl_to_json` | ❌ File Error | Requires valid SCL file path |
| `convert_xml_to_scl` | ❌ File Error | Requires valid XML file path |
| `convert_scl_to_xml` | ❌ File Error | Requires valid SCL file path |
| `convert_plc_tag_xml_to_excel` | ❌ File Error | Requires valid PLC tag XML file path |
| `convert_excel_to_plc_tag_xml` | ❌ File Error | Requires valid Excel file path |
| `convert_udt_xml_to_udt` | ❌ File Error | Requires valid UDT XML file path |
| `convert_udt_to_xml` | ❌ File Error | Requires valid .udt file path |

**Note**: File conversion methods have no session dependencies but require valid file paths.

### Level 1: Session Required
These methods require a valid session but no project:

| Method | Without Project | Condition |
|--------|----------------|-----------|
| `close_project` | ✅ Success | Works even without open project |
| `open_project` | ✅ Success | Requires session + valid project path |
| `close_session` | ❌ Fails | Requires valid session ID |

### Level 2: Session + Project Required
These methods fail without an open project:

| Method | Without Project | With Project | Condition |
|--------|----------------|--------------|-----------|
| `get_project_info` | ❌ "No project open" | ❓ Untested | Requires open project |
| `save_project` | ❌ "No project open" | ❓ Untested | Requires open project |
| `list_blocks` | ❌ "No project open" | ✅ Success | Requires open project |
| `compile_project` | ❌ "No project open" | ✅ Success | Requires open project |
| `get_compilation_errors` | ❌ "No project open" | ✅ Success | Requires open project |

**Issue Found**: Some methods have implementation bugs:
- `list_tag_tables` fails with attribute error regardless of project state
- This indicates handler implementation issues, not dependency issues

### Level 3: Session + Project + Data Required
These methods require open project and may need specific data to exist:

| Method | Result | Condition |
|--------|--------|-----------|
| `export_blocks` | ✅ Success | Exported 5/6 blocks (1 failed due to permissions) |
| `export_all_tag_tables` | ❌ Handler Error | Implementation bug - attribute error |
| `get_tag_table_details` | ❌ Handler Error | Implementation bug - attribute error |

## Method Failure Patterns

### 1. Invalid Session ID
**Test**: Called methods with `session_id: 'invalid'`
**Result**: All session-dependent methods fail
**Error**: Session validation errors

### 2. No Project Open  
**Methods Affected**: Level 2 and 3 methods
**Error Messages**:
- `"No project is currently open"`
- `"No project is open"`

### 3. Invalid File Paths
**Methods Affected**: All conversion methods
**Error Pattern**: `"[File type] file not found: [path]"`

### 4. Implementation Bugs Found
**Methods with Handler Issues**:
- `list_tag_tables`: `'TIAClientWrapper' object has no attribute 'session_manager'`
- `export_all_tag_tables`: Same error
- `get_tag_table_details`: Same error

## Required Call Sequences

### Basic Operations
```
create_session
└── list_sessions ✅
└── close_session ✅
```

### Project Management
```
create_session
└── open_project ✅
    ├── get_project_info ❌ (needs testing with project)
    ├── save_project ❌ (needs testing with project) 
    ├── close_project ✅
    └── list_sessions ✅
```

### Block Operations
```
create_session
└── open_project ✅
    └── list_blocks ✅
        ├── export_blocks ✅ (5/6 blocks exported)
        └── compile_project ✅
            └── get_compilation_errors ✅
```

### Tag Operations (Currently Broken)
```
create_session
└── open_project ✅
    └── list_tag_tables ❌ (implementation error)
        ├── export_all_tag_tables ❌ (implementation error)
        └── get_tag_table_details ❌ (implementation error)
```

### File Conversions (Independent)
```
convert_xml_to_json (requires valid XML file)
convert_json_to_xml (requires valid JSON file)
convert_json_to_scl (requires valid JSON file)
convert_scl_to_json (requires valid SCL file)
convert_xml_to_scl (requires valid XML file)
convert_scl_to_xml (requires valid SCL file)
convert_plc_tag_xml_to_excel (requires valid PLC tag XML file)
convert_excel_to_plc_tag_xml (requires valid Excel file)
convert_udt_xml_to_udt (requires valid UDT XML file)  
convert_udt_to_xml (requires valid .udt file)
```

## Failure Conditions Summary

| Condition | Affected Methods | Error Pattern |
|-----------|-----------------|---------------|
| Invalid session ID | All Level 1-3 methods | Session validation error |
| No project open | Level 2-3 methods | "No project open" error |
| Invalid file path | Conversion methods | "File not found" error |
| Missing export permissions | Some export operations | "Export not permitted" |
| Implementation bugs | Tag-related methods | Attribute errors |

## Call Sequence Dependencies

### Minimum Required Sequence for Each Operation:

1. **Session Management**: `create_session` only
2. **Project Info**: `create_session` → `open_project` → `get_project_info`
3. **Block Operations**: `create_session` → `open_project` → `list_blocks`
4. **Block Export**: `create_session` → `open_project` → `list_blocks` → `export_blocks`
5. **Compilation**: `create_session` → `open_project` → `compile_project`
6. **Tag Operations**: `create_session` → `open_project` → `list_tag_tables` (currently broken)

### Invalid Sequences (Will Fail):

- ❌ `list_blocks` without `open_project`
- ❌ `export_blocks` without `list_blocks` (no explicit dependency, but project must be open)
- ❌ `get_project_info` without `open_project`  
- ❌ Any Level 1+ method with invalid `session_id`
- ❌ File conversion without valid file paths
- ❌ PLC tag conversion without valid XML/Excel files  
- ❌ UDT conversion without valid XML/.udt files

## Implementation Issues Discovered

1. **Tag Handler Bug**: The `TagHandlers` class references `session_manager` incorrectly
2. **Export Permissions**: Some blocks cannot be exported due to TIA Portal restrictions
3. **Error Handling**: Most methods handle missing dependencies gracefully with clear error messages

## Recommendations

1. **Fix Tag Handler Implementation**: Correct the `session_manager` attribute access
2. **Test Missing Scenarios**: Some methods weren't fully tested with projects open
3. **Document Export Limitations**: Not all blocks can be exported due to TIA Portal restrictions
4. **Add Dependency Validation**: Methods could validate their prerequisites before execution