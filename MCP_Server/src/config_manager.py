"""
Production configuration management for TIA Portal MCP Server
"""
import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field, asdict
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Deployment environments"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class TIAPortalConfig:
    """TIA Portal specific configuration"""
    installation_path: str = "C:\\Program Files\\Siemens\\Automation\\Portal V17"
    dll_path: str = "C:\\Program Files\\Siemens\\Automation\\Portal V17\\PublicAPI\\V17\\Siemens.Engineering.dll"
    version: str = "V17"
    max_projects: int = 5
    project_timeout: int = 3600
    
    def validate(self) -> List[str]:
        """Validate TIA Portal configuration"""
        errors = []
        
        if not Path(self.dll_path).exists():
            errors.append(f"TIA Portal DLL not found: {self.dll_path}")
            
        if not Path(self.installation_path).exists():
            errors.append(f"TIA Portal installation not found: {self.installation_path}")
            
        return errors


@dataclass
class SessionConfig:
    """Session management configuration"""
    timeout_seconds: int = 1800
    max_concurrent: int = 5
    cleanup_interval: int = 300
    enable_auto_cleanup: bool = True
    
    def validate(self) -> List[str]:
        """Validate session configuration"""
        errors = []
        
        if self.timeout_seconds < 60:
            errors.append("Session timeout must be at least 60 seconds")
            
        if self.max_concurrent < 1:
            errors.append("Max concurrent sessions must be at least 1")
            
        return errors


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    file_enabled: bool = True
    console_enabled: bool = True
    structured: bool = False
    log_dir: str = "logs"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    
    def validate(self) -> List[str]:
        """Validate logging configuration"""
        errors = []
        
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level not in valid_levels:
            errors.append(f"Invalid log level: {self.level}")
            
        return errors


@dataclass
class PerformanceConfig:
    """Performance optimization configuration"""
    enable_caching: bool = True
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1000
    enable_monitoring: bool = True
    monitoring_history_size: int = 1000
    enable_rate_limiting: bool = False
    rate_limit_calls: int = 100
    rate_limit_window: float = 60.0
    batch_processing_size: int = 100
    batch_flush_interval: float = 5.0
    
    def validate(self) -> List[str]:
        """Validate performance configuration"""
        errors = []
        
        if self.cache_ttl_seconds < 0:
            errors.append("Cache TTL must be non-negative")
            
        if self.rate_limit_calls < 1:
            errors.append("Rate limit calls must be at least 1")
            
        return errors


