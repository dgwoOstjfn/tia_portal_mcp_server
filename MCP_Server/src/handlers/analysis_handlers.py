"""
Project analysis handlers for TIA Portal MCP Server
"""
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import asyncio

# Import block operation modules
from handlers.block_handlers import BlockHandlers, _get_all_blocks_comprehensive, _export_block_direct
from handlers.conversion_handlers import ConversionHandlers
from session.session_manager import TIASession

logger = logging.getLogger(__name__)

class ProjectAnalyzer:
    """Handles project analysis operations"""
    
    @staticmethod
    async def analyze_project_structure(session: TIASession) -> Dict[str, Any]:
        """Get a lightweight tree structure of the project
        
        Args:
            session: TIA session object
            
        Returns:
            Operation result with project tree
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
            
        try:
            def _get_structure():
                plcs = session.client_wrapper.project.get_plcs()
                project_structure = {
                    "project_name": session.current_project,
                    "plcs": []
                }
                
                for plc in plcs:
                    plc_info = {
                        "name": plc.name,
                        "blocks": []
                    }
                    
                    plc_software = plc.get_software()
                    blocks_info = _get_all_blocks_comprehensive(plc_software)
                    
                    # Build a tree structure
                    # We'll use a simple list for now, but grouped by folders
                    for block in blocks_info:
                        # Simplified block info for analysis
                        plc_info["blocks"].append({
                            "name": block["name"],
                            "type": block["type"],
                            "path": block["path"],
                            "folder": block["folder_name"]
                        })
                    
                    project_structure["plcs"].append(plc_info)
                    
                return project_structure
            
            structure = await session.client_wrapper.execute_sync(_get_structure)
            session.update_activity()
            
            # Add stats
            total_blocks = sum(len(plc["blocks"]) for plc in structure["plcs"])
            
            return {
                "success": True,
                "structure": structure,
                "stats": {
                    "total_blocks": total_blocks,
                    "plcs_count": len(structure["plcs"])
                }
            }
            
        except Exception as e:
            logger.error(f"Analyze project structure failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    async def get_flat_code_summary(
        session: TIASession,
        block_names: Optional[List[str]] = None,
        folder_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get concatenated SCL code for selected blocks
        
        Args:
            session: TIA session object
            block_names: Specific list of block names to retrieve
            folder_filter: Filter by folder name (e.g. "Motors")
            type_filter: Filter by block type (e.g. "FB", "DB")
            use_cache: Whether to use cached files
            
        Returns:
            Operation result with concatenated code
        """
        if not session.client_wrapper.project:
            return {
                "success": False,
                "error": "No project is open"
            }
            
        try:
            # 1. Identify target blocks
            def _identify_blocks():
                plcs = session.client_wrapper.project.get_plcs()
                target_blocks = []
                
                for plc in plcs:
                    plc_software = plc.get_software()
                    all_blocks = _get_all_blocks_comprehensive(plc_software)
                    
                    for block in all_blocks:
                        # Apply filters
                        if block_names and block["name"] not in block_names:
                            continue
                            
                        if folder_filter:
                            # Check if folder_filter matches any part of the path
                            # or if it matches the direct folder name
                            if not (block["folder_name"] == folder_filter or 
                                    folder_filter in block["path"]):
                                continue
                                
                        if type_filter and block["type"] != type_filter:
                            continue
                            
                        target_blocks.append(block)
                        
                return target_blocks
            
            target_blocks = await session.client_wrapper.execute_sync(_identify_blocks)
            
            if not target_blocks:
                return {
                    "success": True,
                    "code": "",
                    "message": "No blocks found matching criteria"
                }
            
            # 2. Retrieve code (Check cache -> Export if needed -> Convert)
            conversion_handler = ConversionHandlers()
            concatenated_code = []
            processed_count = 0
            cache_hits = 0
            
            # Create a temp dir for exports if needed
            temp_export_dir = session.cache_manager.session_cache_dir / "temp_exports"
            temp_export_dir.mkdir(parents=True, exist_ok=True)
            
            # We need the PLC software for exports, so we need to run exports in a sync context
            # But we can process cached items directly
            
            blocks_to_export = []
            
            # Check cache first
            for block in target_blocks:
                block_name = block["name"]
                cached_entry = session.cache_manager.get_entry(block_name) if use_cache else None
                
                if cached_entry:
                    # We have a cached file (XML or SCL?)
                    # Ideally we cache the SCL result to avoid conversion overhead
                    # But for now let's assume we cache the exported XML and convert it
                    # OR, let's cache the SCL file directly if we generated it previously.
                    
                    # Let's check if we have a cached SCL file
                    scl_cache_key = f"{block_name}_scl"
                    cached_scl = session.cache_manager.get_entry(scl_cache_key)
                    
                    if cached_scl:
                        try:
                            code = cached_scl.file_path.read_text(encoding='utf-8')
                            concatenated_code.append(f"// Block: {block_name} (Type: {block['type']})\n{code}\n")
                            cache_hits += 1
                            processed_count += 1
                            continue
                        except Exception as e:
                            logger.warning(f"Failed to read cached SCL for {block_name}: {e}")
                            # Fallback to export
                    
                blocks_to_export.append(block)
            
            # Export missing blocks
            if blocks_to_export:
                def _export_batch():
                    results = []
                    plcs = session.client_wrapper.project.get_plcs()
                    if not plcs: return []
                    plc_software = plcs[0].get_software() # Assuming single PLC or first PLC for now
                    
                    for block in blocks_to_export:
                        # Find the actual block object again (since we can't pass ComObjects easily across threads/loops safely if prolonged)
                        # But here we are inside the sync function, so we can use block["block_object"] if it's valid
                        # Re-finding might be safer if the list is stale, but let's try using the object
                        try:
                            export_path = _export_block_direct(plc_software, block, str(temp_export_dir))
                            if export_path:
                                results.append((block, export_path))
                        except Exception as e:
                            logger.error(f"Failed to export {block['name']}: {e}")
                    return results

                export_results = await session.client_wrapper.execute_sync(_export_batch)
                
                # Convert and Cache
                for block, xml_path in export_results:
                    try:
                        # Convert XML to SCL
                        # We can use a temp path for SCL
                        scl_path = Path(xml_path).with_suffix('.scl')
                        
                        # Use conversion handler (which runs standard python code, no TIA API needed)
                        result = conversion_handler.convert_xml_to_scl(xml_path, str(scl_path))
                        
                        if result["success"] and os.path.exists(result["output_file"]):
                            code = Path(result["output_file"]).read_text(encoding='utf-8')
                            concatenated_code.append(f"// Block: {block['name']} (Type: {block['type']})\n{code}\n")
                            processed_count += 1
                            
                            # Update Cache
                            # Cache the XML
                            session.cache_manager.add_entry(block["name"], Path(xml_path), "block_xml")
                            # Cache the SCL
                            session.cache_manager.add_entry(f"{block['name']}_scl", Path(result["output_file"]), "block_scl")
                            
                    except Exception as e:
                        logger.error(f"Failed to process exported block {block['name']}: {e}")

            return {
                "success": True,
                "summary": "\n".join(concatenated_code),
                "stats": {
                    "total_found": len(target_blocks),
                    "processed": processed_count,
                    "cache_hits": cache_hits
                }
            }

        except Exception as e:
            logger.error(f"Get flat code summary failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    async def cache_project_data(session: TIASession) -> Dict[str, Any]:
        """Bulk export and cache all project blocks
        
        Args:
            session: TIA session object
            
        Returns:
            Operation result
        """
        # Re-use get_flat_code_summary logic but for everything and ignore output
        # Or implement a specialized bulk export
        return await ProjectAnalyzer.get_flat_code_summary(session, use_cache=False)

    @staticmethod
    async def clear_cache(session: TIASession) -> Dict[str, Any]:
        """Clear session cache"""
        session.cache_manager.clear_cache()
        return {"success": True, "message": "Cache cleared"}

