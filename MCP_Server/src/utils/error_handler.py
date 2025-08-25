"""
Production-ready error handling for TIA Portal MCP Server
"""
import logging
import traceback
import sys
from typing import Any, Dict, Optional, Type, Callable
from functools import wraps
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    CONNECTION = "connection"
    VALIDATION = "validation"
    PERMISSION = "permission"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    CONFIGURATION = "configuration"
    OPERATION = "operation"
    UNKNOWN = "unknown"


class TIAPortalError(Exception):
    """Base exception for TIA Portal operations"""
    def __init__(self, 
                 message: str, 
                 category: ErrorCategory = ErrorCategory.UNKNOWN,
                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 details: Optional[Dict[str, Any]] = None,
                 original_error: Optional[Exception] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.utcnow().isoformat()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization"""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp,
            "original_error": str(self.original_error) if self.original_error else None
        }


class ConnectionError(TIAPortalError):
    """TIA Portal connection errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.CONNECTION, ErrorSeverity.HIGH, details)


class ValidationError(TIAPortalError):
    """Input validation errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.VALIDATION, ErrorSeverity.LOW, details)


class PermissionError(TIAPortalError):
    """Permission and access errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.PERMISSION, ErrorSeverity.HIGH, details)


class ResourceError(TIAPortalError):
    """Resource availability errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.RESOURCE, ErrorSeverity.MEDIUM, details)


class TimeoutError(TIAPortalError):
    """Operation timeout errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.TIMEOUT, ErrorSeverity.MEDIUM, details)


class ConfigurationError(TIAPortalError):
    """Configuration errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH, details)


class OperationError(TIAPortalError):
    """General operation errors"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.OPERATION, ErrorSeverity.MEDIUM, details)


