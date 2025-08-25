import sys
import os
import traceback
import shutil  # Added for directory removal functions

# Get root directory for imports
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Update path to point to the local modules
sys.path.append(os.path.join(root_dir, "99_TIA_Client"))
sys.path.append(os.path.join(root_dir, "100_Config"))
# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our local tia_config module for YAML configuration
import tia_config
from tia_portal import Client
from tia_portal import PLCSoftware, PLCBlock, PLCBlocks

def clean_exported_blocks_folder():
    """
    Delete all files and subfolders under .tia_portal/exported_blocks
    
    This ensures that temporary export files are cleaned up at the end
    of the service execution.
    """
    try:
        # Build the path to the .tia_portal/exported_blocks directory
        # This assumes the DATA_PATH is accessible through tia_portal.cfg module
        from tia_portal import cfg
        
        if hasattr(cfg, 'DATA_PATH'):
            exported_blocks_dir = os.path.join(cfg.DATA_PATH, "exported_blocks")
            
            if os.path.exists(exported_blocks_dir):
                print(f"Cleaning up temporary files in {exported_blocks_dir}...")
                
                # Option 1: Remove individual files to preserve the directory
                for item in os.listdir(exported_blocks_dir):
                    item_path = os.path.join(exported_blocks_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        print(f"Error while deleting {item_path}: {str(e)}")
                
                print(f"Successfully cleaned up files in {exported_blocks_dir}")
            else:
                print(f"Directory {exported_blocks_dir} does not exist. Nothing to clean up.")
        else:
            print("Warning: Could not determine DATA_PATH. Export cleanup was skipped.")
    except Exception as e:
        print(f"Error during cleanup of exported files: {str(e)}")
        traceback.print_exc()

def export_block_to_xml(tia_software, block_name, export_path, folder_name=None, subfolder_name=None):
    """
    Export a block from TIA Portal project to XML file
    
    Args:
        tia_software: TIA Portal software instance
        block_name: Name of the block to export
        export_path: Base path where the block will be exported
        folder_name: Name of the folder where the block is located. If None, look in root folder.
        subfolder_name: Name of the subfolder inside folder_name where the block is located. If None, look directly in folder_name.
        
    Returns:
        str: Path to the exported file if successful, None otherwise
    """
    try:
        # Validate PLC software object
        if not tia_software or not isinstance(tia_software, PLCSoftware):
            print("Invalid PLC software object")
            return None
        
        # Set the target block to None initially
        target_block = None
        
        # Case 1: folder_name is None, subfolder_name is None - use root
        if not folder_name:
            # Use the default blocks collection from root
            blocks = tia_software.get_blocks()
            if not blocks or not isinstance(blocks, PLCBlocks):
                print("Invalid blocks collection")
                return None
                
            # Try to find the block in the root folder
            target_block = blocks.find(block_name)
        # Case 2 & 3: folder_name has value
        else:
            try:
                # Get user block groups
                user_groups = tia_software.get_user_block_groups()
                # Try to find the specified folder
                user_group = user_groups.find(folder_name)
                # Check if the folder exists
                if not user_group or not user_group.value:
                    print(f"Folder '{folder_name}' not found, skipping export")
                    return None
                
                # Case 2: folder_name has value, subfolder_name is None
                if not subfolder_name:
                    # Use the main folder
                    blocks = user_group.get_blocks()
                    # Try to find the block in this folder
                    target_block = blocks.find(block_name)
                # Case 3: folder_name has value, subfolder_name has value
                else:
                    try:
                        # Get groups collection of the parent folder
                        parent_groups = user_group.get_groups()
                        # Try to find the specified subfolder
                        sub_group = parent_groups.find(subfolder_name)
                        # Check if the subfolder exists
                        if not sub_group or not sub_group.value:
                            print(f"Subfolder '{subfolder_name}' not found in folder '{folder_name}', skipping export")
                            return None
                        # Get blocks from the specified subfolder
                        blocks = sub_group.get_blocks()
                        # Try to find the block in this subfolder
                        target_block = blocks.find(block_name)
                    except Exception as e:
                        print(f"Error accessing subfolder '{subfolder_name}': {str(e)}")
                        return None
            except Exception as e:
                print(f"Error accessing folder '{folder_name}': {str(e)}")
                return None
        
        # Check if the block was found
        if not target_block:
            print(f"Block '{block_name}' not found in the specified location")
            return None
            
        # Create the export directory structure matching the TIA Portal folder structure
        export_dir = export_path
        
        # If folder and subfolder are specified, create that structure
        if folder_name:
            export_dir = os.path.join(export_dir, folder_name)
            if subfolder_name:
                export_dir = os.path.join(export_dir, subfolder_name)
        
        # Create directory if it doesn't exist
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            
        # Construct the export file path
        export_file_path = os.path.join(export_dir, f"{block_name}.xml")
        
        # Export the block
        print(f"Exporting block '{block_name}' to {export_file_path}...")
        try:
            exported_file = target_block.export()
            
            # The export method saves it to a temporary location in the DATA_PATH
            # We need to move it to our desired location
            if os.path.exists(exported_file):
                # Create the directory structure if it doesn't exist
                os.makedirs(os.path.dirname(export_file_path), exist_ok=True)
                
                # If the file already exists at the target location, remove it
                if os.path.exists(export_file_path):
                    os.remove(export_file_path)
                    
                # Move the file from the temporary location to our desired location
                shutil.copyfile(exported_file, export_file_path)
                print(f"Successfully exported block '{block_name}' to {export_file_path}")
                return export_file_path
            else:
                print(f"Export failed: Exported file not found at {exported_file}")
                return None
                
        except Exception as e:
            print(f"Error exporting block: {str(e)}")
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"Operation error: {str(e)}")
        traceback.print_exc()
        return None

