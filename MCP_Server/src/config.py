"""
Configuration management for TIA Portal MCP Server
This module provides backward compatibility while migrating to MCP configuration
"""
import yaml
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from mcp_config import get_mcp_config

class Config:
    """Configuration manager for MCP Server"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration
        
        Args:
            config_path: Path to CONFIG.yml file. If None, uses default location
        """
        if config_path is None:
            # Default to ../100_Config/CONFIG.yml
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "100_Config" / "CONFIG.yml"
        
        self.config_path = Path(config_path)
        self.settings: Dict[str, Any] = {}
        self._load_config()
        self._setup_paths()
        
    def _load_config(self) -> None:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.settings = yaml.safe_load(f) or {}
            # print(f"Configuration loaded from: {self.config_path}")  # Commented out - interferes with MCP protocol
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def _setup_paths(self) -> None:
        """Setup and validate paths from configuration"""
        # Add parent directories to Python path for imports
        base_dir = Path(__file__).parent.parent.parent
        
        # Add paths for importing from other modules
        paths_to_add = [
            base_dir / "99_TIA_Client",
            base_dir / "02_FileConverter", 
            base_dir / "03_BlockImport",
            base_dir / "04_BlockExport",
            base_dir / "21_ChatClient",
            base_dir / "20_OnlineTool",
            base_dir / "100_Config"
        ]
        
        for path in paths_to_add:
            if path.exists() and str(path) not in sys.path:
                sys.path.insert(0, str(path))
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def validate_config(self) -> bool:
        """Validate required configuration fields
        
        Returns:
            True if configuration is valid
        """
        required_fields = [
            'ProjectStorePath',
            'MasterPrgName',
            'TestPrgName'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not self.get(field):
                missing_fields.append(field)
        
        if missing_fields:
            # print(f"Missing required configuration fields: {missing_fields}")  # Commented out - interferes with MCP protocol
            return False
        
        # Validate paths exist
        project_path = self.get('ProjectStorePath')
        if project_path and not Path(project_path).exists():
            # print(f"Warning: ProjectStorePath does not exist: {project_path}")  # Commented out - interferes with MCP protocol
            pass
        
        return True
    
    @property
    def project_store_path(self) -> str:
        """Get project store path"""
        return self.get('ProjectStorePath', '')
    
    @property
    def master_prg_name(self) -> str:
        """Get master program name"""
        return self.get('MasterPrgName', '')
    
    @property
    def test_prg_name(self) -> str:
        """Get test program name"""
        return self.get('TestPrgName', '')
    
    @property
    def test_material_path(self) -> Path:
        """Get test material path"""
        return Path(__file__).parent.parent.parent / "Test_Material"
    
    @property
    def test_project_1(self) -> Path:
        """Get path to first test project"""
        return self.test_material_path / "Test_v17_openness" / "Test_v17_openness.ap17"
    
    @property
    def test_project_2(self) -> Path:
        """Get path to second test project"""
        return self.test_material_path / "Test_v17_2" / "NAME_2.ap17"
    
    @property
    def test_blocks_dir(self) -> Path:
        """Get path to test blocks directory"""
        return self.test_material_path / "exported_blocks"
    
    def __repr__(self) -> str:
        return f"Config(path={self.config_path})"


# Global configuration instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config

def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file"""
    global _config
    _config = Config(config_path)
    return _config


if __name__ == "__main__":
    # Test configuration loading
    print("Testing configuration management...")
    
    try:
        config = get_config()
        print(f"\nConfiguration loaded successfully!")
        print(f"Project Store Path: {config.project_store_path}")
        print(f"Master Program Name: {config.master_prg_name}")
        print(f"Test Program Name: {config.test_prg_name}")
        print(f"Test Material Path: {config.test_material_path}")
        print(f"Test Project 1: {config.test_project_1}")
        print(f"Test Project 2: {config.test_project_2}")
        print(f"Test Blocks Directory: {config.test_blocks_dir}")
        
        # Validate configuration
        if config.validate_config():
            print("\nConfiguration validation: PASSED")
        else:
            print("\nConfiguration validation: FAILED")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()