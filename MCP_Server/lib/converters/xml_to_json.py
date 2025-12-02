import xml.etree.ElementTree as ET
import re
import os
import json
import logging

logger = logging.getLogger(__name__)

def process_member_recursively(member, level=0):
    """Recursively process member elements, handling nested structs"""
    var_name = member.get("Name")
    var_type = member.get("Datatype")
    
    if var_name is None or var_type is None:
        return None
    
    # Create the member object
    member_obj = {
        "name": var_name,
        "datatype": var_type,
        "level": level
    }
    
    # If this is a struct, recursively process its nested members
    if var_type == "Struct":
        nested_members = []
        # Find all direct child members of this struct
        for child in member:
            if child.tag.endswith("}Member") or child.tag == "Member":
                nested_member = process_member_recursively(child, level + 1)
                if nested_member:
                    nested_members.append(nested_member)
        
        if nested_members:
            member_obj["members"] = nested_members
    
    return member_obj

def xml_to_json(xml_file, output_file=None):
    # Parse the XML file
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        return None
    
    # Extract document info and engineering version
    engineering_version = root.find("Engineering").get("version") if root.find("Engineering") is not None else ""
    
    # Get block information - support FB, OB, FC, and GlobalDB
    block = root.find(".//SW.Blocks.FB")
    block_type = "FB"
    if block is None:
        block = root.find(".//SW.Blocks.OB")
        block_type = "OB"
    if block is None:
        block = root.find(".//SW.Blocks.FC")
        block_type = "FC"
    if block is None:
        block = root.find(".//SW.Blocks.GlobalDB")
        block_type = "GlobalDB"
    if block is None:
        logger.error("No supported block type (FB/OB/FC/GlobalDB) found in the XML file")
        return None
    
    attr_list = block.find("AttributeList")
    if attr_list is None:
        logger.error(f"AttributeList not found in the {block_type} block")
        return None
    
    # Extract basic block information
    name = attr_list.find("Name").text if attr_list.find("Name") is not None else "Unknown"
    number = attr_list.find("Number").text if attr_list.find("Number") is not None else "0"
    programming_language = attr_list.find("ProgrammingLanguage").text if attr_list.find("ProgrammingLanguage") is not None else "Unknown"
    memory_layout = attr_list.find("MemoryLayout").text if attr_list.find("MemoryLayout") is not None else "Unknown"
    memory_reserve = attr_list.find("MemoryReserve").text if attr_list.find("MemoryReserve") is not None else "0"
    set_eno = attr_list.find("SetENOAutomatically").text if attr_list.find("SetENOAutomatically") is not None else "false"
    
    # Extract interface sections with original xmlns
    interface_element = attr_list.find("Interface")
    interface_text = ""
    sections_xmlns = ""
    
    if interface_element is not None:
        try:
            # Store the complete Interface XML
            interface_text = ET.tostring(interface_element, encoding='unicode')
            
            # Extract the Interface namespace using the correct pattern
            interface_xmlns_match = re.search(r'xmlns:(\w+)="([^"]+)"', interface_text)
            if interface_xmlns_match:
                namespace_prefix = interface_xmlns_match.group(1)
                sections_xmlns = interface_xmlns_match.group(2)
                logger.info(f"Found Interface xmlns with prefix {namespace_prefix}: {sections_xmlns}")
            else:
                # Hardcode as fallback since we know the value
                sections_xmlns = "http://www.siemens.com/automation/Openness/SW/Interface/v5"
                logger.info(f"Using hardcoded Interface xmlns: {sections_xmlns}")
        except Exception as e:
            logger.warning(f"Warning: Could not extract interface XML: {e}")
    
    # Find the Sections element, possibly with namespace
    sections = None
    if interface_element is not None:
        # Try to find Sections with common Siemens namespace
        sections = interface_element.find(".//{http://www.siemens.com/automation/Openness/SW/Interface/v5}Sections")
        if sections is None:
            # Try to find without specific namespace
            for elem in interface_element.findall(".//*"):
                if elem.tag.endswith("}Sections") or elem.tag == "Sections":
                    sections = elem
                    break
    
    # Create JSON structure
    json_data = {
        "metadata": {
            "blockName": name,
            "blockNumber": number,
            "programmingLanguage": programming_language,
            "memoryLayout": memory_layout,
            "memoryReserve": memory_reserve,
            "enoSetting": set_eno,
            "engineeringVersion": engineering_version,
            "description": f"TIA Portal {block_type} block converted to JSON format",
            "xmlNamespaceInfo": {
                "interface": {
                    "namespace": sections_xmlns,
                    "description": "XML namespace for the Interface/Sections elements"
                },
                "networkSource": {
                    "namespace": "",  # Will be updated later
                    "description": "XML namespace for the NetworkSource/StructuredText elements"
                }
            }
        },
        "sections": {
            "input_section": [],
            "output_section": [],
            "in_out_section": [],
            "static_section": [],
            "temp_section": [],
            "constant_section": []
        },
        "code": []
    }
    
    # Process each section - IMPROVED to prevent duplicates
    section_mapping = {
        "Input": "input_section",
        "Output": "output_section",
        "InOut": "in_out_section",
        "Static": "static_section",
        "Temp": "temp_section",
        "Constant": "constant_section"
    }
    
    if sections is not None:
        # IMPROVED: Direct iteration over immediate children to avoid duplicates
        section_elements = [child for child in sections if child.tag.endswith("}Section") or child.tag == "Section"]
        
        for section in section_elements:
            section_name = section.get("Name")
            if section_name is None:
                continue
                
            json_section_name = section_mapping.get(section_name, section_name.lower())
            
            json_data["sections"][json_section_name] = []
            
            # Process members in this section - IMPROVED to prevent duplicates
            # Direct iteration over immediate children only
            members = [child for child in section if child.tag.endswith("}Member") or child.tag == "Member"]
                
            if members:
                for member in members:
                    member_obj = process_member_recursively(member, 0)
                    if member_obj:
                        json_data["sections"][json_section_name].append(member_obj)
    
    # Extract code
    compile_unit = block.find(".//SW.Blocks.CompileUnit")
    network_source = compile_unit.find("NetworkSource") if compile_unit is not None else None
    
    # Preserve original NetworkSource XML
    network_source_text = ""
    network_source_xmlns = ""
    
    if network_source is not None:
        try:
            # Store the complete NetworkSource XML
            network_source_text = ET.tostring(network_source, encoding='unicode')
            
            # Extract xmlns attribute if present - more robust pattern
            network_source_xmlns_match = re.search(r'<StructuredText\s+xmlns=[\'"]([^\'"]+)[\'"]', network_source_text)
            if network_source_xmlns_match:
                network_source_xmlns = network_source_xmlns_match.group(1)
                logger.info(f"Found NetworkSource xmlns: {network_source_xmlns}")
            else:
                # Try alternate pattern for namespace
                network_source_xmlns_match = re.search(r'xmlns:ns\d+=[\'"]([^\'"]+)[\'"]', network_source_text)
                if network_source_xmlns_match:
                    network_source_xmlns = network_source_xmlns_match.group(1)
                    logger.info(f"Found NetworkSource xmlns (alternate): {network_source_xmlns}")
                else:
                    logger.warning("Warning: Could not find StructuredText xmlns in the NetworkSource")
        except Exception as e:
            logger.warning(f"Warning: Could not extract NetworkSource XML: {e}")
    else:
        logger.warning("Warning: NetworkSource element not found in the XML")
    
    # Add NetworkSource xmlns to metadata
    json_data["metadata"]["xmlNamespaceInfo"]["networkSource"]["namespace"] = network_source_xmlns
    
    # Enhanced code extraction logic
    code_lines = []
    
    if network_source is not None:
        try:
            # IMPROVED: Multiple approaches to find StructuredText
            structured_text = None
            
            # Approach 1: Try with known namespaces
            known_namespaces = [
                "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v3",
                "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v2",
                "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v1"
            ]
            
            for ns in known_namespaces:
                structured_text = network_source.find(f"{{{ns}}}StructuredText")
                if structured_text is not None:
                    logger.info(f"Found StructuredText with namespace: {ns}")
                    break
            
            # Approach 2: If not found, try without namespace specification
            if structured_text is None:
                for elem in network_source.iter():
                    if elem.tag.endswith("}StructuredText") or elem.tag == "StructuredText":
                        structured_text = elem
                        logger.info(f"Found StructuredText element: {elem.tag}")
                        break
            
            if structured_text is not None:
                # Direct method to extract text content
                current_line = ""
                tokens_buffer = []
                
                # Process all child elements
                for child in structured_text:
                    # Get tag name without namespace
                    tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    
                    if tag_name == "Token":
                        tokens_buffer.append(child.get("Text", ""))
                    elif tag_name == "Blank":
                        num = int(child.get("Num", "1"))
                        tokens_buffer.append(" " * num)
                    elif tag_name == "NewLine":
                        # Join all tokens and add to code lines
                        code_lines.append("".join(tokens_buffer))
                        tokens_buffer = []
                    elif tag_name == "Text":
                        # Handle Text elements (for REGION names, etc.)
                        if child.text:
                            tokens_buffer.append(child.text)
                    elif tag_name == "LineComment":
                        # Handle line comments
                        comment_text = ""
                        for text_elem in child.findall(".//Text"):
                            if text_elem.text:
                                comment_text += text_elem.text
                        if comment_text:
                            tokens_buffer.append("// " + comment_text)
                    elif tag_name == "Access":
                        # Handle different scope types with proper SCL formatting:
                        # - LocalVariable: prefix with # (e.g., #stSensor.bCarrierAtPreStop)
                        # - GlobalVariable/GlobalConstant: wrap in quotes (e.g., "DB_HMI_PH1", "gc_nMaxStationDrives")
                        # - LiteralConstant/TypedConstant: output value directly (e.g., FALSE, T#8s)
                        # - Call: handle function/block calls
                        scope = child.get("Scope", "")
                        
                        if scope == "LocalVariable":
                            # Look for Symbol/Component structure
                            symbol = None
                            for sub_elem in child:
                                if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                                    symbol = sub_elem
                                    break
                            
                            if symbol is not None:
                                # Process all symbol children in order
                                first_component = True
                                for elem in symbol:
                                    elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                                    if elem_tag == "Component":
                                        if first_component:
                                            process_component_with_array(elem, tokens_buffer, "#")
                                            first_component = False
                                        else:
                                            process_component_with_array(elem, tokens_buffer, "")
                                    elif elem_tag == "Token":
                                        tokens_buffer.append(elem.get("Text", ""))
                            else:
                                # Simple case - just a Component
                                for comp in child.findall(".//*"):
                                    if comp.tag.endswith("}Component") or comp.tag == "Component":
                                        tokens_buffer.append(f"#{comp.get('Name', '')}")
                                        break
                                        
                        elif scope == "GlobalVariable" or scope == "GlobalConstant":
                            # Look for Symbol or Component or Constant
                            symbol = None
                            constant = None
                            for sub_elem in child:
                                if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                                    symbol = sub_elem
                                    break
                                elif sub_elem.tag.endswith("}Constant") or sub_elem.tag == "Constant":
                                    constant = sub_elem
                                    break
                            
                            if symbol is not None:
                                # Process symbol components, first gets quotes
                                first_component = True
                                for elem in symbol:
                                    elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                                    if elem_tag == "Component":
                                        if first_component:
                                            process_component_with_array(elem, tokens_buffer, '"')
                                            tokens_buffer.append('"')
                                            first_component = False
                                        else:
                                            process_component_with_array(elem, tokens_buffer, "")
                                    elif elem_tag == "Token":
                                        tokens_buffer.append(elem.get("Text", ""))
                            elif constant is not None:
                                # Handle Constant element with Name attribute
                                const_name = constant.get("Name", "")
                                if const_name:
                                    tokens_buffer.append(f'"{const_name}"')
                            else:
                                # Simple case
                                for comp in child.findall(".//*"):
                                    if comp.tag.endswith("}Component") or comp.tag == "Component":
                                        tokens_buffer.append(f'"{comp.get("Name", "")}"')
                                        break
                                        
                        elif scope == "LiteralConstant":
                            # Find the ConstantValue element (with or without namespace)
                            const_value = None
                            # First try direct child
                            for sub_elem in child:
                                if sub_elem.tag.endswith("}ConstantValue") or sub_elem.tag == "ConstantValue":
                                    const_value = sub_elem
                                    break
                            # If not found, try all descendants
                            if const_value is None:
                                for sub_elem in child.findall(".//*"):
                                    if sub_elem.tag.endswith("}ConstantValue") or sub_elem.tag == "ConstantValue":
                                        const_value = sub_elem
                                        break
                            
                            if const_value is not None and const_value.text:
                                tokens_buffer.append(const_value.text)
                            else:
                                # Debug: print what we're looking for
                                logger.warning(f"Warning: ConstantValue not found for LiteralConstant, child elements: {[elem.tag for elem in child]}")
                                
                        elif scope == "TypedConstant":
                            # Look for ConstantValue element
                            found_value = False
                            # First try direct child
                            for constant in child:
                                if constant.tag.endswith("}ConstantValue") or constant.tag == "ConstantValue":
                                    tokens_buffer.append(constant.text or "")
                                    found_value = True
                                    break
                            # If not found, try all descendants
                            if not found_value:
                                for constant in child.findall(".//*"):
                                    if constant.tag.endswith("}ConstantValue") or constant.tag == "ConstantValue":
                                        tokens_buffer.append(constant.text or "")
                                        found_value = True
                                        break
                            if not found_value:
                                logger.warning(f"Warning: ConstantValue not found for TypedConstant, child elements: {[elem.tag for elem in child]}")
                                    
                        elif scope == "Call":
                            # Handle function/block calls - process all child elements
                            call_tokens = []
                            process_call_element(child, call_tokens)
                            tokens_buffer.extend(call_tokens)
                
                # Add any remaining tokens as a line
                if tokens_buffer:
                    code_lines.append("".join(tokens_buffer))
                
                # If still no code extracted, try an alternative approach
                if not code_lines:
                    # Alternative: recursively extract all text content
                    all_text = []
                    
                    def extract_text(element):
                        if element.text and element.text.strip():
                            all_text.append(element.text.strip())
                        for child in element:
                            extract_text(child)
                        if element.tail and element.tail.strip():
                            all_text.append(element.tail.strip())
                    
                    extract_text(structured_text)
                    
                    # Join extracted text into lines
                    if all_text:
                        code_text = " ".join(all_text)
                        # Try to format it into reasonable code lines
                        code_lines = []
                        for statement in code_text.split(";"):
                            if statement.strip():
                                code_lines.append(statement.strip() + ";")
            else:
                logger.warning("Warning: StructuredText element not found in the NetworkSource")
                
                # Last resort: try to extract directly from NetworkSource
                if network_source.text and network_source.text.strip():
                    code_lines = [line.strip() for line in network_source.text.split("\n") if line.strip()]
        except Exception as e:
            logger.error(f"Error extracting code: {e}")
    
    # Add code lines to JSON
    json_data["code"] = code_lines
    
    # Process Interface if present
    if attr_list is not None:
        interface = attr_list.find("Interface")
        if interface is not None:
            # Process sections in the interface
            process_interface_sections(interface, json_data)
            
            # Get the XML content as string for preservation
            ET.register_namespace('', "http://www.siemens.com/automation/Openness/SW/Interface/v5")
            interface_text = ET.tostring(interface, encoding='unicode')
    
    # Convert JSON data to string
    json_content = json.dumps(json_data, indent=2)
    
    # Write to file if output_file is provided
    if output_file is None:
        output_file = os.path.splitext(xml_file)[0] + ".json"
        
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_content)
    logger.info(f"Converted to JSON: {output_file}")
    
    return json_content

