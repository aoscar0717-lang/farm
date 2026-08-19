import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action
from src.tutorial import note_event, update_unlocks, is_unlocked, TUTORIAL_STEPS


class TestTutorial(unittest.TestCase):
    """src/tutorial.py is pure progress-tracking now: it doesn't decide
    what to show anywhere (that's src/thought.py, see test_thought.py) --
    it only answers "has the player ever demonstrated they understand X"."""

    def test_move_unlocks_after_camera_moved_event(self):
        state = new_game()
        self.assertFalse(is_unlocked(state, "move"))
        note_event(state, "camera_moved")
        update_unlocks(state)
        self.assertTrue(is_unlocked(state, "move"))

    def test_unlock_latches_even_if_condition_later_reverses(self):
        # Plant and then remove every crop -- "plant" must stay unlocked
        # (the game shouldn't "forget" the player already learned this).
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "plant_crop_radish_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        update_unlocks(state)
        self.assertTrue(is_unlocked(state, "hoe"))
        self.assertTrue(is_unlocked(state, "plant"))

        # Now remove the crop entirely (shovel it away).
        state = apply_action(state, "use_shovel_5_5")
        update_unlocks(state)
        self.assertEqual(len(state["farm"]["crops"]), 0)
        self.assertTrue(is_unlocked(state, "plant"))  # still latched

    def test_thief_seen_latches_even_after_thief_despawns(self):
        # thief_pos is transient (resets to None once the thief is dealt
        # with), but the update_unlocks latch must remember it happened.
        state = new_game()
        state["farm"]["thief_pos"] = (10, 10)
        update_unlocks(state)
        self.assertTrue(is_unlocked(state, "thief_seen"))

        state["farm"]["thief_pos"] = None
        update_unlocks(state)
        self.assertTrue(is_unlocked(state, "thief_seen"))  # still latched

    def test_combat_unlocks_from_landed_hit_flag(self):
        state = new_game()
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)
        state["farm"]["thief_hp"] = 3
        state["farm"]["thief_iframes"] = 0
        self.assertFalse(is_unlocked(state, "combat"))

        state = apply_action(state, "click_10_10", zone="farm")
        self.assertIn("擊中", state["last_msg"])
        update_unlocks(state)
        self.assertTrue(is_unlocked(state, "combat"))

    def test_night_start_and_night_end_derive_from_day_count(self):
        state = new_game()
        self.assertFalse(is_unlocked(state, "night_start"))
        self.assertFalse(is_unlocked(state, "night_end"))

        # Simulate two full day/night cycles.
        for _ in range(2):
            state = apply_action(state, "start_night")
            for _ in range(70):
                state = apply_action(state, "tick")

        update_unlocks(state)
        self.assertGreaterEqual(state["day_count"], 3)
        self.assertTrue(is_unlocked(state, "night_start"))
        self.assertTrue(is_unlocked(state, "night_end"))

    def test_note_event_does_not_require_new_game_to_know_about_tutorial(self):
        # tutorial.py must work against a bare state dict too (defensive:
        # nothing in capstone_contract.py was touched to add a "tutorial"
        # key, so this has to be created lazily on first use).
        state = new_game()
        if "tutorial" in state:
            del state["tutorial"]
        note_event(state, "camera_moved")
        self.assertTrue(state["tutorial"]["flags"]["camera_moved"])

    def test_every_step_has_id_and_unlock_check_only(self):
        # Tutorial's schema is deliberately minimal now -- display concerns
        # (priority/lines/condition) moved to src/thought.py entirely.
        for step in TUTORIAL_STEPS:
            self.assertIn("id", step)
            self.assertIn("unlock_check", step)
            self.assertTrue(callable(step["unlock_check"]))


if __name__ == '__main__':
    unittest.main()
