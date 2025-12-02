"""
JSON to XML Converter for TIA Portal Blocks
Converts JSON representation back to TIA Portal XML format
Enhanced version with support for all block types (FB, FC, OB, DB)
"""
import xml.etree.ElementTree as ET
import os
import json
import re
from xml.dom import minidom
from typing import List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class TIAXMLGenerator:
    """TIA Portal XML generator with enhanced UId management and structured text formatting"""

    def __init__(self):
        self.uid_counter = 1
        self.scl_operators = [
            ':=', '=', '<>', '>', '<', '>=', '<=', '+', '-', '*', '/', 'MOD',
            'AND', 'OR', 'XOR', 'NOT', '&', 'THEN', 'ELSE', 'ELSEIF',
            'DO', 'TO', 'BY', ';', '(', ')', '[', ']', ',', '.', ':'
        ]
        self.scl_keywords = [
            'IF', 'THEN', 'ELSE', 'ELSEIF', 'END_IF', 'CASE', 'OF', 'END_CASE',
            'FOR', 'TO', 'BY', 'DO', 'END_FOR', 'WHILE', 'END_WHILE',
            'REPEAT', 'UNTIL', 'END_REPEAT', 'EXIT', 'CONTINUE', 'RETURN',
            'TRUE', 'FALSE', 'AND', 'OR', 'XOR', 'NOT', 'REGION', 'END_REGION',
            'ABS', 'MIN', 'MAX'
        ]

    def get_next_uid(self) -> str:
        """Get next UId for XML elements"""
        uid = str(self.uid_counter)
        self.uid_counter += 1
        return uid

    def reset_uid_counter(self, start_value: int = 1):
        """Reset UId counter to specified start value"""
        self.uid_counter = start_value

    def tokenize_scl_line(self, line: str) -> List[Tuple[str, str]]:
        """
        Tokenize SCL code line into (token_type, token_value) tuples
        Enhanced tokenization based on xml_to_json.py logic
        """
        tokens = []
        line = line.strip()
        if not line:
            return tokens

        i = 0
        while i < len(line):
            # Handle whitespace
            if line[i].isspace():
                space_count = 0
                while i < len(line) and line[i].isspace():
                    space_count += 1
                    i += 1
                tokens.append(('WHITESPACE', str(space_count)))
                continue

            # Check for multi-character operators (sorted by length, longest first)
            found_operator = False
            for op in sorted(self.scl_operators, key=len, reverse=True):
                if line[i:].startswith(op):
                    tokens.append(('OPERATOR', op))
                    i += len(op)
                    found_operator = True
                    break

            if found_operator:
                continue

            # Handle numeric constants (including time constants like T#8s)
            if line[i].isdigit() or (line[i].upper() == 'T' and i + 1 < len(line) and line[i + 1] == '#'):
                num_str = ''
                # Handle time constants T#...
                if line[i].upper() == 'T' and i + 1 < len(line) and line[i + 1] == '#':
                    num_str = 'T#'
                    i += 2
                    while i < len(line) and (line[i].isalnum() or line[i] in '._'):
                        num_str += line[i]
                        i += 1
                else:
                    # Regular numbers
                    while i < len(line) and (line[i].isdigit() or line[i] == '.'):
                        num_str += line[i]
                        i += 1
                tokens.append(('CONSTANT', num_str))
                continue

            # Handle string constants
            if line[i] in ['"', "'"]:
                quote = line[i]
                str_literal = quote
                i += 1
                while i < len(line) and line[i] != quote:
                    str_literal += line[i]
                    i += 1
                if i < len(line):
                    str_literal += line[i]
                    i += 1
                tokens.append(('CONSTANT', str_literal))
                continue

            # Handle identifiers (variables, keywords)
            if line[i].isalpha() or line[i] == '_' or line[i] == '#':
                identifier = ''
                # Handle variable references with #
                if line[i] == '#':
                    identifier += line[i]
                    i += 1

                while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                    identifier += line[i]
                    i += 1

                # Check if it's a keyword or constant
                if identifier.upper() in self.scl_keywords:
                    if identifier.upper() in ['TRUE', 'FALSE']:
                        tokens.append(('CONSTANT', identifier.upper()))
                    else:
                        tokens.append(('KEYWORD', identifier.upper()))
                else:
                    tokens.append(('VARIABLE', identifier))
                continue

            # Handle other single characters
            tokens.append(('UNKNOWN', line[i]))
            i += 1

        return tokens

    def create_structured_text_xml(self, code_lines: List[str]) -> str:
        """
        Create StructuredText XML from code lines
        Enhanced version with better token handling
        """
        xml_elements = []

        for line_idx, line in enumerate(code_lines):
            if line_idx > 0:  # Add newline (except for first line)
                xml_elements.append(f'  <NewLine UId="{self.get_next_uid()}" />')

            # Handle empty lines
            if not line.strip():
                continue

            tokens = self.tokenize_scl_line(line)

            for token_type, token_value in tokens:
                if token_type == 'WHITESPACE':
                    # Handle whitespace
                    if token_value == '1':
                        xml_elements.append(f'  <Blank UId="{self.get_next_uid()}" />')
                    else:
                        xml_elements.append(f'  <Blank Num="{token_value}" UId="{self.get_next_uid()}" />')

                elif token_type in ['KEYWORD', 'OPERATOR']:
                    # Keywords and operators as tokens
                    xml_elements.append(f'  <Token Text="{self.escape_xml(token_value)}" UId="{self.get_next_uid()}" />')

                elif token_type == 'VARIABLE':
                    # Variable access - determine scope based on prefix and content
                    var_name = token_value
                    scope = "LocalVariable"  # Default scope

                    # Remove # prefix for component name but keep scope info
                    if var_name.startswith('#'):
                        var_name = var_name[1:]
                        scope = "LocalVariable"
                    elif var_name.startswith('"') and var_name.endswith('"'):
                        scope = "GlobalVariable"
                        var_name = var_name[1:-1]  # Remove quotes for component name

                    access_uid = self.get_next_uid()
                    symbol_uid = self.get_next_uid()
                    component_uid = self.get_next_uid()

                    xml_elements.append(f'  <Access Scope="{scope}" UId="{access_uid}">')
                    xml_elements.append(f'    <Symbol UId="{symbol_uid}">')
                    xml_elements.append(f'      <Component Name="{self.escape_xml(var_name)}" UId="{component_uid}" />')
                    xml_elements.append('    </Symbol>')
                    xml_elements.append('  </Access>')

                elif token_type == 'CONSTANT':
                    # Literal constants
                    scope = "TypedConstant" if token_value.startswith('T#') else "LiteralConstant"
                    access_uid = self.get_next_uid()
                    constant_uid = self.get_next_uid()
                    value_uid = self.get_next_uid()

                    xml_elements.append(f'  <Access Scope="{scope}" UId="{access_uid}">')
                    xml_elements.append(f'    <Constant UId="{constant_uid}">')
                    xml_elements.append(f'      <ConstantValue UId="{value_uid}">{self.escape_xml(token_value)}</ConstantValue>')
                    xml_elements.append('    </Constant>')
                    xml_elements.append('  </Access>')

                else:
                    # Unknown types as tokens
                    xml_elements.append(f'  <Token Text="{self.escape_xml(token_value)}" UId="{self.get_next_uid()}" />')

        # Assemble complete StructuredText element
        structured_text = '<StructuredText xmlns="http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v3">\n'
        structured_text += '\n'.join(xml_elements)
        structured_text += '\n</StructuredText>'

        return structured_text

    def escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text


