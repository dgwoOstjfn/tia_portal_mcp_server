import sys
import os
import traceback
# Get root directory for imports
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Update path to point to the local modules
sys.path.append(os.path.join(root_dir, "99_TIA_Client"))
sys.path.append(os.path.join(root_dir, "100_Config"))
# Add current directory to Python path to find tia_config.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Import our local tia_config module for YAML configuration
import tia_config
from tia_portal import Client
from tia_portal import PLCSoftware, PLCBlocks

def import_block_from_xml(tia_software, xml_path, folder_name=None, subfolder_name=None):
    """
    Import a block from XML file into TIA Portal project

    Args:
        tia_software: TIA Portal software instance
        xml_path: Path to the XML file containing the block
        folder_name: Name of the folder to import the block into. If None, imports to root folder.
        subfolder_name: Name of the subfolder inside folder_name to import the block into. If None, imports directly to folder_name.

    Returns:
        dict: {"success": bool, "error": str or None, "block_name": str or None}
              For backward compatibility, also supports bool return check via truthiness
    """
    try:
        # Validate PLC software object
        if not tia_software or not isinstance(tia_software, PLCSoftware):
            return {"success": False, "error": "Invalid PLC software object", "block_name": None}

        # Case 1: folder_name is None, subfolder_name is None - use root
        if not folder_name:
            # Use the default blocks collection from root
            blocks = tia_software.get_blocks()
            if not blocks or not isinstance(blocks, PLCBlocks):
                return {"success": False, "error": "Invalid blocks collection", "block_name": None}
        # Case 2 & 3: folder_name has value
        else:
            try:
                # Get user block groups
                user_groups = tia_software.get_user_block_groups()
                # Try to find the specified folder
                user_group = user_groups.find(folder_name)
                # Check if the folder exists
                if not user_group or not user_group.value:
                    return {"success": False, "error": f"Folder '{folder_name}' not found in project", "block_name": None}

                # Case 2: folder_name has value, subfolder_name is None
                if not subfolder_name:
                    # Use the main folder
                    blocks = user_group.get_blocks()
                # Case 3: folder_name has value, subfolder_name has value
                else:
                    try:
                        # Get groups collection of the parent folder
                        parent_groups = user_group.get_groups()
                        # Try to find the specified subfolder
                        sub_group = parent_groups.find(subfolder_name)
                        # Check if the subfolder exists
                        if not sub_group or not sub_group.value:
                            return {"success": False, "error": f"Subfolder '{subfolder_name}' not found in folder '{folder_name}'", "block_name": None}
                        # Get blocks from the specified subfolder
                        blocks = sub_group.get_blocks()
                    except Exception as e:
                        return {"success": False, "error": f"Error accessing subfolder '{subfolder_name}': {str(e)}", "block_name": None}
            except Exception as e:
                return {"success": False, "error": f"Error accessing folder '{folder_name}': {str(e)}", "block_name": None}

        block_name = os.path.splitext(os.path.basename(xml_path))[0]

        # Try to import the block - this is where TIA Portal API is called
        try:
            new_block = blocks.create(
                path=xml_path,
                name=block_name,
                labels={"CreatedBy": "Openness API"}
            )
            return {"success": True, "error": None, "block_name": new_block.name}
        except Exception as import_error:
            # Capture the actual TIA Portal error message
            error_msg = str(import_error)
            # Common TIA Portal import errors and their explanations
            if "could not be found" in error_msg.lower() or "not found" in error_msg.lower():
                error_msg = f"TIA Portal import failed: {error_msg}. Check if all referenced UDTs and DBs exist in the project."
            elif "already exists" in error_msg.lower():
                error_msg = f"Block '{block_name}' already exists in the target location. Delete it first or use a different name."
            elif "syntax" in error_msg.lower() or "invalid" in error_msg.lower():
                error_msg = f"TIA Portal import failed due to syntax/validation error: {error_msg}"
            return {"success": False, "error": error_msg, "block_name": block_name}

    except Exception as e:
        error_details = str(e)
        traceback.print_exc()
        return {"success": False, "error": f"Unexpected error during import: {error_details}", "block_name": None}

if __name__ == "__main__":
    try:
        # Load configuration from YAML
        if not tia_config.load():
            print("Error: Failed to load configuration. Please check the config.yml file.")
            input("Press Enter to exit...")
            sys.exit(1)
            
        # Check if required configuration values are set
        if not tia_config.MasterPrgPath or not tia_config.MasterPrgName:
            print("Error: Missing required configuration. Please check MasterPrgPath and MasterPrgName in config.yml")
            input("Press Enter to exit...")
            sys.exit(1)
        
        # Initialize TIA Portal client
        tia_client = Client()
        
        # Construct the full project path
        full_project_path = os.path.join(tia_config.MasterPrgPath, tia_config.MasterPrgName)
        print(f"Opening project: {full_project_path}")
        
        # Open the TIA Portal project
        tia_client.open_project(tia_config.MasterPrgPath, tia_config.MasterPrgName)
        tia_client.project.save_as("NAME_4")
        
        # Get PLCs and software
        plcs = tia_client.project.get_plcs()
        if len(plcs) == 0:
            print("No PLCs found in project")
            input("Press Enter to exit...")
            sys.exit(1)
        elif len(plcs) > 1:
            print("Multiple PLCs found in project, using the first one")
            
        plc = plcs[0]
        tia_software = plc.get_software()
        
        # Check if XML path is configured
        if not tia_config.toImportXMLPath:
            print("Error: Missing XML import path. Please check toImportXMLPath in config.yml")
            input("Press Enter to exit...")
            sys.exit(1)
            
        xml_path = tia_config.toImportXMLPath
        print(f"Importing block from: {xml_path}")
        result = import_block_from_xml(tia_software, xml_path,'bbb','sub_bbb')

        if result.get("success"):
            print(f"Block '{result.get('block_name')}' imported successfully")

            # Save and compile after successful import
            print("Saving project changes...")
            tia_client.project.save()
            print("Project changes saved successfully")

            print("Compiling project...")
            tia_client.project.compile()
            print("Project compiled successfully")
        else:
            print(f"Block import failed: {result.get('error')}")
            
        input("按回车键继续...")
        
    except Exception as e:
        print(f"Program error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)