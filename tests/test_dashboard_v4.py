"""
Unit tests for Milk Toast Taco Dashboard V4 (PyQt6) and Command Bridge integration.
"""

import os
import unittest

# Set offscreen platform for headless PyQt6 execution in test environments
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from core.renderer.dashboard_v4.dashboard_v4 import DashboardV4API
from core.renderer.dashboard_v4.theme import get_theme_palette, get_theme_qss, THEME_PALETTES
from core.renderer.dashboard_v4.ui.main_window import DashboardV4MainWindow


class TestDashboardV4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.api = DashboardV4API()

    def test_theme_generator(self):
        for theme_name in THEME_PALETTES:
            palette = get_theme_palette(theme_name)
            self.assertIn("bg_base", palette)
            self.assertIn("accent", palette)

            qss = get_theme_qss(theme_name)
            self.assertIn(palette["bg_base"], qss)
            self.assertIn(palette["accent"], qss)

    def test_bridge_command_dispatch(self):
        # 1. Gametime via bridge
        res_time = self.api.call_command("time.now")
        self.assertEqual(res_time.get("status"), "success")
        self.assertIn("formatted", res_time)

        # 2. Economy via bridge
        res_bal = self.api.call_command("economy.balance", {"player_id": 1})
        self.assertEqual(res_bal.get("status"), "success")
        self.assertIn("balance", res_bal)

        # 3. Inventory via bridge
        res_inv = self.api.call_command("inventory.list", {"player_id": 1})
        self.assertEqual(res_inv.get("status"), "success")

        # 4. Vehicle shop catalog via bridge
        res_veh = self.api.call_command("vehicleshop.get_catalog")
        self.assertEqual(res_veh.get("status"), "success")

        # 5. Real estate catalog via bridge
        res_re = self.api.call_command("realestate.get_catalog")
        self.assertEqual(res_re.get("status"), "success")

        # 6. Phone contacts via bridge
        res_phone = self.api.call_command("phone.get_contacts")
        self.assertEqual(res_phone.get("status"), "success")

    def test_bridge_list_commands(self):
        res = self.api.list_commands()
        self.assertEqual(res.get("status"), "success")
        cmds = res.get("commands", [])
        self.assertGreater(len(cmds), 10)
        cmd_names = [c["name"] for c in cmds]
        self.assertIn("time.now", cmd_names)
        self.assertIn("economy.balance", cmd_names)
        self.assertIn("bank.banks", cmd_names)

    def test_main_window_initialization_and_tabs(self):
        window = DashboardV4MainWindow(self.api, player_id=1, initial_theme="default")
        self.assertIsNotNone(window)

        # Verify all 10 tabs are created
        self.assertEqual(window.tabs.count(), 10)
        tab_names = [window.tabs.tabText(i) for i in range(window.tabs.count())]
        self.assertTrue(any("Home" in t for t in tab_names))
        self.assertTrue(any("Banking" in t for t in tab_names))
        self.assertTrue(any("Inventory" in t for t in tab_names))
        self.assertTrue(any("Garage" in t for t in tab_names))
        self.assertTrue(any("Real Estate" in t for t in tab_names))
        self.assertTrue(any("Player" in t for t in tab_names))
        self.assertTrue(any("Phone" in t for t in tab_names))
        self.assertTrue(any("Commands" in t for t in tab_names))
        self.assertTrue(any("Saves" in t for t in tab_names))
        self.assertTrue(any("Settings" in t for t in tab_names))

        # Test player change
        window.combo_player.setCurrentIndex(1)
        self.assertEqual(window.current_player_id, 2)

        # Test theme switching
        window.apply_theme("crimson_red")
        self.assertEqual(window.current_theme, "crimson_red")

        # Test tab switching triggers refresh cleanly
        for i in range(window.tabs.count()):
            window.tabs.setCurrentIndex(i)

        window.close()


if __name__ == "__main__":
    unittest.main()
