"""
XML Loader Module for MilkToastTaco

Provides safe, reusable functionality for loading and parsing .xml data files.
Handles invalid/malformed XML gracefully with comprehensive error reporting.
"""

import os
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Any, List
from pathlib import Path


class XMLLoadError(Exception):
    """Custom exception for XML loading errors."""
    pass


def load_xml_file(file_path: str, strict: bool = False) -> Optional[ET.Element]:
    """
    Load and parse an XML file safely.

    Args:
        file_path: Path to the .xml file to load.
        strict: If True, raise exception on malformed XML. If False, return None gracefully.

    Returns:
        ET.Element root element of the parsed XML tree, or None if loading failed.

    Raises:
        XMLLoadError: If strict=True and an error occurs during loading/parsing.
    """
    try:
        # Normalize path
        normalized_path = os.path.normpath(file_path)

        # Check if file exists
        if not os.path.isfile(normalized_path):
            error_msg = f"File not found: {normalized_path}"
            if strict:
                raise XMLLoadError(error_msg)
            else:
                _log_warning(error_msg)
                return None

        # Check if file is readable
        if not os.access(normalized_path, os.R_OK):
            error_msg = f"File not readable: {normalized_path}"
            if strict:
                raise XMLLoadError(error_msg)
            else:
                _log_warning(error_msg)
                return None

        # Parse the XML file
        tree = ET.parse(normalized_path)
        root = tree.getroot()
        return root

    except ET.ParseError as e:
        error_msg = f"XML parsing error in {file_path}: {str(e)}"
        if strict:
            raise XMLLoadError(error_msg) from e
        else:
            _log_warning(error_msg)
            return None
    except IOError as e:
        error_msg = f"IO error reading {file_path}: {str(e)}"
        if strict:
            raise XMLLoadError(error_msg) from e
        else:
            _log_warning(error_msg)
            return None
    except Exception as e:
        error_msg = f"Unexpected error loading {file_path}: {str(e)}"
        if strict:
            raise XMLLoadError(error_msg) from e
        else:
            _log_warning(error_msg)
            return None


def load_xml_string(xml_content: str, strict: bool = False) -> Optional[ET.Element]:
    """
    Parse XML content from a string.

    Args:
        xml_content: XML content as a string.
        strict: If True, raise exception on malformed XML. If False, return None gracefully.

    Returns:
        ET.Element root element of the parsed XML tree, or None if parsing failed.

    Raises:
        XMLLoadError: If strict=True and parsing fails.
    """
    try:
        root = ET.fromstring(xml_content)
        return root
    except ET.ParseError as e:
        error_msg = f"XML parsing error: {str(e)}"
        if strict:
            raise XMLLoadError(error_msg) from e
        else:
            _log_warning(error_msg)
            return None
    except Exception as e:
        error_msg = f"Unexpected error parsing XML string: {str(e)}"
        if strict:
            raise XMLLoadError(error_msg) from e
        else:
            _log_warning(error_msg)
            return None


def get_element_text(element: ET.Element, tag: str, default: str = "") -> str:
    """
    Safely get text content from a child element.

    Args:
        element: Parent element to search within.
        tag: Tag name of the child element.
        default: Default value if element/text not found.

    Returns:
        Text content of the element, or default if not found.
    """
    try:
        child = element.find(tag)
        if child is not None and child.text is not None:
            return child.text.strip()
        return default
    except Exception as e:
        _log_warning(f"Error getting element text for tag '{tag}': {str(e)}")
        return default


def get_element_attribute(element: ET.Element, attr: str, default: str = "") -> str:
    """
    Safely get an attribute value from an element.

    Args:
        element: Element to get the attribute from.
        attr: Attribute name.
        default: Default value if attribute not found.

    Returns:
        Attribute value, or default if not found.
    """
    try:
        return element.get(attr, default)
    except Exception as e:
        _log_warning(f"Error getting attribute '{attr}': {str(e)}")
        return default


def get_child_elements(element: ET.Element, tag: Optional[str] = None) -> List[ET.Element]:
    """
    Get all child elements, optionally filtered by tag.

    Args:
        element: Parent element.
        tag: Optional tag name to filter by. If None, returns all children.

    Returns:
        List of matching child elements.
    """
    try:
        if tag is None:
            return list(element)
        else:
            return element.findall(tag)
    except Exception as e:
        _log_warning(f"Error getting child elements: {str(e)}")
        return []


def element_to_dict(element: ET.Element) -> Dict[str, Any]:
    """
    Convert an XML element and its structure to a Python dictionary.

    Args:
        element: XML element to convert.

    Returns:
        Dictionary representation of the element.
    """
    result = {}

    # Add attributes
    if element.attrib:
        result['@attributes'] = dict(element.attrib)

    # Add text content if present
    if element.text and element.text.strip():
        result['@text'] = element.text.strip()

    # Add child elements
    children = {}
    for child in element:
        child_dict = element_to_dict(child)
        if child.tag in children:
            # Multiple children with same tag - convert to list
            if not isinstance(children[child.tag], list):
                children[child.tag] = [children[child.tag]]
            children[child.tag].append(child_dict)
        else:
            children[child.tag] = child_dict

    if children:
        result['children'] = children

    return result if result else {'@text': ''}


def validate_xml_structure(
    element: ET.Element,
    required_children: Optional[List[str]] = None,
    required_attributes: Optional[List[str]] = None
) -> tuple[bool, str]:
    """
    Validate that an XML element has required children and/or attributes.

    Args:
        element: Element to validate.
        required_children: List of required child tag names.
        required_attributes: List of required attribute names.

    Returns:
        Tuple of (is_valid: bool, error_message: str).
    """
    # Check required children
    if required_children:
        for child_tag in required_children:
            if element.find(child_tag) is None:
                return False, f"Missing required child element: {child_tag}"

    # Check required attributes
    if required_attributes:
        for attr in required_attributes:
            if attr not in element.attrib:
                return False, f"Missing required attribute: {attr}"

    return True, ""


def load_xml_files_from_directory(
    directory: str,
    pattern: str = "*.xml",
    strict: bool = False
) -> Dict[str, ET.Element]:
    """
    Load all XML files from a directory matching a pattern.

    Args:
        directory: Directory path to scan.
        pattern: Glob pattern for files to load (default: *.xml).
        strict: If True, raise exception if any file fails to load.

    Returns:
        Dictionary mapping file names to loaded XML elements.

    Raises:
        XMLLoadError: If strict=True and any file fails to load.
    """
    results = {}

    try:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            error_msg = f"Directory not found: {directory}"
            if strict:
                raise XMLLoadError(error_msg)
            else:
                _log_warning(error_msg)
                return results

        # Find all matching files
        for xml_file in sorted(dir_path.glob(pattern)):
            try:
                root = load_xml_file(str(xml_file), strict=strict)
                if root is not None:
                    results[xml_file.name] = root
            except XMLLoadError as e:
                if strict:
                    raise
                else:
                    _log_warning(f"Failed to load {xml_file.name}: {str(e)}")

        return results

    except XMLLoadError:
        raise
    except Exception as e:
        error_msg = f"Error loading XML files from {directory}: {str(e)}"
        if strict:
            raise XMLLoadError(error_msg) from e
        else:
            _log_warning(error_msg)
            return results


def _log_warning(message: str) -> None:
    """Log a warning message (can be extended to use a logger)."""
    # Try to use the orchestrator's warning function if available
    try:
        from core.systems.orchestrator import warning as orch_warning
        orch_warning(message)
    except (ImportError, ModuleNotFoundError):
        # Fallback to print if orchestrator not available
        print(f"WARNING: {message}")
