"""
MCP Configuration loader for TIA Portal MCP Server
Loads configuration from tia_portal_mcp.json
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class MCPConfig:
    """MCP Configuration manager"""
    
    def __init__(self, config_file: str = "tia_portal_mcp.json"):
        """Initialize MCP configuration
        
        Args:
            config_file: Name of the configuration file
        """
        # Find config file relative to MCP_Server directory
        self.base_dir = Path(__file__).parent.parent
        self.config_path = self.base_dir / config_file
        
        if not self.config_path.exists():
            # Try parent directory
            self.config_path = self.base_dir.parent / config_file
        
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._setup_paths()
        
    def _load_config(self) -> None:
        """Load configuration from JSON file"""
        if not self.config_path.exists():
            # Create default configuration
            self.config = self._get_default_config()
            self._save_config()
        else:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            except Exception as e:
                raise RuntimeError(f"Failed to load MCP configuration: {e}")
    
    def _save_config(self) -> None:
        """Save configuration to JSON file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "name": "tia-portal-mcp",
            "version": "1.0.0",
            "paths": {
                "tia_portal": {
                    "installation_path": "C:\\Program Files\\Siemens\\Automation\\Portal V17",
                    "dll_path": "C:\\Program Files\\Siemens\\Automation\\Portal V17\\PublicAPI\\V17\\Siemens.Engineering.dll"
                },
                "project_defaults": {
                    "store_path": "./projects",
                    "export_path": "./exports",
                    "import_path": "./imports",
                    "temp_path": "./temp"
                },
                "test_materials": {
                    "enabled": True,
                    "path": "../Test_Material"
                },
                "internal_libraries": {
                    "tia_client": "./lib/tia_portal",
                    "converters": "./lib/converters",
                    "utilities": "./lib/utils"
                }
            },
            "settings": {
                "logging": {
                    "level": "INFO"
                },
                "session": {
                    "timeout_seconds": 3600,
                    "max_concurrent": 3
                }
            }
        }
    
    def _setup_paths(self) -> None:
        """Setup Python paths for imports"""
        # Add internal library paths to Python path
        lib_paths = self.get_library_paths()
        for lib_name, lib_path in lib_paths.items():
            abs_path = self._resolve_path(lib_path)
            if abs_path.exists() and str(abs_path) not in sys.path:
                sys.path.insert(0, str(abs_path))
                # Also add parent for direct imports
                if abs_path.parent not in sys.path:
                    sys.path.insert(0, str(abs_path.parent))
    
    def _resolve_path(self, path_str: str) -> Path:
        """Resolve a path string to absolute path
        
        Args:
            path_str: Path string (can be relative)
            
        Returns:
            Absolute Path object
        """
        path = Path(path_str)
        if not path.is_absolute():
            # Resolve relative to base directory
            path = (self.base_dir / path).resolve()
        return path
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation
        
        Args:
            key: Configuration key (e.g., "paths.tia_portal.dll_path")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_tia_portal_dll(self) -> str:
        """Get TIA Portal DLL path"""
        dll_path = self.get("paths.tia_portal.dll_path", "")
        if not dll_path:
            # Try to find it automatically
            possible_paths = [
                "C:\\Program Files\\Siemens\\Automation\\Portal V17\\PublicAPI\\V17\\Siemens.Engineering.dll",
                "C:\\Program Files\\Siemens\\Automation\\Portal V16\\PublicAPI\\V16\\Siemens.Engineering.dll",
                "C:\\Program Files\\Siemens\\Automation\\Portal V15.1\\PublicAPI\\V15.1\\Siemens.Engineering.dll"
            ]
            for path in possible_paths:
                if Path(path).exists():
                    return path
        return dll_path
    
    def get_project_store_path(self) -> Path:
        """Get project store path"""
        path_str = self.get("paths.project_defaults.store_path", "./projects")
        return self._resolve_path(path_str)
    
    def get_export_path(self) -> Path:
        """Get default export path"""
        path_str = self.get("paths.project_defaults.export_path", "./exports")
        return self._resolve_path(path_str)
    
    def get_test_material_path(self) -> Path:
        """Get test material path"""
        path_str = self.get("paths.test_materials.path", "../Test_Material")
        return self._resolve_path(path_str)
    
    def get_test_projects(self) -> list:
        """Get list of test projects"""
        projects = self.get("paths.test_materials.projects", [])
        result = []
        for project in projects:
            if isinstance(project, dict) and "path" in project:
                project["resolved_path"] = str(self._resolve_path(project["path"]))
                result.append(project)
        return result
    
    def get_library_paths(self) -> Dict[str, str]:
        """Get internal library paths"""
        return self.get("paths.internal_libraries", {})
    
    def get_session_timeout(self) -> int:
        """Get session timeout in seconds"""
        return self.get("settings.session.timeout_seconds", 3600)
    
    def get_max_sessions(self) -> int:
        """Get maximum concurrent sessions"""
        return self.get("settings.session.max_concurrent", 3)
    
    def get_logging_level(self) -> str:
        """Get logging level"""
        return self.get("settings.logging.level", "INFO")
    
    def update(self, key: str, value: Any) -> None:
        """Update configuration value
        
        Args:
            key: Configuration key (dot notation)
            value: New value
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Save updated configuration
        self._save_config()
    
    def __repr__(self) -> str:
        return f"MCPConfig(path={self.config_path})"


# Global configuration instance
_mcp_config: Optional[MCPConfig] = None

def get_mcp_config() -> MCPConfig:
    """Get global MCP configuration instance"""
    global _mcp_config
    if _mcp_config is None:
        _mcp_config = MCPConfig()
    return _mcp_config

def reload_mcp_config(config_file: str = "tia_portal_mcp.json") -> MCPConfig:
    """Reload MCP configuration"""
    global _mcp_config
    _mcp_config = MCPConfig(config_file)
    return _mcp_config


if __name__ == "__main__":
    # Test configuration loading
    print("Testing MCP configuration management...")
    
    try:
        config = get_mcp_config()
        print(f"\nConfiguration loaded from: {config.config_path}")
        print(f"TIA Portal DLL: {config.get_tia_portal_dll()}")
        print(f"Project Store Path: {config.get_project_store_path()}")
        print(f"Export Path: {config.get_export_path()}")
        print(f"Test Material Path: {config.get_test_material_path()}")
        print(f"Session Timeout: {config.get_session_timeout()} seconds")
        print(f"Max Sessions: {config.get_max_sessions()}")
        print(f"Logging Level: {config.get_logging_level()}")
        
        print("\nTest Projects:")
        for project in config.get_test_projects():
            print(f"  - {project.get('name', 'Unknown')}: {project.get('resolved_path', 'N/A')}")
        
        print("\nLibrary Paths:")
        for lib_name, lib_path in config.get_library_paths().items():
            resolved = config._resolve_path(lib_path)
            print(f"  - {lib_name}: {resolved} (exists: {resolved.exists()})")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()