"""
Performance optimization utilities for TIA Portal MCP Server
"""
import time
import asyncio
import functools
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from collections import deque, defaultdict
import psutil
import gc

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for an operation"""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_before: Optional[int] = None
    memory_after: Optional[int] = None
    memory_delta: Optional[int] = None
    cpu_percent: Optional[float] = None
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self):
        """Mark operation as complete"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        if self.memory_before and self.memory_after:
            self.memory_delta = self.memory_after - self.memory_before
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "operation": self.operation,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_seconds": self.duration,
            "memory_delta_mb": self.memory_delta / 1024 / 1024 if self.memory_delta else None,
            "cpu_percent": self.cpu_percent,
            "success": self.success,
            "error": self.error,
            "metadata": self.metadata
        }


class PerformanceMonitor:
    """Monitor and track performance metrics"""
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history = deque(maxlen=max_history)
        self.operation_stats = defaultdict(lambda: {
            "count": 0,
            "total_duration": 0,
            "min_duration": float('inf'),
            "max_duration": 0,
            "avg_duration": 0,
            "errors": 0
        })
        self._lock = threading.Lock()
        
    def start_operation(self, operation: str, **metadata) -> PerformanceMetrics:
        """Start monitoring an operation"""
        metrics = PerformanceMetrics(
            operation=operation,
            start_time=time.time(),
            memory_before=self._get_memory_usage(),
            metadata=metadata
        )
        return metrics
        
    def complete_operation(self, metrics: PerformanceMetrics):
        """Complete monitoring an operation"""
        metrics.memory_after = self._get_memory_usage()
        metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
        metrics.complete()
        
        with self._lock:
            self.metrics_history.append(metrics)
            self._update_stats(metrics)
            
    def _update_stats(self, metrics: PerformanceMetrics):
        """Update operation statistics"""
        stats = self.operation_stats[metrics.operation]
        stats["count"] += 1
        
        if metrics.duration:
            stats["total_duration"] += metrics.duration
            stats["min_duration"] = min(stats["min_duration"], metrics.duration)
            stats["max_duration"] = max(stats["max_duration"], metrics.duration)
            stats["avg_duration"] = stats["total_duration"] / stats["count"]
            
        if not metrics.success:
            stats["errors"] += 1
            
    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes"""
        process = psutil.Process()
        return process.memory_info().rss
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        with self._lock:
            return {
                "total_operations": len(self.metrics_history),
                "operation_stats": dict(self.operation_stats),
                "memory_usage_mb": self._get_memory_usage() / 1024 / 1024,
                "cpu_percent": psutil.cpu_percent(interval=0.1)
            }
            
    def get_slow_operations(self, threshold_seconds: float = 5.0) -> List[PerformanceMetrics]:
        """Get operations that exceeded duration threshold"""
        with self._lock:
            return [
                m for m in self.metrics_history
                if m.duration and m.duration > threshold_seconds
            ]
            
    def clear_history(self):
        """Clear metrics history"""
        with self._lock:
            self.metrics_history.clear()
            self.operation_stats.clear()


# Global performance monitor instance
_performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor"""
    return _performance_monitor


def measure_performance(operation_name: Optional[str] = None):
    """
    Decorator to measure function performance
    
    Args:
        operation_name: Name for the operation (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        name = operation_name or func.__name__
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            metrics = monitor.start_operation(name, args_count=len(args), kwargs_count=len(kwargs))
            
            try:
                result = await func(*args, **kwargs)
                metrics.success = True
                return result
            except Exception as e:
                metrics.success = False
                metrics.error = str(e)
                raise
            finally:
                monitor.complete_operation(metrics)
                if metrics.duration > 1.0:  # Log slow operations
                    logger.warning(f"Slow operation: {name} took {metrics.duration:.2f}s")
                    
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            metrics = monitor.start_operation(name, args_count=len(args), kwargs_count=len(kwargs))
            
            try:
                result = func(*args, **kwargs)
                metrics.success = True
                return result
            except Exception as e:
                metrics.success = False
                metrics.error = str(e)
                raise
            finally:
                monitor.complete_operation(metrics)
                if metrics.duration > 1.0:  # Log slow operations
                    logger.warning(f"Slow operation: {name} took {metrics.duration:.2f}s")
                    
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator


class Cache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self, ttl_seconds: int = 300, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return value
                else:
                    del self.cache[key]
        return None
        
    def set(self, key: str, value: Any):
        """Set value in cache"""
        with self._lock:
            # Enforce max size
            if len(self.cache) >= self.max_size:
                # Remove oldest entry
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
                del self.cache[oldest_key]
                
            self.cache[key] = (value, time.time())
            
    def clear(self):
        """Clear cache"""
        with self._lock:
            self.cache.clear()
            
    def cleanup_expired(self):
        """Remove expired entries"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                k for k, (_, timestamp) in self.cache.items()
                if current_time - timestamp >= self.ttl_seconds
            ]
            for key in expired_keys:
                del self.cache[key]