def process_interface_sections(interface, json_data):
    """Process sections in the interface and update JSON data"""
    # Find the Sections element, possibly with namespace
    sections = None
    for child in interface:
        if child.tag.endswith("Sections"):
            sections = child
            break
    
    if sections is None:
        return
    
    # Section mapping between JSON and XML
    section_mapping = {
        "Input": "input_section",
        "Output": "output_section",
        "InOut": "in_out_section",
        "Static": "static_section",
        "Temp": "temp_section",
        "Constant": "constant_section"
    }
    
    # Process each section in the interface
    for section in sections:
        section_name = section.get("Name")
        if section_name is None:
            continue
        
        json_section_name = section_mapping.get(section_name, section_name.lower() + "_section")
        
        # Initialize the section in JSON if it doesn't exist
        if json_section_name not in json_data["sections"]:
            json_data["sections"][json_section_name] = []
        
        # Find member elements in this section
        members = []
        for child in section:
            if child.tag.endswith("Member"):
                members.append(child)
        
        # Process each member in this section
        for member in members:
            member_obj = process_member_recursively(member, 0)
            if member_obj:
                json_data["sections"][json_section_name].append(member_obj)

def patched_xml_to_json(xml_file, output_file=None):
    """Convert XML to JSON without preserving the original XML structure"""
    # Parse the XML file
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError as e:
        logger.error(f"XML parsing error: {e}")
        return None
    
    # Debug: Print root tag
    logger.debug(f"Root tag: {root.tag}")
    
    # Find the block in the document (FB, OB, FC, or GlobalDB)
    block = None
    block_type = "Unknown"
    for child in root.findall(".//*"):
        if child.tag.endswith(".FB"):
            block = child
            block_type = "FB"
            break
        elif child.tag.endswith(".OB"):
            block = child
            block_type = "OB"
            break
        elif child.tag.endswith(".FC"):
            block = child
            block_type = "FC"
            break
        elif child.tag.endswith(".GlobalDB"):
            block = child
            block_type = "GlobalDB"
            break
    
    
    # Initialize basic JSON structure
    json_data = {
        "metadata": {
            "blockName": "",
            "blockNumber": "",
            "programmingLanguage": "",
            "memoryLayout": "",
            "memoryReserve": "",
            "enoSetting": "",
            "engineeringVersion": "",
            "description": f"TIA Portal {block_type} block converted to JSON format",
            "xmlNamespaceInfo": {
                "interface": {
                    "namespace": "",
                    "description": "XML namespace for the Interface/Sections elements"
                },
                "networkSource": {
                    "namespace": "",
                    "description": "XML namespace for the NetworkSource/StructuredText elements"
                }
            }
        },
        "sections": {
            "input_section": [],
            "output_section": [],
            "in_out_section": [],
            "static_section": [],
            "temp_section": [],
            "constant_section": []
        },
        "code": []
    }
    
    if block is not None:
        # Get attribute list
        attr_list = block.find("AttributeList")
        if attr_list is not None:
            # Extract metadata
            for key in ["Name", "Number", "ProgrammingLanguage", "MemoryLayout", "MemoryReserve"]:
                element = attr_list.find(key)
                if element is not None and element.text:
                    json_key = key[0].lower() + key[1:]  # Convert to camelCase
                    json_data["metadata"][json_key] = element.text
            
            # Handle SetENOAutomatically separately
            eno = attr_list.find("SetENOAutomatically")
            if eno is not None:
                json_data["metadata"]["enoSetting"] = eno.text.lower()
        
        # Get engineering version
        engineering = root.find("Engineering")
        if engineering is not None and "version" in engineering.attrib:
            json_data["metadata"]["engineeringVersion"] = engineering.attrib["version"]
        
        # Find CompileUnit for code extraction
        compile_unit = block.find(".//SW.Blocks.CompileUnit")
        if compile_unit is not None:
            logger.info("Found CompileUnit")
        else:
            logger.warning("CompileUnit not found")
        
        # Extract code from NetworkSource
        network_source = find_network_source(compile_unit)
        
        if network_source is not None:
            # Process structure and extract code
            code_lines = extract_code_from_network_source(network_source)
            json_data["code"] = code_lines
            
            # Get the XML content as string for namespace extraction
            ET.register_namespace('', "http://www.siemens.com/automation/Openness/SW/NetworkSource/StructuredText/v3")
            
            # Extract namespace from the network source
            for child in network_source:
                if "StructuredText" in child.tag and "}" in child.tag:
                    ns = child.tag.split("}")[0].strip("{")
                    json_data["metadata"]["xmlNamespaceInfo"]["networkSource"]["namespace"] = ns
                    break
        
        # Process Interface if present
        if attr_list is not None:
            interface = attr_list.find("Interface")
            if interface is not None:
                # Process sections in the interface
                process_interface_sections(interface, json_data)
                
                # Register namespace for extraction
                ET.register_namespace('', "http://www.siemens.com/automation/Openness/SW/Interface/v5")
                
                # Extract namespace from the interface
                for child in interface:
                    if "Sections" in child.tag and "}" in child.tag:
                        ns = child.tag.split("}")[0].strip("{")
                        json_data["metadata"]["xmlNamespaceInfo"]["interface"]["namespace"] = ns
                        break
    
    # Convert JSON data to string
    json_content = json.dumps(json_data, indent=2)
    
    # Write to file if output_file is provided
    if output_file is None:
        output_file = os.path.splitext(xml_file)[0] + ".json"
        
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(json_content)
    logger.info(f"Converted to JSON: {output_file}")
    
    return json_content

