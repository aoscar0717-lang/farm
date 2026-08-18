import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action, CROP_INFO


def _till_and_plant(state, crop_type, pos=(5, 5)):
    """Real gameplay path (not a hand-built crop_data dict): till, wait for
    the tilling building_task to finish, plant, wait for the planting
    building_task to finish. This is what actually reads CROP_INFO's
    growth_time into the new crop_data's max_stage, so it's the only way to
    genuinely exercise the V1.1 growth_time change end to end."""
    gx, gy = pos
    state = apply_action(state, f"use_hoe_{gx}_{gy}")
    for _ in range(2):  # tilling building_task needs 2 ticks
        state = apply_action(state, "tick")
    assert pos in state["farm"]["farmland"], "tilling didn't finish -- test setup is stale"

    state = apply_action(state, f"plant_crop_{crop_type}_{gx}_{gy}")
    for _ in range(3):  # crop building_task needs 3 ticks
        state = apply_action(state, "tick")
    assert pos in state["farm"]["crop_data"], "planting didn't finish -- test setup is stale"
    return state


def _one_night_cycle(state):
    """start_night (this is the only place crop stage advances) then run
    the night phase down to 0 and back to day, quickly."""
    state = apply_action(state, "start_night")
    for _ in range(65):  # night is 60 real seconds/ticks; 65 is a safety margin
        state = apply_action(state, "tick")
        if state["phase"] == "day":
            break
    return state


class TestCropGrowthTimes(unittest.TestCase):
    """V1.1 balance pass: growth_time used to be 5 for every crop (all three
    needing 5 full day/night cycles = ~15 real minutes to mature, no matter
    how cheap or expensive), while the shop description had always claimed
    1/2/3 days. growth_time is now 1/2/3 to match what the shop already
    promised -- these tests plant through the real action path (not a
    hand-built crop_data dict) so they genuinely exercise CROP_INFO."""

    def test_1_radish_matures_after_exactly_one_night(self):
        state = new_game()
        self.assertEqual(CROP_INFO["radish"]["growth_time"], 1)
        state = _till_and_plant(state, "radish")
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertEqual(data["stage"], 0)

        state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertGreaterEqual(data["stage"], data["max_stage"])

    def test_2_carrot_matures_after_exactly_two_nights_not_one(self):
        state = new_game()
        self.assertEqual(CROP_INFO["carrot"]["growth_time"], 2)
        state["farm_level"] = 2  # carrot needs farm_level >= 2
        state = _till_and_plant(state, "carrot")

        state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertLess(data["stage"], data["max_stage"], "should still be growing after only 1 night")

        state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertGreaterEqual(data["stage"], data["max_stage"])

    def test_3_pumpkin_matures_after_exactly_three_nights_not_two(self):
        state = new_game()
        self.assertEqual(CROP_INFO["pumpkin"]["growth_time"], 3)
        state["farm_level"] = 3  # pumpkin needs farm_level >= 3
        state = _till_and_plant(state, "pumpkin")

        for _ in range(2):
            state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertLess(data["stage"], data["max_stage"], "should still be growing after only 2 nights")

        state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertGreaterEqual(data["stage"], data["max_stage"])

    def test_4_fertilizer_still_doubles_growth_per_night(self):
        # Fertilized pumpkin (growth_time=3) should mature in 2 nights
        # instead of 3: night 1 takes it 0 -> 2, night 2 takes it 2 -> 4,
        # clamped to max_stage=3 -- still matured a night early, same
        # "+2/night instead of +1/night" mechanic as before, untouched.
        state = new_game()
        state["farm_level"] = 3
        state = _till_and_plant(state, "pumpkin")
        state = apply_action(state, "use_fertilizer_5_5")
        self.assertTrue(state["farm"]["crop_data"][(5, 5)]["fertilized"])

        state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertLess(data["stage"], data["max_stage"], "should still be growing after only 1 fertilized night")

        state = _one_night_cycle(state)
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertGreaterEqual(data["stage"], data["max_stage"])


if __name__ == '__main__':
    unittest.main()
