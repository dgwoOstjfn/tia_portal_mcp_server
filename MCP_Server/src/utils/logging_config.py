"""
Production-ready logging configuration for TIA Portal MCP Server
"""
import logging
import logging.handlers
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import queue
import threading


class StructuredFormatter(logging.Formatter):
    """JSON structured logging formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
            
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
            
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
            
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """Enhanced console formatter with colors"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and sys.stdout.isatty()
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors for console"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        if self.use_colors:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
            levelname = f"{color}{record.levelname:8}{reset}"
        else:
            levelname = f"{record.levelname:8}"
            
        message = record.getMessage()
        
        if hasattr(record, "session_id"):
            message = f"[{record.session_id[:8]}] {message}"
            
        formatted = f"{timestamp} | {levelname} | {record.name:20} | {message}"
        
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
            
        return formatted


class LogAggregator:
    """Aggregates similar log messages to prevent spam"""
    
    def __init__(self, window_seconds: int = 60, max_duplicates: int = 5):
        self.window_seconds = window_seconds
        self.max_duplicates = max_duplicates
        self.message_counts = {}
        self.lock = threading.Lock()
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
    def should_log(self, message: str) -> bool:
        """Check if message should be logged"""
        with self.lock:
            now = datetime.utcnow()
            key = message[:100]  # Use first 100 chars as key
            
            if key not in self.message_counts:
                self.message_counts[key] = {"count": 1, "first_seen": now}
                return True
                
            entry = self.message_counts[key]
            entry["count"] += 1
            
            return entry["count"] <= self.max_duplicates
            
    def _cleanup_loop(self):
        """Clean up old message counts"""
        import time
        while True:
            time.sleep(self.window_seconds)
            self._cleanup_old_entries()
            
    def _cleanup_old_entries(self):
        """Remove old entries from message counts"""
        with self.lock:
            now = datetime.utcnow()
            cutoff_time = (now.timestamp() - self.window_seconds)
            
            keys_to_remove = []
            for key, entry in self.message_counts.items():
                if entry["first_seen"].timestamp() < cutoff_time:
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                del self.message_counts[key]


