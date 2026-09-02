"""
Unit tests for the xml_loader module.

Tests cover:
- Safe file loading
- XML parsing with error handling
- Element access and data extraction
- Structure validation
- Batch file loading
"""

import os
import tempfile
import unittest
from pathlib import Path

# Import the xml_loader module
from core.xml_loader import (
    load_xml_file,
    load_xml_string,
    get_element_text,
    get_element_attribute,
    get_child_elements,
    element_to_dict,
    validate_xml_structure,
    load_xml_files_from_directory,
    XMLLoadError,
)


class TestLoadXMLFile(unittest.TestCase):
    """Tests for load_xml_file function."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = self.test_dir.name

    def tearDown(self):
        """Clean up temporary directory."""
        self.test_dir.cleanup()

    def test_load_valid_xml_file(self):
        """Test loading a valid XML file."""
        xml_content = """<?xml version="1.0"?>
<root>
    <child>Test Content</child>
</root>"""
        file_path = os.path.join(self.test_path, "test.xml")
        with open(file_path, "w") as f:
            f.write(xml_content)

        root = load_xml_file(file_path)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "root")
        self.assertEqual(len(root), 1)

    def test_load_nonexistent_file_graceful(self):
        """Test loading a non-existent file with graceful error handling."""
        root = load_xml_file("/nonexistent/path/file.xml", strict=False)
        self.assertIsNone(root)

    def test_load_nonexistent_file_strict(self):
        """Test loading a non-existent file in strict mode."""
        with self.assertRaises(XMLLoadError):
            load_xml_file("/nonexistent/path/file.xml", strict=True)

    def test_load_malformed_xml_graceful(self):
        """Test loading malformed XML with graceful error handling."""
        malformed_xml = """<?xml version="1.0"?>
<root>
    <child>Unclosed tag
</root>"""
        file_path = os.path.join(self.test_path, "malformed.xml")
        with open(file_path, "w") as f:
            f.write(malformed_xml)

        root = load_xml_file(file_path, strict=False)
        self.assertIsNone(root)

    def test_load_malformed_xml_strict(self):
        """Test loading malformed XML in strict mode."""
        malformed_xml = """<?xml version="1.0"?>
<root>
    <child>Unclosed tag
</root>"""
        file_path = os.path.join(self.test_path, "malformed.xml")
        with open(file_path, "w") as f:
            f.write(malformed_xml)

        with self.assertRaises(XMLLoadError):
            load_xml_file(file_path, strict=True)


class TestLoadXMLString(unittest.TestCase):
    """Tests for load_xml_string function."""

    def test_parse_valid_xml_string(self):
        """Test parsing valid XML from a string."""
        xml_content = """<?xml version="1.0"?>
<root attr="value">
    <child>Content</child>
</root>"""
        root = load_xml_string(xml_content)
        self.assertIsNotNone(root)
        self.assertEqual(root.tag, "root")
        self.assertEqual(root.get("attr"), "value")

    def test_parse_malformed_xml_string_graceful(self):
        """Test parsing malformed XML from a string gracefully."""
        xml_content = "<root><unclosed>"
        root = load_xml_string(xml_content, strict=False)
        self.assertIsNone(root)

    def test_parse_malformed_xml_string_strict(self):
        """Test parsing malformed XML from a string in strict mode."""
        xml_content = "<root><unclosed>"
        with self.assertRaises(XMLLoadError):
            load_xml_string(xml_content, strict=True)


class TestElementAccess(unittest.TestCase):
    """Tests for element access functions."""

    def setUp(self):
        """Create a sample XML element for testing."""
        xml_content = """<?xml version="1.0"?>
<root id="123" name="test">
    <title>Test Title</title>
    <description>A test description</description>
    <item priority="1">First Item</item>
    <item priority="2">Second Item</item>