def get_xml_template(block_type: str) -> str:
    """Get the XML template for the specified block type"""

    # FB (Function Block) template
    fb_template = '''<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="{engineering_version}" />
  <DocumentInfo>
    <Created>2025-01-01T00:00:00.0000000Z</Created>
    <ExportSetting>None</ExportSetting>
  </DocumentInfo>
  <SW.Blocks.FB ID="0">
    <AttributeList>
      <Interface>{sections_xml}</Interface>
      <MemoryLayout>{memory_layout}</MemoryLayout>
      <MemoryReserve>{memory_reserve}</MemoryReserve>
      <Name>{block_name}</Name>
      <Number>{block_number}</Number>
      <ProgrammingLanguage>{programming_language}</ProgrammingLanguage>
      <SetENOAutomatically>{eno_setting}</SetENOAutomatically>
    </AttributeList>
    <ObjectList>
      <MultilingualText ID="1" CompositionName="Comment">
        <ObjectList>
          <MultilingualTextItem ID="2" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
      <SW.Blocks.CompileUnit ID="3" CompositionName="CompileUnits">
        <AttributeList>
          <NetworkSource>{structured_text}</NetworkSource>
          <ProgrammingLanguage>{programming_language}</ProgrammingLanguage>
        </AttributeList>
        <ObjectList>
          <MultilingualText ID="4" CompositionName="Comment">
            <ObjectList>
              <MultilingualTextItem ID="5" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
          <MultilingualText ID="6" CompositionName="Title">
            <ObjectList>
              <MultilingualTextItem ID="7" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
        </ObjectList>
      </SW.Blocks.CompileUnit>
      <MultilingualText ID="8" CompositionName="Title">
        <ObjectList>
          <MultilingualTextItem ID="9" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
    </ObjectList>
  </SW.Blocks.FB>
</Document>'''

    # FC (Function) template - similar to FB but with SW.Blocks.FC
    fc_template = '''<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="{engineering_version}" />
  <DocumentInfo>
    <Created>2025-01-01T00:00:00.0000000Z</Created>
    <ExportSetting>None</ExportSetting>
  </DocumentInfo>
  <SW.Blocks.FC ID="0">
    <AttributeList>
      <Interface>{sections_xml}</Interface>
      <MemoryLayout>{memory_layout}</MemoryLayout>
      <Name>{block_name}</Name>
      <Number>{block_number}</Number>
      <ProgrammingLanguage>{programming_language}</ProgrammingLanguage>
      <SetENOAutomatically>{eno_setting}</SetENOAutomatically>
    </AttributeList>
    <ObjectList>
      <MultilingualText ID="1" CompositionName="Comment">
        <ObjectList>
          <MultilingualTextItem ID="2" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
      <SW.Blocks.CompileUnit ID="3" CompositionName="CompileUnits">
        <AttributeList>
          <NetworkSource>{structured_text}</NetworkSource>
          <ProgrammingLanguage>{programming_language}</ProgrammingLanguage>
        </AttributeList>
        <ObjectList>
          <MultilingualText ID="4" CompositionName="Comment">
            <ObjectList>
              <MultilingualTextItem ID="5" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
          <MultilingualText ID="6" CompositionName="Title">
            <ObjectList>
              <MultilingualTextItem ID="7" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
        </ObjectList>
      </SW.Blocks.CompileUnit>
      <MultilingualText ID="8" CompositionName="Title">
        <ObjectList>
          <MultilingualTextItem ID="9" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
    </ObjectList>
  </SW.Blocks.FC>
</Document>'''

    # OB (Organization Block) template
    ob_template = '''<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="{engineering_version}" />
  <DocumentInfo>
    <Created>2025-01-01T00:00:00.0000000Z</Created>
    <ExportSetting>None</ExportSetting>
  </DocumentInfo>
  <SW.Blocks.OB ID="0">
    <AttributeList>
      <Interface>{sections_xml}</Interface>
      <MemoryLayout>{memory_layout}</MemoryLayout>
      <Name>{block_name}</Name>
      <Number>{block_number}</Number>
      <ProgrammingLanguage>{programming_language}</ProgrammingLanguage>
      <SecondaryType>ProgramCycle</SecondaryType>
      <SetENOAutomatically>{eno_setting}</SetENOAutomatically>
    </AttributeList>
    <ObjectList>
      <MultilingualText ID="1" CompositionName="Comment">
        <ObjectList>
          <MultilingualTextItem ID="2" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
      <SW.Blocks.CompileUnit ID="3" CompositionName="CompileUnits">
        <AttributeList>
          <NetworkSource>{structured_text}</NetworkSource>
          <ProgrammingLanguage>{programming_language}</ProgrammingLanguage>
        </AttributeList>
        <ObjectList>
          <MultilingualText ID="4" CompositionName="Comment">
            <ObjectList>
              <MultilingualTextItem ID="5" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
          <MultilingualText ID="6" CompositionName="Title">
            <ObjectList>
              <MultilingualTextItem ID="7" CompositionName="Items">
                <AttributeList>
                  <Culture>en-US</Culture>
                  <Text />
                </AttributeList>
              </MultilingualTextItem>
            </ObjectList>
          </MultilingualText>
        </ObjectList>
      </SW.Blocks.CompileUnit>
      <MultilingualText ID="8" CompositionName="Title">
        <ObjectList>
          <MultilingualTextItem ID="9" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
    </ObjectList>
  </SW.Blocks.OB>
</Document>'''

    # GlobalDB (Data Block) template
    db_template = '''<?xml version="1.0" encoding="utf-8"?>
<Document>
  <Engineering version="{engineering_version}" />
  <DocumentInfo>
    <Created>2025-01-01T00:00:00.0000000Z</Created>
    <ExportSetting>None</ExportSetting>
  </DocumentInfo>
  <SW.Blocks.GlobalDB ID="0">
    <AttributeList>
      <Interface>{sections_xml}</Interface>
      <MemoryLayout>{memory_layout}</MemoryLayout>
      <MemoryReserve>{memory_reserve}</MemoryReserve>
      <Name>{block_name}</Name>
      <Number>{block_number}</Number>
      <ProgrammingLanguage>DB</ProgrammingLanguage>
    </AttributeList>
    <ObjectList>
      <MultilingualText ID="1" CompositionName="Comment">
        <ObjectList>
          <MultilingualTextItem ID="2" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
      <MultilingualText ID="3" CompositionName="Title">
        <ObjectList>
          <MultilingualTextItem ID="4" CompositionName="Items">
            <AttributeList>
              <Culture>en-US</Culture>
              <Text />
            </AttributeList>
          </MultilingualTextItem>
        </ObjectList>
      </MultilingualText>
    </ObjectList>
  </SW.Blocks.GlobalDB>
</Document>'''

    templates = {
        "FB": fb_template,
        "FC": fc_template,
        "OB": ob_template,
        "GlobalDB": db_template,
        "InstanceDB": db_template  # Use same template for instance DB
    }

    return templates.get(block_type, fb_template)