def find_network_source(compile_unit):
    """Find the NetworkSource element in a CompileUnit"""
    if compile_unit is None:
        return None
        
    # Method 1: Direct lookup
    network_source = compile_unit.find("NetworkSource")
    if network_source is not None:
        return network_source
        
    # Method 2: Search at any level
    for elem in compile_unit.findall(".//*"):
        if elem.tag.endswith("NetworkSource"):
            return elem
            
    return None

def process_component_with_array(comp_elem, tokens_buffer, prefix="", suffix=""):
    """Process a Component element that might contain array indices"""
    comp_name = comp_elem.get("Name", "")
    tokens_buffer.append(prefix + comp_name + suffix)
    
    # Check if this component has array indices (child elements)
    for child in comp_elem:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        
        if tag_name == "Token":
            tokens_buffer.append(child.get("Text", ""))
        elif tag_name == "Access":
            # Handle access within array index
            scope = child.get("Scope", "")
            if scope == "LocalVariable":
                symbol = None
                for sub_elem in child:
                    if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                        symbol = sub_elem
                        break
                if symbol is not None:
                    # Process all symbol children in order with first_component logic
                    first_component = True
                    for elem in symbol:
                        elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem_tag == "Component":
                            if first_component:
                                process_component_with_array(elem, tokens_buffer, "#")
                                first_component = False
                            else:
                                process_component_with_array(elem, tokens_buffer, "")
                        elif elem_tag == "Token":
                            tokens_buffer.append(elem.get("Text", ""))
            elif scope == "GlobalVariable" or scope == "GlobalConstant":
                constant = None
                for sub_elem in child:
                    if sub_elem.tag.endswith("}Constant") or sub_elem.tag == "Constant":
                        constant = sub_elem
                        break
                if constant is not None:
                    const_name = constant.get("Name", "")
                    if const_name:
                        tokens_buffer.append(f'"{const_name}"')
            elif scope == "LiteralConstant":
                # Handle numeric literal constants (array indices)
                constant = None
                for sub_elem in child:
                    if sub_elem.tag.endswith("}Constant") or sub_elem.tag == "Constant":
                        constant = sub_elem
                        break
                if constant is not None:
                    # Look for ConstantValue element
                    for const_child in constant:
                        const_tag = const_child.tag.split("}")[-1] if "}" in const_child.tag else const_child.tag
                        if const_tag == "ConstantValue":
                            if const_child.text:
                                tokens_buffer.append(const_child.text)

