# TIA Portal MCP Server - Call Sequence Diagrams

## Method Dependency Tree

```
Level 0: No Dependencies
├── list_sessions ✅
├── create_session ✅  
└── File Conversions (require valid file paths)
    ├── convert_xml_to_json
    ├── convert_json_to_xml
    ├── convert_json_to_scl
    ├── convert_scl_to_json
    ├── convert_xml_to_scl
    ├── convert_scl_to_xml
    ├── convert_plc_tag_xml_to_excel
    ├── convert_excel_to_plc_tag_xml
    ├── convert_udt_xml_to_udt
    └── convert_udt_to_xml

Level 1: Session Required
├── create_session ✅
│   ├── open_project ✅
│   ├── close_project ✅
│   └── close_session ✅

Level 2: Session + Project Required  
├── create_session ✅
│   └── open_project ✅
│       ├── get_project_info ❓
│       ├── save_project ❓
│       ├── list_blocks ✅
│       ├── compile_project ✅
│       └── get_compilation_errors ✅

Level 3: Session + Project + Data Required
├── create_session ✅
│   └── open_project ✅
│       ├── list_blocks ✅
│       │   └── export_blocks ✅ (5/6 success)
│       ├── list_tag_tables ❌ (broken)
│       │   ├── export_all_tag_tables ❌ (broken)
│       │   └── get_tag_table_details ❌ (broken)
│       └── discover_all_udts ❓
│           ├── export_all_udts ❓
│           ├── export_specific_udts ❓
│           └── generate_udt_source ❓
```

## Sequential Call Flow Diagrams

### 1. Basic Session Management

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant TIA_Portal

    Client->>MCP_Server: create_session()
    MCP_Server->>TIA_Portal: Connect to TIA Portal
    TIA_Portal-->>MCP_Server: Connection established
    MCP_Server-->>Client: {session_id, success: true}
    
    Client->>MCP_Server: list_sessions()
    MCP_Server-->>Client: {sessions: [...], success: true}
    
    Client->>MCP_Server: close_session(session_id)
    MCP_Server->>TIA_Portal: Disconnect
    TIA_Portal-->>MCP_Server: Disconnected
    MCP_Server-->>Client: {success: true}
```

### 2. Project Operations Flow

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant TIA_Portal

    Client->>MCP_Server: create_session()
    MCP_Server-->>Client: {session_id}
    
    Client->>MCP_Server: open_project(session_id, project_path)
    MCP_Server->>TIA_Portal: Open project file
    TIA_Portal-->>MCP_Server: Project opened
    MCP_Server-->>Client: {success: true}
    
    Note over Client,TIA_Portal: Now project-dependent methods work
    
    Client->>MCP_Server: get_project_info(session_id)
    MCP_Server->>TIA_Portal: Get project details
    TIA_Portal-->>MCP_Server: Project info
    MCP_Server-->>Client: {project_info, success: true}
    
    Client->>MCP_Server: save_project(session_id)  
    MCP_Server->>TIA_Portal: Save project
    TIA_Portal-->>MCP_Server: Project saved
    MCP_Server-->>Client: {success: true}
    
    Client->>MCP_Server: close_project(session_id)
    MCP_Server->>TIA_Portal: Close project
    TIA_Portal-->>MCP_Server: Project closed
    MCP_Server-->>Client: {success: true}
```

### 3. Block Operations Flow

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant TIA_Portal

    Client->>MCP_Server: create_session()
    MCP_Server-->>Client: {session_id}
    
    Client->>MCP_Server: open_project(session_id, project_path)
    MCP_Server-->>Client: {success: true}
    
    Client->>MCP_Server: list_blocks(session_id)
    MCP_Server->>TIA_Portal: Discover all blocks
    TIA_Portal-->>MCP_Server: Block list
    MCP_Server-->>Client: {blocks: [...], count: N}
    
    Client->>MCP_Server: export_blocks(session_id, export_all: true)
    MCP_Server->>TIA_Portal: Export each block
    loop For each block
        TIA_Portal-->>MCP_Server: Block exported (or error)
    end
    MCP_Server-->>Client: {exported_count: 5, failed_count: 1}
    
    Client->>MCP_Server: compile_project(session_id)
    MCP_Server->>TIA_Portal: Compile project
    TIA_Portal-->>MCP_Server: Compilation result
    MCP_Server-->>Client: {success: true}
    
    Client->>MCP_Server: get_compilation_errors(session_id)
    MCP_Server->>TIA_Portal: Get errors/warnings
    TIA_Portal-->>MCP_Server: Error list
    MCP_Server-->>Client: {errors: [...], warnings: [...]}