def generate_sections_xml(sections: dict, metadata: dict, xml_gen: 'TIAXMLGenerator') -> str:
    """Generate the Sections XML based on block type and variables"""

    interface_ns = metadata.get("xmlNamespaceInfo", {}).get("interface", {}).get("namespace",
                                "http://www.siemens.com/automation/Openness/SW/Interface/v5")

    block_type = metadata.get("blockType", "FB")
    return_type = metadata.get("returnType")

    sections_xml = f'<Sections xmlns="{interface_ns}">\n'

    # Section mapping between JSON and XML
    # For FC: Input, Output, InOut, Temp, Constant, Return
    # For FB: Input, Output, InOut, Static, Temp, Constant
    # For OB: Input (for OB parameters), Temp
    # For DB: Static (for data members)

    if block_type == "FC":
        section_order = [
            ("input_section", "Input"),
            ("output_section", "Output"),
            ("in_out_section", "InOut"),
            ("temp_section", "Temp"),
            ("constant_section", "Constant"),
            ("return_section", "Return")  # FC has Return section
        ]
    elif block_type == "OB":
        section_order = [
            ("input_section", "Input"),
            ("temp_section", "Temp"),
            ("constant_section", "Constant")
        ]
    elif block_type in ["GlobalDB", "InstanceDB"]:
        section_order = [
            ("static_section", "Static")  # DB uses Static for data members
        ]
    else:  # FB
        section_order = [
            ("input_section", "Input"),
            ("output_section", "Output"),
            ("in_out_section", "InOut"),
            ("static_section", "Static"),
            ("temp_section", "Temp"),
            ("constant_section", "Constant")
        ]

    for json_section_name, xml_section_name in section_order:
        # Special handling for FC Return section
        if json_section_name == "return_section" and block_type == "FC":
            if return_type and return_type != "Void":
                sections_xml += f'  <Section Name="Return">\n'
                sections_xml += f'    <Member Name="Ret_Val" Datatype="{xml_gen.escape_xml(return_type)}" />\n'
                sections_xml += '  </Section>\n'
            else:
                sections_xml += '  <Section Name="Return" />\n'
            continue

        variables = sections.get(json_section_name, [])

        if variables:
            sections_xml += f'  <Section Name="{xml_section_name}">\n'
            for variable in variables:
                var_name = variable.get("name", "")
                var_datatype = variable.get("datatype", "")
                # Escape XML characters in attributes
                var_name = xml_gen.escape_xml(var_name)
                var_datatype = xml_gen.escape_xml(var_datatype)
                sections_xml += f'    <Member Name="{var_name}" Datatype="{var_datatype}" />\n'
            sections_xml += '  </Section>\n'
        else:
            # Empty sections still need to be present
            sections_xml += f'  <Section Name="{xml_section_name}" />\n'

    sections_xml += '</Sections>'
    return sections_xml