class ErrorHandler:
    """Centralized error handling with recovery strategies"""
    
    def __init__(self):
        self.error_count = {}
        self.recovery_strategies = {}
        self._setup_default_strategies()
        
    def _setup_default_strategies(self):
        """Setup default recovery strategies"""
        self.recovery_strategies[ErrorCategory.CONNECTION] = self._recover_connection
        self.recovery_strategies[ErrorCategory.TIMEOUT] = self._recover_timeout
        self.recovery_strategies[ErrorCategory.RESOURCE] = self._recover_resource
        
    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle an error with appropriate logging and recovery
        
        Args:
            error: The exception to handle
            context: Additional context information
            
        Returns:
            Error information dictionary
        """
        error_info = self._extract_error_info(error, context)
        self._log_error(error_info)
        self._update_error_statistics(error_info)
        
        recovery_action = self._determine_recovery_action(error_info)
        if recovery_action:
            error_info["recovery_action"] = recovery_action
            
        return error_info
        
    def _extract_error_info(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extract structured information from an error"""
        if isinstance(error, TIAPortalError):
            error_info = error.to_dict()
        else:
            error_info = {
                "error": error.__class__.__name__,
                "message": str(error),
                "category": self._classify_error(error).value,
                "severity": self._determine_severity(error).value,
                "timestamp": datetime.utcnow().isoformat(),
                "traceback": traceback.format_exc()
            }
            
        if context:
            error_info["context"] = context
            
        return error_info
        
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify an error into a category"""
        error_msg = str(error).lower()
        
        if "connection" in error_msg or "connect" in error_msg or "com" in error_msg:
            return ErrorCategory.CONNECTION
        elif "timeout" in error_msg or "timed out" in error_msg:
            return ErrorCategory.TIMEOUT
        elif "permission" in error_msg or "access" in error_msg or "denied" in error_msg:
            return ErrorCategory.PERMISSION
        elif "not found" in error_msg or "does not exist" in error_msg:
            return ErrorCategory.RESOURCE
        elif "invalid" in error_msg or "validation" in error_msg:
            return ErrorCategory.VALIDATION
        elif "config" in error_msg or "setting" in error_msg:
            return ErrorCategory.CONFIGURATION
        else:
            return ErrorCategory.UNKNOWN
            
    def _determine_severity(self, error: Exception) -> ErrorSeverity:
        """Determine error severity"""
        category = self._classify_error(error)
        
        severity_map = {
            ErrorCategory.CONNECTION: ErrorSeverity.HIGH,
            ErrorCategory.PERMISSION: ErrorSeverity.HIGH,
            ErrorCategory.CONFIGURATION: ErrorSeverity.HIGH,
            ErrorCategory.TIMEOUT: ErrorSeverity.MEDIUM,
            ErrorCategory.RESOURCE: ErrorSeverity.MEDIUM,
            ErrorCategory.OPERATION: ErrorSeverity.MEDIUM,
            ErrorCategory.VALIDATION: ErrorSeverity.LOW,
            ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM
        }
        
        return severity_map.get(category, ErrorSeverity.MEDIUM)
        
    def _log_error(self, error_info: Dict[str, Any]):
        """Log error with appropriate level"""
        severity = ErrorSeverity(error_info.get("severity", "medium"))
        message = f"[{error_info['category']}] {error_info['message']}"
        
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(message, extra=error_info)
        elif severity == ErrorSeverity.HIGH:
            logger.error(message, extra=error_info)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(message, extra=error_info)
        else:
            logger.info(message, extra=error_info)
            
    def _update_error_statistics(self, error_info: Dict[str, Any]):
        """Update error statistics for monitoring"""
        category = error_info.get("category", "unknown")
        if category not in self.error_count:
            self.error_count[category] = 0
        self.error_count[category] += 1
        
    def _determine_recovery_action(self, error_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Determine recovery action based on error type"""
        category = ErrorCategory(error_info.get("category", "unknown"))
        
        if category in self.recovery_strategies:
            return self.recovery_strategies[category](error_info)
        return None
        
    def _recover_connection(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Recovery strategy for connection errors"""
        return {
            "action": "reconnect",
            "delay": 5,
            "max_retries": 3,
            "message": "Will attempt to reconnect to TIA Portal"
        }
        
    def _recover_timeout(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Recovery strategy for timeout errors"""
        return {
            "action": "retry",
            "delay": 2,
            "max_retries": 2,
            "message": "Will retry operation with increased timeout"
        }
        
    def _recover_resource(self, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """Recovery strategy for resource errors"""
        return {
            "action": "wait_and_retry",
            "delay": 10,
            "max_retries": 1,
            "message": "Will wait for resource availability"
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "error_counts": self.error_count,
            "total_errors": sum(self.error_count.values())
        }


def with_error_handling(
    default_return=None,
    reraise: bool = False,
    category: Optional[ErrorCategory] = None
):
    """
    Decorator for automatic error handling
    
    Args:
        default_return: Default value to return on error
        reraise: Whether to reraise the exception after handling
        category: Override error category
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_handler = ErrorHandler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                
                if category:
                    if isinstance(e, TIAPortalError):
                        e.category = category
                        
                error_info = error_handler.handle_error(e, context)
                
                if reraise:
                    raise
                    
                return default_return
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_handler = ErrorHandler()
                context = {
                    "function": func.__name__,
                    "args": str(args)[:200],
                    "kwargs": str(kwargs)[:200]
                }
                
                if category:
                    if isinstance(e, TIAPortalError):
                        e.category = category
                        
                error_info = error_handler.handle_error(e, context)
                
                if reraise:
                    raise
                    
                return default_return
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


def validate_input(validators: Dict[str, Callable]):
    """
    Decorator for input validation
    
    Args:
        validators: Dictionary of parameter names to validation functions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValidationError(
                            f"Invalid value for parameter '{param_name}': {value}",
                            details={"parameter": param_name, "value": str(value)[:100]}
                        )
            return await func(*args, **kwargs)
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            for param_name, validator in validators.items():
                if param_name in kwargs:
                    value = kwargs[param_name]
                    if not validator(value):
                        raise ValidationError(
                            f"Invalid value for parameter '{param_name}': {value}",
                            details={"parameter": param_name, "value": str(value)[:100]}
                        )
            return func(*args, **kwargs)
            
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


import asyncio


class RetryPolicy:
    """Retry policy for operations"""
    
    def __init__(self, 
                 max_retries: int = 3,
                 initial_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt"""
        delay = min(self.initial_delay * (self.exponential_base ** attempt), self.max_delay)
        
        if self.jitter:
            import random
            delay = delay * (0.5 + random.random())
            
        return delay


def with_retry(policy: Optional[RetryPolicy] = None, 
               retryable_errors: Optional[tuple] = None):
    """
    Decorator for automatic retry logic
    
    Args:
        policy: Retry policy to use
        retryable_errors: Tuple of exception types to retry on
    """
    if policy is None:
        policy = RetryPolicy()
        
    if retryable_errors is None:
        retryable_errors = (ConnectionError, TimeoutError, ResourceError)
        
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(policy.max_retries):
                try:
                    return await func(*args, **kwargs)
                except retryable_errors as e:
                    last_error = e
                    if attempt < policy.max_retries - 1:
                        delay = policy.calculate_delay(attempt)
                        logger.warning(f"Retry {attempt + 1}/{policy.max_retries} after {delay:.2f}s: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {policy.max_retries} retries failed")
                        raise
                except Exception:
                    raise
                    
            if last_error:
                raise last_error
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            last_error = None
            
            for attempt in range(policy.max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_error = e
                    if attempt < policy.max_retries - 1:
                        delay = policy.calculate_delay(attempt)
                        logger.warning(f"Retry {attempt + 1}/{policy.max_retries} after {delay:.2f}s: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"All {policy.max_retries} retries failed")
                        raise
                except Exception:
                    raise
                    
            if last_error:
                raise last_error
                
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    @with_error_handling(default_return=None, reraise=False)
    def test_function():
        raise ConnectionError("Failed to connect to TIA Portal")
        
    @with_retry(policy=RetryPolicy(max_retries=2, initial_delay=0.5))
    def test_retry():
        import random
        if random.random() < 0.7:
            raise ConnectionError("Random connection failure")
        return "Success"
        
    print("Testing error handling...")
    result = test_function()
    print(f"Result: {result}")
    
    print("\nTesting retry logic...")
    try:
        result = test_retry()
        print(f"Result: {result}")
    except Exception as e:
        print(f"Failed after retries: {e}")