def cached(ttl_seconds: int = 300, key_func: Optional[Callable] = None):
    """
    Decorator for caching function results
    
    Args:
        ttl_seconds: Time to live for cached results
        key_func: Function to generate cache key from arguments
    """
    cache = Cache(ttl_seconds=ttl_seconds)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
                
            # Check cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value
                
            # Execute function
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result)
            
            return result
            
        wrapper.cache = cache
        return wrapper
        
    return decorator


class ResourcePool:
    """Resource pool for connection management"""
    
    def __init__(self, 
                 create_func: Callable,
                 destroy_func: Optional[Callable] = None,
                 max_size: int = 10,
                 min_size: int = 1):
        self.create_func = create_func
        self.destroy_func = destroy_func
        self.max_size = max_size
        self.min_size = min_size
        self.pool: List[Any] = []
        self.in_use: List[Any] = []
        self._lock = threading.Lock()
        
        # Pre-create minimum resources
        for _ in range(min_size):
            resource = create_func()
            self.pool.append(resource)
            
    def acquire(self, timeout: float = 30.0) -> Any:
        """Acquire resource from pool"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            with self._lock:
                if self.pool:
                    resource = self.pool.pop()
                    self.in_use.append(resource)
                    return resource
                elif len(self.in_use) < self.max_size:
                    # Create new resource
                    resource = self.create_func()
                    self.in_use.append(resource)
                    return resource
                    
            time.sleep(0.1)
            
        raise TimeoutError(f"Failed to acquire resource within {timeout} seconds")
        
    def release(self, resource: Any):
        """Release resource back to pool"""
        with self._lock:
            if resource in self.in_use:
                self.in_use.remove(resource)
                self.pool.append(resource)
                
    def cleanup(self):
        """Cleanup all resources"""
        with self._lock:
            if self.destroy_func:
                for resource in self.pool + self.in_use:
                    try:
                        self.destroy_func(resource)
                    except Exception as e:
                        logger.error(f"Error destroying resource: {e}")
                        
            self.pool.clear()
            self.in_use.clear()


class BatchProcessor:
    """Process operations in batches for efficiency"""
    
    def __init__(self, 
                 batch_size: int = 100,
                 flush_interval: float = 5.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.batch: List[Any] = []
        self.last_flush = time.time()
        self._lock = threading.Lock()
        
    def add(self, item: Any) -> bool:
        """Add item to batch"""
        with self._lock:
            self.batch.append(item)
            
            # Check if batch should be processed
            if len(self.batch) >= self.batch_size:
                return True
            elif time.time() - self.last_flush >= self.flush_interval:
                return True
                
        return False
        
    def get_batch(self) -> List[Any]:
        """Get current batch and reset"""
        with self._lock:
            batch = self.batch.copy()
            self.batch.clear()
            self.last_flush = time.time()
            return batch


def optimize_memory():
    """Optimize memory usage"""
    # Force garbage collection
    gc.collect()
    
    # Get memory stats
    process = psutil.Process()
    memory_info = process.memory_info()
    
    logger.info(f"Memory optimization complete. Current usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    
    return {
        "memory_mb": memory_info.rss / 1024 / 1024,
        "objects_collected": gc.collect()
    }


class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: float):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self._lock = threading.Lock()
        
    def acquire(self) -> bool:
        """Check if call is allowed"""
        with self._lock:
            now = time.time()
            
            # Remove old calls outside window
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
                
            # Check if we can make a call
            if len(self.calls) < self.max_calls:
                self.calls.append(now)
                return True
                
        return False
        
    def wait_if_needed(self):
        """Wait if rate limit is exceeded"""
        while not self.acquire():
            time.sleep(0.1)


def rate_limited(max_calls: int = 10, time_window: float = 1.0):
    """
    Decorator for rate limiting function calls
    
    Args:
        max_calls: Maximum calls allowed
        time_window: Time window in seconds
    """
    limiter = RateLimiter(max_calls, time_window)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            return func(*args, **kwargs)
            
        return wrapper
        
    return decorator


if __name__ == "__main__":
    # Test performance monitoring
    @measure_performance()
    def slow_function():
        time.sleep(0.5)
        return "done"
        
    @cached(ttl_seconds=5)
    def expensive_calculation(x: int) -> int:
        time.sleep(1)
        return x * x
        
    print("Testing performance monitoring...")
    slow_function()
    
    print("\nTesting caching...")
    print(f"First call: {expensive_calculation(5)}")
    print(f"Second call (cached): {expensive_calculation(5)}")
    
    monitor = get_performance_monitor()
    stats = monitor.get_statistics()
    print(f"\nPerformance stats: {stats}")
    
    print("\nMemory optimization...")
    print(optimize_memory())