```

### 4. Failed Tag Operations Flow (Broken Implementation)

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant Handler
    participant TIA_Portal

    Client->>MCP_Server: create_session()
    MCP_Server-->>Client: {session_id}
    
    Client->>MCP_Server: open_project(session_id, project_path)
    MCP_Server-->>Client: {success: true}
    
    Client->>MCP_Server: list_tag_tables(session_id)
    MCP_Server->>Handler: TagHandlers.list_tag_tables()
    Handler->>Handler: Access session_manager (❌ FAILS)
    Handler-->>MCP_Server: AttributeError
    MCP_Server-->>Client: {success: false, error: "implementation error"}
    
    Note over Client,TIA_Portal: All tag operations fail due to handler bug
```

### 5. File Conversion Flow (Independent)

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant FileSystem

    Client->>MCP_Server: convert_xml_to_json(xml_file_path)
    MCP_Server->>FileSystem: Check if XML file exists
    FileSystem-->>MCP_Server: File not found ❌
    MCP_Server-->>Client: {success: false, error: "XML file not found"}
    
    Note over Client,FileSystem: With valid file:
    
    Client->>MCP_Server: convert_xml_to_json(valid_xml_path)
    MCP_Server->>FileSystem: Read XML file
    FileSystem-->>MCP_Server: XML content
    MCP_Server->>MCP_Server: Convert XML to JSON
    MCP_Server->>FileSystem: Write JSON file
    MCP_Server-->>Client: {success: true, output_path}
```

### 6. PLC Tag Conversion Flow (New)

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant PLCTagConverter
    participant FileSystem

    Client->>MCP_Server: convert_plc_tag_xml_to_excel(xml_file_path)
    MCP_Server->>PLCTagConverter: Parse PLC tag XML
    PLCTagConverter->>FileSystem: Read XML file
    FileSystem-->>PLCTagConverter: XML content
    PLCTagConverter->>PLCTagConverter: Extract Variables, User Constants, System Constants
    PLCTagConverter->>FileSystem: Create Excel with multiple sheets
    FileSystem-->>PLCTagConverter: Excel file created
    PLCTagConverter-->>MCP_Server: Conversion successful
    MCP_Server-->>Client: {success: true, output_file}
    
    Note over Client,FileSystem: Reverse conversion:
    
    Client->>MCP_Server: convert_excel_to_plc_tag_xml(excel_file_path)
    MCP_Server->>PLCTagConverter: Parse Excel sheets
    PLCTagConverter->>PLCTagConverter: Process Variables and Constants
    PLCTagConverter->>FileSystem: Generate TIA Portal XML
    PLCTagConverter-->>MCP_Server: XML created
    MCP_Server-->>Client: {success: true, output_file}
```

### 7. UDT Conversion Flow (New)

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant UDTConverter
    participant FileSystem

    Client->>MCP_Server: convert_udt_xml_to_udt(xml_file_path)
    MCP_Server->>UDTConverter: Parse UDT XML
    UDTConverter->>FileSystem: Read XML file
    FileSystem-->>UDTConverter: XML content
    UDTConverter->>UDTConverter: Extract UDT structure, members, comments
    UDTConverter->>FileSystem: Generate .udt SCL format
    FileSystem-->>UDTConverter: .udt file created
    UDTConverter-->>MCP_Server: Conversion successful
    MCP_Server-->>Client: {success: true, output_file}
    
    Note over Client,FileSystem: Reverse conversion:
    
    Client->>MCP_Server: convert_udt_to_xml(udt_file_path)
    MCP_Server->>UDTConverter: Parse .udt file
    UDTConverter->>UDTConverter: Parse SCL structure and comments
    UDTConverter->>FileSystem: Generate TIA Portal XML
    UDTConverter-->>MCP_Server: XML created
    MCP_Server-->>Client: {success: true, output_file}
```

## Error Flow Diagrams

### 1. Invalid Session Error

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    
    Client->>MCP_Server: get_project_info("invalid_session")
    MCP_Server->>MCP_Server: Validate session
    MCP_Server-->>Client: {success: false, error: "Invalid session"}
    
    Client->>MCP_Server: list_blocks("invalid_session")
    MCP_Server->>MCP_Server: Validate session
    MCP_Server-->>Client: {success: false, error: "Invalid session"}
```