</root>"""
        self.root = load_xml_string(xml_content)

    def test_get_element_text(self):
        """Test getting text from child element."""
        title = get_element_text(self.root, "title")
        self.assertEqual(title, "Test Title")

    def test_get_element_text_with_whitespace(self):
        """Test getting text with surrounding whitespace."""
        xml_content = "<root><value>   spaced text   </value></root>"
        root = load_xml_string(xml_content)
        value = get_element_text(root, "value")
        self.assertEqual(value, "spaced text")

    def test_get_element_text_nonexistent(self):
        """Test getting text from non-existent element."""
        value = get_element_text(self.root, "nonexistent")
        self.assertEqual(value, "")

    def test_get_element_text_default(self):
        """Test getting text with custom default."""
        value = get_element_text(self.root, "nonexistent", default="default_value")
        self.assertEqual(value, "default_value")

    def test_get_element_attribute(self):
        """Test getting attribute value."""
        attr_value = get_element_attribute(self.root, "id")
        self.assertEqual(attr_value, "123")

    def test_get_element_attribute_nonexistent(self):
        """Test getting non-existent attribute."""
        attr_value = get_element_attribute(self.root, "nonexistent")
        self.assertEqual(attr_value, "")

    def test_get_element_attribute_default(self):
        """Test getting attribute with custom default."""
        attr_value = get_element_attribute(self.root, "nonexistent", default="default")
        self.assertEqual(attr_value, "default")

    def test_get_child_elements_all(self):
        """Test getting all child elements."""
        children = get_child_elements(self.root)
        self.assertEqual(len(children), 4)

    def test_get_child_elements_filtered(self):
        """Test getting child elements filtered by tag."""
        items = get_child_elements(self.root, "item")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].text, "First Item")
        self.assertEqual(items[1].text, "Second Item")


class TestElementToDict(unittest.TestCase):
    """Tests for element_to_dict conversion."""

    def test_simple_element_to_dict(self):
        """Test converting simple element to dict."""
        xml_content = "<root><name>Test</name></root>"
        root = load_xml_string(xml_content)
        result = element_to_dict(root)
        self.assertIn("children", result)
        self.assertIn("name", result["children"])

    def test_element_with_attributes_to_dict(self):
        """Test converting element with attributes to dict."""
        xml_content = '<root id="123" type="test"><value>Data</value></root>'
        root = load_xml_string(xml_content)
        result = element_to_dict(root)
        self.assertIn("@attributes", result)
        self.assertEqual(result["@attributes"]["id"], "123")

    def test_element_with_text_to_dict(self):
        """Test converting element with text to dict."""
        xml_content = "<root>Direct text content</root>"
        root = load_xml_string(xml_content)
        result = element_to_dict(root)
        self.assertIn("@text", result)
        self.assertEqual(result["@text"], "Direct text content")

    def test_nested_elements_to_dict(self):
        """Test converting nested elements to dict."""
        xml_content = """<root>
    <parent>
        <child>Value</child>
    </parent>
</root>"""
        root = load_xml_string(xml_content)
        result = element_to_dict(root)
        self.assertIn("children", result)
        self.assertIn("parent", result["children"])


class TestValidateXMLStructure(unittest.TestCase):
    """Tests for validate_xml_structure function."""

    def setUp(self):
        """Create a sample XML element for testing."""
        xml_content = """<?xml version="1.0"?>
<root id="123" name="test">
    <required_child>Value</required_child>
    <optional_child>Value</optional_child>
