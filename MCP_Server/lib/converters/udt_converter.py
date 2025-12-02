"""
UDT (User-Defined Type) XML to .udt converter and vice versa
Handles conversion between TIA Portal UDT XML format and .udt SCL-like format
"""
import xml.etree.ElementTree as ET
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class UDTConverter:
    """Converts UDTs between XML and .udt formats"""
    
    def __init__(self):
        self.namespaces = {
            'ns': 'http://www.siemens.com/automation/Openness/SW/DataTypes/v5'
        }
        
    def xml_to_udt(self, xml_file_path: str, output_path: str = None) -> str:
        """
        Convert UDT XML to .udt format
        
        Args:
            xml_file_path: Path to input XML file
            output_path: Path for output .udt file (optional)
            
        Returns:
            Path to generated .udt file
        """
        try:
            # Parse XML
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # Find UDT element
            udt_element = root.find('.//SW.Types.PlcStruct')
            if udt_element is None:
                # Try alternative element names
                udt_element = root.find('.//SW.DataTypes.PlcStruct')
                if udt_element is None:
                    raise ValueError("No PlcStruct (UDT) found in XML")
            
            # Extract UDT data
            udt_data = self._extract_udt_data(udt_element)
            
            # Generate .udt content
            udt_content = self._generate_udt_content(udt_data)
            
            # Determine output path
            if output_path is None:
                base_name = Path(xml_file_path).stem
                output_dir = os.path.dirname(xml_file_path)
                output_path = os.path.join(output_dir, f"{base_name}.udt")
            
            # Write .udt file
            with open(output_path, 'w', encoding='utf-8-sig') as f:
                f.write(udt_content)
            
            logger.info(f"Successfully converted {xml_file_path} to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting XML to UDT: {e}")
            raise
    
    def _extract_udt_data(self, udt_element) -> Dict[str, Any]:
        """Extract UDT data from XML element"""
        udt_data = {
            'name': '',
            'version': '0.1',
            'author': '',
            'family': '',
            'description': '',
            'members': []
        }
        
        # Extract attributes
        attrs = udt_element.find('AttributeList')
        if attrs is not None:
            for attr in attrs:
                if attr.tag == 'Name':
                    udt_data['name'] = attr.text or 'UnknownUDT'
                elif attr.tag == 'Version':
                    udt_data['version'] = attr.text or '0.1'
                elif attr.tag == 'Author':
                    udt_data['author'] = attr.text or ''
                elif attr.tag == 'Family':
                    udt_data['family'] = attr.text or ''
        
        # Extract description (comment)
        comment = udt_element.find('.//MultilingualText[@CompositionName="Comment"]')
        if comment is not None:
            # Get English comment by default, fallback to first available
            for item in comment.findall('.//MultilingualTextItem'):
                culture = item.find('AttributeList/Culture')
                text = item.find('AttributeList/Text')
                if culture is not None and text is not None:
                    if culture.text == 'en-US' or not udt_data['description']:
                        udt_data['description'] = text.text or ''
        
        # Extract structure members - try different XML structures
        # First try with Interface/Sections
        interface = udt_element.find('.//Interface')
        if interface is not None:
            sections = interface.find('.//Sections') or interface.find('.//{http://www.siemens.com/automation/Openness/SW/Interface/v5}Sections')
            if sections is not None:
                # Handle with namespace
                for section in sections.findall('.//{http://www.siemens.com/automation/Openness/SW/Interface/v5}Section'):
                    section_name = section.get('Name', '')
                    for member in section.findall('.//{http://www.siemens.com/automation/Openness/SW/Interface/v5}Member'):
                        member_data = self._extract_member_data(member)
                        member_data['section'] = section_name
                        udt_data['members'].append(member_data)
                # Also try without namespace
                for section in sections.findall('.//Section'):
                    section_name = section.get('Name', '')
                    for member in section.findall('.//Member'):
                        member_data = self._extract_member_data(member)
                        member_data['section'] = section_name
                        if member_data not in udt_data['members']:  # Avoid duplicates
                            udt_data['members'].append(member_data)
        
        # Also try direct Sections element
        if not udt_data['members']:
            sections = udt_element.find('.//Sections')
            if sections is not None:
                for section in sections.findall('Section'):
                    section_name = section.get('Name', '')
                    for member in section.findall('Member'):
                        member_data = self._extract_member_data(member)
                        member_data['section'] = section_name
                        udt_data['members'].append(member_data)
        
        return udt_data
    
    def _extract_member_data(self, member_element) -> Dict[str, Any]:
        """Extract member data from XML element"""
        member_data = {
            'name': member_element.get('Name', ''),
            'datatype': member_element.get('Datatype', 'Bool'),
            'comment': '',
            'initial_value': '',
            'attributes': {}
        }
        
        # Extract comment - try with and without namespace
        comment_elem = None
        
        # Try with namespace first
        for child in member_element:
            if 'Comment' in child.tag:
                comment_elem = child
                break
        
        # If not found, try without namespace
        if comment_elem is None:
            comment_elem = member_element.find('Comment')
        
        if comment_elem is not None:
            # First check for direct text content
            if comment_elem.text:
                member_data['comment'] = comment_elem.text.strip()
            else:
                # Try to find multilingual text
                multilingual = comment_elem.find('.//MultilingualTextItem')
                if multilingual is not None:
                    text = multilingual.find('AttributeList/Text')
                    if text is not None and text.text:
                        member_data['comment'] = text.text.strip()
        
        # Extract initial value
        start_value = member_element.find('StartValue')
        if start_value is not None:
            member_data['initial_value'] = start_value.text or ''
        
        # Extract attributes (Retain, etc.)
        for attr in member_element.findall('AttributeList/*'):
            member_data['attributes'][attr.tag] = attr.text
        
        # Handle nested structures and arrays
        if member_element.find('Member') is not None:
            # Nested structure
            member_data['nested_members'] = []
            for nested in member_element.findall('Member'):
                member_data['nested_members'].append(self._extract_member_data(nested))
        
        # Check for array dimensions
        array_bounds = member_element.find('ArrayBounds')
        if array_bounds is not None:
            bounds = []
            for dimension in array_bounds.findall('Dimension'):
                lower = dimension.get('Lower', '0')
                upper = dimension.get('Upper', '0')
                bounds.append(f"[{lower}..{upper}]")
            if bounds:
                member_data['array_bounds'] = ''.join(bounds)
        
        return member_data
    
    def _generate_udt_content(self, udt_data: Dict) -> str:
        """Generate .udt file content from UDT data"""
        lines = []
        
        # Header
        lines.append(f'TYPE "{udt_data["name"]}"')
        lines.append(f'VERSION : {udt_data["version"]}')
        
        # Add author and family as comments if present
        if udt_data.get('author'):
            lines.append(f'   // Author: {udt_data["author"]}')
        if udt_data.get('family'):
            lines.append(f'   // Family: {udt_data["family"]}')
        if udt_data.get('description'):
            lines.append(f'   // {udt_data["description"]}')
        
        # Structure
        lines.append('   STRUCT')
        
        # Members
        for member in udt_data['members']:
            lines.extend(self._format_member(member, indent=6))
        
        # End structure
        lines.append('   END_STRUCT;')
        lines.append('')
        lines.append('END_TYPE')
        lines.append('')
        lines.append('')
        
        return '\n'.join(lines)
    
    def _format_member(self, member: Dict, indent: int = 6) -> List[str]:
        """Format a single member for .udt output"""
        lines = []
        indent_str = ' ' * indent
        
        # Handle nested structures
        if member.get('nested_members'):
            # Nested struct
            line = f"{indent_str}{member['name']} : STRUCT"
            if member.get('comment'):
                line += f"   // {member['comment']}"
            lines.append(line)
            
            for nested in member['nested_members']:
                lines.extend(self._format_member(nested, indent + 3))
            
            lines.append(f"{indent_str}END_STRUCT;")
        else:
            # Simple member
            datatype = member['datatype']
            
            # Add array bounds if present
            if member.get('array_bounds'):
                datatype = f"Array{member['array_bounds']} of {datatype}"
            
            line = f"{indent_str}{member['name']} : {datatype}"
            
            # Add initial value if present
            if member.get('initial_value'):
                line += f" := {member['initial_value']}"
            
            line += ";"
            
            # Add comment if present
            if member.get('comment'):
                line += f"   // {member['comment']}"
            
            lines.append(line)
        
        return lines
    
    def udt_to_xml(self, udt_file_path: str, output_path: str = None,
                   engineering_version: str = "V20") -> str:
        """
        Convert .udt file to UDT XML format

        Args:
            udt_file_path: Path to input .udt file
            output_path: Path for output XML file (optional)
            engineering_version: TIA Portal version (default: V20)
            
        Returns:
            Path to generated XML file
        """
        try:
            # Parse .udt file
            with open(udt_file_path, 'r', encoding='utf-8-sig') as f:
                udt_content = f.read()
            
            udt_data = self._parse_udt_content(udt_content)
            
            # Create XML structure
            root = self._create_udt_xml(udt_data, engineering_version)
            
            # Determine output path
            if output_path is None:
                base_name = Path(udt_file_path).stem
                output_dir = os.path.dirname(udt_file_path)
                output_path = os.path.join(output_dir, f"{base_name}.xml")
            
            # Write XML with proper formatting
            self._write_formatted_xml(root, output_path)
            
            logger.info(f"Successfully converted {udt_file_path} to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting UDT to XML: {e}")
            raise
    
    def _parse_udt_content(self, content: str) -> Dict[str, Any]:
        """Parse .udt file content"""
        udt_data = {
            'name': '',
            'version': '0.1',
            'author': '',
            'family': '',
            'description': '',
            'members': []
        }
        
        lines = content.split('\n')
        current_line = 0
        
        while current_line < len(lines):
            line = lines[current_line].strip()
            
            # Parse TYPE declaration
            if line.startswith('TYPE'):
                match = re.match(r'TYPE\s+"([^"]+)"', line)
                if match:
                    udt_data['name'] = match.group(1)
            
            # Parse VERSION
            elif line.startswith('VERSION'):
                match = re.match(r'VERSION\s*:\s*(\S+)', line)
                if match:
                    udt_data['version'] = match.group(1)
            
            # Parse comments for metadata
            elif line.startswith('//'):
                comment = line[2:].strip()
                if comment.startswith('Author:'):
                    udt_data['author'] = comment[7:].strip()
                elif comment.startswith('Family:'):
                    udt_data['family'] = comment[7:].strip()
                elif not udt_data['description'] and not comment.startswith('Author:') and not comment.startswith('Family:'):
                    udt_data['description'] = comment
            
            # Parse STRUCT section
            elif line == 'STRUCT':
                current_line += 1
                members, current_line = self._parse_struct_members(lines, current_line)
                udt_data['members'] = members
            
            current_line += 1
        
        return udt_data
    
    def _parse_struct_members(self, lines: List[str], start_line: int) -> Tuple[List[Dict], int]:
        """Parse structure members from .udt content"""
        members = []
        current_line = start_line
        
        while current_line < len(lines):
            # Get original line with leading spaces preserved
            full_line = lines[current_line]
            line = full_line.strip()
            
            # Check for end of struct
            if line.startswith('END_STRUCT'):
                break
            
            # Skip empty lines and comments
            if not line or line.startswith('//'):
                current_line += 1
                continue
            
            # Parse member declaration - handle both simple and complex formats
            # Match: name : type ; // comment
            # or: name : type := value ; // comment
            member_match = re.match(r'(\w+)\s*:\s*([^;:=]+?)(?:\s*:=\s*([^;]+?))?(?:\s*;)?(?:\s*//\s*(.+))?$', line)
            if member_match:
                member_name = member_match.group(1)
                member_type = member_match.group(2).strip()
                initial_value = member_match.group(3) or ''
                comment = member_match.group(4) or ''
                
                member_data = {
                    'name': member_name,
                    'datatype': member_type,
                    'initial_value': initial_value.strip(),
                    'comment': comment.strip()
                }
                
                # Check for nested STRUCT
                if member_type == 'STRUCT':
                    current_line += 1
                    nested_members, current_line = self._parse_struct_members(lines, current_line)
                    member_data['nested_members'] = nested_members
                    member_data['datatype'] = 'Struct'
                
                # Check for arrays
                array_match = re.match(r'Array\[(.+?)\]\s+of\s+(.+)', member_type)
                if array_match:
                    bounds = array_match.group(1)
                    base_type = array_match.group(2)
                    member_data['datatype'] = base_type
                    member_data['array_bounds'] = bounds
                
                members.append(member_data)
            
            current_line += 1
        
        return members, current_line
    
    def _create_udt_xml(self, udt_data: Dict, engineering_version: str) -> ET.Element:
        """Create UDT XML structure from parsed data"""
        # Create root element
        root = ET.Element("Document")
        
        # Add engineering version
        eng = ET.SubElement(root, "Engineering")
        eng.set("version", engineering_version)
        
        # Add DocumentInfo
        doc_info = ET.SubElement(root, "DocumentInfo")
        created = ET.SubElement(doc_info, "Created")
        from datetime import datetime
        created.text = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        export_setting = ET.SubElement(doc_info, "ExportSetting")
        export_setting.text = "None"
        
        # Add SW.Types.PlcStruct (UDT)
        udt_elem = ET.SubElement(root, "SW.Types.PlcStruct")
        udt_elem.set("ID", "0")
        
        # Add attributes
        attr_list = ET.SubElement(udt_elem, "AttributeList")

        # UDT Name - TIA Portal requires <Name> element in AttributeList
        name_elem = ET.SubElement(attr_list, "Name")
        name_elem.text = udt_data['name']
        
        # Add interface with sections (Must be inside AttributeList after Name)
        interface = ET.SubElement(attr_list, "Interface")
        sections = ET.SubElement(interface, "Sections")
        sections.set("xmlns", "http://www.siemens.com/automation/Openness/SW/Interface/v5")
        
        # Create section for members (UDT uses "None" section)
        section = ET.SubElement(sections, "Section")
        section.set("Name", "None")
        
        # Add members
        for member in udt_data['members']:
            self._add_member_xml(section, member)
        
        # Add Namespace (optional but recommended)
        ET.SubElement(attr_list, "Namespace")

        # Add description as comment (ObjectList is sibling of AttributeList)
        obj_list = ET.SubElement(udt_elem, "ObjectList")
        
        if udt_data.get('description'):
            comment = ET.SubElement(obj_list, "MultilingualText")
            comment.set("ID", "1")
            comment.set("CompositionName", "Comment")
            
            comment_obj_list = ET.SubElement(comment, "ObjectList")
            
            # Add for multiple languages
            for culture in ['en-US', 'de-DE', 'zh-CN', 'hu-HU']:
                item = ET.SubElement(comment_obj_list, "MultilingualTextItem")
                item.set("ID", hex(2 + ['en-US', 'de-DE', 'zh-CN', 'hu-HU'].index(culture))[2:].upper())
                item.set("CompositionName", "Items")
                
                item_attr_list = ET.SubElement(item, "AttributeList")
                culture_elem = ET.SubElement(item_attr_list, "Culture")
                culture_elem.text = culture
                text_elem = ET.SubElement(item_attr_list, "Text")
                text_elem.text = udt_data['description']
        
        # Add Title (required for some imports)
        title = ET.SubElement(obj_list, "MultilingualText")
        # Generate unique ID for Title (avoid conflict with Comment ID 1 and its children)
        title.set("ID", "10") 
        title.set("CompositionName", "Title")
        title_obj_list = ET.SubElement(title, "ObjectList")
        title_item = ET.SubElement(title_obj_list, "MultilingualTextItem")
        title_item.set("ID", "11")
        title_item.set("CompositionName", "Items")
        title_attr = ET.SubElement(title_item, "AttributeList")
        ET.SubElement(title_attr, "Culture").text = "en-US"
        ET.SubElement(title_attr, "Text")
        
        return root

        
        return root
    
    def _add_member_xml(self, parent_elem, member: Dict):
        """Add member element to XML"""
        member_elem = ET.SubElement(parent_elem, "Member")
        member_elem.set("Name", member['name'])
        
        # Handle nested structures
        if member.get('nested_members'):
            member_elem.set("Datatype", "Struct")
            
            # Add nested members
            for nested in member['nested_members']:
                self._add_member_xml(member_elem, nested)
        else:
            # Set datatype
            datatype = member['datatype']
            member_elem.set("Datatype", datatype)
        
        # Add array bounds if present
        if member.get('array_bounds'):
            array_elem = ET.SubElement(member_elem, "ArrayBounds")
            # Parse bounds like [0..9] or [1..10]
            bounds_match = re.match(r'\[(\d+)\.\.(\d+)\]', member['array_bounds'])
            if bounds_match:
                dimension = ET.SubElement(array_elem, "Dimension")
                dimension.set("Lower", bounds_match.group(1))
                dimension.set("Upper", bounds_match.group(2))
        
        # Add initial value if present
        if member.get('initial_value'):
            start_value = ET.SubElement(member_elem, "StartValue")
            start_value.text = member['initial_value']
        
        # Add comment if present
        if member.get('comment'):
            comment_elem = ET.SubElement(member_elem, "Comment")
            comment_elem.text = member['comment']
    
    def _write_formatted_xml(self, root, output_path: str):
        """Write XML with proper formatting"""
        from xml.dom import minidom
        
        # Convert to string and format
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        
        # Get pretty printed version
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding='utf-8')
        
        # Remove extra blank lines
        lines = pretty_xml.decode('utf-8').split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(non_empty_lines))