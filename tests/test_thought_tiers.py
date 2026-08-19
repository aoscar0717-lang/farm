import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game
from src.thought import get_contemplation_lines, reset_hold_session
from src.tutorial import get_seen_count


def _skip_beginner_intros(state):
    state["tutorial"] = {
        "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
        "flags": {}, "seen_counts": {},
    }
    return state


class TestTieredTextTill(unittest.TestCase):
    """action_till: tier1 (not learned) must equal the original static
    string test_thought.py already pins; tier2 (learned, seen_count < 6);
    tier3 (learned, seen_count >= 6)."""

    def test_tier1_matches_original_pinned_text(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡似乎可以開墾成農田。"])

    def test_tier2_after_learned_but_not_yet_seen_six_times(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0  # keep the demoted "afford defenses" hint from winning
        state["farm"]["farmland"].append((99, 99))  # latches "hoe" learned
        from src.tutorial import update_unlocks
        update_unlocks(state)
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["使用鋤頭可以開墾這塊土地。"])

    def test_tier3_after_seen_six_times(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["farmland"].append((99, 99))
        from src.tutorial import update_unlocks
        update_unlocks(state)
        # Each hover at a DIFFERENT cell forces a fresh "look" (seen_count
        # increments once per distinct entry-becomes-shown transition, see
        # thought.py's _last_shown_id dedup) -- six distinct hovers.
        for i in range(6):
            get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5 + i, 5))
            reset_hold_session(state)
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡可以開墾。"])
        self.assertGreaterEqual(get_seen_count(state, "action_till"), 6)


class TestTieredTextPlant(unittest.TestCase):
    def test_tier1_matches_original_pinned_text(self):
        state = new_game()
        state["farm"]["farmland"].append((5, 5))
        lines = get_contemplation_lines(state, "farm", "radish", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這塊土地應該可以種下種子。"])

    def test_tier2_after_learned(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["farmland"].append((5, 5))
        state["farm"]["crops"].append((50, 50))  # latches "plant" learned
        from src.tutorial import update_unlocks
        update_unlocks(state)
        lines = get_contemplation_lines(state, "farm", "radish", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["選擇一種種子，然後種在這裡。"])


class TestTieredTextHarvest(unittest.TestCase):
    def _mature_crop_state(self):
        state = new_game()
        pos = (5, 5)
        state["farm"]["crops"].append(pos)
        state["farm"]["crop_data"][pos] = {
            "type": "radish", "stage": 5, "max_stage": 5, "fertilized": False, "growth_timer": 0,
        }
        return state, pos

    def test_tier1_matches_original_pinned_text(self):
        state, pos = self._mature_crop_state()
        lines = get_contemplation_lines(state, "farm", "scythe", False, hover_pos=pos)
        self.assertEqual(lines, ["這株作物似乎已經成熟了，也許可以收割。"])

    def test_tier2_after_learned(self):
        state, pos = self._mature_crop_state()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["inventory"].setdefault("radish", {})["normal"] = 1  # latches "harvest"
        from src.tutorial import update_unlocks
        update_unlocks(state)
        lines = get_contemplation_lines(state, "farm", "scythe", False, hover_pos=pos)
        self.assertEqual(lines, ["作物成熟了，用鐮刀可以收割。"])


class TestSeenCountBookkeeping(unittest.TestCase):
    """Section 九: seen_counts increments only when an entry is actually
    the one shown (not every frame it continues to be shown), and
    reset_hold_session makes the next F-press count as a fresh look."""

    def test_seen_count_does_not_increment_every_frame_of_a_continuous_hold(self):
        state = new_game()
        for _ in range(10):
            get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        # Same entry (action_till, same hover cell) shown for 10 consecutive
        # "frames" without releasing F -- should count as ONE look, not ten.
        self.assertEqual(get_seen_count(state, "action_till"), 1)

    def test_reset_hold_session_makes_next_press_a_fresh_look(self):
        state = new_game()
        get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(get_seen_count(state, "action_till"), 1)
        reset_hold_session(state)
        get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(get_seen_count(state, "action_till"), 2)

    def test_seen_count_only_increments_for_the_entry_actually_selected(self):
        """Hovering something whose condition evaluates true but that isn't
        the winning (lowest-priority) entry this frame must NOT increment --
        only the entry actually returned counts as "shown"."""
        state = new_game()
        # danger_thief_present (priority 2) should win over action_till
        # (priority 10) when a thief is present in the farm zone at night.
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (5, 5)
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])
        self.assertEqual(get_seen_count(state, "action_till"), 0)
        self.assertEqual(get_seen_count(state, "danger_thief_present"), 1)


if __name__ == "__main__":
    unittest.main()