</root>"""
        self.root = load_xml_string(xml_content)

    def test_validate_required_children_present(self):
        """Test validation when all required children are present."""
        is_valid, msg = validate_xml_structure(self.root, required_children=["required_child"])
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_validate_required_children_missing(self):
        """Test validation when required child is missing."""
        is_valid, msg = validate_xml_structure(self.root, required_children=["missing_child"])
        self.assertFalse(is_valid)
        self.assertIn("missing_child", msg)

    def test_validate_required_attributes_present(self):
        """Test validation when all required attributes are present."""
        is_valid, msg = validate_xml_structure(self.root, required_attributes=["id", "name"])
        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_validate_required_attributes_missing(self):
        """Test validation when required attribute is missing."""
        is_valid, msg = validate_xml_structure(self.root, required_attributes=["missing_attr"])
        self.assertFalse(is_valid)
        self.assertIn("missing_attr", msg)

    def test_validate_combined_requirements(self):
        """Test validation with both children and attribute requirements."""
        is_valid, msg = validate_xml_structure(
            self.root,
            required_children=["required_child"],
            required_attributes=["id"]
        )
        self.assertTrue(is_valid)


class TestLoadXMLFilesFromDirectory(unittest.TestCase):
    """Tests for load_xml_files_from_directory function."""

    def setUp(self):
        """Create a temporary directory with test XML files."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = self.test_dir.name

        # Create test XML files
        xml_files = {
            "test1.xml": "<root><id>1</id></root>",
            "test2.xml": "<root><id>2</id></root>",
            "test3.xml": "<root><id>3</id></root>",
            "notxml.txt": "This is not XML",
        }

        for filename, content in xml_files.items():
            path = os.path.join(self.test_path, filename)
            with open(path, "w") as f:
                f.write(content)

    def tearDown(self):
        """Clean up temporary directory."""
        self.test_dir.cleanup()

    def test_load_xml_files_from_directory(self):
        """Test loading all XML files from a directory."""
        results = load_xml_files_from_directory(self.test_path)
        self.assertEqual(len(results), 3)
        self.assertIn("test1.xml", results)
        self.assertIn("test2.xml", results)
        self.assertIn("test3.xml", results)

    def test_load_xml_files_with_pattern(self):
        """Test loading XML files with custom pattern."""
        # Create additional file
        custom_file = os.path.join(self.test_path, "custom_file.data.xml")
        with open(custom_file, "w") as f:
            f.write("<root><data>custom</data></root>")

        results = load_xml_files_from_directory(self.test_path, pattern="*.data.xml")
        self.assertEqual(len(results), 1)
        self.assertIn("custom_file.data.xml", results)

    def test_load_xml_files_nonexistent_directory_graceful(self):
        """Test loading from non-existent directory gracefully."""
        results = load_xml_files_from_directory("/nonexistent/path", strict=False)
        self.assertEqual(len(results), 0)

    def test_load_xml_files_nonexistent_directory_strict(self):
        """Test loading from non-existent directory in strict mode."""
        with self.assertRaises(XMLLoadError):
            load_xml_files_from_directory("/nonexistent/path", strict=True)


class TestIntegration(unittest.TestCase):
    """Integration tests combining multiple functions."""

    def setUp(self):
        """Create a temporary directory with a complex XML file."""
        self.test_dir = tempfile.TemporaryDirectory()
        self.test_path = self.test_dir.name

        xml_content = """<?xml version="1.0"?>
<bank id="bank1" name="First Bank">
    <account id="acc001" type="checking">
        <owner>John Doe</owner>
        <balance>1000.00</balance>
        <transaction>
            <amount>100.00</amount>
            <date>2024-01-01</date>
        </transaction>
    </account>
    <account id="acc002" type="savings">
        <owner>Jane Smith</owner>
        <balance>5000.00</balance>
        <transaction>
            <amount>500.00</amount>
            <date>2024-01-02</date>
        </transaction>
    </account>
</bank>"""

        self.file_path = os.path.join(self.test_path, "bank.xml")
        with open(self.file_path, "w") as f:
            f.write(xml_content)

        self.root = load_xml_file(self.file_path)

    def tearDown(self):
        """Clean up temporary directory."""
        self.test_dir.cleanup()

    def test_integration_bank_data_extraction(self):
        """Test extracting data from a complex bank XML structure."""
        # Verify root
        self.assertEqual(self.root.tag, "bank")
        self.assertEqual(get_element_attribute(self.root, "id"), "bank1")

        # Get accounts
        accounts = get_child_elements(self.root, "account")
        self.assertEqual(len(accounts), 2)

        # Get first account details
        first_account = accounts[0]
        self.assertEqual(get_element_attribute(first_account, "type"), "checking")
        self.assertEqual(get_element_text(first_account, "owner"), "John Doe")
        self.assertEqual(get_element_text(first_account, "balance"), "1000.00")

    def test_integration_validation_and_extraction(self):
        """Test validation and extraction together."""
        # Validate structure
        is_valid, msg = validate_xml_structure(
            self.root,
            required_children=["account"],
            required_attributes=["id"]
        )
        self.assertTrue(is_valid)

        # Extract and convert to dict
        data_dict = element_to_dict(self.root)
        self.assertIn("@attributes", data_dict)
        self.assertIn("children", data_dict)


if __name__ == "__main__":
    unittest.main()