def export_all_blocks(tia_software, export_base_path):
    """
    Export all blocks from the TIA Portal project preserving folder structure
    
    Args:
        tia_software: TIA Portal software instance
        export_base_path: Base path where blocks will be exported
        
    Returns:
        int: Number of successfully exported blocks
    """
    try:
        # Count of successfully exported blocks
        export_count = 0
        
        # First, export blocks from the root folder
        root_blocks = tia_software.get_blocks()
        if root_blocks and hasattr(root_blocks, "value") and root_blocks.value is not None:
            for block in root_blocks:
                try:
                    # Skip system blocks (typically starting with _)
                    if block.name.startswith("_"):
                        continue
                        
                    result = export_block_to_xml(tia_software, block.name, export_base_path)
                    if result:
                        export_count += 1
                except Exception as block_ex:
                    print(f"Error exporting root block {block.name}: {str(block_ex)}")
        
        # Next, export blocks from user block groups
        user_groups = tia_software.get_user_block_groups()
        if user_groups and hasattr(user_groups, "value") and user_groups.value is not None:
            # Iterate through each top-level folder
            for folder in user_groups:
                try:
                    # Export blocks directly in this folder
                    folder_blocks = folder.get_blocks()
                    if folder_blocks and hasattr(folder_blocks, "value") and folder_blocks.value is not None:
                        for block in folder_blocks:
                            try:
                                result = export_block_to_xml(
                                    tia_software, 
                                    block.name, 
                                    export_base_path,
                                    folder_name=folder.name
                                )
                                if result:
                                    export_count += 1
                            except Exception as block_ex:
                                print(f"Error exporting block {block.name} in folder {folder.name}: {str(block_ex)}")
                    
                    # Get subfolders
                    subfolders = folder.get_groups()
                    if subfolders and hasattr(subfolders, "value") and subfolders.value is not None:
                        # Iterate through each subfolder
                        for subfolder in subfolders:
                            try:
                                # Export blocks in this subfolder
                                subfolder_blocks = subfolder.get_blocks()
                                if subfolder_blocks and hasattr(subfolder_blocks, "value") and subfolder_blocks.value is not None:
                                    for block in subfolder_blocks:
                                        try:
                                            result = export_block_to_xml(
                                                tia_software,
                                                block.name,
                                                export_base_path,
                                                folder_name=folder.name,
                                                subfolder_name=subfolder.name
                                            )
                                            if result:
                                                export_count += 1
                                        except Exception as block_ex:
                                            print(f"Error exporting block {block.name} in subfolder {subfolder.name}: {str(block_ex)}")
                            except Exception as subfolder_ex:
                                print(f"Error processing subfolder {subfolder.name}: {str(subfolder_ex)}")
                except Exception as folder_ex:
                    print(f"Error processing folder {folder.name}: {str(folder_ex)}")
                    
        return export_count
    except Exception as e:
        print(f"Error exporting all blocks: {str(e)}")
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    try:
        # Load configuration from YAML
        if not tia_config.load():
            print("Error: Failed to load configuration. Please check the config.yml file.")
            input("Press Enter to exit...")
            sys.exit(1)
            
        # Check if required configuration values are set
        if not tia_config.ProjectStorePath or not tia_config.MasterPrgName:
            print("Error: Missing required configuration. Please check ProjectStorePath and MasterPrgName in config.yml")
            input("Press Enter to exit...")
            sys.exit(1)
        
        # Initialize TIA Portal client
        tia_client = Client()
        
        # Construct the full project path
        full_project_path = os.path.join(tia_config.ProjectStorePath, tia_config.MasterPrgName)
        print(f"Opening project: {full_project_path}")
        
        # Open the TIA Portal project
        tia_client.open_project(tia_config.ProjectStorePath, tia_config.MasterPrgName)
        
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
        
        # Clean up temporary files in .tia_portal/exported_blocks before starting the export process
        print("Cleaning up existing exported files before starting...")
        clean_exported_blocks_folder()
        
        # Create an export directory within the project store path
        export_base_path = os.path.join(tia_config.ProjectStorePath, "exported_blocks")
        
        # Ensure the export directory exists
        if not os.path.exists(export_base_path):
            os.makedirs(export_base_path)
            
        print(f"Exporting blocks to: {export_base_path}")
        
        # Export all blocks
        count = export_all_blocks(tia_software, export_base_path)
        
        if count > 0:
            print(f"Successfully exported {count} blocks")
        else:
            print("No blocks were exported")
            
        # Clean up temporary files in .tia_portal/exported_blocks
        clean_exported_blocks_folder()
            
        input("Press Enter to continue...")
        
    except Exception as e:
        print(f"Program error: {str(e)}")
        traceback.print_exc()
        
        # Even if there was an error, try to clean up
        try:
            clean_exported_blocks_folder()
        except Exception as cleanup_error:
            print(f"Error during cleanup: {str(cleanup_error)}")
            
        input("Press Enter to exit...")
        sys.exit(1)
