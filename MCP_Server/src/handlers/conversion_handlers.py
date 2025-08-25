"""
File format conversion handlers for TIA Portal MCP Server
Handles conversion between XML, JSON, and SCL formats
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Setup paths for imports
base_dir = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(base_dir / "02_FileConverter"))
sys.path.insert(0, str(base_dir / "MCP_Server" / "lib" / "converters"))

# Import conversion modules
try:
    from xml_to_json import xml_to_json, patched_xml_to_json
    from json_to_xml import json_to_xml, TIAXMLGenerator
    from json_to_scl import JSONToSCLConverter
    from scl_to_json import SCLToJSONConverter
    from plc_tag_converter import PLCTagConverter
    from udt_converter import UDTConverter
except ImportError as e:
    print(f"Error importing conversion modules: {e}")
    raise

logger = logging.getLogger(__name__)


class ConversionHandlers:
    """Handles file format conversions for the MCP server"""
    
    def __init__(self):
        self.json_to_scl_converter = JSONToSCLConverter()
        self.scl_to_json_converter = SCLToJSONConverter()
        self.tia_xml_generator = TIAXMLGenerator()
        self.plc_tag_converter = PLCTagConverter()
        self.udt_converter = UDTConverter()
        self.use_patched_xml_to_json = True  # Flag to use patched version if needed - FIXED: Use correct NetworkSource path
    
    def convert_xml_to_json(self, xml_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert XML file to JSON format
        
        Args:
            xml_file_path: Path to input XML file
            output_path: Path for output JSON file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(xml_file_path):
                return {
                    "success": False,
                    "error": f"XML file not found: {xml_file_path}"
                }
            
            logger.info(f"Converting XML to JSON: {xml_file_path}")
            
            # Perform conversion
            # Use patched version if flag is set (for debugging or special cases)
            if self.use_patched_xml_to_json:
                result_file = patched_xml_to_json(xml_file_path, output_path)
            else:
                result_file = xml_to_json(xml_file_path, output_path)
            
            if result_file:
                # Get absolute path for consistency
                output_file = os.path.abspath(output_path) if output_path else os.path.abspath(result_file)
                return {
                    "success": True,
                    "output_file": output_file,
                    "message": f"Successfully converted XML to JSON: {output_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "XML to JSON conversion failed - check if the XML contains a supported block type (FB/OB/FC/GlobalDB)"
                }
                
        except Exception as e:
            logger.error(f"Error in XML to JSON conversion: {e}")
            return {
                "success": False,
                "error": f"XML to JSON conversion error: {str(e)}"
            }
    
    def convert_json_to_xml(self, json_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert JSON file to XML format
        
        Args:
            json_file_path: Path to input JSON file
            output_path: Path for output XML file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(json_file_path):
                return {
                    "success": False,
                    "error": f"JSON file not found: {json_file_path}"
                }
            
            logger.info(f"Converting JSON to XML: {json_file_path}")
            
            # Perform conversion
            result_file = json_to_xml(json_file_path, output_path)
            
            if result_file:
                # Get absolute path for consistency
                output_file = os.path.abspath(output_path) if output_path else os.path.abspath(result_file)
                return {
                    "success": True,
                    "output_file": output_file,
                    "message": f"Successfully converted JSON to XML: {output_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "JSON to XML conversion failed - check JSON structure matches expected format"
                }
                
        except Exception as e:
            logger.error(f"Error in JSON to XML conversion: {e}")
            return {
                "success": False,
                "error": f"JSON to XML conversion error: {str(e)}"
            }
    
    def convert_json_to_scl(self, json_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert JSON file to SCL format
        
        Args:
            json_file_path: Path to input JSON file
            output_path: Path for output SCL file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(json_file_path):
                return {
                    "success": False,
                    "error": f"JSON file not found: {json_file_path}"
                }
            
            logger.info(f"Converting JSON to SCL: {json_file_path}")
            
            # Perform conversion
            result_file = self.json_to_scl_converter.json_to_scl(json_file_path, output_path)
            
            if result_file:
                # Get absolute path for consistency
                output_file = os.path.abspath(output_path) if output_path else os.path.abspath(result_file)
                return {
                    "success": True,
                    "output_file": output_file,
                    "message": f"Successfully converted JSON to SCL: {output_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "JSON to SCL conversion failed - check JSON structure matches expected format"
                }
                
        except Exception as e:
            logger.error(f"Error in JSON to SCL conversion: {e}")
            return {
                "success": False,
                "error": f"JSON to SCL conversion error: {str(e)}"
            }
    
    def convert_scl_to_json(self, scl_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert SCL file to JSON format
        
        Args:
            scl_file_path: Path to input SCL file
            output_path: Path for output JSON file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(scl_file_path):
                return {
                    "success": False,
                    "error": f"SCL file not found: {scl_file_path}"
                }
            
            logger.info(f"Converting SCL to JSON: {scl_file_path}")
            
            # Perform conversion
            result_file = self.scl_to_json_converter.scl_to_json(scl_file_path, output_path)
            
            if result_file:
                # Get absolute path for consistency
                output_file = os.path.abspath(output_path) if output_path else os.path.abspath(result_file)
                return {
                    "success": True,
                    "output_file": output_file,
                    "message": f"Successfully converted SCL to JSON: {output_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "SCL to JSON conversion failed - check SCL syntax and structure"
                }
                
        except Exception as e:
            logger.error(f"Error in SCL to JSON conversion: {e}")
            return {
                "success": False,
                "error": f"SCL to JSON conversion error: {str(e)}"
            }
    
    def convert_xml_to_scl(self, xml_file_path: str, output_path: str = None, temp_dir: str = None) -> Dict[str, Any]:
        """
        Convert XML file to SCL format (compound operation: XML -> JSON -> SCL)
        
        Args:
            xml_file_path: Path to input XML file
            output_path: Path for output SCL file (optional)
            temp_dir: Directory for temporary files (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(xml_file_path):
                return {
                    "success": False,
                    "error": f"XML file not found: {xml_file_path}"
                }
            
            logger.info(f"Converting XML to SCL (via JSON): {xml_file_path}")
            
            # Step 1: XML to JSON
            if temp_dir:
                temp_json = os.path.join(temp_dir, os.path.splitext(os.path.basename(xml_file_path))[0] + "_temp.json")
            else:
                temp_json = os.path.splitext(xml_file_path)[0] + "_temp.json"
            
            xml_to_json_result = self.convert_xml_to_json(xml_file_path, temp_json)
            if not xml_to_json_result["success"]:
                return xml_to_json_result
            
            # Step 2: JSON to SCL
            scl_result = self.convert_json_to_scl(temp_json, output_path)
            
            # Clean up temporary file
            try:
                if os.path.exists(temp_json):
                    os.remove(temp_json)
            except Exception as e:
                logger.warning(f"Could not remove temporary file {temp_json}: {e}")
            
            if scl_result["success"]:
                scl_result["message"] = f"Successfully converted XML to SCL: {scl_result['output_file']}"
            
            return scl_result
            
        except Exception as e:
            logger.error(f"Error in XML to SCL conversion: {e}")
            return {
                "success": False,
                "error": f"XML to SCL conversion error: {str(e)}"
            }
    
    def convert_scl_to_xml(self, scl_file_path: str, output_path: str = None, temp_dir: str = None) -> Dict[str, Any]:
        """
        Convert SCL file to XML format (compound operation: SCL -> JSON -> XML)
        
        Args:
            scl_file_path: Path to input SCL file
            output_path: Path for output XML file (optional)
            temp_dir: Directory for temporary files (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(scl_file_path):
                return {
                    "success": False,
                    "error": f"SCL file not found: {scl_file_path}"
                }
            
            logger.info(f"Converting SCL to XML (via JSON): {scl_file_path}")
            
            # Step 1: SCL to JSON
            if temp_dir:
                temp_json = os.path.join(temp_dir, os.path.splitext(os.path.basename(scl_file_path))[0] + "_temp.json")
            else:
                temp_json = os.path.splitext(scl_file_path)[0] + "_temp.json"
            
            scl_to_json_result = self.convert_scl_to_json(scl_file_path, temp_json)
            if not scl_to_json_result["success"]:
                return scl_to_json_result
            
            # Step 2: JSON to XML
            xml_result = self.convert_json_to_xml(temp_json, output_path)
            
            # Clean up temporary file
            try:
                if os.path.exists(temp_json):
                    os.remove(temp_json)
            except Exception as e:
                logger.warning(f"Could not remove temporary file {temp_json}: {e}")
            
            if xml_result["success"]:
                xml_result["message"] = f"Successfully converted SCL to XML: {xml_result['output_file']}"
            
            return xml_result
            
        except Exception as e:
            logger.error(f"Error in SCL to XML conversion: {e}")
            return {
                "success": False,
                "error": f"SCL to XML conversion error: {str(e)}"
            }
    
    def create_structured_text_xml(self, code_lines: List[str]) -> Dict[str, Any]:
        """
        Create StructuredText XML from code lines using TIAXMLGenerator
        
        Args:
            code_lines: List of SCL code lines
            
        Returns:
            Dictionary with XML string
        """
        try:
            logger.info(f"Creating StructuredText XML from {len(code_lines)} code lines")
            
            # Reset UID counter for consistent output
            self.tia_xml_generator.reset_uid_counter(21)
            
            # Generate XML
            structured_text_xml = self.tia_xml_generator.create_structured_text_xml(code_lines)
            
            return {
                "success": True,
                "xml": structured_text_xml,
                "message": f"Successfully created StructuredText XML with {self.tia_xml_generator.uid_counter - 1} UIDs"
            }
            
        except Exception as e:
            logger.error(f"Error creating StructuredText XML: {e}")
            return {
                "success": False,
                "error": f"StructuredText XML creation error: {str(e)}"
            }
    
    def tokenize_scl_line(self, line: str) -> List[tuple]:
        """
        Tokenize SCL code line using TIAXMLGenerator
        
        Args:
            line: SCL code line to tokenize
            
        Returns:
            List of (token_type, token_value) tuples
        """
        try:
            tokens = self.tia_xml_generator.tokenize_scl_line(line)
            return tokens
        except Exception as e:
            logger.error(f"Error tokenizing SCL line: {e}")
            return []
    
    def convert_plc_tag_xml_to_excel(self, xml_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert PLC tag table XML to Excel format
        
        Args:
            xml_file_path: Path to input XML file
            output_path: Path for output Excel file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(xml_file_path):
                return {
                    "success": False,
                    "error": f"XML file not found: {xml_file_path}"
                }
            
            logger.info(f"Converting PLC tag XML to Excel: {xml_file_path}")
            
            # Perform conversion
            result_file = self.plc_tag_converter.xml_to_excel(xml_file_path, output_path)
            
            if result_file:
                return {
                    "success": True,
                    "output_file": result_file,
                    "message": f"Successfully converted PLC tag XML to Excel: {result_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "PLC tag XML to Excel conversion failed"
                }
                
        except Exception as e:
            logger.error(f"Error in PLC tag XML to Excel conversion: {e}")
            return {
                "success": False,
                "error": f"PLC tag XML to Excel conversion error: {str(e)}"
            }
    
    def convert_excel_to_plc_tag_xml(self, excel_file_path: str, output_path: str = None, 
                                      table_name: str = None) -> Dict[str, Any]:
        """
        Convert Excel file to PLC tag table XML format
        
        Args:
            excel_file_path: Path to input Excel file
            output_path: Path for output XML file (optional)
            table_name: Name for the tag table (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(excel_file_path):
                return {
                    "success": False,
                    "error": f"Excel file not found: {excel_file_path}"
                }
            
            logger.info(f"Converting Excel to PLC tag XML: {excel_file_path}")
            
            # Perform conversion
            result_file = self.plc_tag_converter.excel_to_xml(excel_file_path, output_path, table_name)
            
            if result_file:
                return {
                    "success": True,
                    "output_file": result_file,
                    "message": f"Successfully converted Excel to PLC tag XML: {result_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "Excel to PLC tag XML conversion failed"
                }
                
        except Exception as e:
            logger.error(f"Error in Excel to PLC tag XML conversion: {e}")
            return {
                "success": False,
                "error": f"Excel to PLC tag XML conversion error: {str(e)}"
            }
    
    def convert_udt_xml_to_udt(self, xml_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert UDT XML to .udt format
        
        Args:
            xml_file_path: Path to input XML file
            output_path: Path for output .udt file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(xml_file_path):
                return {
                    "success": False,
                    "error": f"XML file not found: {xml_file_path}"
                }
            
            logger.info(f"Converting UDT XML to .udt: {xml_file_path}")
            
            # Perform conversion
            result_file = self.udt_converter.xml_to_udt(xml_file_path, output_path)
            
            if result_file:
                return {
                    "success": True,
                    "output_file": result_file,
                    "message": f"Successfully converted UDT XML to .udt: {result_file}"
                }
            else:
                return {
                    "success": False,
                    "error": "UDT XML to .udt conversion failed"
                }
                
        except Exception as e:
            logger.error(f"Error in UDT XML to .udt conversion: {e}")
            return {
                "success": False,
                "error": f"UDT XML to .udt conversion error: {str(e)}"
            }
    
    def convert_udt_to_xml(self, udt_file_path: str, output_path: str = None) -> Dict[str, Any]:
        """
        Convert .udt file to UDT XML format
        
        Args:
            udt_file_path: Path to input .udt file
            output_path: Path for output XML file (optional)
            
        Returns:
            Dictionary with conversion result
        """
        try:
            if not os.path.exists(udt_file_path):
                return {
                    "success": False,
                    "error": f"UDT file not found: {udt_file_path}"
                }
            
            logger.info(f"Converting .udt to UDT XML: {udt_file_path}")
            
            # Perform conversion
            result_file = self.udt_converter.udt_to_xml(udt_file_path, output_path)
            
            if result_file:
                return {
                    "success": True,
                    "output_file": result_file,
                    "message": f"Successfully converted .udt to UDT XML: {result_file}"
                }
            else:
                return {
                    "success": False,
                    "error": ".udt to UDT XML conversion failed"
                }
                
        except Exception as e:
            logger.error(f"Error in .udt to UDT XML conversion: {e}")
            return {
                "success": False,
                "error": f".udt to UDT XML conversion error: {str(e)}"
            }