### 2. No Project Open Error

```mermaid
sequenceDiagram
    participant Client
    participant MCP_Server
    participant TIA_Portal
    
    Client->>MCP_Server: create_session()
    MCP_Server-->>Client: {session_id}
    
    Note over Client,TIA_Portal: Skip open_project step
    
    Client->>MCP_Server: list_blocks(session_id)
    MCP_Server->>TIA_Portal: Check project status
    TIA_Portal-->>MCP_Server: No project open
    MCP_Server-->>Client: {success: false, error: "No project is open"}
    
    Client->>MCP_Server: compile_project(session_id)
    MCP_Server->>TIA_Portal: Check project status
    TIA_Portal-->>MCP_Server: No project open  
    MCP_Server-->>Client: {success: false, error: "No project is open"}
```

## Method Success/Failure Matrix

| Method | No Session | Invalid Session | Session Only | Session + Project | Notes |
|--------|-----------|-----------------|--------------|------------------|-------|
| `list_sessions` | ✅ | ✅ | ✅ | ✅ | Always works |
| `create_session` | ✅ | ✅ | ✅ | ✅ | Always works |
| `close_session` | ❌ | ❌ | ✅ | ✅ | Needs valid session |
| `open_project` | ❌ | ❌ | ✅ | ✅ | Needs valid session + path |
| `close_project` | ❌ | ❌ | ✅ | ✅ | Works even without project |
| `get_project_info` | ❌ | ❌ | ❌ | ❓ | Needs open project |
| `save_project` | ❌ | ❌ | ❌ | ❓ | Needs open project |
| `list_blocks` | ❌ | ❌ | ❌ | ✅ | Needs open project |
| `export_blocks` | ❌ | ❌ | ❌ | ✅ | Needs open project + blocks |
| `compile_project` | ❌ | ❌ | ❌ | ✅ | Needs open project |
| `get_compilation_errors` | ❌ | ❌ | ❌ | ✅ | Needs open project |
| `list_tag_tables` | ❌ | ❌ | ❌ | ❌ | Handler bug |
| File conversions | ✅* | ✅* | ✅* | ✅* | *Needs valid file paths |
| PLC tag conversions | ✅* | ✅* | ✅* | ✅* | *Needs valid XML/Excel files |
| UDT conversions | ✅* | ✅* | ✅* | ✅* | *Needs valid XML/.udt files |

## Critical Call Sequences

### ✅ Working Sequences

1. **Basic Session Management**:
   ```
   create_session() → list_sessions() → close_session()
   ```

2. **Project Access**:
   ```
   create_session() → open_project() → close_project()
   ```

3. **Block Operations**:
   ```
   create_session() → open_project() → list_blocks() → export_blocks()
   ```

4. **Compilation Workflow**:
   ```
   create_session() → open_project() → compile_project() → get_compilation_errors()
   ```

### ❌ Failing Sequences

1. **Skip Session Creation**:
   ```
   list_blocks() ❌ → Error: Invalid session
   ```

2. **Skip Project Opening**:
   ```
   create_session() → list_blocks() ❌ → Error: No project open
   ```

3. **Tag Operations** (due to implementation bug):
   ```
   create_session() → open_project() → list_tag_tables() ❌ → Handler error
   ```

## Dependency Chain Summary

```
Level 0 (Independent)
├── list_sessions
├── create_session  
└── convert_* (with valid files)
    ├── PLC tag conversions (XML ↔ Excel)
    └── UDT conversions (XML ↔ .udt)

Level 1 (Requires Session)
├── create_session ──┐
│                   └── open_project
│                   └── close_project  
│                   └── close_session

Level 2 (Requires Session + Project)  
├── create_session ──┐
│                   └── open_project ──┐
│                                     ├── get_project_info
│                                     ├── save_project
│                                     ├── list_blocks
│                                     ├── compile_project
│                                     └── get_compilation_errors

Level 3 (Requires Session + Project + Data)
├── create_session ──┐
│                   └── open_project ──┐
│                                     └── list_blocks ──┐
│                                                       └── export_blocks
```

**Key Finding**: The dependency chain is linear - each level builds on the previous one, and breaking any link in the chain causes all downstream methods to fail with predictable error messages.