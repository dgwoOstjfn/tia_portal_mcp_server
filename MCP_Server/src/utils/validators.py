"""
Input validation utilities for TIA Portal MCP Server
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Validation error with details"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value
        self.details = {
            "field": field,
            "value": str(value)[:100] if value is not None else None,
            "message": message
        }


class Validator:
    """Base validator class"""
    
    def __init__(self, error_message: str = None):
        self.error_message = error_message or "Validation failed"
        
    def validate(self, value: Any) -> bool:
        """Validate value"""
        raise NotImplementedError
        
    def __call__(self, value: Any) -> bool:
        """Make validator callable"""
        return self.validate(value)
        
    def raise_if_invalid(self, value: Any, field: str = None):
        """Raise ValidationError if value is invalid"""
        if not self.validate(value):
            raise ValidationError(self.error_message, field, value)


class PathValidator(Validator):
    """Validate file system paths"""
    
    def __init__(self, 
                 must_exist: bool = False,
                 must_be_file: bool = False,
                 must_be_dir: bool = False,
                 extensions: List[str] = None,
                 allow_relative: bool = True):
        super().__init__()
        self.must_exist = must_exist
        self.must_be_file = must_be_file
        self.must_be_dir = must_be_dir
        self.extensions = extensions
        self.allow_relative = allow_relative
        
    def validate(self, value: Any) -> bool:
        """Validate path"""
        if not value:
            return False
            
        try:
            path = Path(value)
            
            # Check if path is absolute when required
            if not self.allow_relative and not path.is_absolute():
                self.error_message = f"Path must be absolute: {value}"
                return False
                
            # Check existence
            if self.must_exist and not path.exists():
                self.error_message = f"Path does not exist: {value}"
                return False
                
            # Check file type
            if self.must_be_file and path.exists() and not path.is_file():
                self.error_message = f"Path is not a file: {value}"
                return False
                
            if self.must_be_dir and path.exists() and not path.is_dir():
                self.error_message = f"Path is not a directory: {value}"
                return False
                
            # Check extension
            if self.extensions and path.suffix.lower() not in [ext.lower() for ext in self.extensions]:
                self.error_message = f"Invalid file extension. Expected: {self.extensions}, got: {path.suffix}"
                return False
                
            return True
            
        except Exception as e:
            self.error_message = f"Invalid path: {e}"
            return False


class TIAProjectPathValidator(PathValidator):
    """Validate TIA Portal project paths"""
    
    def __init__(self, must_exist: bool = True):
        super().__init__(
            must_exist=must_exist,
            extensions=['.ap15', '.ap15_1', '.ap16', '.ap17', '.ap18', '.ap19', '.ap20']
        )
        
    def validate(self, value: Any) -> bool:
        """Validate TIA project path"""
        if not value:
            return False
            
        path = Path(value)
        
        # Check if it's a directory containing a project file
        if path.is_dir():
            project_files = list(path.glob("*.ap*"))
            if not project_files:
                self.error_message = f"No TIA Portal project files found in directory: {value}"
                return False
            return True
            
        # Check if it's a project file
        return super().validate(value)


class StringValidator(Validator):
    """Validate string values"""
    
    def __init__(self,
                 min_length: int = None,
                 max_length: int = None,
                 pattern: str = None,
                 allowed_chars: str = None,
                 forbidden_chars: str = None):
        super().__init__()
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.allowed_chars = set(allowed_chars) if allowed_chars else None
        self.forbidden_chars = set(forbidden_chars) if forbidden_chars else None
        
    def validate(self, value: Any) -> bool:
        """Validate string"""
        if not isinstance(value, str):
            self.error_message = f"Value must be a string, got {type(value).__name__}"
            return False
            
        # Check length
        if self.min_length is not None and len(value) < self.min_length:
            self.error_message = f"String too short. Min length: {self.min_length}, got: {len(value)}"
            return False
            
        if self.max_length is not None and len(value) > self.max_length:
            self.error_message = f"String too long. Max length: {self.max_length}, got: {len(value)}"
            return False
            
        # Check pattern
        if self.pattern and not self.pattern.match(value):
            self.error_message = f"String does not match required pattern"
            return False
            
        # Check allowed characters
        if self.allowed_chars:
            invalid_chars = set(value) - self.allowed_chars
            if invalid_chars:
                self.error_message = f"String contains invalid characters: {invalid_chars}"
                return False
                
        # Check forbidden characters
        if self.forbidden_chars:
            found_forbidden = set(value) & self.forbidden_chars
            if found_forbidden:
                self.error_message = f"String contains forbidden characters: {found_forbidden}"
                return False
                
        return True


class BlockNameValidator(StringValidator):
    """Validate TIA Portal block names"""
    
    def __init__(self):
        super().__init__(
            min_length=1,
            max_length=128,
            pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        )
        self.error_message = "Invalid block name. Must start with letter or underscore and contain only alphanumeric characters and underscores"


class SessionIdValidator(StringValidator):
    """Validate session IDs"""
    
    def __init__(self):
        super().__init__(
            pattern=r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        )
        self.error_message = "Invalid session ID format. Expected UUID format"


class NumberValidator(Validator):
    """Validate numeric values"""
    
    def __init__(self,
                 min_value: float = None,
                 max_value: float = None,
                 allow_negative: bool = True,
                 allow_zero: bool = True,
                 must_be_int: bool = False):
        super().__init__()
        self.min_value = min_value
        self.max_value = max_value
        self.allow_negative = allow_negative
        self.allow_zero = allow_zero
        self.must_be_int = must_be_int
        
    def validate(self, value: Any) -> bool:
        """Validate number"""
        try:
            if self.must_be_int:
                if not isinstance(value, int):
                    value = int(value)
            else:
                value = float(value)
                
            if not self.allow_negative and value < 0:
                self.error_message = "Negative values not allowed"
                return False
                
            if not self.allow_zero and value == 0:
                self.error_message = "Zero value not allowed"
                return False
                
            if self.min_value is not None and value < self.min_value:
                self.error_message = f"Value too small. Min: {self.min_value}, got: {value}"
                return False
                
            if self.max_value is not None and value > self.max_value:
                self.error_message = f"Value too large. Max: {self.max_value}, got: {value}"
                return False
                
            return True
            
        except (ValueError, TypeError):
            self.error_message = f"Invalid numeric value: {value}"
            return False


class ListValidator(Validator):
    """Validate list values"""
    
    def __init__(self,
                 min_length: int = None,
                 max_length: int = None,
                 item_validator: Validator = None,
                 unique_items: bool = False):
        super().__init__()
        self.min_length = min_length
        self.max_length = max_length
        self.item_validator = item_validator
        self.unique_items = unique_items
        
    def validate(self, value: Any) -> bool:
        """Validate list"""
        if not isinstance(value, (list, tuple)):
            self.error_message = f"Value must be a list, got {type(value).__name__}"
            return False
            
        # Check length
        if self.min_length is not None and len(value) < self.min_length:
            self.error_message = f"List too short. Min length: {self.min_length}, got: {len(value)}"
            return False
            
        if self.max_length is not None and len(value) > self.max_length:
            self.error_message = f"List too long. Max length: {self.max_length}, got: {len(value)}"
            return False
            
        # Check uniqueness
        if self.unique_items and len(value) != len(set(value)):
            self.error_message = "List must contain unique items"
            return False
            
        # Validate items
        if self.item_validator:
            for i, item in enumerate(value):
                if not self.item_validator.validate(item):
                    self.error_message = f"Invalid item at index {i}: {self.item_validator.error_message}"
                    return False
                    
        return True


class DictValidator(Validator):
    """Validate dictionary values"""
    
    def __init__(self,
                 required_keys: List[str] = None,
                 optional_keys: List[str] = None,
                 key_validators: Dict[str, Validator] = None):
        super().__init__()
        self.required_keys = required_keys or []
        self.optional_keys = optional_keys or []
        self.key_validators = key_validators or {}
        
    def validate(self, value: Any) -> bool:
        """Validate dictionary"""
        if not isinstance(value, dict):
            self.error_message = f"Value must be a dictionary, got {type(value).__name__}"
            return False
            
        # Check required keys
        for key in self.required_keys:
            if key not in value:
                self.error_message = f"Missing required key: {key}"
                return False
                
        # Check for unexpected keys
        allowed_keys = set(self.required_keys + self.optional_keys)
        if allowed_keys:
            unexpected_keys = set(value.keys()) - allowed_keys
            if unexpected_keys:
                self.error_message = f"Unexpected keys: {unexpected_keys}"
                return False
                
        # Validate specific keys
        for key, validator in self.key_validators.items():
            if key in value:
                if not validator.validate(value[key]):
                    self.error_message = f"Invalid value for key '{key}': {validator.error_message}"
                    return False
                    
        return True


class InputSanitizer:
    """Sanitize input values"""
    
    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitize file system path"""
        if not path:
            return path
            
        # Convert to Path and resolve
        p = Path(path)
        
        # Remove potentially dangerous path components
        parts = []
        for part in p.parts:
            # Remove null bytes
            part = part.replace('\x00', '')
            # Remove control characters
            part = ''.join(c for c in part if ord(c) >= 32)
            if part and part not in ['.', '..']:
                parts.append(part)
                
        # Reconstruct path
        if p.is_absolute():
            return str(Path(p.anchor).joinpath(*parts))
        else:
            return str(Path(*parts))
            
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for file system"""
        if not filename:
            return filename
            
        # Remove invalid characters
        invalid_chars = '<>:"|?*\x00'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Limit length
        max_length = 255
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            filename = name[:max_length - len(ext)] + ext
            
        return filename
        
    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """Sanitize general string input"""
        if not value:
            return value
            
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove control characters except newline and tab
        value = ''.join(c for c in value if ord(c) >= 32 or c in '\n\t')
        
        # Limit length
        if len(value) > max_length:
            value = value[:max_length]
            
        return value.strip()
        
    @staticmethod
    def sanitize_block_name(name: str) -> str:
        """Sanitize TIA Portal block name"""
        if not name:
            return name
            
        # Remove invalid characters
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        
        # Ensure it starts with letter or underscore
        if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
            sanitized = '_' + sanitized
            
        # Limit length
        max_length = 128
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            
        return sanitized


def validate_input(validators: Dict[str, Validator]):
    """
    Decorator for input validation
    
    Args:
        validators: Dictionary mapping parameter names to validators
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each parameter
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    try:
                        validator.raise_if_invalid(value, param_name)
                    except ValidationError as e:
                        logger.error(f"Validation failed for {func.__name__}: {e}")
                        raise
                        
            return func(*args, **kwargs)
            
        return wrapper
    return decorator


