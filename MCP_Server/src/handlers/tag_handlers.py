"""
PLC Tag operation handlers for TIA Portal MCP Server
Integrated from 99_TIA_Client proven functionality
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class TagHandlers:
    """Handlers for PLC tag operations"""
    
    @staticmethod
    def export_all_tag_tables(session, output_path: str = "./exports") -> Dict[str, Any]:
        """
        Export all PLC tag tables to XML files
        
        Args:
            session: TIA session object (contains client_wrapper and project)
            output_path: Output directory path
            
        Returns:
            Dict with success status and results
        """
        try:
            # Check if project is open
            if not session.client_wrapper.project:
                return {
                    "success": False,
                    "error": "No project is currently open",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.client_wrapper.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TagTableGroup'):
                            plc_software = software
                            break
                if plc_software:
                    break
            
            if not plc_software:
                return {
                    "success": False,
                    "error": "No PLC software found in project",
                    "details": {}
                }
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Export all tag tables
            tag_table_group = plc_software.value.TagTableGroup
            tag_tables = list(tag_table_group.TagTables) if hasattr(tag_table_group, 'TagTables') else []
            exported_tables = []
            total_size = 0
            
            for tag_table in tag_tables:
                try:
                    export_file_path = os.path.join(output_path, f"{tag_table.Name}.xml")
                    result_path = tag_table.Export(export_file_path)
                    
                    # Verify file was created and get size
                    if os.path.exists(export_file_path):
                        file_size = os.path.getsize(export_file_path)
                        total_size += file_size
                        
                        exported_tables.append({
                            "name": tag_table.Name,
                            "path": export_file_path,
                            "size_bytes": file_size,
                            "status": "success"
                        })
                        logger.info(f"Exported tag table: {tag_table.Name} ({file_size} bytes)")
                    else:
                        exported_tables.append({
                            "name": tag_table.Name,
                            "path": export_file_path,
                            "size_bytes": 0,
                            "status": "failed",
                            "error": "File not created"
                        })
                        
                except Exception as e:
                    exported_tables.append({
                        "name": tag_table.Name,
                        "status": "failed",
                        "error": str(e)
                    })
                    logger.error(f"Failed to export tag table {tag_table.Name}: {e}")
            
            success_count = len([t for t in exported_tables if t["status"] == "success"])
            
            return {
                "success": True,
                "message": f"Tag table export completed: {success_count}/{len(exported_tables)} successful",
                "details": {
                    "output_path": output_path,
                    "tables_found": len(exported_tables),
                    "tables_exported": success_count,
                    "total_size_bytes": total_size,
                    "exported_tables": exported_tables
                }
            }
            
        except Exception as e:
            logger.error(f"Error in export_all_tag_tables: {e}")
            return {
                "success": False,
                "error": f"Export operation failed: {str(e)}",
                "details": {}
            }
    
    @staticmethod
    def export_specific_tag_tables(session, table_names: List[str], output_path: str = "./exports") -> Dict[str, Any]:
        """
        Export specific PLC tag tables to XML files
        
        Args:
            session: TIA session object (contains client_wrapper and project)
            table_names: List of tag table names to export
            output_path: Output directory path
            
        Returns:
            Dict with success status and results
        """
        try:
            # Check if project is open
            if not session.client_wrapper.project:
                return {
                    "success": False,
                    "error": "No project is currently open",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.client_wrapper.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TagTableGroup'):
                            plc_software = software
                            break
                if plc_software:
                    break
            
            if not plc_software:
                return {
                    "success": False,
                    "error": "No PLC software found in project",
                    "details": {}
                }
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # Export specified tag tables
            tag_table_group = plc_software.value.TagTableGroup
            tag_tables = list(tag_table_group.TagTables) if hasattr(tag_table_group, 'TagTables') else []
            exported_tables = []
            total_size = 0
            
            for table_name in table_names:
                try:
                    # Find the tag table
                    tag_table = None
                    for table in tag_tables:
                        if table.name == table_name:
                            tag_table = table
                            break
                    
                    if not tag_table:
                        exported_tables.append({
                            "name": table_name,
                            "status": "failed",
                            "error": "Tag table not found"
                        })
                        continue
                    
                    # Export the tag table
                    export_file_path = os.path.join(output_path, f"{tag_table.Name}.xml")
                    result_path = tag_table.Export(export_file_path)
                    
                    # Verify file was created and get size
                    if os.path.exists(export_file_path):
                        file_size = os.path.getsize(export_file_path)
                        total_size += file_size
                        
                        exported_tables.append({
                            "name": tag_table.Name,
                            "path": export_file_path,
                            "size_bytes": file_size,
                            "status": "success"
                        })
                        logger.info(f"Exported tag table: {tag_table.Name} ({file_size} bytes)")
                    else:
                        exported_tables.append({
                            "name": tag_table.Name,
                            "path": export_file_path,
                            "size_bytes": 0,
                            "status": "failed",
                            "error": "File not created"
                        })
                        
                except Exception as e:
                    exported_tables.append({
                        "name": table_name,
                        "status": "failed",
                        "error": str(e)
                    })
                    logger.error(f"Failed to export tag table {table_name}: {e}")
            
            success_count = len([t for t in exported_tables if t["status"] == "success"])
            
            return {
                "success": True,
                "message": f"Specific tag table export completed: {success_count}/{len(table_names)} successful",
                "details": {
                    "output_path": output_path,
                    "tables_requested": table_names,
                    "tables_exported": success_count,
                    "total_size_bytes": total_size,
                    "exported_tables": exported_tables
                }
            }
            
        except Exception as e:
            logger.error(f"Error in export_specific_tag_tables: {e}")
            return {
                "success": False,
                "error": f"Export operation failed: {str(e)}",
                "details": {}
            }
    
    @staticmethod
    def list_tag_tables(session) -> Dict[str, Any]:
        """
        List all available PLC tag tables
        
        Args:
            session: TIA session object (contains client_wrapper and project)
            
        Returns:
            Dict with success status and tag table list
        """
        try:
            # Check if project is open
            if not session.client_wrapper.project:
                return {
                    "success": False,
                    "error": "No project is currently open",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.client_wrapper.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TagTableGroup'):
                            plc_software = software
                            break
                if plc_software:
                    break
            
            if not plc_software:
                return {
                    "success": False,
                    "error": "No PLC software found in project",
                    "details": {}
                }
            
            # List all tag tables
            tag_table_group = plc_software.value.TagTableGroup
            tag_tables = list(tag_table_group.TagTables) if hasattr(tag_table_group, 'TagTables') else []
            table_info = []
            
            for tag_table in tag_tables:
                try:
                    # Get basic table info
                    table_data = {
                        "name": tag_table.Name,
                        "type": "TagTable"
                    }
                    
                    # Try to get tag count if possible
                    try:
                        tags = list(tag_table.Tags) if hasattr(tag_table, 'Tags') else []
                        tag_count = len(tags)
                        table_data["tag_count"] = tag_count
                    except:
                        table_data["tag_count"] = "Unknown"
                    
                    table_info.append(table_data)
                    
                except Exception as e:
                    logger.warning(f"Error getting info for tag table {tag_table.Name}: {e}")
                    table_info.append({
                        "name": getattr(tag_table, 'Name', 'Unknown'),
                        "type": "TagTable",
                        "tag_count": "Error",
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"Found {len(table_info)} tag tables",
                "details": {
                    "tag_tables": table_info,
                    "total_count": len(table_info)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in list_tag_tables: {e}")
            return {
                "success": False,
                "error": f"List operation failed: {str(e)}",
                "details": {}
            }
    
    @staticmethod
    def get_tag_table_details(session, table_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific tag table including individual tags
        
        Args:
            session: TIA session object (contains client_wrapper and project)
            table_name: Name of the tag table
            
        Returns:
            Dict with success status and detailed tag table information
        """
        try:
            # Check if project is open
            if not session.client_wrapper.project:
                return {
                    "success": False,
                    "error": "No project is currently open",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.client_wrapper.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TagTableGroup'):
                            plc_software = software
                            break
                if plc_software:
                    break
            
            if not plc_software:
                return {
                    "success": False,
                    "error": "No PLC software found in project",
                    "details": {}
                }
            
            # Find the specific tag table
            tag_table_group = plc_software.value.TagTableGroup
            tag_tables = list(tag_table_group.TagTables) if hasattr(tag_table_group, 'TagTables') else []
            target_table = None
            
            for table in tag_tables:
                if table.Name == table_name:
                    target_table = table
                    break
            
            if not target_table:
                return {
                    "success": False,
                    "error": f"Tag table '{table_name}' not found",
                    "details": {}
                }
            
            # Get detailed tag information
            tags_info = []
            
            try:
                tags = list(target_table.Tags) if hasattr(target_table, 'Tags') else []
                for tag in tags:
                    try:
                        tag_data = {
                            "name": getattr(tag, 'Name', 'Unknown'),
                            "data_type": getattr(tag, 'DataTypeName', 'Unknown'),
                            "logical_address": getattr(tag, 'LogicalAddress', 'Unknown')
                        }
                        
                        # Try to get additional properties if available
                        if hasattr(tag, 'Comment'):
                            tag_data["comment"] = tag.Comment
                        if hasattr(tag, 'ExternalAccessible'):
                            tag_data["external_accessible"] = tag.ExternalAccessible
                        if hasattr(tag, 'ExternalVisible'):
                            tag_data["external_visible"] = tag.ExternalVisible
                        if hasattr(tag, 'ExternalWritable'):
                            tag_data["external_writable"] = tag.ExternalWritable
                            
                        tags_info.append(tag_data)
                        
                    except Exception as e:
                        tags_info.append({
                            "name": "Error",
                            "error": f"Failed to read tag: {str(e)}"
                        })
                        
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to access tags in table '{table_name}': {str(e)}",
                    "details": {}
                }
            
            return {
                "success": True,
                "message": f"Retrieved details for tag table '{table_name}'",
                "details": {
                    "table_name": table_name,
                    "tag_count": len(tags_info),
                    "tags": tags_info
                }
            }
            
        except Exception as e:
            logger.error(f"Error in get_tag_table_details: {e}")
            return {
                "success": False,
                "error": f"Get details operation failed: {str(e)}",
                "details": {}
            }