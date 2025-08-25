"""
TIA Portal Client Wrapper with Async Support
"""
import asyncio
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional, Dict, List, Callable
from pathlib import Path
import traceback

# Setup import paths using MCP configuration
from mcp_config import get_mcp_config
try:
    mcp_config = get_mcp_config()
    # MCP config handles path setup automatically
except Exception as e:
    # Fallback to legacy path setup
    from pathlib import Path
    base_dir = Path(__file__).parent.parent.parent
    tia_client_path = base_dir / "99_TIA_Client"
    if tia_client_path.exists():
        sys.path.insert(0, str(tia_client_path))

# Import TIA Portal client
try:
    import tia_portal
except ImportError as e:
    print(f"Error: Could not import tia_portal: {e}")
    print(f"Attempted to add path: {tia_client_path}")
    print(f"Current sys.path: {sys.path[:3]}...")  # Show first 3 paths
    sys.exit(1)

class TIAClientWrapper:
    """Async wrapper for synchronous TIA Portal operations"""
    
    def __init__(self):
        """Initialize the TIA client wrapper"""
        # Single thread executor for COM STA requirements
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="TIA-COM")
        self.client: Optional[tia_portal.Client] = None
        self.project: Optional[Any] = None
        self.is_connected = False
        
    async def execute_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Execute synchronous function in thread pool
        
        Args:
            func: Synchronous function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
        """
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self.executor,
                func,
                *args,
                **kwargs
            )
            return result
        except Exception as e:
            print(f"Error executing {func.__name__}: {str(e)}")
            traceback.print_exc()
            raise
    
    async def connect(self) -> bool:
        """Connect to TIA Portal
        
        Returns:
            True if connection successful
        """
        try:
            def _connect():
                self.client = tia_portal.Client()
                return True
            
            result = await self.execute_sync(_connect)
            self.is_connected = result
            print("Successfully connected to TIA Portal")
            return result
        except Exception as e:
            print(f"Failed to connect to TIA Portal: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from TIA Portal
        
        Returns:
            True if disconnection successful
        """
        try:
            if self.project:
                await self.save_project()
                await self.close_project()
            
            if self.client:
                def _disconnect():
                    self.client.close()
                    return True
                
                result = await self.execute_sync(_disconnect)
                self.client = None
                self.is_connected = False
                print("Disconnected from TIA Portal")
                return result
            return True
        except Exception as e:
            print(f"Error during disconnect: {e}")
            return False
    
    async def open_project(self, project_path: str, project_name: Optional[str] = None) -> Dict[str, Any]:
        """Open a TIA Portal project
        
        Args:
            project_path: Path to project file or directory
            project_name: Project name (optional if path is to .ap* file)
            
        Returns:
            Dict with success status and project info
        """
        if not self.is_connected:
            await self.connect()
        
        try:
            def _open_project():
                # Handle both file and directory paths
                path = Path(project_path)
                
                if path.is_file() and path.suffix.startswith('.ap'):
                    # Direct project file
                    project_dir = path.parent
                    store_path = project_dir.parent
                    proj_name = project_dir.name
                else:
                    # Directory path - find project file
                    store_path = str(path)
                    if not project_name:
                        # Try to find project file
                        ap_files = list(path.glob('**/*.ap*'))
                        if ap_files:
                            proj_name = ap_files[0].parent.name
                        else:
                            raise ValueError("No project file found in directory")
                    else:
                        proj_name = project_name
                
                print(f"Opening project: {proj_name} from {store_path}")
                self.project = self.client.open_project(store_path, proj_name)
                
                return {
                    "success": True,
                    "project_name": proj_name,
                    "store_path": str(store_path),  # Convert Path to string for JSON
                    "is_modified": self.project.is_modified() if hasattr(self.project, 'is_modified') else False
                }
            
            result = await self.execute_sync(_open_project)
            print(f"Project opened successfully: {result['project_name']}")
            return result
            
        except Exception as e:
            print(f"Failed to open project: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def save_project(self) -> Dict[str, Any]:
        """Save the current project
        
        Returns:
            Dict with success status
        """
        if not self.project:
            return {
                "success": False,
                "error": "No project is currently open"
            }
        
        try:
            def _save_project():
                self.project.save()
                return True
            
            await self.execute_sync(_save_project)
            print("Project saved successfully")
            return {"success": True}
            
        except Exception as e:
            print(f"Failed to save project: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close_project(self) -> Dict[str, Any]:
        """Close the current project
        
        Returns:
            Dict with success status
        """
        if not self.project:
            return {"success": True}
        
        try:
            def _close_project():
                self.project.close()
                return True
            
            await self.execute_sync(_close_project)
            self.project = None
            print("Project closed successfully")
            return {"success": True}
            
        except Exception as e:
            print(f"Failed to close project: {e}")
            return {
                "success": False, 
                "error": str(e)
            }
    
    async def get_project_info(self) -> Dict[str, Any]:
        """Get information about current project
        
        Returns:
            Dict with project information
        """
        if not self.project:
            return {
                "success": False,
                "error": "No project is currently open"
            }
        
        try:
            def _get_info():
                info = {
                    "name": self.project.name if hasattr(self.project, 'name') else "Unknown",
                    "is_modified": self.project.is_modified() if hasattr(self.project, 'is_modified') else False,
                    "path": str(self.project.path) if hasattr(self.project, 'path') else "Unknown"
                }
                
                # Get devices if available
                if hasattr(self.project, 'get_devices'):
                    devices = self.project.get_devices()
                    info["device_count"] = len(devices) if devices else 0
                
                return info
            
            info = await self.execute_sync(_get_info)
            return {
                "success": True,
                "project_info": info
            }
            
        except Exception as e:
            print(f"Failed to get project info: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def __del__(self):
        """Cleanup on deletion"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# Test functions
async def test_basic_operations():
    """Test basic TIA client operations"""
    # Fix import for running as script
    if __name__ == "__main__":
        from config import get_config
    else:
        from src.config import get_config
    
    print("\n=== Testing TIA Client Wrapper ===\n")
    
    config = get_config()
    wrapper = TIAClientWrapper()
    
    try:
        # Test 1: Connect to TIA Portal
        print("Test 1: Connecting to TIA Portal...")
        connected = await wrapper.connect()
        print(f"Connection result: {'SUCCESS' if connected else 'FAILED'}")
        
        if not connected:
            print("Cannot proceed without TIA Portal connection")
            return
        
        # Test 2: Open test project
        print("\nTest 2: Opening test project...")
        test_project_path = str(config.test_project_1)
        print(f"Project path: {test_project_path}")
        
        result = await wrapper.open_project(test_project_path)
        print(f"Open project result: {result}")
        
        if result["success"]:
            # Test 3: Get project info
            print("\nTest 3: Getting project info...")
            info = await wrapper.get_project_info()
            print(f"Project info: {info}")
            
            # Test 4: Save project
            print("\nTest 4: Saving project...")
            save_result = await wrapper.save_project()
            print(f"Save result: {save_result}")
            
            # Test 5: Close project
            print("\nTest 5: Closing project...")
            close_result = await wrapper.close_project()
            print(f"Close result: {close_result}")
        
        # Test 6: Disconnect
        print("\nTest 6: Disconnecting from TIA Portal...")
        disconnect_result = await wrapper.disconnect()
        print(f"Disconnect result: {'SUCCESS' if disconnect_result else 'FAILED'}")
        
        print("\n=== All tests completed ===")
        
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        traceback.print_exc()
    finally:
        # Ensure cleanup
        if wrapper.is_connected:
            await wrapper.disconnect()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_basic_operations())