def json_to_xml(json_file: str, output_xml_file: str = None) -> str:
    """
    Convert JSON file to TIA Portal XML format
    Enhanced version with support for all block types (FB, FC, OB, DB)

    Args:
        json_file: Path to input JSON file
        output_xml_file: Path to output XML file (optional)

    Returns:
        Generated XML file path or None if failed
    """
    try:
        # Read JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        logger.info(f"Processing JSON file: {json_file}")

    except Exception as e:
        logger.error(f"Error reading JSON file: {e}")
        return None

    # Extract data from JSON
    metadata = json_data.get("metadata", {})
    sections = json_data.get("sections", {})
    code_lines = json_data.get("code", [])

    # Determine block type
    block_type = metadata.get("blockType", "FB")

    logger.info(f"Block name: {metadata.get('blockName', 'N/A')}, Block type: {block_type}")
    logger.debug(f"Sections: {[k for k, v in sections.items() if v]}")
    logger.debug(f"Code lines: {len(code_lines)}")

    # Create XML generator
    xml_gen = TIAXMLGenerator()

    # Get the appropriate XML template for this block type
    xml_template = get_xml_template(block_type)

    # Generate Sections XML based on block type
    sections_xml = generate_sections_xml(sections, metadata, xml_gen)

    # Generate StructuredText XML (only for blocks with code)
    if block_type in ["FB", "FC", "OB"]:
        xml_gen.reset_uid_counter(21)  # Start from 21 following TIA Portal convention
        structured_text = xml_gen.create_structured_text_xml(code_lines)
    else:
        structured_text = ""  # DB blocks don't have structured text

    # Ensure required attributes are not empty
    block_number = metadata.get("blockNumber", "") or metadata.get("number", "") or "1"
    block_name = metadata.get("blockName", "") or metadata.get("name", "")
    if not block_name:
        # Use filename as fallback
        block_name = os.path.splitext(os.path.basename(json_file))[0]

    # Fill template with data
    xml_content = xml_template.format(
        engineering_version=metadata.get("engineeringVersion", "V17"),
        sections_xml=sections_xml,
        memory_layout=metadata.get("memoryLayout", "Optimized"),
        memory_reserve=metadata.get("memoryReserve", "100"),
        block_name=xml_gen.escape_xml(block_name),
        block_number=xml_gen.escape_xml(block_number),
        programming_language=metadata.get("programmingLanguage", "SCL"),
        eno_setting=metadata.get("enoSetting", "false"),
        structured_text=structured_text
    )

    # Write output file
    if output_xml_file is None:
        output_xml_file = os.path.splitext(json_file)[0] + "_generated.xml"

    try:
        with open(output_xml_file, 'w', encoding='utf-8') as f:
            f.write(xml_content)

        logger.info(f"Successfully generated TIA Portal XML: {output_xml_file}")
        logger.info(f"Block type: {block_type}, Total UIds generated: {xml_gen.uid_counter - 1}")
        return output_xml_file

    except Exception as e:
        logger.error(f"Error writing XML file: {e}")
        return None


def main():
    """Main function for command line usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python json_to_xml.py <json_file> [output_xml_file]")
        print("\nExample:")
        print("  python json_to_xml.py FB_Example.json FB_Example_generated.xml")
        print("  python json_to_xml.py FC_Example.json FC_Example_generated.xml")
        print("\nSupported block types: FB, FC, OB, GlobalDB")
        print("\nThis script converts JSON files (created by xml_to_json.py or scl_to_json.py)")
        print("back to TIA Portal XML format.")
        return

    json_file = sys.argv[1]
    output_xml_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(json_file):
        print(f"Error: JSON file not found: {json_file}")
        return

    # Execute conversion
    result = json_to_xml(json_file, output_xml_file)

    if result:
        print(f"\nConversion completed successfully!")
        print(f"Output file: {result}")

        # Display preview of generated XML
        try:
            with open(result, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print("\n--- Generated XML Preview (first 30 lines) ---")
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
