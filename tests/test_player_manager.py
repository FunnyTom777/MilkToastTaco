import unittest
from core.systems import player_manager


class TestPlayerManager(unittest.TestCase):
    def setUp(self):
        # Reset internal state for isolation between tests
        # Re-import module-level _players by clearing and re-adding default
        player_manager._players.clear()
        player_manager._players[1] = (0, 0, 0)
        player_manager._sync_player_pos1()

    def test_add_update_get_remove_player(self):
        self.assertEqual(player_manager.get_player_pos(1), (0, 0, 0))

        self.assertTrue(player_manager.add_player(2, (1, 2, 3)))
        self.assertEqual(player_manager.get_player_pos(2), (1, 2, 3))

        self.assertTrue(player_manager.update_player_pos(2, (4, 5, 6)))
        self.assertEqual(player_manager.get_player_pos(2), (4, 5, 6))

        self.assertTrue(player_manager.remove_player(2))
        self.assertIsNone(player_manager.get_player_pos(2))

    def test_invalid_operations(self):
        with self.assertRaises(ValueError):
            player_manager.add_player(1, (0, 0, 0))

        with self.assertRaises(ValueError):
            player_manager.update_player_pos(999, (0, 0, 0))

        with self.assertRaises(ValueError):
            player_manager.remove_player(999)

        with self.assertRaises(ValueError):
            player_manager.add_player(3, (1, 2))

        with self.assertRaises(ValueError):
            player_manager.update_player_pos(1, (1,))


if __name__ == '__main__':
    unittest.main()