def process_call_element(call_elem, tokens_buffer):
    """Process a Call element recursively to extract all tokens"""
    for child in call_elem:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        
        if tag_name == "CallInfo":
            # Get block type to handle FC vs FB calls
            block_type = child.get("BlockType", "")
            
            # Process CallInfo children
            for call_child in child:
                call_tag = call_child.tag.split("}")[-1] if "}" in call_child.tag else call_child.tag
                
                if call_tag == "Instance":
                    # Handle instance based on scope
                    scope = call_child.get("Scope", "")
                    if scope == "LocalVariable":
                        # Find Symbol element for proper processing
                        symbol = None
                        for sub_elem in call_child:
                            if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                                symbol = sub_elem
                                break
                        if symbol is not None:
                            # Process all symbol children in order with first_component logic
                            first_component = True
                            for elem in symbol:
                                elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                                if elem_tag == "Component":
                                    if first_component:
                                        process_component_with_array(elem, tokens_buffer, "#")
                                        first_component = False
                                    else:
                                        process_component_with_array(elem, tokens_buffer, "")
                                elif elem_tag == "Token":
                                    tokens_buffer.append(elem.get("Text", ""))
                        else:
                            # Fallback for simple case
                            for comp in call_child.findall(".//*"):
                                if comp.tag.endswith("}Component") or comp.tag == "Component":
                                    tokens_buffer.append(f"#{comp.get('Name', '')}")
                                    break
                    elif scope == "GlobalVariable":
                        # For FC calls, the function name is global
                        for comp in call_child.findall(".//*"):
                            if comp.tag.endswith("}Component") or comp.tag == "Component":
                                tokens_buffer.append(f'"{comp.get("Name", "")}"')
                                break
                elif call_tag == "Token":
                    tokens_buffer.append(call_child.get("Text", ""))
                elif call_tag == "Parameter":
                    # Recursively process parameter content
                    process_parameter_element(call_child, tokens_buffer)
        elif tag_name == "Token":
            tokens_buffer.append(child.get("Text", ""))
        elif tag_name == "Blank":
            num = int(child.get("Num", "1"))
            tokens_buffer.append(" " * num)
        elif tag_name == "NewLine":
            # Don't add newline in the middle of a call
            pass

def process_parameter_element(param_elem, tokens_buffer):
    """Process a Parameter element to extract its content"""
    # Parameter name is an attribute, not a token
    param_name = param_elem.get("Name", "")
    if param_name:
        tokens_buffer.append(param_name)
    
    # Process parameter content
    for child in param_elem:
        tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        
        if tag_name == "Token":
            tokens_buffer.append(child.get("Text", ""))
        elif tag_name == "Blank":
            num = int(child.get("Num", "1"))
            tokens_buffer.append(" " * num)
        elif tag_name == "Access":
            # Handle access within parameters
            scope = child.get("Scope", "")
            if scope == "LocalVariable":
                # Find Symbol element
                symbol = None
                for sub_elem in child:
                    if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                        symbol = sub_elem
                        break
                if symbol is not None:
                    # Process all symbol children in order
                    first_component = True
                    for elem in symbol:
                        elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem_tag == "Component":
                            if first_component:
                                process_component_with_array(elem, tokens_buffer, "#")
                                first_component = False
                            else:
                                process_component_with_array(elem, tokens_buffer, "")
                        elif elem_tag == "Token":
                            tokens_buffer.append(elem.get("Text", ""))
                else:
                    # Simple case - just a Component without Symbol
                    for comp in child.findall(".//*"):
                        if comp.tag.endswith("}Component") or comp.tag == "Component":
                            tokens_buffer.append(f"#{comp.get('Name', '')}")
                            break
            elif scope == "GlobalVariable" or scope == "GlobalConstant":
                # Find Symbol element
                symbol = None
                constant = None
                for sub_elem in child:
                    if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                        symbol = sub_elem
                        break
                    elif sub_elem.tag.endswith("}Constant") or sub_elem.tag == "Constant":
                        constant = sub_elem
                        break
                        
                if symbol is not None:
                    # Process symbol components, first gets quotes
                    first_component = True
                    for elem in symbol:
                        elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                        if elem_tag == "Component":
                            if first_component:
                                process_component_with_array(elem, tokens_buffer, '"')
                                tokens_buffer.append('"')
                                first_component = False
                            else:
                                process_component_with_array(elem, tokens_buffer, "")
                        elif elem_tag == "Token":
                            tokens_buffer.append(elem.get("Text", ""))
                elif constant is not None:
                    # Handle Constant element with Name attribute
                    const_name = constant.get("Name", "")
                    if const_name:
                        tokens_buffer.append(f'"{const_name}"')
            elif scope == "LiteralConstant":
                # Find the ConstantValue element
                const_value = None
                for sub_elem in child:
                    if sub_elem.tag.endswith("}ConstantValue") or sub_elem.tag == "ConstantValue":
                        const_value = sub_elem
                        break
                if const_value is None:
                    for sub_elem in child.findall(".//*"):
                        if sub_elem.tag.endswith("}ConstantValue") or sub_elem.tag == "ConstantValue":
                            const_value = sub_elem
                            break
                
                if const_value is not None and const_value.text:
                    tokens_buffer.append(const_value.text)
            elif scope == "TypedConstant":
                # Look for ConstantValue element
                for constant in child:
                    if constant.tag.endswith("}ConstantValue") or constant.tag == "ConstantValue":
                        tokens_buffer.append(constant.text or "")
                        break
                else:
                    for constant in child.findall(".//*"):
                        if constant.tag.endswith("}ConstantValue") or constant.tag == "ConstantValue":
                            tokens_buffer.append(constant.text or "")
                            break

def extract_code_from_network_source(network_source):
    """Extract code lines from a NetworkSource element"""
    code_lines = []
    
    if network_source is None:
        return code_lines
        
    try:
        # Process all children to identify the StructuredText element
        structured_text = None
        for child in network_source:
            if "StructuredText" in child.tag:
                structured_text = child
                logger.info(f"Found StructuredText element: {child.tag}")
                break
        
        if structured_text is not None:
            # Direct token extraction
            tokens_buffer = []
            
            for child in structured_text:
                tag_name = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                
                if tag_name == "Token":
                    tokens_buffer.append(child.get("Text", ""))
                elif tag_name == "Blank":
                    num = int(child.get("Num", "1"))
                    tokens_buffer.append(" " * num)
                elif tag_name == "NewLine":
                    code_lines.append("".join(tokens_buffer))
                    tokens_buffer = []
                elif tag_name == "Text":
                    # Handle Text elements (for REGION names, etc.)
                    if child.text:
                        tokens_buffer.append(child.text)
                elif tag_name == "LineComment":
                    # Handle line comments
                    comment_text = ""
                    for text_elem in child.findall(".//Text"):
                        if text_elem.text:
                            comment_text += text_elem.text
                    if comment_text:
                        tokens_buffer.append("// " + comment_text)
                elif tag_name == "Access":
                    # Handle different scope types with proper SCL formatting:
                    # - LocalVariable: prefix with # (e.g., #stSensor.bCarrierAtPreStop)
                    # - GlobalVariable/GlobalConstant: wrap in quotes (e.g., "DB_HMI_PH1", "gc_nMaxStationDrives")
                    # - LiteralConstant/TypedConstant: output value directly (e.g., FALSE, T#8s)
                    # - Call: handle function/block calls
                    scope = child.get("Scope", "")
                    
                    if scope == "LocalVariable":
                        # Look for Symbol/Component structure
                        symbol = None
                        for sub_elem in child:
                            if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                                symbol = sub_elem
                                break
                        
                        if symbol is not None:
                            # Process all symbol children in order with first_component logic
                            first_component = True
                            for elem in symbol:
                                elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                                if elem_tag == "Component":
                                    if first_component:
                                        process_component_with_array(elem, tokens_buffer, "#")
                                        first_component = False
                                    else:
                                        process_component_with_array(elem, tokens_buffer, "")
                                elif elem_tag == "Token":
                                    tokens_buffer.append(elem.get("Text", ""))
                        else:
                            # Simple case - just a Component
                            for comp in child.findall(".//*"):
                                if comp.tag.endswith("}Component") or comp.tag == "Component":
                                    tokens_buffer.append(f"#{comp.get('Name', '')}")
                                    break
                                    
                    elif scope == "GlobalVariable" or scope == "GlobalConstant":
                        # Look for Symbol or Component or Constant
                        symbol = None
                        constant = None
                        for sub_elem in child:
                            if sub_elem.tag.endswith("}Symbol") or sub_elem.tag == "Symbol":
                                symbol = sub_elem
                                break
                            elif sub_elem.tag.endswith("}Constant") or sub_elem.tag == "Constant":
                                constant = sub_elem
                                break
                        
                        if symbol is not None:
                            # Process symbol components, first gets quotes
                            first_component = True
                            for elem in symbol:
                                elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                                if elem_tag == "Component":
                                    if first_component:
                                        process_component_with_array(elem, tokens_buffer, '"')
                                        tokens_buffer.append('"')
                                        first_component = False
                                    else:
                                        process_component_with_array(elem, tokens_buffer, "")
                                elif elem_tag == "Token":
                                    tokens_buffer.append(elem.get("Text", ""))
                        elif constant is not None:
                            # Handle Constant element with Name attribute
                            const_name = constant.get("Name", "")
                            if const_name:
                                tokens_buffer.append(f'"{const_name}"')
                        else:
                            # Simple case
                            for comp in child.findall(".//*"):
                                if comp.tag.endswith("}Component") or comp.tag == "Component":
                                    tokens_buffer.append(f'"{comp.get("Name", "")}"')
                                    break
                                    
                    elif scope == "LiteralConstant":
                        # Look for ConstantValue element
                        for constant in child.findall(".//*"):
                            if constant.tag.endswith("}ConstantValue") or constant.tag == "ConstantValue":
                                tokens_buffer.append(constant.text or "")
                                break
                                
                    elif scope == "TypedConstant":
                        # Look for ConstantValue element
                        for constant in child.findall(".//*"):
                            if constant.tag.endswith("}ConstantValue") or constant.tag == "ConstantValue":
                                tokens_buffer.append(constant.text or "")
                                break
                                
                    elif scope == "Call":
                        # Handle function/block calls - process all child elements
                        call_tokens = []
                        process_call_element(child, call_tokens)
                        tokens_buffer.extend(call_tokens)
            
            # Add any remaining tokens
            if tokens_buffer:
                code_lines.append("".join(tokens_buffer))
            
            # Post-process to improve formatting of long function calls
            formatted_lines = []
            for line in code_lines:
                if len(line) > 120 and "(" in line and ":=" in line and "," in line:
                    # This looks like a long function call, try to format it better
                    formatted_lines.extend(format_long_function_call(line))
                else:
                    formatted_lines.append(line)
            code_lines = formatted_lines
    except Exception as e:
        logger.error(f"Error extracting code: {e}")
            
    return code_lines

def format_long_function_call(line):
    """Format a long function call by splitting parameters across multiple lines"""
    # Extract the indentation from the original line
    indent = len(line) - len(line.lstrip())
    base_indent = " " * indent
    param_indent = " " * (indent + 4)  # Add 4 more spaces for parameters
    
    # Find the opening parenthesis
    paren_pos = line.find("(")
    if paren_pos == -1:
        return [line]
    
    # Split into function name/opening and parameters
    function_part = line[:paren_pos + 1]  # Include the opening parenthesis
    params_part = line[paren_pos + 1:]  # Everything after opening parenthesis
    
    # Remove the closing parenthesis and semicolon from the end
    if params_part.endswith(");"):
        params_part = params_part[:-2]
        ending = ");"
    elif params_part.endswith(")"):
        params_part = params_part[:-1]
        ending = ")"
    else:
        ending = ""
    
    # Split parameters by comma, but be careful about nested structures
    params = []
    current_param = ""
    paren_depth = 0
    
    for char in params_part:
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif char == "," and paren_depth == 0:
            params.append(current_param.strip())
            current_param = ""
            continue
        current_param += char
    
    # Add the last parameter
    if current_param.strip():
        params.append(current_param.strip())
    
    # If we don't have enough parameters to make it worth splitting, return as is
    if len(params) <= 2:
        return [line]
    
    # Format the result
    result = [function_part]
    for i, param in enumerate(params):
        if i == len(params) - 1:  # Last parameter
            result.append(f"{param_indent}{param}{ending}")
        else:
            result.append(f"{param_indent}{param},")
    
    return result

def xml_to_structured_text(xml_file, output_file=None):
    """For backward compatibility"""
    logger.warning("This function is deprecated. Please use xml_to_json instead.")
    return xml_to_json(xml_file, output_file)

# Main execution block for when this script is run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        
        # Call the conversion function
        patched_xml_to_json(xml_file, output_file)
    else:
        print("Usage: python xml_to_json.py <xml_file> [output_json_file]") 