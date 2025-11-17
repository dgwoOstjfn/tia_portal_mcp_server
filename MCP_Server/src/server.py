"""
TIA Portal MCP Server
Main server implementation
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import anyio

# Add MCP imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.lowlevel.server import NotificationOptions
    import mcp.types as types
except ImportError:
    # Use mock for testing
    # print("Warning: MCP package not installed. Using mock for testing.")  # Commented out - interferes with MCP protocol
    from mcp_mock import Server, InitializationOptions, NotificationOptions, types

# Import local modules
from mcp_config import get_mcp_config
from config import get_config  # Keep for backward compatibility
from session.session_manager import SessionManager
from tia_client_wrapper import TIAClientWrapper
from handlers.block_handlers import BlockHandlers
from handlers.compilation_handlers import CompilationHandlers
from handlers.conversion_handlers import ConversionHandlers
from handlers.tag_handlers import TagHandlers
from handlers.udt_handlers import UDTHandlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TIAPortalMCPServer:
    """MCP Server for TIA Portal operations"""
    
    def __init__(self):
        """Initialize the TIA Portal MCP Server"""
        self.name = "tia-portal-server"
        self.version = "1.0.0"
        
        # Initialize components
        try:
            # Try new MCP configuration first
            self.mcp_config = get_mcp_config()
            self.config = None  # Legacy config is optional now
        except Exception as e:
            logger.warning(f"Could not load MCP config, using legacy: {e}")
            self.config = get_config()
            self.mcp_config = None
            
        self.session_manager = SessionManager()
        self.conversion_handlers = ConversionHandlers()
        
        # Initialize MCP server
        self.server = Server(self.name, version=self.version)
        
        # Register handlers
        self._register_handlers()
        
        logger.info(f"Initialized {self.name} v{self.version}")
    
    def _register_handlers(self):
        """Register all MCP handlers"""
        # Register initialization handler
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools"""
            return [
                types.Tool(
                    name="open_project",
                    description="Open a TIA Portal project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "Path to project file or directory"
                            },
                            "project_name": {
                                "type": "string", 
                                "description": "Project name (optional if path is to .ap* file)"
                            },
                            "session_id": {
                                "type": "string",
                                "description": "Session ID (optional, creates new if not provided)"
                            }
                        },
                        "required": ["project_path"]
                    }
                ),
                types.Tool(
                    name="save_project",
                    description="Save the current project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="close_project",
                    description="Close the current project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="get_project_info",
                    description="Get information about the current project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="create_session",
                    description="Create a new TIA Portal session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "metadata": {
                                "type": "object",
                                "description": "Optional session metadata"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="close_session",
                    description="Close a TIA Portal session",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID to close"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="list_sessions",
                    description="List all active sessions",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="import_blocks",
                    description="Import blocks from XML files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "xml_paths": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of XML file paths to import"
                            },
                            "target_folder": {
                                "type": "string",
                                "description": "Target folder in PLC software (optional)"
                            },
                            "preserve_structure": {
                                "type": "boolean",
                                "description": "Preserve folder structure from XML path",
                                "default": True
                            },
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["xml_paths", "session_id"]
                    }
                ),
                types.Tool(
                    name="export_blocks",
                    description="Export blocks to XML files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "block_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of block names to export (empty for all)"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Output directory path",
                                "default": "./exports"
                            },
                            "export_all": {
                                "type": "boolean",
                                "description": "Export all blocks",
                                "default": False
                            },
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="list_blocks",
                    description="List all blocks in the current project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="compile_project",
                    description="Compile the entire project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="compile_device",
                    description="Compile a specific device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "device_name": {
                                "type": "string",
                                "description": "Name of device to compile (optional, uses first device if not provided)"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="compile_block",
                    description="Compile a specific block",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "block_name": {
                                "type": "string",
                                "description": "Name of block to compile"
                            }
                        },
                        "required": ["session_id", "block_name"]
                    }
                ),
                types.Tool(
                    name="get_compilation_errors",
                    description="Get compilation errors and warnings from the project",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                # File conversion tools
                types.Tool(
                    name="convert_xml_to_json",
                    description="Convert XML file to JSON format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "xml_file_path": {
                                "type": "string",
                                "description": "Path to input XML file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for output JSON file (optional)"
                            }
                        },
                        "required": ["xml_file_path"]
                    }
                ),
                types.Tool(
                    name="convert_json_to_xml",
                    description="Convert JSON file to XML format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "json_file_path": {
                                "type": "string",
                                "description": "Path to input JSON file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for output XML file (optional)"
                            }
                        },
                        "required": ["json_file_path"]
                    }
                ),
                types.Tool(
                    name="convert_json_to_scl",
                    description="Convert JSON file to SCL format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "json_file_path": {
                                "type": "string",
                                "description": "Path to input JSON file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for output SCL file (optional)"
                            }
                        },
                        "required": ["json_file_path"]
                    }
                ),
                types.Tool(
                    name="convert_scl_to_json",
                    description="Convert SCL file to JSON format",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "scl_file_path": {
                                "type": "string",
                                "description": "Path to input SCL file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for output JSON file (optional)"
                            }
                        },
                        "required": ["scl_file_path"]
                    }
                ),
                types.Tool(
                    name="convert_xml_to_scl",
                    description="Convert XML file to SCL format (via JSON)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "xml_file_path": {
                                "type": "string",
                                "description": "Path to input XML file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for output SCL file (optional)"
                            },
                            "temp_dir": {
                                "type": "string",
                                "description": "Directory for temporary files (optional)"
                            }
                        },
                        "required": ["xml_file_path"]
                    }
                ),
                types.Tool(
                    name="convert_scl_to_xml",
                    description="Convert SCL file to XML format (via JSON)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "scl_file_path": {
                                "type": "string",
                                "description": "Path to input SCL file"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Path for output XML file (optional)"
                            },
                            "temp_dir": {
                                "type": "string",
                                "description": "Directory for temporary files (optional)"
                            }
                        },
                        "required": ["scl_file_path"]
                    }
                ),
                # PLC Tag Tools
                types.Tool(
                    name="export_all_tag_tables",
                    description="Export all PLC tag tables to XML files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Output directory path",
                                "default": "./exports"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="export_specific_tag_tables",
                    description="Export specific PLC tag tables to XML files",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "table_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of tag table names to export"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Output directory path",
                                "default": "./exports"
                            }
                        },
                        "required": ["session_id", "table_names"]
                    }
                ),
                types.Tool(
                    name="list_tag_tables",
                    description="List all available PLC tag tables",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="get_tag_table_details",
                    description="Get detailed information about a specific tag table including individual tags",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "table_name": {
                                "type": "string",
                                "description": "Name of the tag table"
                            }
                        },
                        "required": ["session_id", "table_name"]
                    }
                ),
                # UDT Tools
                types.Tool(
                    name="discover_all_udts",
                    description="Discover all UDTs in the project using recursive nested group exploration",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="export_all_udts",
                    description="Export all UDTs to XML files maintaining folder structure",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Base output directory",
                                "default": "./exports"
                            },
                            "export_all": {
                                "type": "boolean",
                                "description": "Whether to export all UDTs or only exportable ones",
                                "default": False
                            }
                        },
                        "required": ["session_id"]
                    }
                ),
                types.Tool(
                    name="export_specific_udts",
                    description="Export specific UDTs by name",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "udt_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of UDT names to export"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Output directory",
                                "default": "./exports"
                            }
                        },
                        "required": ["session_id", "udt_names"]
                    }
                ),
                types.Tool(
                    name="generate_udt_source",
                    description="Generate SCL source code from UDTs",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "session_id": {
                                "type": "string",
                                "description": "Session ID"
                            },
                            "udt_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of UDT names to generate source for"
                            },
                            "output_path": {
                                "type": "string",
                                "description": "Output SCL file path"
                            },
                            "with_dependencies": {
                                "type": "boolean",
                                "description": "Whether to include dependencies",
                                "default": True
                            }
                        },
                        "required": ["session_id", "udt_names", "output_path"]
                    }
                )
            ]
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """List available resources"""
            return [
                types.Resource(
                    uri="tia://config",
                    name="Server Configuration",
                    description="Current server configuration",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri="tia://test-projects",
                    name="Test Projects",
                    description="Available test projects",
                    mimeType="application/json"
                )
            ]
        
        # Tool handlers
        @self.server.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: Optional[Dict[str, Any]] = None
        ) -> List[types.TextContent]:
            """Handle tool calls"""
            try:
                result = await self._execute_tool(name, arguments or {})
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                return [types.TextContent(
                    type="text", 
                    text=json.dumps({
                        "success": False,
                        "error": str(e)
                    }, indent=2)
                )]
        
        # Resource handlers
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Handle resource reads"""
            if uri == "tia://config":
                return json.dumps({
                    "server_version": self.version,
                    "project_store_path": self.config.project_store_path,
                    "master_prg_name": self.config.master_prg_name,
                    "test_prg_name": self.config.test_prg_name,
                    "session_timeout": self.session_manager.timeout_seconds,
                    "max_sessions": self.session_manager.max_sessions
                }, indent=2)
            
            elif uri == "tia://test-projects":
                return json.dumps({
                    "test_projects": [
                        {
                            "name": "Test_v17_openness",
                            "path": str(self.config.test_project_1),
                            "exists": self.config.test_project_1.exists()
                        },
                        {
                            "name": "NAME_2", 
                            "path": str(self.config.test_project_2),
                            "exists": self.config.test_project_2.exists()
                        }
                    ],
                    "test_blocks": {
                        "path": str(self.config.test_blocks_dir),
                        "exists": self.config.test_blocks_dir.exists(),
                        "blocks": list(self.config.test_blocks_dir.glob("**/*.xml")) if self.config.test_blocks_dir.exists() else []
                    }
                }, indent=2)
            
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool with given arguments"""
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")
        
        # Session management tools
        if tool_name == "create_session":
            session = await self.session_manager.create_session(
                metadata=arguments.get("metadata")
            )
            return {
                "success": True,
                "session_id": session.session_id,
                "created_at": session.created_at
            }
        
        elif tool_name == "close_session":
            session_id = arguments["session_id"]
            result = await self.session_manager.close_session(session_id)
            return {
                "success": result,
                "message": "Session closed" if result else "Session not found"
            }
        
        elif tool_name == "list_sessions":
            sessions = await self.session_manager.list_sessions()
            return {
                "success": True,
                "sessions": sessions,
                "count": len(sessions)
            }
        
        # Project operation tools
        elif tool_name == "open_project":
            session_id = arguments.get("session_id")
            
            # Get or create session
            if session_id:
                session = await self.session_manager.get_session(session_id)
                if not session:
                    return {
                        "success": False,
                        "error": f"Session not found: {session_id}"
                    }
            else:
                session = await self.session_manager.create_session()
                session_id = session.session_id
            
            # Open project
            result = await session.client_wrapper.open_project(
                arguments["project_path"],
                arguments.get("project_name")
            )
            
            if result["success"]:
                session.current_project = result["project_name"]
                session.update_activity()
            
            result["session_id"] = session_id
            return result
        
        elif tool_name == "save_project":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await session.client_wrapper.save_project()
            if result["success"]:
                session.project_modified = False
                session.update_activity()
            
            return result
        
        elif tool_name == "close_project":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await session.client_wrapper.close_project()
            if result["success"]:
                session.current_project = None
                session.project_modified = False
                session.update_activity()
            
            return result
        
        elif tool_name == "get_project_info":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await session.client_wrapper.get_project_info()
            session.update_activity()
            
            return result
        
        # Block operation tools
        elif tool_name == "import_blocks":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await BlockHandlers.import_blocks(
                session,
                arguments["xml_paths"],
                arguments.get("target_folder"),
                arguments.get("preserve_structure", True)
            )
            session.update_activity()
            return result
        
        elif tool_name == "export_blocks":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await BlockHandlers.export_blocks(
                session,
                arguments.get("block_names"),
                arguments.get("output_path", "./exports"),
                arguments.get("export_all", False)
            )
            session.update_activity()
            return result
        
        elif tool_name == "list_blocks":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await BlockHandlers.list_blocks(session)
            session.update_activity()
            return result
        
        # Compilation operation tools
        elif tool_name == "compile_project":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await CompilationHandlers.compile_project(session)
            session.update_activity()
            return result
        
        elif tool_name == "compile_device":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await CompilationHandlers.compile_device(
                session,
                arguments.get("device_name")
            )
            session.update_activity()
            return result
        
        elif tool_name == "compile_block":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await CompilationHandlers.compile_block(
                session,
                arguments["block_name"]
            )
            session.update_activity()
            return result
        
        elif tool_name == "get_compilation_errors":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = await CompilationHandlers.get_compilation_errors(session)
            session.update_activity()
            return result
        
        # File conversion tools
        elif tool_name == "convert_xml_to_json":
            return self.conversion_handlers.convert_xml_to_json(
                arguments["xml_file_path"],
                arguments.get("output_path")
            )
        
        elif tool_name == "convert_json_to_xml":
            return self.conversion_handlers.convert_json_to_xml(
                arguments["json_file_path"],
                arguments.get("output_path")
            )
        
        elif tool_name == "convert_json_to_scl":
            return self.conversion_handlers.convert_json_to_scl(
                arguments["json_file_path"],
                arguments.get("output_path")
            )
        
        elif tool_name == "convert_scl_to_json":
            return self.conversion_handlers.convert_scl_to_json(
                arguments["scl_file_path"],
                arguments.get("output_path")
            )
        
        elif tool_name == "convert_xml_to_scl":
            return self.conversion_handlers.convert_xml_to_scl(
                arguments["xml_file_path"],
                arguments.get("output_path"),
                arguments.get("temp_dir")
            )
        
        elif tool_name == "convert_scl_to_xml":
            return self.conversion_handlers.convert_scl_to_xml(
                arguments["scl_file_path"],
                arguments.get("output_path"),
                arguments.get("temp_dir")
            )
        
        # PLC Tag operation tools
        elif tool_name == "export_all_tag_tables":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = TagHandlers.export_all_tag_tables(
                session,
                arguments.get("output_path", "./exports")
            )
            session.update_activity()
            return result
        
        elif tool_name == "export_specific_tag_tables":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = TagHandlers.export_specific_tag_tables(
                session,
                arguments["table_names"],
                arguments.get("output_path", "./exports")
            )
            session.update_activity()
            return result
        
        elif tool_name == "list_tag_tables":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = TagHandlers.list_tag_tables(session)
            session.update_activity()
            return result
        
        elif tool_name == "get_tag_table_details":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = TagHandlers.get_tag_table_details(
                session,
                arguments["table_name"]
            )
            session.update_activity()
            return result
        
        # UDT operation tools
        elif tool_name == "discover_all_udts":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = UDTHandlers.discover_all_udts(
                session.client_wrapper,
                arguments["session_id"]
            )
            session.update_activity()
            return result
        
        elif tool_name == "export_all_udts":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = UDTHandlers.export_all_udts(
                session.client_wrapper,
                arguments["session_id"],
                arguments.get("output_path", "./exports"),
                arguments.get("export_all", False)
            )
            session.update_activity()
            return result
        
        elif tool_name == "export_specific_udts":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = UDTHandlers.export_specific_udts(
                session.client_wrapper,
                arguments["session_id"],
                arguments["udt_names"],
                arguments.get("output_path", "./exports")
            )
            session.update_activity()
            return result
        
        elif tool_name == "generate_udt_source":
            session = await self.session_manager.get_session(arguments["session_id"])
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            result = UDTHandlers.generate_udt_source(
                session.client_wrapper,
                arguments["session_id"],
                arguments["udt_names"],
                arguments["output_path"],
                arguments.get("with_dependencies", True)
            )
            session.update_activity()
            return result
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def start(self):
        """Start the MCP server"""
        logger.info("Starting TIA Portal MCP Server...")

        # Start session manager
        await self.session_manager.start()

        # Use MCP's built-in stdio transport
        from mcp.server.stdio import stdio_server

        try:
            # Run server using stdio transport
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name=self.name,
                        server_version=self.version,
                        capabilities=self.server.get_capabilities(
                            NotificationOptions(),
                            {}
                        )
                    )
                )
        finally:
            # Ensure cleanup happens even if server.run() is interrupted
            await self.stop()

    async def stop(self):
        """Stop the MCP server and cleanup resources"""
        logger.info("Stopping TIA Portal MCP Server...")
        await self.session_manager.stop()

        # Note: COM resource cleanup delay is handled in TIAClientWrapper.disconnect()
        # No delay here to allow process to exit quickly during reconnects


