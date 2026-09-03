import datetime
import unittest

from core.systems.inventory.loader import ItemDef, load_item_defs, get_item_def, get_all_item_defs, clear_cache
from core.systems.inventory.manager import Inventory, InventoryStack, DEFAULT_MAX_WEIGHT, clear_all_inventories, ensure_inventory, get_inventory, set_max_weight
from core.systems import player_manager


class TestInventoryLoader(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def test_load_all_items(self):
        defs = load_item_defs()
        # data/items.xml currently has 24 items
        self.assertEqual(len(defs), 24)
        # Spot-check a few known items
        bread = defs.get(1)
        self.assertIsNotNone(bread)
        self.assertEqual(bread.name, "bread loaf")
        self.assertAlmostEqual(bread.weight, 0.5)
        self.assertTrue(bread.perishable)
        self.assertEqual(bread.spoil_hours, 72)

        battery = defs.get(3)
        self.assertIsNotNone(battery)
        self.assertEqual(battery.name, "car battery")
        self.assertAlmostEqual(battery.weight, 7.0)

        beans = defs.get(5)
        self.assertFalse(beans.perishable)
        self.assertIsNone(beans.spoil_hours)

        log = defs.get(40)
        self.assertAlmostEqual(log.weight, 25.0)

    def test_get_item_def_caching(self):
        # Should auto-load if cache empty
        defn = get_item_def(1)
        self.assertIsNotNone(defn)
        all_defs = get_all_item_defs()
        self.assertEqual(len(all_defs), 24)

    def test_tags_parsed(self):
        defs = load_item_defs()
        hammer = defs[10]
        self.assertIn("tool", hammer.tags)
        self.assertIn("construction", hammer.tags)
        bread = defs[1]
        self.assertIn("food", bread.tags)

    def test_clear_cache(self):
        load_item_defs()
        clear_cache()
        # After clear, get should reload
        from core.systems.inventory import loader as loader_mod
        self.assertEqual(len(loader_mod._ITEM_DEFS), 0)
        defn = get_item_def(1)
        self.assertIsNotNone(defn)


class TestInventoryWeight(unittest.TestCase):
    def setUp(self):
        clear_cache()
        load_item_defs()
        clear_all_inventories()

    def test_empty_weight(self):
        inv = Inventory()
        self.assertAlmostEqual(inv.total_weight(), 0.0)
        self.assertTrue(inv.is_empty())

    def test_add_within_limit(self):
        inv = Inventory(max_weight=35.0)
        self.assertTrue(inv.add(1, 10))  # 10 bread = 5kg
        self.assertAlmostEqual(inv.total_weight(), 5.0)
        self.assertEqual(inv.count(1), 10)

    def test_can_add_and_weight_limit(self):
        inv = Inventory(max_weight=35.0)
        # 1 felled log = 25kg
        self.assertTrue(inv.add(40, 1))
        self.assertAlmostEqual(inv.total_weight(), 25.0)
        # Second log would be 50kg > 35, should fail
        self.assertFalse(inv.can_add(40, 1))
        self.assertFalse(inv.add(40, 1))
        self.assertAlmostEqual(inv.total_weight(), 25.0)
        # But 10 bread (5kg) fits within remaining 10kg
        self.assertTrue(inv.can_add(1, 10))
        self.assertTrue(inv.add(1, 10))
        self.assertAlmostEqual(inv.total_weight(), 30.0)

    def test_three_logs_exceed(self):
        inv = Inventory()  # 35kg default
        self.assertTrue(inv.add(40, 1))  # 25
        self.assertFalse(inv.add(40, 1))  # would be 50
        # With bigger limit, can carry 2
        inv2 = Inventory(max_weight=60)
        self.assertTrue(inv2.add(40, 2))
        self.assertAlmostEqual(inv2.total_weight(), 50.0)
        self.assertFalse(inv2.add(40, 1))  # would be 75

    def test_jerry_can_weight(self):
        inv = Inventory()
        # jerry can = 15kg, 2 = 30 fits, 3 =45 fails
        self.assertTrue(inv.add(32, 2))
        self.assertFalse(inv.add(32, 1))

    def test_remove(self):
        inv = Inventory()
        inv.add(1, 5)
        self.assertTrue(inv.remove(1, 2))
        self.assertEqual(inv.count(1), 3)
        self.assertAlmostEqual(inv.total_weight(), 1.5)
        # Remove all
        self.assertTrue(inv.remove(1, 3))
        self.assertTrue(inv.is_empty())
        # Not enough to remove
        self.assertFalse(inv.remove(1, 1))

    def test_add_unknown_item(self):
        inv = Inventory()
        self.assertFalse(inv.add(9999, 1))

    def test_invalid_quantity(self):
        inv = Inventory()
        with self.assertRaises(ValueError):
            inv.add(1, 0)
        with self.assertRaises(ValueError):
            inv.add(1, -1)
        with self.assertRaises(ValueError):
            inv.remove(1, 0)

    def test_has(self):
        inv = Inventory()
        inv.add(1, 3)
        self.assertTrue(inv.has(1, 2))
        self.assertFalse(inv.has(1, 4))
        self.assertFalse(inv.has(999, 1))

    def test_remaining_capacity(self):
        inv = Inventory(max_weight=10)
        inv.add(1, 10)  # 5kg
        self.assertAlmostEqual(inv.remaining_capacity(), 5.0)

    def test_serialization(self):
        inv = Inventory(max_weight=50)
        inv.add(1, 2)
        inv.add(40, 1)
        data = inv.to_dict()
        inv2 = Inventory.from_dict(data)
        self.assertAlmostEqual(inv2.total_weight(), inv.total_weight())
        self.assertEqual(inv2.max_weight, 50)
        self.assertEqual(inv2.count(1), 2)
        self.assertEqual(inv2.count(40), 1)


class TestInventorySpoilage(unittest.TestCase):
    def setUp(self):
        clear_cache()
        load_item_defs()
        clear_all_inventories()

    def test_bread_spoil(self):
        inv = Inventory()
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=73)
        inv.add(1, 1, acquired_at=past)  # bread spoil 72h
        self.assertEqual(len(inv.spoiled_stacks()), 1)
        self.assertTrue(inv.list_items()[0].is_spoiled())

    def test_bread_not_yet_spoiled(self):
        inv = Inventory()
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=71)
        inv.add(1, 1, acquired_at=past)
        self.assertEqual(len(inv.spoiled_stacks()), 0)

    def test_non_perishable_never_spoils(self):
        inv = Inventory()
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1000)
        inv.add(5, 1, acquired_at=past)  # canned beans not perishable
        self.assertEqual(len(inv.spoiled_stacks()), 0)

    def test_mayonnaise_long_spoil(self):
        inv = Inventory()
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=239)
        inv.add(2, 1, acquired_at=past)  # mayo 240h
        self.assertEqual(len(inv.spoiled_stacks()), 0)
        past2 = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=241)
        inv2 = Inventory()
        inv2.add(2, 1, acquired_at=past2)
        self.assertEqual(len(inv2.spoiled_stacks()), 1)

    def test_remove_spoiled(self):
        inv = Inventory()
        past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=200)
        inv.add(1, 1, acquired_at=past)  # spoiled
        inv.add(5, 1)  # not spoiled
        removed = inv.remove_spoiled()
        self.assertEqual(removed, 1)
        self.assertEqual(inv.count(1), 0)
        self.assertEqual(inv.count(5), 1)


