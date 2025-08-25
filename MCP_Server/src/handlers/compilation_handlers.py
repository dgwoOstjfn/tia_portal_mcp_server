"""
Compilation operation handlers for TIA Portal MCP Server
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Use MCP configuration for imports
try:
    from ..mcp_config import get_mcp_config
    mcp_config = get_mcp_config()
    # Paths are already set up by mcp_config
except ImportError:
    # Fallback for development
    base_dir = Path(__file__).parent.parent.parent.parent
    tia_client_path = base_dir / "99_TIA_Client"
    if tia_client_path.exists():
        sys.path.insert(0, str(tia_client_path))

logger = logging.getLogger(__name__)


class CompilationHandlers:
    """Handles compilation-related operations for MCP server"""
    
    @staticmethod
    async def compile_project(session) -> Dict[str, Any]:
        """Compile the entire project
        
        Args:
            session: TIA session object
            
        Returns:
            Operation result with compilation details
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        try:
            def _compile_project():
                """Execute project compilation"""
                print("Starting project compilation...")
                
                # Use the project's compile method
                result = session.client_wrapper.project.compile()
                
                # Check if compilation was successful
                if result is True:
                    print("Project compilation completed successfully")
                    return True
                elif result is False:
                    print("Project compilation completed with warnings/errors")
                    return False
                else:
                    # Handle string result or other return types
                    print(f"Project compilation result: {result}")
                    return result
            
            compile_result = await session.client_wrapper.execute_sync(_compile_project)
            
            # Mark project as potentially modified
            session.project_modified = True
            
            return {
                "success": True,
                "compilation_result": compile_result,
                "message": "Project compilation completed" if compile_result else "Project compilation completed with issues"
            }
            
        except Exception as e:
            logger.error(f"Project compilation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def compile_device(session, device_name: Optional[str] = None) -> Dict[str, Any]:
        """Compile a specific device
        
        Args:
            session: TIA session object
            device_name: Name of device to compile (None for first device)
            
        Returns:
            Operation result with compilation details
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        try:
            def _compile_device():
                """Execute device compilation"""
                print(f"Starting device compilation for: {device_name or 'first device'}")
                
                # Get PLCs from project
                plcs = session.client_wrapper.project.get_plcs()
                
                if not plcs or len(plcs) == 0:
                    raise ValueError("No PLCs found in project")
                
                # Find target PLC
                target_plc = None
                if device_name:
                    for plc in plcs:
                        if hasattr(plc, 'name') and plc.name == device_name:
                            target_plc = plc
                            break
                    if not target_plc:
                        raise ValueError(f"PLC '{device_name}' not found")
                else:
                    # Use first PLC
                    target_plc = plcs[0]
                
                print(f"Compiling PLC: {target_plc.name if hasattr(target_plc, 'name') else 'Unknown'}")
                
                # Get PLC software and compile it
                plc_software = target_plc.get_software()
                if hasattr(plc_software, 'compile'):
                    result = plc_software.compile()
                    print(f"PLC software compilation result: {result}")
                    return result
                else:
                    print("PLC software does not support compilation")
                    return False
            
            compile_result = await session.client_wrapper.execute_sync(_compile_device)
            
            return {
                "success": True,
                "compilation_result": compile_result,
                "device_name": device_name,
                "message": f"Device compilation completed for {device_name or 'first device'}"
            }
            
        except Exception as e:
            logger.error(f"Device compilation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def compile_block(session, block_name: str) -> Dict[str, Any]:
        """Compile a specific block
        
        Args:
            session: TIA session object
            block_name: Name of block to compile
            
        Returns:
            Operation result with compilation details
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        try:
            def _compile_block():
                """Execute block compilation"""
                print(f"Starting block compilation for: {block_name}")
                
                # Get PLCs from project
                plcs = session.client_wrapper.project.get_plcs()
                
                if not plcs or len(plcs) == 0:
                    raise ValueError("No PLCs found in project")
                
                # Search for the block in all PLCs
                target_block = None
                plc_software = None
                
                for plc in plcs:
                    software = plc.get_software()
                    
                    # Search in different block collections
                    collections_to_search = []
                    
                    # Add root blocks
                    if hasattr(software, 'get_blocks'):
                        collections_to_search.append(software.get_blocks())
                    
                    # Add user groups
                    if hasattr(software, 'get_user_block_groups'):
                        user_groups = software.get_user_block_groups()
                        collections_to_search.extend(_get_block_collections_from_groups(user_groups))
                    
                    # Search in all collections
                    for collection in collections_to_search:
                        if collection:
                            block = _find_block_in_collection(collection, block_name)
                            if block:
                                target_block = block
                                plc_software = software
                                break
                    
                    if target_block:
                        break
                
                if not target_block:
                    raise ValueError(f"Block '{block_name}' not found in project")
                
                print(f"Found block '{block_name}', attempting compilation...")
                
                # Try to compile the block
                if hasattr(target_block, 'compile'):
                    result = target_block.compile()
                    print(f"Block compilation result: {result}")
                    return result
                else:
                    # Try compiling the entire PLC software containing the block
                    print(f"Block does not support direct compilation, compiling PLC software...")
                    if hasattr(plc_software, 'compile'):
                        result = plc_software.compile()
                        print(f"PLC software compilation result: {result}")
                        return result
                    else:
                        print("Neither block nor PLC software supports compilation")
                        return False
            
            def _get_block_collections_from_groups(groups):
                """Recursively get block collections from groups"""
                collections = []
                for group in groups:
                    if hasattr(group, 'get_blocks'):
                        collections.append(group.get_blocks())
                    if hasattr(group, 'get_groups'):
                        collections.extend(_get_block_collections_from_groups(group.get_groups()))
                return collections
            
            def _find_block_in_collection(collection, name):
                """Find block by name in collection"""
                try:
                    if hasattr(collection, 'find'):
                        found = collection.find(name)
                        if found and hasattr(found, 'value'):
                            return found.value
                    
                    # Alternative: iterate through collection
                    for block in collection:
                        if hasattr(block, 'name') and block.name == name:
                            return block
                            
                except Exception as e:
                    print(f"Error searching in collection: {e}")
                
                return None
            
            compile_result = await session.client_wrapper.execute_sync(_compile_block)
            
            return {
                "success": True,
                "compilation_result": compile_result,
                "block_name": block_name,
                "message": f"Block compilation completed for '{block_name}'"
            }
            
        except Exception as e:
            logger.error(f"Block compilation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_compilation_errors(session) -> Dict[str, Any]:
        """Get compilation errors and warnings from the project
        
        Args:
            session: TIA session object
            
        Returns:
            Operation result with error details
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        try:
            def _get_errors():
                """Get compilation errors"""
                print("Retrieving compilation errors and warnings...")
                
                errors = []
                warnings = []
                
                # Try to get compilation info from project
                if hasattr(session.client_wrapper.project, 'get_compilation_info'):
                    info = session.client_wrapper.project.get_compilation_info()
                    if info:
                        if hasattr(info, 'errors'):
                            errors = info.errors
                        if hasattr(info, 'warnings'):
                            warnings = info.warnings
                
                # Alternative: check PLCs for compilation status
                plcs = session.client_wrapper.project.get_plcs()
                device_status = []
                
                for plc in plcs:
                    device_info = {
                        "name": plc.name if hasattr(plc, 'name') else "Unknown",
                        "status": "Unknown"
                    }
                    
                    # Try to get software compilation status
                    try:
                        plc_software = plc.get_software()
                        if hasattr(plc_software, 'get_compilation_status'):
                            status = plc_software.get_compilation_status()
                            device_info["status"] = str(status)
                        else:
                            device_info["status"] = "Status check not supported"
                    except Exception as e:
                        device_info["status"] = f"Status check failed: {str(e)}"
                    
                    device_status.append(device_info)
                
                return {
                    "errors": errors,
                    "warnings": warnings,
                    "device_status": device_status
                }
            
            result = await session.client_wrapper.execute_sync(_get_errors)
            
            return {
                "success": True,
                "compilation_info": result,
                "error_count": len(result.get("errors", [])),
                "warning_count": len(result.get("warnings", []))
            }
            
        except Exception as e:
            logger.error(f"Get compilation errors failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }