"""
Block operation handlers for TIA Portal MCP Server
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Setup paths for imports
base_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(base_dir / "lib" / "converters"))
sys.path.insert(0, str(base_dir / "lib"))

# Import block operation modules
try:
    from BlockImport import import_block_from_xml
    from BlockExport import export_block_to_xml, export_all_blocks, clean_exported_blocks_folder
except ImportError as e:
    import logging
    logging.getLogger(__name__).error(f"Error importing block operation modules: {e}")
    raise

logger = logging.getLogger(__name__)


def _sanitize_folder_name(folder_name):
    """Sanitize folder name by removing invalid characters for file system"""
    if not folder_name:
        return folder_name
    
    # Replace invalid characters with underscores
    invalid_chars = '<>:"|?*'
    sanitized = folder_name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Replace quotes with underscore
    sanitized = sanitized.replace('"', '_').replace("'", '_')
    
    # Trim leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    return sanitized


def _collect_all_blocks_recursive(groups, block_list, parent_path="/", parent_folder=None):
    """Recursively collect all blocks from groups with full path information"""
    for group in groups:
        group_path = f"{parent_path}{group.name}/"
        
        # Get blocks in this group
        if hasattr(group, 'get_blocks'):
            blocks = group.get_blocks()
            for block in blocks:
                # Determine folder structure - only use the direct parent folder
                folder_parts = group_path.strip('/').split('/')
                folder_name = _sanitize_folder_name(folder_parts[0]) if len(folder_parts) > 0 else None
                
                # For export, we need to handle nested folders differently
                # Store the full sanitized path for direct export
                sanitized_path_parts = [_sanitize_folder_name(part) for part in folder_parts]
                export_path = '/'.join(sanitized_path_parts)
                
                block_list.append({
                    "name": block.name if hasattr(block, 'name') else "Unknown",
                    "type": block.type if hasattr(block, 'type') else "Unknown",
                    "path": group_path,
                    "folder_name": folder_name,
                    "subfolder_name": None,  # We'll handle this in export
                    "export_path": export_path,
                    "full_path_parts": sanitized_path_parts,
                    "block_object": block
                })
        
        # Recurse into subgroups
        if hasattr(group, 'get_groups'):
            subgroups = group.get_groups()
            _collect_all_blocks_recursive(subgroups, block_list, group_path, group.name)


def _get_all_blocks_comprehensive(plc_software):
    """Get all blocks from the PLC software with complete folder information"""
    all_blocks = []
    
    # First, get blocks from the root folder
    if hasattr(plc_software, 'get_blocks'):
        blocks = plc_software.get_blocks()
        if blocks and hasattr(blocks, "value") and blocks.value is not None:
            for block in blocks:
                # Skip system blocks if needed
                if hasattr(block, 'name') and not block.name.startswith("_"):
                    all_blocks.append({
                        "name": block.name,
                        "type": getattr(block, 'type', 'Unknown'),
                        "path": "/",
                        "folder_name": None,
                        "subfolder_name": None,
                        "export_path": "",  # Root level - no subpath
                        "full_path_parts": [],
                        "block_object": block
                    })
    
    # Then, get blocks from user block groups
    if hasattr(plc_software, 'get_user_block_groups'):
        user_groups = plc_software.get_user_block_groups()
        if user_groups and hasattr(user_groups, "value") and user_groups.value is not None:
            _collect_all_blocks_recursive(user_groups, all_blocks)
    
    return all_blocks


def _ensure_folder_exists(plc_software, folder_name, subfolder_name=None):
    """Ensure target folder exists, create if needed
    
    Args:
        plc_software: TIA Portal software instance
        folder_name: Main folder name
        subfolder_name: Optional subfolder name
        
    Returns:
        bool: True if folder exists or was created successfully
    """
    try:
        # Get user block groups
        user_groups = plc_software.get_user_block_groups()
        
        # Check if main folder exists
        user_group = user_groups.find(folder_name)
        if not user_group or not user_group.value:
            # Create main folder
            logger.info(f"Creating folder '{folder_name}'...")
            try:
                new_group = user_groups.create(folder_name)
                if not new_group:
                    logger.error(f"Failed to create folder '{folder_name}'")
                    return False
                logger.info(f"Successfully created folder '{folder_name}'")
                user_group = new_group
            except Exception as e:
                logger.error(f"Error creating folder '{folder_name}': {str(e)}")
                return False

        # If subfolder specified, check/create it
        if subfolder_name:
            try:
                parent_groups = user_group.get_groups()
                sub_group = parent_groups.find(subfolder_name)
                if not sub_group or not sub_group.value:
                    # Create subfolder
                    logger.info(f"Creating subfolder '{subfolder_name}' in '{folder_name}'...")
                    try:
                        new_sub_group = parent_groups.create(subfolder_name)
                        if not new_sub_group:
                            logger.error(f"Failed to create subfolder '{subfolder_name}'")
                            return False
                        logger.info(f"Successfully created subfolder '{subfolder_name}'")
                    except Exception as e:
                        logger.error(f"Error creating subfolder '{subfolder_name}': {str(e)}")
                        return False
            except Exception as e:
                logger.error(f"Error accessing parent folder '{folder_name}': {str(e)}")
                return False

        return True

    except Exception as e:
        logger.error(f"Error ensuring folder exists: {str(e)}")
        return False


def _export_block_direct(plc_software, block_info, export_base_path):
    """Export a single block directly to its target location"""
    try:
        # Create the target directory path
        if block_info.get('export_path'):
            # Use the sanitized export path
            target_dir = os.path.join(export_base_path, block_info['export_path'])
        else:
            # Root level block
            target_dir = export_base_path

        # Ensure directory exists
        os.makedirs(target_dir, exist_ok=True)

        # Create the export file path
        export_file_path = os.path.join(target_dir, f"{block_info['name']}.xml")

        # Get the block object and export it
        block = block_info['block_object']

        logger.debug(f"Exporting block '{block_info['name']}' to {export_file_path}")

        # Clean up any existing temporary file before export
        # TIA Portal API exports to ~/.tia_portal/exported_blocks/ and fails if file exists
        temp_export_path = os.path.join(os.path.expanduser("~"), ".tia_portal", "exported_blocks", f"{block_info['name']}.xml")
        if os.path.exists(temp_export_path):
            try:
                os.remove(temp_export_path)
                logger.debug(f"Removed existing temp file: {temp_export_path}")
            except Exception as e:
                logger.warning(f"Could not remove temp file {temp_export_path}: {e}")

        # Export the block using the TIA Portal API
        exported_file = block.export()
        
        # Move the file from the temporary location to our target location
        if os.path.exists(exported_file):
            # Create the directory structure if it doesn't exist
            os.makedirs(os.path.dirname(export_file_path), exist_ok=True)
            
            # If the file already exists at the target location, remove it
            if os.path.exists(export_file_path):
                os.remove(export_file_path)
                
            # Move the file from the temporary location to our desired location
            import shutil
            shutil.copyfile(exported_file, export_file_path)
            
            logger.info(f"Successfully exported block '{block_info['name']}' to {export_file_path}")
            return export_file_path
        else:
            logger.error(f"Export failed: Exported file not found at {exported_file}")
            return None
            
    except Exception as e:
        logger.error(f"Error exporting block '{block_info['name']}': {str(e)}")
        return None


def _export_all_blocks_comprehensive(plc_software, export_base_path):
    """Export all blocks using comprehensive traversal logic"""
    export_count = 0
    errors = []
    
    try:
        # Clean up temporary export files before starting
        try:
            clean_exported_blocks_folder()
            logger.info("Cleaned temporary export files")
        except Exception as e:
            logger.warning(f"Could not clean temporary files: {e}")
        
        # Get all blocks with their complete folder information
        all_blocks = _get_all_blocks_comprehensive(plc_software)
        
        logger.info(f"Found {len(all_blocks)} blocks to export")
        
        # Export each block
        for block_info in all_blocks:
            try:
                # Use direct export method that handles paths properly
                export_result = _export_block_direct(plc_software, block_info, export_base_path)
                
                if export_result:
                    export_count += 1
                    logger.info(f"Exported block '{block_info['name']}' from path '{block_info['path']}'")
                else:
                    errors.append(f"Failed to export block '{block_info['name']}'")
                    
            except Exception as e:
                error_msg = f"Error exporting block '{block_info['name']}': {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Export completed: {export_count} blocks exported, {len(errors)} errors")
        
        # Log summary of errors (not all details to avoid spam)
        if errors:
            logger.warning(f"Total export errors: {len(errors)}")
            # Log first few errors as examples
            for error in errors[:5]:
                logger.error(error)
            if len(errors) > 5:
                logger.warning(f"... and {len(errors) - 5} more errors")
            
        return export_count
        
    except Exception as e:
        logger.error(f"Error in comprehensive export: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        return 0


class BlockHandlers:
    """Handles block-related operations for MCP server"""
    
    @staticmethod
    async def import_blocks(
        session, 
        xml_paths: List[str],
        target_folder: Optional[str] = None,
        preserve_structure: bool = True
    ) -> Dict[str, Any]:
        """Import blocks from XML files
        
        Args:
            session: TIA session object
            xml_paths: List of XML file paths to import
            target_folder: Target folder in PLC software
            preserve_structure: Whether to preserve folder structure from XML path
            
        Returns:
            Operation result with imported block details
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        imported_blocks = []
        errors = []
        
        try:
            # Get PLC software
            def _get_plc_software():
                # Get PLCs from project
                plcs = session.client_wrapper.project.get_plcs()
                
                if not plcs or len(plcs) == 0:
                    raise ValueError("No PLCs found in project")
                
                # Use first PLC
                plc = plcs[0]
                return plc.get_software()
            
            # Execute in sync context
            plc_software = await session.client_wrapper.execute_sync(_get_plc_software)
            
            # Import each block
            for xml_path in xml_paths:
                path = Path(xml_path)
                if not path.exists():
                    errors.append({
                        "path": xml_path,
                        "error": "File not found"
                    })
                    continue
                
                try:
                    # Determine folder structure
                    folder_name = target_folder
                    subfolder_name = None
                    
                    if preserve_structure and path.parent.name != "exported_blocks":
                        # Use parent folder name as subfolder, but avoid duplication
                        parent_folder_name = path.parent.name
                        if target_folder and parent_folder_name == target_folder:
                            # Avoid duplication: target folder already matches parent folder
                            subfolder_name = None
                        else:
                            subfolder_name = parent_folder_name
                    
                    # Import block
                    def _import_block():
                        # First, ensure the target folder exists if specified
                        if folder_name:
                            folder_success = _ensure_folder_exists(plc_software, folder_name, subfolder_name)
                            if not folder_success:
                                return {"success": False, "error": f"Failed to create/access folder '{folder_name}'", "block_name": None}

                        result = import_block_from_xml(
                            plc_software,
                            str(path),
                            folder_name=folder_name,
                            subfolder_name=subfolder_name
                        )
                        return result

                    import_result = await session.client_wrapper.execute_sync(_import_block)

                    # Handle both dict (new) and bool (legacy) return types
                    if isinstance(import_result, dict):
                        if import_result.get("success"):
                            imported_blocks.append({
                                "path": xml_path,
                                "block_name": import_result.get("block_name", path.stem),
                                "folder": folder_name,
                                "subfolder": subfolder_name
                            })
                            logger.info(f"Imported block from {xml_path}")
                        else:
                            errors.append({
                                "path": xml_path,
                                "error": import_result.get("error", "Import failed with unknown error")
                            })
                            logger.error(f"Failed to import {xml_path}: {import_result.get('error')}")
                    elif import_result:  # Legacy bool True
                        imported_blocks.append({
                            "path": xml_path,
                            "block_name": path.stem,
                            "folder": folder_name,
                            "subfolder": subfolder_name
                        })
                        logger.info(f"Imported block from {xml_path}")
                    else:  # Legacy bool False
                        errors.append({
                            "path": xml_path,
                            "error": "Import failed"
                        })
                        
                except Exception as e:
                    errors.append({
                        "path": xml_path,
                        "error": str(e)
                    })
                    logger.error(f"Failed to import {xml_path}: {e}")
            
            # Mark project as modified
            session.project_modified = True
            
            return {
                "success": len(imported_blocks) > 0,
                "imported": imported_blocks,
                "errors": errors,
                "summary": {
                    "total": len(xml_paths),
                    "imported": len(imported_blocks),
                    "failed": len(errors)
                }
            }
            
        except Exception as e:
            logger.error(f"Import blocks operation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def export_blocks(
        session,
        block_names: Optional[List[str]] = None,
        output_path: str = "./exports",
        export_all: bool = False
    ) -> Dict[str, Any]:
        """Export blocks to XML files
        
        Args:
            session: TIA session object
            block_names: List of block names to export (None to export all)
            output_path: Directory to export blocks to
            export_all: Whether to export all blocks
            
        Returns:
            Operation result with exported block details
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        try:
            # Ensure output directory exists
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get PLC software
            def _get_plc_software():
                plcs = session.client_wrapper.project.get_plcs()
                
                if not plcs or len(plcs) == 0:
                    raise ValueError("No PLCs found in project")
                
                # Use first PLC
                plc = plcs[0]
                return plc.get_software()
            
            plc_software = await session.client_wrapper.execute_sync(_get_plc_software)
            
            if export_all or not block_names:
                # Export all blocks using comprehensive method
                def _export_all():
                    # Use the new comprehensive export function
                    return _export_all_blocks_comprehensive(plc_software, str(output_dir))
                
                exported_count = await session.client_wrapper.execute_sync(_export_all)
                
                return {
                    "success": exported_count > 0,
                    "exported_count": exported_count,
                    "output_path": str(output_dir),
                    "message": f"Exported {exported_count} blocks"
                }
                    
            else:
                # Export specific blocks
                exported_blocks = []
                errors = []

                # First, get all blocks with their folder info to enable searching by name
                def _get_all_blocks_info():
                    return _get_all_blocks_comprehensive(plc_software)

                all_blocks_info = await session.client_wrapper.execute_sync(_get_all_blocks_info)

                # Create a lookup by block name
                block_lookup = {}
                for block_info in all_blocks_info:
                    block_lookup[block_info['name']] = block_info

                for block_name in block_names:
                    try:
                        # Look up the block info to get folder location
                        if block_name not in block_lookup:
                            errors.append({
                                "block_name": block_name,
                                "error": f"Block '{block_name}' not found in project"
                            })
                            continue

                        block_info = block_lookup[block_name]

                        # Use _export_block_direct which already has the block object
                        # This avoids the folder depth limitation in export_block_to_xml
                        def _export_single(info=block_info):
                            return _export_block_direct(plc_software, info, str(output_dir))

                        file_path = await session.client_wrapper.execute_sync(_export_single)

                        if file_path:
                            exported_blocks.append({
                                "block_name": block_name,
                                "file_path": file_path,
                                "path": block_info.get('path', '/'),
                                "export_path": block_info.get('export_path', '')
                            })
                        else:
                            errors.append({
                                "block_name": block_name,
                                "error": "Export failed - block may have compilation errors"
                            })

                    except Exception as e:
                        errors.append({
                            "block_name": block_name,
                            "error": str(e)
                        })
                
                return {
                    "success": len(exported_blocks) > 0,
                    "exported": exported_blocks,
                    "errors": errors,
                    "output_path": str(output_dir),
                    "summary": {
                        "total": len(block_names),
                        "exported": len(exported_blocks),
                        "failed": len(errors)
                    }
                }
                
        except Exception as e:
            logger.error(f"Export blocks operation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def list_blocks(session) -> Dict[str, Any]:
        """List all blocks in the current project
        
        Args:
            session: TIA session object
            
        Returns:
            Operation result with block list
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
        
        try:
            def _list_blocks():
                plcs = session.client_wrapper.project.get_plcs()
                all_blocks = []
                
                for plc in plcs:
                    plc_software = plc.get_software()
                    
                    # Use the comprehensive block collection method
                    blocks_info = _get_all_blocks_comprehensive(plc_software)
                    
                    # Convert to the expected format for list_blocks
                    for block_info in blocks_info:
                        all_blocks.append({
                            "name": block_info['name'],
                            "type": block_info['type'],
                            "path": block_info['path']
                        })
                
                return all_blocks
            
            blocks = await session.client_wrapper.execute_sync(_list_blocks)
            
            return {
                "success": True,
                "blocks": blocks,
                "count": len(blocks)
            }
            
        except Exception as e:
            logger.error(f"List blocks operation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def clean_exports(output_path: str = "./exports") -> Dict[str, Any]:
        """Clean exported blocks folder
        
        Args:
            output_path: Path to clean
            
        Returns:
            Operation result
        """
        try:
            # Use the utility function
            clean_exported_blocks_folder()
            
            # Also clean custom path if different
            if output_path != "./exports":
                import shutil
                if Path(output_path).exists():
                    shutil.rmtree(output_path)
                    
            return {
                "success": True,
                "message": "Export folders cleaned"
            }
            
        except Exception as e:
            logger.error(f"Clean exports failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }