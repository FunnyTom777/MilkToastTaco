"""
XML Loader System - User Guide & API Reference

The xml_loader module provides a safe, reusable system for loading and parsing .xml 
data files throughout the MilkToastTaco project. It handles errors gracefully and 
provides utilities for extracting and validating data.
"""

# ============================================================================
# QUICK START
# ============================================================================

"""
Basic usage - load an XML file:

    from core.xml_loader import load_xml_file

    root = load_xml_file('data/config.xml')
    if root is not None:
        # Process the XML
        pass
"""

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

"""
load_xml_file(file_path: str, strict: bool = False) -> Optional[ET.Element]
    Load and parse an XML file from disk.
    
    Args:
        file_path: Path to the .xml file
        strict: If True, raise XMLLoadError on failure; if False, return None gracefully
    
    Returns:
        ET.Element root, or None if loading failed (graceful mode only)
    
    Examples:
        # Graceful loading (recommended for most cases)
        root = load_xml_file('config.xml')
        if root is not None:
            # Process data
            pass
        
        # Strict mode (fail fast for critical files)
        try:
            root = load_xml_file('critical.xml', strict=True)
        except XMLLoadError as e:
            print(f"Failed to load critical.xml: {e}")


load_xml_string(xml_content: str, strict: bool = False) -> Optional[ET.Element]
    Parse XML content from a string.
    
    Args:
        xml_content: XML as a string
        strict: If True, raise XMLLoadError on parsing failure
    
    Returns:
        ET.Element root, or None if parsing failed
    
    Examples:
        xml_str = '<root><name>Test</name></root>'
        root = load_xml_string(xml_str)


get_element_text(element: ET.Element, tag: str, default: str = "") -> str
    Safely get text content from a child element.
    
    Args:
        element: Parent element
        tag: Tag name of child element
        default: Value to return if element/text not found
    
    Returns:
        Text content (whitespace trimmed), or default
    
    Examples:
        title = get_element_text(root, 'title', default='Untitled')
        # Whitespace is automatically stripped


get_element_attribute(element: ET.Element, attr: str, default: str = "") -> str
    Safely get an attribute value from an element.
    
    Args:
        element: Element to read from
        attr: Attribute name
        default: Value if attribute not found
    
    Returns:
        Attribute value, or default
    
    Examples:
        bank_id = get_element_attribute(root, 'id', default='unknown')


get_child_elements(element: ET.Element, tag: Optional[str] = None) -> List[ET.Element]
    Get child elements, optionally filtered by tag name.
    
    Args:
        element: Parent element
        tag: Optional tag name to filter by
    
    Returns:
        List of matching child elements (empty list if none found)
    
    Examples:
        # Get all children
        all_children = get_child_elements(root)
        
        # Get children with specific tag
        accounts = get_child_elements(root, 'account')


validate_xml_structure(
    element: ET.Element,
    required_children: Optional[List[str]] = None,
    required_attributes: Optional[List[str]] = None
) -> tuple[bool, str]
    Validate that an element has required children/attributes.
    
    Args:
        element: Element to validate
        required_children: List of required child tag names
        required_attributes: List of required attribute names
    
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    
    Examples:
        is_valid, msg = validate_xml_structure(
            root,
            required_children=['name', 'value'],
            required_attributes=['id']
        )
        if not is_valid:
            print(f"Validation failed: {msg}")


element_to_dict(element: ET.Element) -> Dict[str, Any]
    Convert an XML element to a Python dictionary.
    
    Returns dict with:
        - '@attributes': dict of element attributes
        - '@text': element's text content
        - 'children': dict of child elements by tag
    
    Examples:
        root = load_xml_file('data.xml')
        data_dict = element_to_dict(root)
        bank_id = data_dict['@attributes']['id']


load_xml_files_from_directory(
    directory: str,
    pattern: str = "*.xml",
    strict: bool = False
) -> Dict[str, ET.Element]
    Load multiple XML files from a directory.
    
    Args:
        directory: Path to directory
        pattern: Glob pattern (default: *.xml)
        strict: Fail on first error if True
    
    Returns:
        Dict mapping filenames to parsed elements
    
    Examples:
        # Load all .xml files from a directory
        files = load_xml_files_from_directory('data/')
        for filename, root in files.items():
            print(f"Loaded {filename}")


# ============================================================================
# EXCEPTION HANDLING
# ============================================================================

"""
XMLLoadError: Custom exception raised when strict=True and loading/parsing fails.

Error types handled:
    - File not found
    - File not readable (permission issues)
    - XML parsing errors (malformed XML)
    - IO errors (disk read failures)
    - Unexpected exceptions

Example:
    try:
        root = load_xml_file('config.xml', strict=True)
    except XMLLoadError as e:
        # Handle critical error
        print(f"Critical error: {e}")
"""


# ============================================================================
# PRACTICAL EXAMPLES
# ============================================================================

"""
Example 1: Loading Bank Data

    from core.xml_loader import load_xml_file, get_element_text, get_child_elements

    root = load_xml_file('banks.xml')
    if root is not None:
        for account in get_child_elements(root, 'account'):
            owner = get_element_text(account, 'owner')
            balance = get_element_text(account, 'balance')
            print(f"{owner}: ${balance}")


Example 2: Validating Configuration

    from core.xml_loader import load_xml_file, validate_xml_structure
    
    root = load_xml_file('config.xml')
    if root is not None:
        is_valid, msg = validate_xml_structure(
            root,
            required_children=['database', 'server'],
            required_attributes=['version']
        )
        if is_valid:
            # Process configuration
            pass
        else:
            print(f"Invalid config: {msg}")


Example 3: Batch Loading

    from core.xml_loader import load_xml_files_from_directory, element_to_dict
    
    # Load all XML files from a directory
    data_files = load_xml_files_from_directory('game_data/')
    
    for filename, root in data_files.items():
        data = element_to_dict(root)
        # Process each file
        print(f"Processed {filename}")


Example 4: Accessing Nested Data

    from core.xml_loader import load_xml_file, get_child_elements, get_element_text
    
    root = load_xml_file('complex.xml')
    if root is not None:
        for section in get_child_elements(root, 'section'):
            section_name = get_element_text(section, 'name')
            for item in get_child_elements(section, 'item'):
                item_value = get_element_text(item, 'value')
                print(f"{section_name}: {item_value}")


# ============================================================================
# DESIGN PRINCIPLES
# ============================================================================

"""
The xml_loader module follows these principles:

1. SAFETY FIRST
   - Graceful error handling by default (strict=False)
   - No exceptions thrown unless explicitly requested
   - Whitespace automatically trimmed from text content

2. REUSABILITY
   - Utilities work with any XML structure
   - Modular functions for different tasks
   - Easy integration with existing systems

3. FLEXIBILITY
   - Support for both file and string loading
   - Graceful and strict modes for different scenarios
   - Batch loading capabilities

4. ROBUSTNESS
   - Comprehensive error handling
   - Validation utilities for structure checking
   - Fallback to orchestrator logging when available

5. SIMPLICITY
   - Clear, intuitive API
   - Type hints for IDE support
   - Minimal dependencies (Python stdlib only)


# ============================================================================
# INTEGRATION WITH MTT SYSTEMS
# ============================================================================

"""
The xml_loader can be used by any MTT system that needs to load data:

    from core.xml_loader import load_xml_file, get_element_text, get_child_elements
    
    # In a bank/economy system:
    banks_root = load_xml_file('config/banks.xml')
    if banks_root:
        for bank in get_child_elements(banks_root, 'bank'):
            bank_name = get_element_text(bank, 'name')
            # Initialize bank
    
    # In a game item system:
    items_root = load_xml_file('data/items.xml')
    if items_root:
        for item in get_child_elements(items_root, 'item'):
            item_id = get_element_text(item, 'id')
            item_type = get_element_text(item, 'type')
            # Create item instance
"""