class AggregatingFilter(logging.Filter):
    """Filter that aggregates similar messages"""
    
    def __init__(self, aggregator: LogAggregator):
        super().__init__()
        self.aggregator = aggregator
        
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter log record based on aggregation"""
        return self.aggregator.should_log(record.getMessage())


class AsyncHandler(logging.Handler):
    """Asynchronous logging handler for non-blocking logs"""
    
    def __init__(self, handler: logging.Handler):
        super().__init__()
        self.handler = handler
        self.queue = queue.Queue(-1)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        
    def _worker(self):
        """Worker thread for processing log records"""
        while True:
            try:
                record = self.queue.get()
                if record is None:
                    break
                self.handler.emit(record)
            except Exception:
                import traceback
                traceback.print_exc()
                
    def emit(self, record: logging.LogRecord):
        """Queue log record for async processing"""
        self.queue.put(record)
        
    def close(self):
        """Close handler and stop worker thread"""
        self.queue.put(None)
        self.thread.join()
        self.handler.close()
        super().close()


class LoggingConfig:
    """Production logging configuration manager"""
    
    def __init__(self, 
                 log_dir: Optional[Path] = None,
                 log_level: str = "INFO",
                 enable_file_logging: bool = True,
                 enable_console_logging: bool = True,
                 enable_structured_logging: bool = False,
                 enable_aggregation: bool = True,
                 max_bytes: int = 10485760,  # 10MB
                 backup_count: int = 5):
        """
        Initialize logging configuration
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level
            enable_file_logging: Enable file output
            enable_console_logging: Enable console output
            enable_structured_logging: Use JSON structured logging
            enable_aggregation: Enable log aggregation
            max_bytes: Max size for log files before rotation
            backup_count: Number of backup files to keep
        """
        self.log_dir = log_dir or Path("logs")
        self.log_level = getattr(logging, log_level.upper())
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.enable_structured_logging = enable_structured_logging
        self.enable_aggregation = enable_aggregation
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        self.aggregator = LogAggregator() if enable_aggregation else None
        self.handlers = []
        
    def setup(self, logger_name: Optional[str] = None):
        """
        Setup logging configuration
        
        Args:
            logger_name: Name of logger to configure (None for root)
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.log_level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create log directory if needed
        if self.enable_file_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
        # Setup handlers
        if self.enable_console_logging:
            self._add_console_handler(logger)
            
        if self.enable_file_logging:
            self._add_file_handlers(logger)
            
        return logger
        
    def _add_console_handler(self, logger: logging.Logger):
        """Add console handler to logger"""
        handler = logging.StreamHandler(sys.stdout)
        
        if self.enable_structured_logging:
            formatter = StructuredFormatter()
        else:
            formatter = ConsoleFormatter()
            
        handler.setFormatter(formatter)
        
        if self.aggregator:
            handler.addFilter(AggregatingFilter(self.aggregator))
            
        logger.addHandler(handler)
        self.handlers.append(handler)
        
    def _add_file_handlers(self, logger: logging.Logger):
        """Add file handlers to logger"""
        # Main log file
        main_log_file = self.log_dir / "tia_portal_mcp.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        
        if self.enable_structured_logging:
            main_handler.setFormatter(StructuredFormatter())
        else:
            main_handler.setFormatter(
                logging.Formatter(
                    '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
                )
            )
            
        if self.aggregator:
            main_handler.addFilter(AggregatingFilter(self.aggregator))
            
        # Wrap in async handler for non-blocking writes
        async_handler = AsyncHandler(main_handler)
        logger.addHandler(async_handler)
        self.handlers.append(async_handler)
        
        # Error log file
        error_log_file = self.log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
            )
        )
        
        logger.addHandler(error_handler)
        self.handlers.append(error_handler)
        
    def get_logger(self, name: str) -> logging.Logger:
        """Get configured logger by name"""
        logger = logging.getLogger(name)
        
        if not logger.handlers:
            self.setup(name)
            
        return logger
        
    def cleanup(self):
        """Cleanup logging resources"""
        for handler in self.handlers:
            if isinstance(handler, AsyncHandler):
                handler.close()
                

class OperationLogger:
    """Context manager for operation logging"""
    
    def __init__(self, logger: logging.Logger, operation: str, **kwargs):
        self.logger = logger
        self.operation = operation
        self.extra = kwargs
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.info(
            f"Starting operation: {self.operation}",
            extra={"operation": self.operation, **self.extra}
        )
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(
                f"Operation failed: {self.operation} ({duration:.2f}s)",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={"operation": self.operation, "duration": duration, **self.extra}
            )
        else:
            self.logger.info(
                f"Operation completed: {self.operation} ({duration:.2f}s)",
                extra={"operation": self.operation, "duration": duration, **self.extra}
            )
            
        return False


def setup_production_logging(
    log_dir: Optional[str] = None,
    log_level: str = "INFO",
    enable_structured: bool = False
) -> LoggingConfig:
    """
    Quick setup for production logging
    
    Args:
        log_dir: Directory for log files
        log_level: Logging level
        enable_structured: Enable JSON structured logging
        
    Returns:
        Configured LoggingConfig instance
    """
    config = LoggingConfig(
        log_dir=Path(log_dir) if log_dir else Path("logs"),
        log_level=log_level,
        enable_structured_logging=enable_structured,
        enable_aggregation=True
    )
    
    # Setup root logger
    config.setup()
    
    # Setup specific loggers
    for logger_name in ["tia_portal", "mcp_server", "session_manager"]:
        config.setup(logger_name)
        
    return config


if __name__ == "__main__":
    # Test logging configuration
    config = setup_production_logging(log_level="DEBUG", enable_structured=False)
    
    logger = config.get_logger("test_logger")
    
    with OperationLogger(logger, "test_operation", session_id="test123"):
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        
        # Test aggregation
        for i in range(10):
            logger.info("Repeated message")
            
        # Test error
        try:
            raise ValueError("Test error")
        except Exception:
            logger.error("Error occurred", exc_info=True)
            
    config.cleanup()