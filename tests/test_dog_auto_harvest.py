import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action, CROP_INFO, DOG_HARVEST_COOLDOWN_TICKS
from src.thought import get_contemplation_lines, _dog_status_text


def _place_dog(state, pos):
    """Places a dog the same way the real building_tasks pipeline would
    (bypassing the multi-tick construction delay, which isn't what this
    test is about) -- appends to both "dogs" and its matching "dog_meta"
    entry, exactly like _tick_zone_building's "dog" branch does."""
    state["farm"]["dogs"].append(pos)
    state["farm"]["dog_meta"].append({"mode": "idle", "target": None, "harvest_cooldown": 0})
    return state


def _place_mature_crop(state, pos, crop_type="radish"):
    state["farm"]["crops"].append(pos)
    state["farm"]["crop_data"][pos] = {
        "type": crop_type,
        "stage": CROP_INFO[crop_type]["growth_time"],
        "max_stage": CROP_INFO[crop_type]["growth_time"],
        "fertilized": False,
        "growth_timer": 0,
    }
    return state


class TestDogAutoHarvestsMatureCropsDuringTheDay(unittest.TestCase):
    """狗在白天自動收割作物: advances time (via "tick", this engine's
    real update(dt) equivalent -- see capstone_contract.py's comment above
    apply_action) and confirms a mature crop the dog is standing on
    disappears and its yield value lands in state["money"]."""

    def test_mature_crop_disappears_and_money_increases_after_ticking(self):
        state = new_game()
        state["phase"] = "day"
        crop_pos = (50, 50)
        state = _place_mature_crop(state, crop_pos, "radish")
        state = _place_dog(state, crop_pos)  # dog starts exactly on the crop -> harvests on the very next tick
        money_before = state["money"]
        expected_yield = CROP_INFO["radish"]["yield"]

        state = apply_action(state, "tick")

        self.assertNotIn(crop_pos, state["farm"]["crops"])
        self.assertNotIn(crop_pos, state["farm"]["crop_data"])
        self.assertEqual(state["money"], money_before + expected_yield)

    def test_dog_walks_to_a_distant_mature_crop_before_harvesting_it(self):
        state = new_game()
        state["phase"] = "day"
        crop_pos = (100, 50)
        state = _place_mature_crop(state, crop_pos, "carrot")
        state = _place_dog(state, (50, 50))  # far away -- needs several ticks to walk over
        money_before = state["money"]

        for _ in range(200):  # generous upper bound; a real walk takes ~50 ticks at step=1.0/tick
            state = apply_action(state, "tick")
            if crop_pos not in state["farm"]["crop_data"]:
                break

        self.assertNotIn(crop_pos, state["farm"]["crop_data"])
        self.assertEqual(state["money"], money_before + CROP_INFO["carrot"]["yield"])

    def test_dog_does_not_touch_immature_crops(self):
        state = new_game()
        state["phase"] = "day"
        pos = (50, 50)
        state["farm"]["crops"].append(pos)
        state["farm"]["crop_data"][pos] = {
            "type": "radish", "stage": 0, "max_stage": 5,
            "fertilized": False, "growth_timer": 0,
        }
        state = _place_dog(state, pos)
        money_before = state["money"]

        for _ in range(10):
            state = apply_action(state, "tick")

        self.assertIn(pos, state["farm"]["crop_data"])
        self.assertEqual(state["money"], money_before)

    def test_dog_rests_after_harvesting_before_seeking_the_next_crop(self):
        """The cooldown that prevents "instantly clears the whole field" --
        two adjacent mature crops, one dog: the second one must still be
        there immediately after the first is harvested, and only actually
        get harvested after DOG_HARVEST_COOLDOWN_TICKS have passed."""
        state = new_game()
        state["phase"] = "day"
        pos_a, pos_b = (50, 50), (60, 50)
        state = _place_mature_crop(state, pos_a, "radish")
        state = _place_mature_crop(state, pos_b, "radish")
        state = _place_dog(state, pos_a)

        state = apply_action(state, "tick")  # harvests pos_a, enters cooldown
        self.assertNotIn(pos_a, state["farm"]["crop_data"])
        self.assertIn(pos_b, state["farm"]["crop_data"])  # not touched yet -- dog is resting, not teleporting

        for _ in range(DOG_HARVEST_COOLDOWN_TICKS):
            state = apply_action(state, "tick")

        # Cooldown over -- the dog should now be free to walk to/harvest b
        # given enough further ticks (b is adjacent, one step away).
        for _ in range(20):
            state = apply_action(state, "tick")
            if pos_b not in state["farm"]["crop_data"]:
                break
        self.assertNotIn(pos_b, state["farm"]["crop_data"])

    def test_dogs_do_not_auto_harvest_at_night(self):
        state = new_game()
        state["phase"] = "night"
        crop_pos = (50, 50)
        state = _place_mature_crop(state, crop_pos, "radish")
        state = _place_dog(state, crop_pos)
        money_before = state["money"]

        state = apply_action(state, "tick")

        self.assertIn(crop_pos, state["farm"]["crop_data"])
        self.assertEqual(state["money"], money_before)


class TestDogHoverThought(unittest.TestCase):
    def _skip_intros(self, state):
        state["tutorial"] = {
            "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
            "flags": {}, "seen_counts": {},
        }
        state["money"] = 0
        return state

    def test_hover_idle_dog_during_day(self):
        state = new_game()
        self._skip_intros(state)
        state["phase"] = "day"
        pos = (50, 50)
        state = _place_dog(state, pos)
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=pos)
        self.assertTrue(any("呼呼大睡" in l for l in lines))

    def test_hover_dog_actively_harvesting(self):
        """The dog's own cell (not the crop's -- action_harvest, priority
        ~11-32, would otherwise legitimately outrank the dog-status hover
        at priority 31 whenever the two happen to share a cell; that's
        existing, correct tier behavior, not something this test is
        about)."""
        state = new_game()
        self._skip_intros(state)
        state["phase"] = "day"
        crop_pos, dog_pos = (50, 50), (40, 50)
        state = _place_mature_crop(state, crop_pos, "radish")
        state = _place_dog(state, dog_pos)
        state["farm"]["dog_meta"][0] = {"mode": "chasing_crop", "target": crop_pos, "harvest_cooldown": 0}
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=dog_pos)
        self.assertTrue(any("白蘿蔔" in l and "收割" in l for l in lines))

    def test_hover_dog_fighting_at_night_text_logic(self):
        """danger_thief_present (priority 2, unconditional on hover
        whenever thief_pos is set at all) will always outrank this
        priority-31 hover entry through the real get_contemplation_lines
        call while an active thief exists on the map -- that's existing,
        correct danger-always-wins behavior, not a bug here. This test
        instead checks the text-generation logic directly (_dog_status_text
        reading dog_meta's "fighting" mode), which is the part this feature
        actually added."""
        state = new_game()
        pos = (50, 50)
        state["farm"]["dogs"].append(pos)
        state["farm"]["dog_meta"].append({"mode": "fighting", "target": pos, "harvest_cooldown": 0})
        text = _dog_status_text(state, {"active_zone": "farm", "hover_pos": pos})
        self.assertIn("搏鬥", text)


if __name__ == "__main__":
    unittest.main()
