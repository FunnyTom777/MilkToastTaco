"""
Example usage of xml_loader in MilkToastTaco systems.

This file demonstrates how to integrate the xml_loader module into various
MTT systems to load and parse XML configuration and data files.
"""

from core.xml_loader import (
    load_xml_file,
    load_xml_string,
    get_element_text,
    get_element_attribute,
    get_child_elements,
    validate_xml_structure,
    element_to_dict,
    XMLLoadError,
)


def example_load_bank_configuration():
    """
    Example: Load bank configuration from XML file.
    
    Demonstrates:
    - Loading XML files
    - Extracting attributes and text
    - Iterating over child elements
    - Graceful error handling
    """
    print("Example 1: Loading Bank Configuration")
    print("-" * 50)

    # Load the banks.xml configuration file
    root = load_xml_file("config/banks.xml")

    if root is None:
        print("Warning: Could not load banks.xml")
        return

    # Process each bank
    for bank in get_child_elements(root, "bank"):
        bank_id = get_element_attribute(bank, "id")
        bank_name = get_element_text(bank, "name", default="Unknown")
        min_balance = get_element_text(bank, "min_balance", default="0")

        print(f"Bank: {bank_name} (ID: {bank_id})")
        print(f"  Minimum Balance: ${min_balance}")
        print()


def example_validate_xml_structure():
    """
    Example: Validate XML structure before processing.
    
    Demonstrates:
    - Structure validation
    - Required elements and attributes checking
    - Error handling
    """
    print("Example 2: Validating XML Structure")
    print("-" * 50)

    root = load_xml_file("config/game_config.xml")

    if root is None:
        print("Warning: Could not load game_config.xml")
        return

    # Validate that required configuration elements exist
    is_valid, error_msg = validate_xml_structure(
        root,
        required_children=["database", "server", "logging"],
        required_attributes=["version", "environment"],
    )

    if is_valid:
        print("Configuration is valid!")
        version = get_element_attribute(root, "version")
        environment = get_element_attribute(root, "environment")
        print(f"  Version: {version}")
        print(f"  Environment: {environment}")
    else:
        print(f"Configuration validation failed: {error_msg}")
    print()


def example_extract_nested_data():
    """
    Example: Extract data from nested XML structures.
    
    Demonstrates:
    - Navigating nested elements
    - Extracting multiple levels of data
    - Converting elements to dictionaries
    """
    print("Example 3: Extracting Nested Data")
    print("-" * 50)

    xml_content = """
    <game>
        <levels>
            <level id="1" name="Tutorial">
                <reward>100</reward>
                <difficulty>Easy</difficulty>
            </level>
            <level id="2" name="Forest">
                <reward>250</reward>
                <difficulty>Medium</difficulty>
            </level>
        </levels>
    </game>
    """

    root = load_xml_string(xml_content)

    if root is not None:
        # Iterate through levels
        for level in get_child_elements(root, "level"):
            # Skip 'levels' wrapper and get individual 'level' elements
            level_id = get_element_attribute(level, "id")
            level_name = get_element_attribute(level, "name")
            reward = get_element_text(level, "reward")
            difficulty = get_element_text(level, "difficulty")

            print(f"Level {level_id}: {level_name}")
            print(f"  Reward: {reward} points")
            print(f"  Difficulty: {difficulty}")
        print()


def example_convert_to_dict():
    """
    Example: Convert XML to Python dictionary.
    
    Demonstrates:
    - Converting XML elements to dicts
    - Accessing attributes and children as dict keys
    - Working with the dictionary representation
    """
    print("Example 4: Converting XML to Dictionary")
    print("-" * 50)

    xml_content = """
    <item id="sword_001" type="weapon">
        <name>Iron Sword</name>
        <damage>15</damage>
        <value>100</value>
    </item>
    """

    root = load_xml_string(xml_content)

    if root is not None:
        # Convert to dictionary
        item_dict = element_to_dict(root)

        print("Item data as dictionary:")
        print(f"  Attributes: {item_dict.get('@attributes', {})}")

        if "children" in item_dict:
            print("  Children:")
            for child_name, child_data in item_dict["children"].items():
                if isinstance(child_data, dict) and "@text" in child_data:
                    print(f"    {child_name}: {child_data['@text']}")
        print()


def example_strict_mode():
    """
    Example: Using strict mode for critical configurations.
    
    Demonstrates:
    - Strict mode error handling
    - XMLLoadError exception handling
    - Fail-fast behavior for critical files
    """
    print("Example 5: Strict Mode for Critical Files")
    print("-" * 50)

    try:
        # Load a critical configuration file in strict mode
        root = load_xml_file("config/critical.xml", strict=True)
        print("Critical configuration loaded successfully")
    except XMLLoadError as e:
        print(f"Critical error loading configuration: {e}")
    except FileNotFoundError:
        print("Critical configuration file not found (expected in this example)")
    print()


def example_batch_loading():
    """
    Example: Batch loading multiple XML files from a directory.
    
    Demonstrates:
    - Loading multiple files at once
    - Pattern matching for file selection
    - Processing results
    """
    print("Example 6: Batch Loading XML Files")
    print("-" * 50)

    from core.xml_loader import load_xml_files_from_directory

    # Load all XML files from the data directory
    files = load_xml_files_from_directory("game_data/")

    print(f"Loaded {len(files)} XML files:")
    for filename, root in files.items():
        # Process each file
        data_dict = element_to_dict(root)
        print(f"  - {filename}")
    print()


def example_economy_system_integration():
    """
    Example: Integration with economy system.
    
    Demonstrates:
    - Real-world use case with bank system
    - Error handling
    - Data extraction and processing
    """
    print("Example 7: Economy System Integration")
    print("-" * 50)

    xml_content = """
    <bank id="bank1" name="First National Bank">
        <account id="acc001" type="checking">
            <owner>John Doe</owner>
            <balance>1500.50</balance>
        </account>
        <account id="acc002" type="savings">
            <owner>Jane Smith</owner>
            <balance>5000.00</balance>
        </account>
    </bank>
    """

    root = load_xml_string(xml_content)

    if root is not None:
        bank_name = get_element_text(root, "name")
        print(f"Bank: {bank_name}")
        print("Accounts:")

        total_balance = 0
        for account in get_child_elements(root, "account"):
            owner = get_element_text(account, "owner")
            balance = float(get_element_text(account, "balance", default="0"))
            total_balance += balance

            print(f"  {owner}: ${balance:,.2f}")

        print(f"Total Balance: ${total_balance:,.2f}")
    print()


if __name__ == "__main__":
    print("XML Loader Module - Usage Examples")
    print("=" * 50)
    print()

    # Run all examples
    example_load_bank_configuration()
    example_validate_xml_structure()
    example_extract_nested_data()
    example_convert_to_dict()
    example_strict_mode()
    example_batch_loading()
    example_economy_system_integration()

    print("=" * 50)
    print("Examples completed!")
