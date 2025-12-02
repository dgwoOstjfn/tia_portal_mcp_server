"""
SCL to JSON Converter for TIA Portal Blocks
Converts SCL (Structured Control Language) format to JSON representation
Enhanced version based on xml_to_json.py logic
"""
import json
import os
import re
from typing import Dict, List, Any, Optional, Tuple


class SCLToJSONConverter:
    """Converts SCL format to JSON structured data"""
    
    def __init__(self):
        self.current_line = 0
        self.lines = []
        
    def parse_scl_header(self, content: str) -> Dict[str, str]:
        """Parse SCL header information with support for all block types (FB, FC, OB, DB)"""
        metadata = {
            "blockName": "",
            "blockType": "FB",  # Default to FB, will be detected
            "blockNumber": "1",
            "programmingLanguage": "SCL",
            "memoryLayout": "Optimized",
            "memoryReserve": "100",
            "enoSetting": "false",
            "engineeringVersion": "V17",
            "description": "TIA Portal block converted from SCL",
            "returnType": None,  # For FC return type
            "xmlNamespaceInfo": {
                "interface": {
                    "namespace": "http://www.siemens.com/automation/Openness/SW/Interface/v5",
                    "description": "XML namespace for the Interface/Sections elements"
                },
                "networkSource": {
                    "namespace": "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v3",
                    "description": "XML namespace for the NetworkSource/StructuredText elements"
                }
            }
        }

        # Try to match different block types in order of specificity

        # 1. FUNCTION_BLOCK (FB) - must check before FUNCTION
        fb_match = re.search(r'FUNCTION_BLOCK\s+"([^"]+)"', content)
        if fb_match:
            metadata["blockName"] = fb_match.group(1)
            metadata["name"] = fb_match.group(1)
            metadata["blockType"] = "FB"
            metadata["description"] = "TIA Portal Function Block converted from SCL"

        # 2. FUNCTION (FC) - with optional return type
        # Pattern: FUNCTION "name" : ReturnType
        elif re.search(r'(?<!FUNCTION_BLOCK\s)FUNCTION\s+"([^"]+)"', content):
            fc_match = re.search(r'FUNCTION\s+"([^"]+)"\s*:\s*(\w+)', content)
            if fc_match:
                metadata["blockName"] = fc_match.group(1)
                metadata["name"] = fc_match.group(1)
                metadata["blockType"] = "FC"
                metadata["returnType"] = fc_match.group(2)
                metadata["description"] = "TIA Portal Function converted from SCL"
            else:
                # FC without return type (returns Void)
                fc_match_no_ret = re.search(r'FUNCTION\s+"([^"]+)"', content)
                if fc_match_no_ret:
                    metadata["blockName"] = fc_match_no_ret.group(1)
                    metadata["name"] = fc_match_no_ret.group(1)
                    metadata["blockType"] = "FC"
                    metadata["returnType"] = "Void"
                    metadata["description"] = "TIA Portal Function converted from SCL"

        # 3. ORGANIZATION_BLOCK (OB)
        ob_match = re.search(r'ORGANIZATION_BLOCK\s+"([^"]+)"', content)
        if ob_match:
            metadata["blockName"] = ob_match.group(1)
            metadata["name"] = ob_match.group(1)
            metadata["blockType"] = "OB"
            metadata["description"] = "TIA Portal Organization Block converted from SCL"
            # Extract OB number if present (e.g., OB1, OB100)
            ob_num_match = re.search(r'OB(\d+)', ob_match.group(1))
            if ob_num_match:
                metadata["blockNumber"] = ob_num_match.group(1)

        # 4. DATA_BLOCK (DB)
        db_match = re.search(r'DATA_BLOCK\s+"([^"]+)"', content)
        if db_match:
            metadata["blockName"] = db_match.group(1)
            metadata["name"] = db_match.group(1)
            metadata["blockType"] = "GlobalDB"
            metadata["description"] = "TIA Portal Data Block converted from SCL"
            metadata["programmingLanguage"] = "DB"

        # Extract S7_Optimized_Access setting
        opt_match = re.search(r'S7_Optimized_Access\s*:=\s*[\'"]([^\'"]+)[\'"]', content)
        if opt_match:
            metadata["memoryLayout"] = "Optimized" if opt_match.group(1) == "TRUE" else "Standard"

        # Extract version if present
        version_match = re.search(r'VERSION\s*:\s*([\d.]+)', content)
        if version_match:
            metadata["version"] = version_match.group(1)

        # Extract author if present
        author_match = re.search(r'AUTHOR\s*:\s*([^\n]+)', content)
        if author_match:
            metadata["author"] = author_match.group(1).strip()

        return metadata
    
    def parse_variable_section(self, section_content: str, section_type: str) -> List[Dict[str, str]]:
        """Parse a variable section (VAR_INPUT, VAR_OUTPUT, etc.) with enhanced struct handling"""
        variables = []
        
        # Remove section declaration and END_VAR
        lines = section_content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines, comments, and section markers
            if not line or line.startswith('//') or line.startswith('(*') or line.startswith('VAR') or line.startswith('END_VAR'):
                i += 1
                continue
            
            # Handle multi-line struct definitions
            if 'Struct' in line and not line.endswith(';'):
                # This is a struct definition that spans multiple lines
                struct_var_match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*.*?\s*:\s*Struct.*', line)
                if struct_var_match:
                    var_name = struct_var_match.group(1)
                    variables.append({
                        "name": var_name,
                        "datatype": "Struct"
                    })
                
                # Skip to END_STRUCT
                i += 1
                while i < len(lines) and 'END_STRUCT' not in lines[i]:
                    i += 1
                i += 1  # Skip END_STRUCT line
                continue
            
            # Handle struct end markers
            if 'END_STRUCT' in line:
                i += 1
                continue
                
            # Parse variable declarations: name : datatype;
            # Enhanced pattern to handle attributes and complex datatypes
            var_match = re.match(r'\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\{[^}]*\})?\s*:\s*([^;]+);.*', line)
            if var_match:
                var_name = var_match.group(1)
                var_datatype = var_match.group(2).strip()
                
                # Clean up datatype - remove attributes and extra spaces
                var_datatype = re.sub(r'\s*\{[^}]*\}\s*', '', var_datatype).strip()
                
                # Handle quoted datatypes (keep quotes for UDTs)
                # No modification needed for quoted types
                
                variables.append({
                    "name": var_name,
                    "datatype": var_datatype
                })
            
            i += 1
        
        return variables
    
    def extract_variable_sections(self, content: str) -> Dict[str, List[Dict[str, str]]]:
        """Extract all variable sections from SCL content with enhanced parsing"""
        sections = {
            "input_section": [],
            "output_section": [],
            "in_out_section": [],
            "static_section": [],
            "temp_section": [],
            "constant_section": []
        }
        
        # Process sections in order, removing matched sections to avoid conflicts
        remaining_content = content
        
        # 1. VAR_INPUT
        input_matches = re.findall(r'VAR_INPUT(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in input_matches:
            variables = self.parse_variable_section(match, "input_section")
            sections["input_section"].extend(variables)
        remaining_content = re.sub(r'VAR_INPUT.*?END_VAR', '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 2. VAR_OUTPUT
        output_matches = re.findall(r'VAR_OUTPUT(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in output_matches:
            variables = self.parse_variable_section(match, "output_section")
            sections["output_section"].extend(variables)
        remaining_content = re.sub(r'VAR_OUTPUT.*?END_VAR', '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 3. VAR_IN_OUT
        inout_matches = re.findall(r'VAR_IN_OUT(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in inout_matches:
            variables = self.parse_variable_section(match, "in_out_section")
            sections["in_out_section"].extend(variables)
        remaining_content = re.sub(r'VAR_IN_OUT.*?END_VAR', '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 4. VAR_TEMP
        temp_matches = re.findall(r'VAR_TEMP(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in temp_matches:
            variables = self.parse_variable_section(match, "temp_section")
            sections["temp_section"].extend(variables)
        remaining_content = re.sub(r'VAR_TEMP.*?END_VAR', '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 5. VAR CONSTANT
        constant_matches = re.findall(r'VAR\s+CONSTANT(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in constant_matches:
            variables = self.parse_variable_section(match, "constant_section")
            sections["constant_section"].extend(variables)
        remaining_content = re.sub(r'VAR\s+CONSTANT.*?END_VAR', '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 6. VAR RETAIN (before plain VAR)
        retain_matches = re.findall(r'VAR\s+RETAIN(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in retain_matches:
            variables = self.parse_variable_section(match, "static_section")
            sections["static_section"].extend(variables)
        remaining_content = re.sub(r'VAR\s+RETAIN.*?END_VAR', '', remaining_content, flags=re.DOTALL | re.IGNORECASE)
        
        # 7. VAR (static) - Only plain VAR without any suffix
        static_matches = re.findall(r'(?<!\w)VAR\s*\n(.*?)END_VAR', remaining_content, re.DOTALL | re.IGNORECASE)
        for match in static_matches:
            variables = self.parse_variable_section(match, "static_section")
            sections["static_section"].extend(variables)
        
        return sections
    
    def extract_code_section(self, content: str, block_type: str = None) -> List[str]:
        """Extract code section between BEGIN and END marker for all block types

        Supports:
        - FB: BEGIN...END_FUNCTION_BLOCK
        - FC: BEGIN...END_FUNCTION
        - OB: BEGIN...END_ORGANIZATION_BLOCK
        - DB: BEGIN...END_DATA_BLOCK (for initial values)
        """
        code_lines = []

        # Define END markers for each block type
        end_markers = {
            "FB": "END_FUNCTION_BLOCK",
            "FC": "END_FUNCTION",
            "OB": "END_ORGANIZATION_BLOCK",
            "GlobalDB": "END_DATA_BLOCK",
            "InstanceDB": "END_DATA_BLOCK"
        }

        # If block_type not specified, try all patterns
        if block_type and block_type in end_markers:
            patterns_to_try = [end_markers[block_type]]
        else:
            # Try all patterns in order of specificity (longest first to avoid partial matches)
            patterns_to_try = ["END_FUNCTION_BLOCK", "END_ORGANIZATION_BLOCK", "END_DATA_BLOCK", "END_FUNCTION"]

        begin_match = None
        for end_marker in patterns_to_try:
            pattern = rf'BEGIN\s*\n(.*?){end_marker}'
            begin_match = re.search(pattern, content, re.DOTALL)
            if begin_match:
                break

        if begin_match:
            code_content = begin_match.group(1)

            # Split into lines and clean up
            lines = code_content.split('\n')
            for line in lines:
                # Keep original line (don't strip leading whitespace for indentation)
                cleaned_line = line.rstrip()

                # Filter out obvious placeholder lines but keep meaningful code
                if cleaned_line and not (cleaned_line.strip() == "// No code available" or
                                        cleaned_line.strip() == "// Add your logic here"):
                    code_lines.append(cleaned_line)
                elif cleaned_line == "":  # Keep empty lines for structure
                    code_lines.append(cleaned_line)

            # Remove trailing empty lines
            while code_lines and not code_lines[-1]:
                code_lines.pop()

            # Remove leading empty lines
            while code_lines and not code_lines[0]:
                code_lines.pop(0)

        return code_lines
    
    def scl_to_json(self, scl_file: str, output_json_file: str = None) -> str:
        """
        Convert SCL file to JSON format with enhanced error handling and logging
        
        Args:
            scl_file: Path to input SCL file
            output_json_file: Path to output JSON file (optional)
            
        Returns:
            Generated JSON file path or None if failed
        """
        try:
            # Read SCL file
            with open(scl_file, 'r', encoding='utf-8') as f:
                scl_content = f.read()
            
            print(f"Processing SCL file: {scl_file}")
            
            # Parse header information
            metadata = self.parse_scl_header(scl_content)
            block_type = metadata.get("blockType", "FB")
            print(f"Parsed metadata: Block name = {metadata.get('blockName', 'N/A')}, Block type = {block_type}")

            # Extract variable sections
            sections = self.extract_variable_sections(scl_content)
            section_summary = {k: len(v) for k, v in sections.items() if v}
            print(f"Extracted sections: {section_summary}")

            # Extract code section (pass block_type for correct END marker matching)
            code_lines = self.extract_code_section(scl_content, block_type)
            print(f"Extracted {len(code_lines)} lines of code")
            
            # Build JSON structure matching xml_to_json.py format
            json_data = {
                "metadata": metadata,
                "sections": sections,
                "code": code_lines
            }
            
            # Generate output file path if not provided
            if output_json_file is None:
                output_json_file = os.path.splitext(scl_file)[0] + "_fromscl.json"
            
            # Write JSON file
            with open(output_json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            print(f"Successfully converted SCL to JSON: {output_json_file}")
            return output_json_file
            
        except Exception as e:
            print(f"Error converting SCL to JSON: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python scl_to_json.py <scl_file> [output_json_file]")
        print("\nExample:")
        print("  python scl_to_json.py FB_Example.scl FB_Example_fromscl.json")
        return
    
    scl_file = sys.argv[1]
    output_json_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(scl_file):
        print(f"Error: SCL file not found: {scl_file}")
        return
    
    # Create converter and convert
    converter = SCLToJSONConverter()
    result = converter.scl_to_json(scl_file, output_json_file)
    
    if result:
        print(f"Conversion completed successfully!")
        print(f"Output file: {result}")
        
        # Display preview of generated JSON
        try:
            with open(result, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                print("\n--- Generated JSON Preview ---")
                print(f"Block Name: {json_data.get('metadata', {}).get('blockName', 'N/A')}")
                print(f"Programming Language: {json_data.get('metadata', {}).get('programmingLanguage', 'N/A')}")
                
                sections = json_data.get('sections', {})
                for section_name, variables in sections.items():
                    if variables:
                        print(f"{section_name}: {len(variables)} variables")
                
                code_lines = json_data.get('code', [])
                print(f"Code lines: {len(code_lines)}")
                
                if code_lines:
                    print("\n--- First few code lines ---")
                    for i, line in enumerate(code_lines[:10]):
                        print(f"{i+1:3d}: {line}")
                    if len(code_lines) > 10:
                        print(f"... ({len(code_lines) - 10} more lines)")
                        
        except Exception as e:
            print(f"Could not display preview: {e}")
    else:
        print("Conversion failed!")


if __name__ == "__main__":
    main()