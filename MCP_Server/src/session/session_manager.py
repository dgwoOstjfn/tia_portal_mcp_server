"""
Session management for TIA Portal MCP Server
"""
import asyncio
import uuid
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from handlers.cache_handlers import CacheManager

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class TIASession:
    """Represents a TIA Portal session"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    client_wrapper: Optional[Any] = None  # TIAClientWrapper instance
    current_project: Optional[str] = None
    project_modified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    cache_manager: Optional[CacheManager] = None

    def __post_init__(self):
        """Initialize cache manager after creation"""
        if not self.cache_manager:
            self.cache_manager = CacheManager(self.session_id)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def is_expired(self, timeout_seconds: int) -> bool:
        """Check if session has expired"""
        return (time.time() - self.last_activity) > timeout_seconds
    
    @property
    def age_seconds(self) -> float:
        """Get session age in seconds"""
        return time.time() - self.created_at
    
    @property
    def idle_seconds(self) -> float:
        """Get idle time in seconds"""
        return time.time() - self.last_activity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary"""
        return {
            "session_id": self.session_id,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "last_activity": datetime.fromtimestamp(self.last_activity).isoformat(),
            "current_project": self.current_project,
            "project_modified": self.project_modified,
            "age_seconds": self.age_seconds,
            "idle_seconds": self.idle_seconds,
            "metadata": self.metadata
        }


class SessionManager:
    """Manages TIA Portal sessions for MCP Server"""
    
    def __init__(self, 
                 timeout_seconds: int = 1800,  # 30 minutes default
                 max_sessions: int = 5,
                 cleanup_interval: int = 300):  # 5 minutes
        """Initialize session manager
        
        Args:
            timeout_seconds: Session timeout in seconds
            max_sessions: Maximum concurrent sessions
            cleanup_interval: Cleanup check interval in seconds
        """
        self.sessions: Dict[str, TIASession] = {}
        self.timeout_seconds = timeout_seconds
        self.max_sessions = max_sessions
        self.cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    async def start(self):
        """Start session manager and cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session manager started")
    
    async def stop(self):
        """Stop session manager and cleanup all sessions"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        # Close all sessions
        await self.cleanup_all_sessions()
        logger.info("Session manager stopped")
    
    async def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> TIASession:
        """Create a new TIA Portal session
        
        Args:
            metadata: Optional metadata for the session
            
        Returns:
            New session object
            
        Raises:
            RuntimeError: If max sessions reached
        """
        async with self._lock:
            # Check session limit
            if len(self.sessions) >= self.max_sessions:
                # Try cleanup first
                await self._cleanup_expired_sessions()
                
                if len(self.sessions) >= self.max_sessions:
                    raise RuntimeError(
                        f"Maximum sessions ({self.max_sessions}) reached. "
                        "Please close existing sessions."
                    )
            
            # Create new session
            session_id = str(uuid.uuid4())
            session = TIASession(
                session_id=session_id,
                metadata=metadata or {}
            )
            
            # Initialize TIA client wrapper
            try:
                from ..tia_client_wrapper import TIAClientWrapper
            except ImportError:
                # For standalone testing
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent))
                from tia_client_wrapper import TIAClientWrapper
            
            session.client_wrapper = TIAClientWrapper()
            
            self.sessions[session_id] = session
            logger.info(f"Created new session: {session_id}")
            
            return session
    
    async def get_session(self, session_id: str) -> Optional[TIASession]:
        """Get session by ID
        
        Args:
            session_id: Session ID
            
        Returns:
            Session object or None if not found
        """
        session = self.sessions.get(session_id)
        if session:
            # Check if expired
            if session.is_expired(self.timeout_seconds):
                logger.warning(f"Session {session_id} has expired")
                await self.close_session(session_id)
                return None
            
            # Update activity
            session.update_activity()
        
        return session
    
    async def close_session(self, session_id: str) -> bool:
        """Close a session
        
        Args:
            session_id: Session ID to close
            
        Returns:
            True if session was closed
        """
        async with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            # Disconnect TIA client
            if session.client_wrapper:
                try:
                    await session.client_wrapper.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting session {session_id}: {e}")
            
            # Cleanup cache
            if session.cache_manager:
                try:
                    session.cache_manager.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up cache for session {session_id}: {e}")

            # Remove session
            del self.sessions[session_id]
            logger.info(f"Closed session: {session_id}")
            
            return True
    
    async def list_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active sessions
        
        Returns:
            Dictionary of session info
        """
        return {
            session_id: session.to_dict()
            for session_id, session in self.sessions.items()
        }
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        expired_sessions = [
            session_id 
            for session_id, session in self.sessions.items()
            if session.is_expired(self.timeout_seconds)
        ]
        
        for session_id in expired_sessions:
            await self.close_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")
    
    async def cleanup_all_sessions(self):
        """Clean up all sessions"""
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
    
    async def _cleanup_loop(self):
        """Background task to clean up expired sessions"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# Test functions
async def test_session_manager():
    """Test session manager functionality"""
    print("\n=== Testing Session Manager ===\n")
    
    manager = SessionManager(timeout_seconds=5, cleanup_interval=2)
    
    try:
        # Start manager
        await manager.start()
        
        # Test 1: Create sessions
        print("Test 1: Creating sessions...")
        session1 = await manager.create_session({"user": "test1"})
        print(f"Created session 1: {session1.session_id}")
        
        session2 = await manager.create_session({"user": "test2"})
        print(f"Created session 2: {session2.session_id}")
        
        # Test 2: Get session
        print("\nTest 2: Getting session...")
        retrieved = await manager.get_session(session1.session_id)
        print(f"Retrieved session: {retrieved.session_id if retrieved else 'None'}")
        
        # Test 3: List sessions
        print("\nTest 3: Listing sessions...")
        sessions = await manager.list_sessions()
        print(f"Active sessions: {len(sessions)}")
        for sid, info in sessions.items():
            print(f"  - {sid}: idle={info['idle_seconds']:.1f}s")
        
        # Test 4: Session expiration
        print("\nTest 4: Testing session expiration...")
        print("Waiting 6 seconds for sessions to expire...")
        await asyncio.sleep(6)
        
        expired_session = await manager.get_session(session1.session_id)
        print(f"Expired session retrieved: {expired_session is None}")
        
        # Test 5: Manual cleanup
        print("\nTest 5: Manual session close...")
        close_result = await manager.close_session(session2.session_id)
        print(f"Close result: {close_result}")
        
        # Test 6: Final session count
        sessions = await manager.list_sessions()
        print(f"\nFinal active sessions: {len(sessions)}")
        
        print("\n[OK] All tests passed!")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Configure logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run tests
    asyncio.run(test_session_manager())