def sanitize_input(sanitizers: Dict[str, Callable]):
    """
    Decorator for input sanitization
    
    Args:
        sanitizers: Dictionary mapping parameter names to sanitizer functions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Sanitize each parameter
            for param_name, sanitizer in sanitizers.items():
                if param_name in bound_args.arguments:
                    original_value = bound_args.arguments[param_name]
                    sanitized_value = sanitizer(original_value)
                    bound_args.arguments[param_name] = sanitized_value
                    
                    if original_value != sanitized_value:
                        logger.debug(f"Sanitized {param_name} in {func.__name__}")
                        
            return func(*bound_args.args, **bound_args.kwargs)
            
        return wrapper
    return decorator


# Pre-configured validators
VALIDATORS = {
    "project_path": TIAProjectPathValidator(must_exist=True),
    "export_path": PathValidator(must_be_dir=True),
    "import_path": PathValidator(must_exist=True),
    "block_name": BlockNameValidator(),
    "session_id": SessionIdValidator(),
    "timeout": NumberValidator(min_value=0, max_value=3600, must_be_int=True),
    "max_retries": NumberValidator(min_value=0, max_value=10, must_be_int=True)
}


if __name__ == "__main__":
    # Test validators
    print("Testing validators...")
    
    # Test path validator
    path_validator = PathValidator(must_exist=False, must_be_file=False)
    assert path_validator.validate("/path/to/file.txt")
    assert not path_validator.validate("")
    
    # Test string validator
    string_validator = StringValidator(min_length=3, max_length=10)
    assert string_validator.validate("hello")
    assert not string_validator.validate("hi")
    assert not string_validator.validate("this is too long")
    
    # Test block name validator
    block_validator = BlockNameValidator()
    assert block_validator.validate("Main_Block_1")
    assert not block_validator.validate("123_Invalid")
    assert not block_validator.validate("Block-Name")
    
    # Test sanitizers
    print("\nTesting sanitizers...")
    assert InputSanitizer.sanitize_filename("file<name>.txt") == "file_name_.txt"
    assert InputSanitizer.sanitize_block_name("123-block name") == "_123_block_name"
    assert InputSanitizer.sanitize_path("/path/../to/./file") == "/path/to/file" or InputSanitizer.sanitize_path("/path/../to/./file") == "\\path\\to\\file"
    
    print("\nAll tests passed!")