async def test_server():
    """Test server initialization and basic operations"""
    print("\n=== Testing TIA Portal MCP Server ===\n")
    
    server = TIAPortalMCPServer()
    
    try:
        # Test tool listing  
        if hasattr(server.server, '_list_tools_handler'):
            tools = await server.server._list_tools_handler()
            print(f"Available tools: {len(tools)}")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
        
        # Test resource listing
        if hasattr(server.server, '_list_resources_handler'):
            resources = await server.server._list_resources_handler() 
            print(f"\nAvailable resources: {len(resources)}")
            for resource in resources:
                print(f"  - {resource.uri}: {resource.name}")
        
        # Test session creation
        print("\n\nTest 1: Create session")
        result = await server._execute_tool("create_session", {"metadata": {"test": True}})
        print(f"Result: {json.dumps(result, indent=2)}")
        session_id = result.get("session_id")
        
        # Test project open
        print("\nTest 2: Open test project")
        # Use MCP configuration if available
        if server.mcp_config:
            test_projects = server.mcp_config.get_test_projects()
            project_path = test_projects[0]["resolved_path"] if test_projects else "../Test_Material/Test_v17_openness/Test_v17_openness.ap17"
        else:
            project_path = str(server.config.test_project_1)
            
        result = await server._execute_tool("open_project", {
            "project_path": project_path,
            "session_id": session_id
        })
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Test project info
        print("\nTest 3: Get project info")
        result = await server._execute_tool("get_project_info", {
            "session_id": session_id
        })
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Test session listing
        print("\nTest 4: List sessions")
        result = await server._execute_tool("list_sessions", {})
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Cleanup
        print("\nTest 5: Close session")
        result = await server._execute_tool("close_session", {
            "session_id": session_id
        })
        print(f"Result: {json.dumps(result, indent=2)}")
        
        print("\n[OK] All tests passed!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await server.session_manager.stop()


def main():
    """Main entry point for the MCP server"""
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Run tests
        asyncio.run(test_server())
    else:
        # Run server
        server = TIAPortalMCPServer()
        try:
            asyncio.run(server.start())
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            import traceback
            traceback.print_exc()
        # Note: cleanup is handled in start() method's finally block


if __name__ == "__main__":
    main()