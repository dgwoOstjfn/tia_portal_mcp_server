"""
TIA Portal YAML configuration module.
This module loads configuration from a YAML file in the 100_Config directory.
"""
import os
import yaml

# Default configuration values
MasterPrgPath = ""
MasterPrgName = ""
TestPrgName = ""
ProjectStorePath = ""
toImportXMLPath = ""
AmiHostPath = ""

# Flag to track if configuration has been loaded
_config_loaded = False

def load():
    """
    Load configuration from the config.yml file.
    Sets global variables with values from the config file.
    """
    global _config_loaded
    
    # If configuration is already loaded, don't load it again
    if _config_loaded:
        return True
        
    try:
        # Get the project root directory (assuming this file is in 03_BlockImport)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        config_path = os.path.join(current_dir, "config.yml")
        
        # Check if the config file exists
        if not os.path.exists(config_path):
            # print(f"Warning: Config file not found at: {config_path}")  # Commented out - interferes with MCP protocol
            return False
            
        # Load the configuration from YAML
        with open(config_path, 'r') as config_file:
            config_data = yaml.safe_load(config_file)
            
        # Set global variables based on the loaded configuration
        global MasterPrgPath, MasterPrgName, TestPrgName, ProjectStorePath, toImportXMLPath, AmiHostPath
        
        # Set the variables from config
        if 'ProjectStorePath' in config_data:
            ProjectStorePath = config_data['ProjectStorePath']
            MasterPrgPath = config_data['ProjectStorePath']  # For backward compatibility
            
        if 'MasterPrgName' in config_data:
            MasterPrgName = config_data['MasterPrgName']
            
        if 'TestPrgName' in config_data:
            TestPrgName = config_data['TestPrgName']
            
        if 'toImportXMLPath' in config_data:
            toImportXMLPath = config_data['toImportXMLPath']
        
        # Handle AmiHostPath - check environment variable first, then config file
        env_ami_path = os.environ.get('TIA_AMI_HOST_PATH')
        if env_ami_path:
            AmiHostPath = env_ami_path
        elif 'AmiHostPath' in config_data:
            AmiHostPath = config_data['AmiHostPath']
            
        # print(f"Configuration loaded successfully from: {config_path}")  # Commented out - interferes with MCP protocol
        _config_loaded = True
        return True
        
    except Exception as e:
        # print(f"Error loading configuration: {str(e)}")  # Commented out - interferes with MCP protocol
        return False

# Load configuration when module is imported
load() 