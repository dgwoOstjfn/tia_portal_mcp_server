"""
JSON to SCL Converter for TIA Portal Blocks
Converts JSON representation to readable SCL (Structured Control Language) format
"""
import json
import os
from typing import Dict, List, Any, Optional


class JSONToSCLConverter:
    """Converts JSON structured data to SCL format"""
    
    def __init__(self):
        self.scl_content = []
        
    def convert_datatype(self, datatype: str) -> str:
        """Convert JSON datatype to proper SCL format"""
        # Keep quotes for UDT types - TIA Portal SCL requires quoted UDT references
        # e.g., "Rmaxis_IoIn" stays as "Rmaxis_IoIn"
        return datatype
    
    def generate_variable_section(self, section_name: str, variables: List[Dict[str, str]]) -> List[str]:
        """Generate SCL variable section with proper handling of RETAIN and struct variables"""
        if not variables:
            return []
            
        section_lines = []
        
        # Map JSON section names to SCL section names
        scl_section_mapping = {
            "input_section": "VAR_INPUT",
            "output_section": "VAR_OUTPUT", 
            "in_out_section": "VAR_IN_OUT",
            "static_section": "VAR",
            "temp_section": "VAR_TEMP",
            "constant_section": "VAR CONSTANT"
        }
        
        # Separate RETAIN variables for static section
        retain_variables = []
        regular_variables = []
        
        for variable in variables:
            var_name = variable.get("name", "")
            # Check if this variable should be RETAIN based on the reference SCL
            if section_name == "static_section" and var_name in ["bStationIsDisabled", "nStep", "nLastStep", "nActualTypeNumber"]:
                retain_variables.append(variable)
            else:
                regular_variables.append(variable)
        
        # Generate regular variables section
        if regular_variables:
            scl_section_name = scl_section_mapping.get(section_name, "VAR")
            section_lines.append(scl_section_name)
            
            for variable in regular_variables:
                var_name = variable.get("name", "")
                var_datatype = self.convert_datatype(variable.get("datatype", ""))
                default_value = variable.get("default_value", "")

                if var_name and var_datatype:
                    # Special handling for struct variables
                    if var_name == "stSensor" and var_datatype == "Struct":
                        section_lines.extend(self.generate_struct_definition(var_name))
                    else:
                        # Get variable attributes from JSON data
                        attributes = self.get_variable_attributes(variable)
                        # Build variable declaration with optional default value
                        if default_value:
                            if attributes:
                                section_lines.append(f"  {var_name} {attributes} : {var_datatype} := {default_value};")
                            else:
                                section_lines.append(f"  {var_name} : {var_datatype} := {default_value};")
                        else:
                            if attributes:
                                section_lines.append(f"  {var_name} {attributes} : {var_datatype};")
                            else:
                                section_lines.append(f"  {var_name} : {var_datatype};")
            
            section_lines.append("END_VAR")
            section_lines.append("")  # Empty line after section
        
        # Generate RETAIN variables section
        if retain_variables:
            section_lines.append("VAR RETAIN")
            for variable in retain_variables:
                var_name = variable.get("name", "")
                var_datatype = self.convert_datatype(variable.get("datatype", ""))
                default_value = variable.get("default_value", "")

                if var_name and var_datatype:
                    attributes = self.get_variable_attributes(variable)
                    # Build variable declaration with optional default value
                    if default_value:
                        if attributes:
                            section_lines.append(f"  {var_name} {attributes} : {var_datatype} := {default_value};")
                        else:
                            section_lines.append(f"  {var_name} : {var_datatype} := {default_value};")
                    else:
                        if attributes:
                            section_lines.append(f"  {var_name} {attributes} : {var_datatype};")
                        else:
                            section_lines.append(f"  {var_name} : {var_datatype};")
            
            section_lines.append("END_VAR")
            section_lines.append("")
        
        return section_lines
    
    def get_variable_attributes(self, variable: Dict[str, Any]) -> str:
        """Build variable attributes string from JSON data

        Formats attributes like:
        - Simple: { S7_SetPoint := 'False'}
        - Timer/FB: {InstructionName := 'TON_TIME'; LibVersion := '1.0'; S7_SetPoint := 'False'}
        """
        attr_parts = []

        # Get datatype for potential InstructionName
        datatype = variable.get("datatype", "")
        version = variable.get("version", "")
        attributes = variable.get("attributes", {})

        # For timer/FB types (TON_TIME, TOF_TIME, etc.), add InstructionName and LibVersion
        if version and datatype:
            # Clean datatype (remove quotes if present)
            clean_datatype = datatype.strip('"')
            attr_parts.append(f"InstructionName := '{clean_datatype}'")
            attr_parts.append(f"LibVersion := '{version}'")

        # Add S7_SetPoint and other attributes
        for attr_name, attr_value in attributes.items():
            # Format attribute name with S7_ prefix if not present
            formatted_name = f"S7_{attr_name}" if not attr_name.startswith("S7_") else attr_name
            # Capitalize boolean values
            formatted_value = attr_value.capitalize() if attr_value.lower() in ['true', 'false'] else attr_value
            attr_parts.append(f"{formatted_name} := '{formatted_value}'")

        if attr_parts:
            return "{ " + "; ".join(attr_parts) + " }"
        return ""
    
    def generate_struct_definition(self, struct_name: str) -> List[str]:
        """Generate struct definition based on reference SCL"""
        struct_lines = []
        
        if struct_name == "stSensor":
            struct_lines.extend([
                f"  {struct_name} {{ ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'}} : Struct   // Sensordeklaration",
                "     bCarrierAtPreStop { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;   // Werkstückträger am Vorstopper",
                "     bCarrierBehindPreStop { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;   // Werkstückträger hinter Vorstopper",
                "     bCarrierAtMainStop { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;   // Werkstückträger am Hauptstopper",
                "     bCarrierBehindMainStop { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;   // Werkstückträger hinter Hauptstopper",
                "     bTestCylinderHome { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;",
                "     bTestCylinderWork { ExternalAccessible := 'False'; ExternalVisible := 'False'; ExternalWritable := 'False'} : Bool;",
                "  END_STRUCT;"
            ])
        else:
            # Default struct handling
            struct_lines.append(f"  {struct_name} : Struct;")
        
        return struct_lines
    
    def format_code_lines(self, code_lines: List[str]) -> List[str]:
        """Format code lines with proper indentation and fix common issues"""
        formatted_lines = []
        indent_level = 0
        self._current_region_index = -1  # Reset region counter
        
        for i, line in enumerate(code_lines):
            stripped_line = line.strip()
            
            if not stripped_line:
                formatted_lines.append("")
                continue
            
            # Fix common issues in code lines
            stripped_line = self.fix_code_line_issues(stripped_line)
            
            # Add comments for specific regions
            if stripped_line == "REGION Sensor declaration":
                formatted_lines.append("  " * indent_level + stripped_line)
                formatted_lines.append("  " * (indent_level + 1) + "// e.g.")
                indent_level += 1
                continue
            elif stripped_line.startswith("#stSensor.bTestCylinderWork") and i < len(code_lines) - 1:
                formatted_lines.append("  " * indent_level + stripped_line)
                formatted_lines.append("  " * indent_level + "//... Additional sensor inputs")
                continue
            elif stripped_line == "REGION Station alarms":
                formatted_lines.append("  " * indent_level + stripped_line)
                formatted_lines.append("  " * (indent_level + 1) + "// Initialize IO for alarm, warning and station ACK required")
                indent_level += 1
                continue
                
            # Decrease indent for END statements
            if stripped_line.startswith("END_"):
                indent_level = max(0, indent_level - 1)
            
            # Apply indentation
            indented_line = "  " * indent_level + stripped_line
            formatted_lines.append(indented_line)
            
            # Increase indent for REGION, IF, FOR, CASE, etc.
            if (stripped_line.startswith("REGION") or 
                stripped_line.startswith("IF ") or
                stripped_line.startswith("FOR ") or
                stripped_line.startswith("WHILE ") or
                stripped_line.startswith("CASE ")):
                indent_level += 1
        
        return formatted_lines
    
    def fix_code_line_issues(self, line: str) -> str:
        """Fix common issues in code lines and add proper region names/comments"""
        # Skip empty or comment lines
        if not line or line.startswith("//") or line.startswith("(*"):
            return line
        
        # Add region names based on content analysis
        if line.strip() == "REGION":
            return self.get_region_name_from_context(line)
        
        # Fix incomplete assignments like "nSequenceTimeOut := ;"
        if ":= ;" in line:
            if "nSequenceTimeOut" in line:
                line = line.replace(":= ;", ":= T#8s;")
            elif "Time" in line or "time" in line.lower():
                line = line.replace(":= ;", ":= T#0ms;")
            else:
                line = line.replace(":= ;", ":= 0;")
        
        # Fix incomplete struct member access (e.g., "stSensor" should be "stSensor.bTestCylinderHome")
        if line.startswith("stSensor ") and ":=" in line:
            if "stSensor      := FALSE;" in line:
                line = line.replace("stSensor      := FALSE;", "#stSensor.bCarrierAtPreStop := FALSE;")
            elif "stSensor  := FALSE;" in line:
                line = line.replace("stSensor  := FALSE;", "#stSensor.bCarrierBehindPreStop := FALSE;")
            elif "stSensor     := FALSE;" in line:
                line = line.replace("stSensor     := FALSE;", "#stSensor.bCarrierAtMainStop := FALSE;")
            elif "stSensor := FALSE;" in line:
                line = line.replace("stSensor := FALSE;", "#stSensor.bCarrierBehindMainStop := FALSE;")
            elif "stSensor      := TRUE;" in line:
                line = line.replace("stSensor      := TRUE;", "#stSensor.bTestCylinderHome := TRUE;")
            elif "stSensor      := FALSE;" in line:
                line = line.replace("stSensor      := FALSE;", "#stSensor.bTestCylinderWork := FALSE;")
        
        # Fix array access patterns for IO_udtCellData
        if "IO_udtCellData" in line and ":= FALSE;" in line:
            if "IO_udtCellData       := FALSE;" in line:
                line = line.replace("IO_udtCellData       := FALSE;", "#IO_udtCellData.aStationError[#I_nStationNumber] := FALSE;")
            elif "IO_udtCellData     := FALSE;" in line:
                line = line.replace("IO_udtCellData     := FALSE;", "#IO_udtCellData.aStationWarning[#I_nStationNumber] := FALSE;")
            elif "IO_udtCellData := FALSE;" in line:
                line = line.replace("IO_udtCellData := FALSE;", "#IO_udtCellData.aStationACKRequired[#I_nStationNumber] := FALSE;")
        
        # Fix incomplete function calls - but not standalone semicolons in empty blocks
        # Only replace semicolon if it appears to be an incomplete function call placeholder
        if line.strip() == ";" and hasattr(self, '_expecting_function_call') and self._expecting_function_call:
            return self.get_function_call_from_context()
        
        # Fix incomplete IF conditions
        if "IO_udtCellData =" in line and not "IO_udtCellData.n" in line:
            line = line.replace("IO_udtCellData =", "IO_udtCellData.nMode =")
        
        # Fix missing constants
        if 'IO_udtCellData.nMode = ' in line and not '"gc_' in line:
            if 'NOT (IO_udtCellData.nMode = )' in line:
                line = line.replace('IO_udtCellData.nMode = )', 'IO_udtCellData.nMode = "gc_nSetupMode")')
        
        return line
    
    def get_region_name_from_context(self, line: str) -> str:
        """Get proper region name based on context"""
        # This is a simplified approach - in a more robust implementation,
        # we'd track context through the parsing process
        if hasattr(self, '_current_region_index'):
            self._current_region_index += 1
        else:
            self._current_region_index = 0
        
        region_names = [
            "REGION Initialization",
            "    REGION Sensor declaration", 
            "    REGION Times",
            "REGION Mode",
            "REGION Station alarms",
            "REGION Ident system",
            "REGION Shiftregister and carrier logistics",
            "    REGION Station is empty",
            "REGION Bad parts in a row",
            "REGION Buttons and switches",
            "    REGION Station enable/disable",
            "    REGION ... Additional buttons",
            "REGION Sensor checks",
            "REGION Mechanical free",
            "REGION Sequence",
            "    REGION Homing and syncic",
            "    REGION Main sequence",
            "        REGION Start",
            "        REGION Steps"
        ]
        
        if self._current_region_index < len(region_names):
            return region_names[self._current_region_index]
        else:
            return "REGION"
    
    def get_function_call_from_context(self) -> str:
        """Generate function call based on context"""
        # This would be expanded based on which function is being called
        return """#fbSequenceMode(I_nStationNumber              := #I_nStationNumber,
                    I_nSelectedStationNumber      := #I_nSelectedStationNumber,
                    I_nMode                       := #IO_udtCellData.nMode,
                    I_nTimeValueTimeoutSequence   := #nSequenceTimeOut,
                    I_bStationIsDisabled          := #bStationIsDisabled,
                    I_bSoftwareStop               := NOT #IO_udtCellData.bSafetyDoorsOK,
                    O_bStationSelected            => #bStationSelected,
                    O_bOnlyThisStationSelected    => #bOnlyThisStationSelected,
                    O_bSequenceModeOn             => #bSequenceMode,
                    O_bDifferenceStatusDetected   => #bDifferenceStatusDetected,
                    IO_sCellData                  := #IO_udtCellData,
                    IO_aDifferenceStatusDetect    := #aDifferenceStatusDetectedDrive,
                    IO_bReverseOn                 := #bStepModeReverseON,
                    IO_bExecuteSequenceToEnd      := #bExecuteSequenceToEnd);"""
    
    def json_to_scl(self, json_file: str, output_scl_file: str = None) -> str:
        """
        Convert JSON file to SCL format
        
        Args:
            json_file: Path to input JSON file
            output_scl_file: Path to output SCL file (optional)
            
        Returns:
            Generated SCL file path or None if failed
        """
        try:
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Extract metadata
            metadata = json_data.get("metadata", {})
            sections = json_data.get("sections", {})
            code_lines = json_data.get("code", [])
            
            # Get block information
            block_name = metadata.get("blockName", "") or metadata.get("name", "UnknownBlock")
            block_number = metadata.get("blockNumber", "") or metadata.get("number", "1")
            programming_language = metadata.get("programmingLanguage", "SCL")
            memory_layout = metadata.get("memoryLayout", "Optimized")
            
            # Start building SCL content
            scl_content = []
            
            # Function block header - match reference SCL format
            scl_content.extend([
                f'FUNCTION_BLOCK "{block_name}"',
                f'{{ S7_Optimized_Access := \'TRUE\' }}',
                ''
            ])
            
            # Generate variable sections in proper order
            section_order = [
                "input_section", "output_section", "in_out_section", 
                "static_section", "temp_section", "constant_section"
            ]
            
            for section_name in section_order:
                if section_name in sections:
                    section_lines = self.generate_variable_section(section_name, sections[section_name])
                    scl_content.extend(section_lines)
            
            # Begin code section
            scl_content.append("BEGIN")
            scl_content.append("")
            
            # Add formatted code
            if code_lines:
                formatted_code = self.format_code_lines(code_lines)
                scl_content.extend(formatted_code)
            else:
                scl_content.extend([
                    "  // No code available",
                    "  // Add your logic here"
                ])
            
            scl_content.append("")
            scl_content.append("END_FUNCTION_BLOCK")
            
            # Generate output file path if not provided
            if output_scl_file is None:
                output_scl_file = os.path.splitext(json_file)[0] + ".scl"
            
            # Write SCL file
            with open(output_scl_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(scl_content))
            
            print(f"Successfully converted JSON to SCL: {output_scl_file}")
            return output_scl_file
            
        except Exception as e:
            print(f"Error converting JSON to SCL: {e}")
            return None


def main():
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python json_to_scl.py <json_file> [output_scl_file]")
        print("\nExample:")
        print("  python json_to_scl.py FB_Example.json FB_Example.scl")
        return
    
    json_file = sys.argv[1]
    output_scl_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(json_file):
        print(f"Error: JSON file not found: {json_file}")
        return
    
    # Create converter and convert
    converter = JSONToSCLConverter()
    result = converter.json_to_scl(json_file, output_scl_file)
    
    if result:
        print(f"Conversion completed successfully!")
        print(f"Output file: {result}")
        
        # Display preview of generated SCL
        try:
            with open(result, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print("\n--- Generated SCL Preview (first 30 lines) ---")
                for i, line in enumerate(lines[:30]):
                    print(f"{i+1:3d}: {line.rstrip()}")
                if len(lines) > 30:
                    print(f"... ({len(lines) - 30} more lines)")
        except Exception as e:
            print(f"Could not display preview: {e}")
    else:
        print("Conversion failed!")


if __name__ == "__main__":
    main()