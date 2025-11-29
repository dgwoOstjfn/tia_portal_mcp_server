"""
Tests for Analysis Handlers
"""
import sys
import os
from pathlib import Path
import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock System and tia_portal before importing handlers
sys.modules["System"] = MagicMock()
sys.modules["System.Diagnostics"] = MagicMock()
sys.modules["tia_portal"] = MagicMock()
sys.modules["BlockImport"] = MagicMock()
sys.modules["BlockExport"] = MagicMock()

# Now import handlers
from handlers.analysis_handlers import ProjectAnalyzer
from session.session_manager import TIASession, SessionManager
from handlers.cache_handlers import CacheManager

class TestAnalysisHandlers(unittest.IsolatedAsyncioTestCase):
    
    async def asyncSetUp(self):
        # Mock session
        self.session = MagicMock(spec=TIASession)
        self.session.session_id = "test_session"
        self.session.current_project = "TestProject"
        self.session.client_wrapper = MagicMock()
        
        # Mock CacheManager
        self.session.cache_manager = MagicMock(spec=CacheManager)
        self.session.cache_manager.session_cache_dir = Path("./test_cache/test_session")
        self.session.cache_manager.get_entry.return_value = None
        
        # Mock TIA project
        self.mock_project = MagicMock()
        self.session.client_wrapper.project = self.mock_project
        
        # Mock execute_sync
        async def mock_execute_sync(func):
            if asyncio.iscoroutinefunction(func):
                return await func()
            return func()
        self.session.client_wrapper.execute_sync = mock_execute_sync

    async def test_analyze_project_structure(self):
        # Mock return data for _get_structure
        # Since _get_structure is an inner function that calls TIA API, 
        # we are mocking the result of execute_sync if we could, but here we mock the inner calls
        
        # We need to patch _get_all_blocks_comprehensive
        with patch('handlers.analysis_handlers._get_all_blocks_comprehensive') as mock_get_blocks:
            mock_get_blocks.return_value = [
                {"name": "Block1", "type": "FB", "path": "/Folder1/Block1", "folder_name": "Folder1"},
                {"name": "Block2", "type": "DB", "path": "/Block2", "folder_name": None}
            ]
            
            # Mock PLC
            mock_plc = MagicMock()
            mock_plc.name = "PLC_1"
            self.mock_project.get_plcs.return_value = [mock_plc]
            
            result = await ProjectAnalyzer.analyze_project_structure(self.session)
            
            self.assertTrue(result["success"])
            self.assertEqual(len(result["structure"]["plcs"]), 1)
            self.assertEqual(len(result["structure"]["plcs"][0]["blocks"]), 2)
            self.assertEqual(result["stats"]["total_blocks"], 2)

    async def test_get_flat_code_summary_no_blocks(self):
        # Test with no blocks found
        with patch('handlers.analysis_handlers._get_all_blocks_comprehensive') as mock_get_blocks:
            mock_get_blocks.return_value = []
            
            # Mock PLC
            mock_plc = MagicMock()
            self.mock_project.get_plcs.return_value = [mock_plc]
            
            result = await ProjectAnalyzer.get_flat_code_summary(self.session)
            
            self.assertTrue(result["success"])
            self.assertEqual(result["code"], "")

    @patch('handlers.analysis_handlers.ConversionHandlers')
    async def test_get_flat_code_summary_with_export(self, MockConversionHandlers):
        # Test flow where export is needed
        with patch('handlers.analysis_handlers._get_all_blocks_comprehensive') as mock_get_blocks, \
             patch('handlers.analysis_handlers._export_block_direct') as mock_export:
            
            # Setup blocks
            mock_get_blocks.return_value = [
                {"name": "Block1", "type": "FB", "path": "/Block1", "folder_name": None, "block_object": MagicMock()}
            ]
            
            # Setup PLC
            mock_plc = MagicMock()
            self.mock_project.get_plcs.return_value = [mock_plc]
            
            # Setup Export
            mock_export.return_value = "temp/Block1.xml"
            
            # Setup Conversion
            mock_converter = MockConversionHandlers.return_value
            mock_converter.convert_xml_to_scl.return_value = {
                "success": True, 
                "output_file": "temp/Block1.scl"
            }
            
            # Mock file reading
            with patch('pathlib.Path.read_text', return_value="FUNCTION_BLOCK Block1..."):
                with patch('os.path.exists', return_value=True):
                    result = await ProjectAnalyzer.get_flat_code_summary(self.session, block_names=["Block1"])
            
            self.assertTrue(result["success"])
            self.assertIn("FUNCTION_BLOCK Block1", result["summary"])
            self.assertEqual(result["stats"]["processed"], 1)
            
            # Verify cache update was called
            self.session.cache_manager.add_entry.assert_called()

if __name__ == '__main__':
    unittest.main()
