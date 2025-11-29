"""
Cache management for TIA Portal MCP Server
"""
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """Represents a cached item"""
    file_path: Path
    last_modified: float
    item_type: str  # 'block', 'udt', etc.
    metadata: Dict[str, Any] = field(default_factory=dict)

class CacheManager:
    """Manages caching of project data for a session"""
    
    def __init__(self, session_id: str, cache_dir: Optional[Path] = None):
        """Initialize cache manager
        
        Args:
            session_id: Session ID owner of this cache
            cache_dir: Base directory for cache (default: ./cache)
        """
        self.session_id = session_id
        self.base_dir = cache_dir or Path("./cache")
        self.session_cache_dir = self.base_dir / session_id
        self.entries: Dict[str, CacheEntry] = {}
        
        # Create cache directory
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not self.session_cache_dir.exists():
            self.session_cache_dir.mkdir(parents=True, exist_ok=True)
            
    def get_entry(self, key: str) -> Optional[CacheEntry]:
        """Get cache entry by key (e.g., block name)"""
        entry = self.entries.get(key)
        if entry and entry.file_path.exists():
            return entry
        return None
        
    def add_entry(self, key: str, file_path: Path, item_type: str, metadata: Dict[str, Any] = None):
        """Add entry to cache"""
        # If file is not already in session cache dir, copy it there
        target_path = file_path
        if self.session_cache_dir not in file_path.parents:
            target_path = self.session_cache_dir / file_path.name
            try:
                shutil.copy2(file_path, target_path)
            except Exception as e:
                logger.warning(f"Failed to copy file to cache: {e}")
                # Fallback to original path if copy fails, but prefer managing our own copy
                target_path = file_path
                
        self.entries[key] = CacheEntry(
            file_path=target_path,
            last_modified=target_path.stat().st_mtime if target_path.exists() else 0,
            item_type=item_type,
            metadata=metadata or {}
        )
        
    def clear_cache(self):
        """Clear all cache for this session"""
        self.entries.clear()
        if self.session_cache_dir.exists():
            try:
                shutil.rmtree(self.session_cache_dir)
                self._ensure_cache_dir()
            except Exception as e:
                logger.error(f"Failed to clear cache directory: {e}")

    def cleanup(self):
        """Cleanup resources (call on session close)"""
        self.clear_cache()
        try:
            if self.session_cache_dir.exists():
                self.session_cache_dir.rmdir()
        except Exception:
            pass