class TestPerPlayerInventory(unittest.TestCase):
    def setUp(self):
        clear_cache()
        load_item_defs()
        clear_all_inventories()
        # Reset player_manager
        player_manager._players.clear()
        player_manager._players[1] = (0, 0, 0)
        player_manager._sync_player_pos1()
        # Ensure inventory for player 1 exists after reset
        clear_all_inventories()
        ensure_inventory(1)
        # Also need to re-sync ensure for player 1 via player_manager import side effect
        # (we cleared inventories, so re-ensure)
        ensure_inventory(1)

    def test_per_player_isolation(self):
        inv1 = ensure_inventory(1)
        inv2 = ensure_inventory(2)
        inv1.add(1, 5)
        inv2.add(40, 1)
        self.assertEqual(inv1.count(1), 5)
        self.assertEqual(inv2.count(40), 1)
        self.assertEqual(inv1.count(40), 0)

    def test_player_manager_wiring(self):
        # add_player should auto-create inventory
        player_manager.add_player(99, (10, 10, 10))
        inv = get_inventory(99)
        self.assertIsNotNone(inv)
        self.assertTrue(inv.is_empty())
        # add items to that player
        inv.add(1, 2)
        self.assertEqual(inv.count(1), 2)
        # remove_player should clean up inventory
        player_manager.remove_player(99)
        self.assertIsNone(get_inventory(99))

    def test_set_max_weight(self):
        inv = ensure_inventory(1)
        # Default 35, log 25 fits, second log would fail
        inv.add(40, 1)
        self.assertFalse(inv.add(40, 1))
        set_max_weight(1, 60)
        self.assertTrue(inv.add(40, 1))
        self.assertAlmostEqual(inv.total_weight(), 50.0)

    def test_clear_all(self):
        ensure_inventory(1).add(1, 1)
        ensure_inventory(2).add(1, 1)
        clear_all_inventories()
        self.assertIsNone(get_inventory(1))
        self.assertIsNone(get_inventory(2))


if __name__ == "__main__":
    unittest.main()
