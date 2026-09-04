import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

from core.systems.save import manager as save_manager
from core.systems.save.xml_codec import value_to_element, element_to_value
from core.xml_loader import XMLLoadError
from core.systems import player_manager
from core.systems.inventory.loader import load_item_defs, clear_cache
from core.systems.inventory.manager import ensure_inventory, clear_all_inventories, get_inventory


class TestXmlCodec(unittest.TestCase):
    """Round-trip tests for the generic value <-> XML codec."""

    def test_roundtrip_scalars(self):
        for value in [42, 3.14, "hello", True, False, None, ""]:
            el = value_to_element("v", value)
            self.assertEqual(element_to_value(el), value)

    def test_roundtrip_nested_structure(self):
        data = {
            "1": {"max_weight": 35.0, "stacks": [{"item_id": 1, "quantity": 3}]},
            "2": [0, 0, 0],
        }
        el = value_to_element("system", data)
        self.assertEqual(element_to_value(el), data)

    def test_bool_not_confused_with_int(self):
        # bool is an int subclass in Python - make sure we don't serialize
        # True/False as "1"/"0" ints and lose the type on the way back
        el = value_to_element("v", True)
        self.assertEqual(el.get("type"), "bool")
        self.assertEqual(element_to_value(el), True)
        self.assertIsInstance(element_to_value(el), bool)

    def test_special_characters_survive_real_xml_serialization(self):
        value = {"name": "Bob & Alice <3", "note": "line1\nline2\ttabbed"}
        el = value_to_element("v", value)
        xml_bytes = ET.tostring(el)
        parsed = ET.fromstring(xml_bytes)
        self.assertEqual(element_to_value(parsed), value)

    def test_unsupported_type_raises(self):
        class Weird:
            pass
        with self.assertRaises(TypeError):
            value_to_element("v", Weird())


class TestSaveManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

        # Reset player_manager to a known state
        player_manager._players.clear()
        player_manager._players[1] = (0, 0, 0)
        player_manager._sync_player_pos1()

        # Reset inventory system to a known state
        clear_cache()
        load_item_defs()
        clear_all_inventories()
        ensure_inventory(1)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_save_writes_expected_structure(self):
        path = save_manager.save_game("slot1", directory=self.tmp_dir)
        self.assertTrue(os.path.isfile(path))
        self.assertTrue(path.endswith(".xml"))

        root = ET.parse(path).getroot()
        self.assertEqual(root.tag, "save")
        self.assertEqual(root.get("version"), str(save_manager.SAVE_VERSION))
        self.assertEqual(root.get("name"), "slot1")
        self.assertIsNotNone(root.get("saved_at"))

        system_keys = {el.get("key") for el in root.find("systems").findall("system")}
        self.assertIn("players", system_keys)
        self.assertIn("inventory", system_keys)

    def test_save_and_load_roundtrip(self):
        player_manager.add_player(2, (5, 5, 5))
        ensure_inventory(2).add(1, 3)  # 3x bread loaf

        save_manager.save_game("slot1", directory=self.tmp_dir)

        # Mutate state after saving
        player_manager.update_player_pos(2, (99, 99, 99))
        ensure_inventory(2).add(1, 1)

        loaded = save_manager.load_game("slot1", directory=self.tmp_dir)
        self.assertTrue(loaded)

        # Positions and inventory should be restored to save-time values
        self.assertEqual(player_manager.get_player_pos(2), (5, 5, 5))
        self.assertEqual(get_inventory(2).count(1), 3)

    def test_load_missing_file_graceful(self):
        result = save_manager.load_game("does_not_exist", directory=self.tmp_dir)
        self.assertFalse(result)

    def test_load_missing_file_strict_raises(self):
        with self.assertRaises(XMLLoadError):
            save_manager.load_game("does_not_exist", directory=self.tmp_dir, strict=True)

    def test_load_malformed_xml_graceful(self):
        bad_path = os.path.join(self.tmp_dir, "corrupt.xml")
        with open(bad_path, "w") as f:
            f.write("<save><unclosed>")
        result = save_manager.load_game("corrupt", directory=self.tmp_dir)
        self.assertFalse(result)

    def test_list_and_delete_saves(self):
        save_manager.save_game("alpha", directory=self.tmp_dir)
        save_manager.save_game("beta", directory=self.tmp_dir)

        self.assertEqual(save_manager.list_saves(directory=self.tmp_dir), ["alpha", "beta"])

        self.assertTrue(save_manager.delete_save("alpha", directory=self.tmp_dir))
        self.assertEqual(save_manager.list_saves(directory=self.tmp_dir), ["beta"])
        self.assertFalse(save_manager.delete_save("alpha", directory=self.tmp_dir))

    def test_unknown_system_in_save_file_warns_but_does_not_crash(self):
        path = save_manager.save_game("slot1", directory=self.tmp_dir)

        tree = ET.parse(path)
        root = tree.getroot()
        systems_el = root.find("systems")
        unknown = ET.SubElement(systems_el, "system", {"key": "some_future_system", "type": "dict"})
        entry = ET.SubElement(unknown, "entry", {"key": "foo", "type": "str"})
        entry.text = "bar"
        tree.write(path, encoding="utf-8", xml_declaration=True)

        result = save_manager.load_game("slot1", directory=self.tmp_dir)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