@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_authentication: bool = False
    api_key: Optional[str] = None
    allowed_hosts: List[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    enable_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    max_request_size: int = 10485760  # 10MB
    
    def validate(self) -> List[str]:
        """Validate security configuration"""
        errors = []
        
        if self.enable_authentication and not self.api_key:
            errors.append("API key required when authentication is enabled")
            
        if self.enable_ssl:
            if not self.ssl_cert_path or not Path(self.ssl_cert_path).exists():
                errors.append("SSL certificate not found")
            if not self.ssl_key_path or not Path(self.ssl_key_path).exists():
                errors.append("SSL key not found")
                
        return errors


@dataclass
class PathConfig:
    """Path configuration"""
    project_store: str = "./projects"
    export_path: str = "./exports"
    import_path: str = "./imports"
    temp_path: str = "./temp"
    test_materials: str = "../Test_Material"
    
    def validate(self) -> List[str]:
        """Validate path configuration"""
        errors = []
        
        # Create directories if they don't exist
        for path_name, path_value in asdict(self).items():
            path = Path(path_value)
            if not path.exists():
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created directory: {path}")
                except Exception as e:
                    errors.append(f"Failed to create {path_name} directory: {e}")
                    
        return errors


@dataclass
class ServerConfig:
    """Main server configuration"""
    name: str = "tia-portal-mcp-server"
    version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    host: str = "localhost"
    port: int = 5000
    
    # Sub-configurations
    tia_portal: TIAPortalConfig = field(default_factory=TIAPortalConfig)
    session: SessionConfig = field(default_factory=SessionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    
    # Feature flags
    features: Dict[str, bool] = field(default_factory=lambda: {
        "block_operations": True,
        "compilation": True,
        "tag_operations": True,
        "udt_operations": True,
        "conversion": True,
        "diagnostics": True
    })
    
    def validate(self) -> Dict[str, List[str]]:
        """Validate entire configuration"""
        all_errors = {}
        
        # Validate sub-configurations
        for config_name, config_obj in [
            ("tia_portal", self.tia_portal),
            ("session", self.session),
            ("logging", self.logging),
            ("performance", self.performance),
            ("security", self.security),
            ("paths", self.paths)
        ]:
            errors = config_obj.validate()
            if errors:
                all_errors[config_name] = errors
                
        return all_errors
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config_dict = asdict(self)
        config_dict["environment"] = self.environment.value
        return config_dict
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConfig':
        """Create configuration from dictionary"""
        # Handle environment enum
        if "environment" in data:
            data["environment"] = Environment(data["environment"])
            
        # Handle nested configurations
        if "tia_portal" in data:
            data["tia_portal"] = TIAPortalConfig(**data["tia_portal"])
        if "session" in data:
            data["session"] = SessionConfig(**data["session"])
        if "logging" in data:
            data["logging"] = LoggingConfig(**data["logging"])
        if "performance" in data:
            data["performance"] = PerformanceConfig(**data["performance"])
        if "security" in data:
            data["security"] = SecurityConfig(**data["security"])
        if "paths" in data:
            data["paths"] = PathConfig(**data["paths"])
            
        return cls(**data)


class ConfigManager:
    """Manage server configuration with environment support"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("config")
        self.config_dir.mkdir(exist_ok=True)
        self.config: Optional[ServerConfig] = None
        self.environment = self._detect_environment()
        
    def _detect_environment(self) -> Environment:
        """Detect current environment from env variable or default"""
        env_name = os.getenv("TIA_MCP_ENV", "development").lower()
        
        try:
            return Environment(env_name)
        except ValueError:
            logger.warning(f"Unknown environment: {env_name}, defaulting to development")
            return Environment.DEVELOPMENT
            
    def load_config(self, config_file: Optional[str] = None) -> ServerConfig:
        """Load configuration from file"""
        if config_file:
            config_path = Path(config_file)
        else:
            # Try environment-specific config first
            env_config = self.config_dir / f"config.{self.environment.value}.json"
            default_config = self.config_dir / "config.json"
            
            if env_config.exists():
                config_path = env_config
            elif default_config.exists():
                config_path = default_config
            else:
                # Create default configuration
                logger.info("No configuration found, creating default")
                self.config = ServerConfig(environment=self.environment)
                self.save_config()
                return self.config
                
        # Load configuration
        try:
            with open(config_path, 'r') as f:
                if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
                    
            self.config = ServerConfig.from_dict(data)
            logger.info(f"Configuration loaded from {config_path}")
            
            # Validate configuration
            errors = self.config.validate()
            if errors:
                logger.warning(f"Configuration validation errors: {errors}")
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self.config = ServerConfig(environment=self.environment)
            
        return self.config
        
    def save_config(self, config_file: Optional[str] = None):
        """Save configuration to file"""
        if not self.config:
            raise ValueError("No configuration to save")
            
        if config_file:
            config_path = Path(config_file)
        else:
            config_path = self.config_dir / f"config.{self.environment.value}.json"
            
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config.to_dict(), f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
            
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values"""
        if not self.config:
            self.config = ServerConfig(environment=self.environment)
            
        # Apply updates
        for key, value in updates.items():
            if hasattr(self.config, key):
                if isinstance(value, dict):
                    # Update nested configuration
                    current = getattr(self.config, key)
                    for sub_key, sub_value in value.items():
                        if hasattr(current, sub_key):
                            setattr(current, sub_key, sub_value)
                else:
                    setattr(self.config, key, value)
                    
        # Validate after update
        errors = self.config.validate()
        if errors:
            logger.warning(f"Configuration validation errors after update: {errors}")
            
    def get_config(self) -> ServerConfig:
        """Get current configuration"""
        if not self.config:
            self.load_config()
        return self.config
        
    def reload_config(self):
        """Reload configuration from file"""
        self.config = None
        return self.load_config()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_server_config() -> ServerConfig:
    """Get server configuration"""
    return get_config_manager().get_config()


if __name__ == "__main__":
    # Test configuration management
    print("Testing configuration management...")
    
    # Create configuration manager
    manager = ConfigManager()
    
    # Load or create configuration
    config = manager.load_config()
    print(f"\nEnvironment: {config.environment.value}")
    print(f"Server: {config.name} v{config.version}")
    print(f"TIA Portal DLL: {config.tia_portal.dll_path}")
    print(f"Session timeout: {config.session.timeout_seconds}s")
    print(f"Log level: {config.logging.level}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print("\nValidation errors:")
        for category, error_list in errors.items():
            for error in error_list:
                print(f"  {category}: {error}")
    else:
        print("\n✅ Configuration is valid")
        
    # Update configuration
    manager.update_config({
        "logging": {"level": "DEBUG"},
        "session": {"timeout_seconds": 3600}
    })
    
    # Save configuration
    manager.save_config()
    print("\nConfiguration saved successfully")