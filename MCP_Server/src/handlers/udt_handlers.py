"""
UDT (User-Defined Types) operation handlers for TIA Portal MCP Server
Integrated from 99_TIA_Client proven functionality with nested group support
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class UDTHandlers:
    """Handlers for UDT operations"""
    
    @staticmethod
    def _sanitize_path_name(path_name: str) -> str:
        """Sanitize path name for file system compatibility"""
        if not path_name:
            return path_name
        
        # Replace invalid characters with safe alternatives
        replacements = {
            '<': '',
            '>': '',
            ':': '_',
            '"': '',
            '|': '_',
            '?': '_',
            '*': '_',
            '/': os.sep,
            '\\': os.sep
        }
        
        sanitized = path_name
        for char, replacement in replacements.items():
            sanitized = sanitized.replace(char, replacement)
        
        # Trim leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        
        return sanitized
    
    @staticmethod
    def _discover_udts_recursive(group, path="", discovered_udts=None) -> List[Dict[str, Any]]:
        """
        Recursively discover all UDTs in nested type groups
        This is the PROVEN method from our successful implementation
        """
        if discovered_udts is None:
            discovered_udts = []
        
        # Check for UDTs in current group
        if hasattr(group, 'Types'):
            for udt in group.Types:
                try:
                    udt_info = {
                        "name": getattr(udt, 'Name', 'Unknown'),
                        "path": path,
                        "is_know_how_protected": getattr(udt, 'IsKnowHowProtected', False),
                        "is_consistent": getattr(udt, 'IsConsistent', True),
                        "creation_date": getattr(udt, 'CreationDate', None),
                        "modified_date": getattr(udt, 'ModifiedDate', None),
                        "udt_object": udt  # Store reference for export
                    }
                    
                    # Convert dates to string if they exist
                    for date_field in ["creation_date", "modified_date"]:
                        if udt_info[date_field]:
                            try:
                                udt_info[date_field] = str(udt_info[date_field])
                            except:
                                udt_info[date_field] = "Unknown"
                    
                    discovered_udts.append(udt_info)
                    
                except Exception as e:
                    logger.warning(f"Error processing UDT in path {path}: {e}")
                    discovered_udts.append({
                        "name": "Error",
                        "path": path,
                        "error": str(e),
                        "is_know_how_protected": True,
                        "is_consistent": False,
                        "udt_object": None
                    })
        
        # Recurse into nested groups
        if hasattr(group, 'Groups'):
            for nested_group in group.Groups:
                group_name = getattr(nested_group, 'Name', 'Unknown')
                nested_path = f"{path}/{group_name}" if path else group_name
                UDTHandlers._discover_udts_recursive(nested_group, nested_path, discovered_udts)
        
        return discovered_udts
    
    @staticmethod
    def discover_all_udts(tia_client_wrapper, session_id: str) -> Dict[str, Any]:
        """
        Discover all UDTs in the project using recursive nested group exploration
        
        Args:
            tia_client_wrapper: TIA client wrapper instance
            session_id: Session ID
            
        Returns:
            Dict with success status and UDT discovery results
        """
        try:
            # Get the session
            session = tia_client_wrapper.session_manager.get_session(session_id)
            if not session or not session.project:
                return {
                    "success": False,
                    "error": f"Invalid session or no project open: {session_id}",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TypeGroup'):
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
            
            # Start recursive UDT discovery
            type_group = plc_software.value.TypeGroup
            all_udts = UDTHandlers._discover_udts_recursive(type_group)
            
            # Categorize UDTs
            exportable_udts = [udt for udt in all_udts if not udt.get("is_know_how_protected", False) and udt.get("udt_object") is not None]
            protected_udts = [udt for udt in all_udts if udt.get("is_know_how_protected", False)]
            inconsistent_udts = [udt for udt in all_udts if not udt.get("is_consistent", True)]
            
            # Group by categories
            categories = {}
            for udt in all_udts:
                path = udt.get("path", "Root")
                category = path.split('/')[0] if path else "Root"
                
                if category not in categories:
                    categories[category] = []
                categories[category].append({
                    "name": udt["name"],
                    "path": udt["path"],
                    "exportable": not udt.get("is_know_how_protected", False),
                    "consistent": udt.get("is_consistent", True)
                })
            
            return {
                "success": True,
                "message": f"UDT discovery completed: {len(all_udts)} UDTs found",
                "details": {
                    "total_udts": len(all_udts),
                    "exportable_udts": len(exportable_udts),
                    "protected_udts": len(protected_udts),
                    "inconsistent_udts": len(inconsistent_udts),
                    "categories": categories,
                    "all_udts": [{
                        "name": udt["name"],
                        "path": udt["path"],
                        "is_know_how_protected": udt.get("is_know_how_protected", False),
                        "is_consistent": udt.get("is_consistent", True),
                        "creation_date": udt.get("creation_date"),
                        "modified_date": udt.get("modified_date")
                    } for udt in all_udts]  # Remove object references from output
                }
            }
            
        except Exception as e:
            logger.error(f"Error in discover_all_udts: {e}")
            return {
                "success": False,
                "error": f"UDT discovery failed: {str(e)}",
                "details": {}
            }
    
    @staticmethod
    def export_all_udts(tia_client_wrapper, session_id: str, output_path: str = "./exports", export_all: bool = False) -> Dict[str, Any]:
        """
        Export all UDTs using the PROVEN direct C# API method
        
        Args:
            tia_client_wrapper: TIA client wrapper instance
            session_id: Session ID
            output_path: Base output directory
            export_all: Whether to export all UDTs or only exportable ones
            
        Returns:
            Dict with success status and export results
        """
        try:
            # Get the session
            session = tia_client_wrapper.session_manager.get_session(session_id)
            if not session or not session.project:
                return {
                    "success": False,
                    "error": f"Invalid session or no project open: {session_id}",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TypeGroup'):
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
            
            # Import required C# objects
            try:
                from System.IO import FileInfo
                import Siemens.Engineering as tia
            except ImportError as e:
                return {
                    "success": False,
                    "error": f"Failed to import C# libraries: {str(e)}",
                    "details": {}
                }
            
            # Create base output directory
            os.makedirs(output_path, exist_ok=True)
            
            def export_udt_group_recursive(group, path=""):
                """Recursively export UDTs maintaining folder structure"""
                exported_count = 0
                found_count = 0
                export_results = []
                
                # Create directory for this group if it has a path
                if path:
                    clean_path = UDTHandlers._sanitize_path_name(path)
                    group_dir = os.path.join(output_path, clean_path)
                    os.makedirs(group_dir, exist_ok=True)
                else:
                    group_dir = output_path
                
                # Export UDTs in current group
                if hasattr(group, 'Types'):
                    for udt in group.Types:
                        found_count += 1
                        
                        try:
                            udt_name = getattr(udt, 'Name', 'Unknown')
                            
                            # Check if exportable
                            is_protected = getattr(udt, 'IsKnowHowProtected', False)
                            is_consistent = getattr(udt, 'IsConsistent', True)
                            
                            if not export_all and is_protected:
                                export_results.append({
                                    "name": udt_name,
                                    "path": path,
                                    "status": "skipped",
                                    "reason": "Know-how protected"
                                })
                                continue
                            
                            if not is_consistent:
                                export_results.append({
                                    "name": udt_name,
                                    "path": path,
                                    "status": "warning",
                                    "reason": "Not consistent"
                                })
                            
                            # Export using PROVEN direct C# API method
                            export_file_path = os.path.join(group_dir, f"{udt_name}.xml")
                            file_info = FileInfo(export_file_path)
                            
                            # Use direct C# API (this is the WORKING method)
                            udt.Export(file_info, tia.ExportOptions(0))
                            
                            # Verify file was created
                            if os.path.exists(export_file_path):
                                file_size = os.path.getsize(export_file_path)
                                exported_count += 1
                                
                                export_results.append({
                                    "name": udt_name,
                                    "path": path,
                                    "export_path": export_file_path,
                                    "size_bytes": file_size,
                                    "status": "success",
                                    "is_consistent": is_consistent
                                })
                                logger.info(f"Exported UDT: {udt_name} ({file_size} bytes)")
                            else:
                                export_results.append({
                                    "name": udt_name,
                                    "path": path,
                                    "status": "failed",
                                    "reason": "File not created"
                                })
                                
                        except Exception as e:
                            export_results.append({
                                "name": getattr(udt, 'Name', 'Unknown'),
                                "path": path,
                                "status": "failed",
                                "reason": str(e)
                            })
                            logger.error(f"Failed to export UDT in path {path}: {e}")
                
                # Process nested groups
                if hasattr(group, 'Groups'):
                    for nested_group in group.Groups:
                        group_name = getattr(nested_group, 'Name', 'Unknown')
                        nested_path = f"{path}/{group_name}" if path else group_name
                        
                        nested_found, nested_exported, nested_results = export_udt_group_recursive(nested_group, nested_path)
                        found_count += nested_found
                        exported_count += nested_exported
                        export_results.extend(nested_results)
                
                return found_count, exported_count, export_results
            
            # Start recursive export
            type_group = plc_software.value.TypeGroup
            total_found, total_exported, all_results = export_udt_group_recursive(type_group)
            
            # Calculate statistics
            success_results = [r for r in all_results if r["status"] == "success"]
            failed_results = [r for r in all_results if r["status"] == "failed"]
            skipped_results = [r for r in all_results if r["status"] == "skipped"]
            total_size = sum(r.get("size_bytes", 0) for r in success_results)
            
            return {
                "success": True,
                "message": f"UDT export completed: {total_exported}/{total_found} UDTs exported successfully",
                "details": {
                    "output_path": output_path,
                    "total_found": total_found,
                    "total_exported": total_exported,
                    "total_failed": len(failed_results),
                    "total_skipped": len(skipped_results),
                    "total_size_bytes": total_size,
                    "export_results": all_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error in export_all_udts: {e}")
            return {
                "success": False,
                "error": f"UDT export failed: {str(e)}",
                "details": {}
            }
    
    @staticmethod
    def export_specific_udts(tia_client_wrapper, session_id: str, udt_names: List[str], output_path: str = "./exports") -> Dict[str, Any]:
        """
        Export specific UDTs by name
        
        Args:
            tia_client_wrapper: TIA client wrapper instance
            session_id: Session ID
            udt_names: List of UDT names to export
            output_path: Output directory
            
        Returns:
            Dict with success status and export results
        """
        try:
            # Get the session
            session = tia_client_wrapper.session_manager.get_session(session_id)
            if not session or not session.project:
                return {
                    "success": False,
                    "error": f"Invalid session or no project open: {session_id}",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TypeGroup'):
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
            
            # Import required C# objects
            try:
                from System.IO import FileInfo
                import Siemens.Engineering as tia
            except ImportError as e:
                return {
                    "success": False,
                    "error": f"Failed to import C# libraries: {str(e)}",
                    "details": {}
                }
            
            # Create output directory
            os.makedirs(output_path, exist_ok=True)
            
            # First, discover all UDTs to create a lookup table
            type_group = plc_software.value.TypeGroup
            all_udts = UDTHandlers._discover_udts_recursive(type_group)
            
            # Create lookup table by name
            udt_lookup = {}
            for udt_info in all_udts:
                udt_lookup[udt_info["name"]] = udt_info
            
            # Export requested UDTs
            export_results = []
            total_size = 0
            
            for udt_name in udt_names:
                try:
                    if udt_name not in udt_lookup:
                        export_results.append({
                            "name": udt_name,
                            "status": "failed",
                            "reason": "UDT not found"
                        })
                        continue
                    
                    udt_info = udt_lookup[udt_name]
                    udt_object = udt_info.get("udt_object")
                    
                    if not udt_object:
                        export_results.append({
                            "name": udt_name,
                            "status": "failed",
                            "reason": "UDT object not available"
                        })
                        continue
                    
                    # Check if exportable
                    if udt_info.get("is_know_how_protected", False):
                        export_results.append({
                            "name": udt_name,
                            "path": udt_info.get("path", ""),
                            "status": "skipped",
                            "reason": "Know-how protected"
                        })
                        continue
                    
                    # Export using direct C# API
                    export_file_path = os.path.join(output_path, f"{udt_name}.xml")
                    file_info = FileInfo(export_file_path)
                    
                    udt_object.Export(file_info, tia.ExportOptions(0))
                    
                    # Verify file was created
                    if os.path.exists(export_file_path):
                        file_size = os.path.getsize(export_file_path)
                        total_size += file_size
                        
                        export_results.append({
                            "name": udt_name,
                            "path": udt_info.get("path", ""),
                            "export_path": export_file_path,
                            "size_bytes": file_size,
                            "status": "success",
                            "is_consistent": udt_info.get("is_consistent", True)
                        })
                        logger.info(f"Exported UDT: {udt_name} ({file_size} bytes)")
                    else:
                        export_results.append({
                            "name": udt_name,
                            "path": udt_info.get("path", ""),
                            "status": "failed",
                            "reason": "File not created"
                        })
                        
                except Exception as e:
                    export_results.append({
                        "name": udt_name,
                        "status": "failed",
                        "reason": str(e)
                    })
                    logger.error(f"Failed to export UDT {udt_name}: {e}")
            
            success_count = len([r for r in export_results if r["status"] == "success"])
            
            return {
                "success": True,
                "message": f"Specific UDT export completed: {success_count}/{len(udt_names)} successful",
                "details": {
                    "output_path": output_path,
                    "udts_requested": udt_names,
                    "udts_exported": success_count,
                    "total_size_bytes": total_size,
                    "export_results": export_results
                }
            }
            
        except Exception as e:
            logger.error(f"Error in export_specific_udts: {e}")
            return {
                "success": False,
                "error": f"Specific UDT export failed: {str(e)}",
                "details": {}
            }
    
    @staticmethod
    def generate_udt_source(tia_client_wrapper, session_id: str, udt_names: List[str], output_path: str, with_dependencies: bool = True) -> Dict[str, Any]:
        """
        Generate SCL source code from UDTs
        
        Args:
            tia_client_wrapper: TIA client wrapper instance
            session_id: Session ID
            udt_names: List of UDT names to generate source for
            output_path: Output SCL file path
            with_dependencies: Whether to include dependencies
            
        Returns:
            Dict with success status and generation results
        """
        try:
            # Get the session
            session = tia_client_wrapper.session_manager.get_session(session_id)
            if not session or not session.project:
                return {
                    "success": False,
                    "error": f"Invalid session or no project open: {session_id}",
                    "details": {}
                }
            
            # Find PLC software
            plc_software = None
            for device in session.project.devices:
                items = device.get_items()
                if items:
                    for item in items:
                        software = item.get_software()
                        if software and hasattr(software.value, 'TypeGroup'):
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
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Use the proven generate_source_from_udts method
            try:
                success = plc_software.generate_source_from_udts(
                    udt_names,
                    output_path,
                    with_dependencies=with_dependencies
                )
                
                if success and os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    
                    return {
                        "success": True,
                        "message": f"SCL source generated successfully",
                        "details": {
                            "output_path": output_path,
                            "udt_names": udt_names,
                            "with_dependencies": with_dependencies,
                            "file_size_bytes": file_size
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "SCL source generation failed - method returned False or file not created",
                        "details": {
                            "udt_names": udt_names,
                            "output_path": output_path
                        }
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"SCL source generation error: {str(e)}",
                    "details": {
                        "udt_names": udt_names,
                        "output_path": output_path
                    }
                }
            
        except Exception as e:
            logger.error(f"Error in generate_udt_source: {e}")
            return {
                "success": False,
                "error": f"Source generation failed: {str(e)}",
                "details": {}
            }