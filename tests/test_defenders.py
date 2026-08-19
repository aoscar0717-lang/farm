import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action, is_terminal

class TestDefenseAnimals(unittest.TestCase):
    def test_place_and_spawn_all_animals(self):
        state = new_game()
        state["money"] = 2000

        # Place Cat, Goose, Sheep, Bull, Owl
        state = apply_action(state, "place_cat_10_10")
        state = apply_action(state, "place_goose_20_20")
        state = apply_action(state, "place_sheep_30_30")
        state = apply_action(state, "place_bull_40_40")
        state = apply_action(state, "place_owl_50_50")

        # Advance construction ticks
        for _ in range(3):
            state = apply_action(state, "tick")

        farm = state["farm"]
        self.assertIn((10, 10), farm["cats"])
        self.assertIn((20, 20), farm["geese"])
        self.assertIn((30, 30), farm["sheeps"])
        self.assertIn((40, 40), farm["bulls"])
        self.assertIn((50, 50), farm["owls"])

    def test_cat_daytime_money_bonus(self):
        state = new_game()
        state["money"] = 500
        state["farm"]["cats"].append((10, 10))

        initial_money = state["money"]
        # Advance 25 ticks to trigger cat gold bonus
        for _ in range(26):
            state = apply_action(state, "tick")

        self.assertGreater(state["money"], initial_money)
        self.assertIn("招財小貓", state.get("last_msg", ""))

    def test_bull_double_damage_combat(self):
        state = new_game()
        state["farm"]["bulls"].append((10, 10))
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)
        state["farm"]["thief_path"] = [(20, 20)]
        state["farm"]["thief_hp"] = 5
        state["farm"]["thief_iframes"] = 0


        state = apply_action(state, "night_tick")
        # Bull deals 2 damage per hit
        self.assertEqual(state["farm"]["thief_hp"], 3)

    def test_shovel_reclaims_animals(self):
        state = new_game()
        state["farm"]["cats"].append((10, 10))
        state["farm"]["bulls"].append((20, 20))

        state = apply_action(state, "use_shovel_10_10")
        self.assertNotIn((10, 10), state["farm"]["cats"])

        state = apply_action(state, "use_shovel_20_20")
        self.assertNotIn((20, 20), state["farm"]["bulls"])

if __name__ == "__main__":
    unittest.main()
