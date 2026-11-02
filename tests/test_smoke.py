import random
import unittest

from depths.dungeon import biome, make_dungeon, place_entities
from depths.game import Game


class DungeonTests(unittest.TestCase):
    def test_biome_by_depth(self):
        self.assertEqual(biome(1), "Dungeon")
        self.assertEqual(biome(4), "Caves")
        self.assertEqual(biome(7), "Crypt")
        self.assertEqual(biome(10), "Abyss")

    def test_dungeon_fills_rooms(self):
        random.seed(1)
        width, height = 60, 25
        grid, rooms = make_dungeon(1, width, height)
        self.assertGreaterEqual(len(rooms), 1)
        self.assertEqual(len(grid), height)
        self.assertTrue(all(len(row) == width for row in grid))
        self.assertGreater(sum(tile == 1 for row in grid for tile in row), 0)

    def test_entities_stay_inside_floor(self):
        random.seed(2)
        width, height = 60, 25
        grid, rooms = make_dungeon(1, width, height)
        player = rooms[0][:2]
        entities, items, traps, merchant = place_entities(
            grid, width, height, 1, player, rooms
        )
        for thing in entities + items + traps:
            x, y = thing["x"], thing["y"]
            self.assertTrue(0 < x < width - 1, (x, y))
            self.assertTrue(0 < y < height - 1, (x, y))
            self.assertNotEqual(grid[y][x], 0, (x, y))


class GameTests(unittest.TestCase):
    def test_new_game_is_playable(self):
        game = Game(mw=40, mh=25)
        self.assertEqual(game.floor, 1)
        self.assertGreater(game.player["hp"], 0)
        self.assertTrue(0 <= game.player["x"] < game.mw)
        self.assertTrue(0 <= game.player["y"] < game.mh)

    def test_auto_pilot_survives_a_run(self):
        random.seed(3)
        game = Game(mw=40, mh=25)
        game.auto = True
        for _ in range(200):
            game.auto_step()
            self.assertGreaterEqual(game.player["hp"], 0)
            self.assertTrue(0 <= game.player["x"] < game.mw)
            self.assertTrue(0 <= game.player["y"] < game.mh)


if __name__ == "__main__":
    unittest.main()
