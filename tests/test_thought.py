import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action
from src.thought import get_contemplation_lines


def _grow_one_night(state):
    """Crop stage only advances inside the start_night handler (once per
    day->night transition), not via plain "tick" -- so simulate a full,
    quick night to get back to day and be able to call start_night again."""
    state = apply_action(state, "start_night")
    for _ in range(65):
        state = apply_action(state, "tick")
        if state["phase"] == "day":
            break
    return state


def _skip_beginner_intros(state):
    """Tier-2 "haven't learned this yet" entries (move / shop / zone
    switch) are unconditional the moment a fresh game starts, and Tier 2
    outranks Tier 3 by design (an unlearned mechanic matters more than an
    ambient description of something nearby) -- exactly like a real player
    who's already panned the camera and opened the shop once. Directly
    marking these learned isolates the Tier-3 scenario under test instead
    of incidentally re-testing Tier-2-beats-Tier-3 (covered separately by
    TestThoughtPriorityTiers)."""
    state["tutorial"] = {"unlocked": {"move": True, "shop_sell": True, "zone_switch": True}, "flags": {}}


class TestThoughtScenarios(unittest.TestCase):
    """The six situations requested for manual testing, exercised directly
    against the Thought engine (no pygame needed -- main.py just computes
    hover_pos from the mouse and forwards everything else unchanged)."""

    def test_A_hovering_a_growing_crop(self):
        state = new_game()
        _skip_beginner_intros(state)
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "plant_crop_radish_5_5")
        for _ in range(3):  # building_tasks "crop" needs 3 ticks to materialize
            state = apply_action(state, "tick")
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertLess(data["stage"], data["max_stage"])

        state["money"] = 0  # otherwise "afford defenses" (Tier 1) outranks this Tier 3 info
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertEqual(lines, ["作物正在生長，可能還需要一點時間才會成熟。"])

    def test_B_hovering_a_mature_crop(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "plant_crop_radish_5_5")
        for _ in range(3):
            state = apply_action(state, "tick")
        data = state["farm"]["crop_data"][(5, 5)]
        # radish's growth_time is 5; stage only advances inside start_night
        # (once per day->night transition), never via plain "tick".
        while data["stage"] < data["max_stage"]:
            state = _grow_one_night(state)
            data = state["farm"]["crop_data"][(5, 5)]
        self.assertGreaterEqual(data["stage"], data["max_stage"])

        lines = get_contemplation_lines(state, "farm", "scythe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這株作物似乎已經成熟了，也許可以收割。"])

    def test_C_hoe_over_untilled_ground(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡似乎可以開墾成農田。"])

    def test_D_seed_over_tilled_farmland(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertIn((5, 5), state["farm"]["farmland"])

        lines = get_contemplation_lines(state, "farm", "radish", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這塊土地應該可以種下種子。"])

    def test_E_thief_appears_at_night(self):
        state = new_game()
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)

        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=None)
        self.assertEqual(lines, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])

    def test_F_hovering_near_a_fence(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0  # otherwise "afford defenses" (Tier 1) outranks this Tier 3 info
        state["farm"]["fences"].append((20, 20, 3))

        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["圍欄可以擋住敵人的行動路線，替作物或造景爭取時間。"])


class TestThoughtPriorityTiers(unittest.TestCase):
    def test_danger_outranks_everything_else(self):
        # Stack a Tier-1 actionable condition (hovering tillable ground
        # with the hoe out), a Tier-2 unlearned-mechanic condition (fresh
        # game, "move" not learned), and a Tier-0 danger condition (thief
        # present at night) all at once -- danger must win.
        state = new_game()
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)

        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])

    def test_unlearned_mechanic_outranks_ambient_fallback(self):
        state = new_game()
        # Below the $20 threshold so "you could afford defenses" (Tier 1)
        # doesn't also fire and legitimately outrank this (per the spec,
        # Tier 1 actionable > Tier 2 unlearned mechanic > Tier 4 ambient --
        # this test isolates Tier 2 vs Tier 4 specifically).
        state["money"] = 0
        # Nothing hovered, no danger, no immediate action -- but "move"
        # hasn't been learned yet, so it should win over the status fallback.
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=None)
        self.assertEqual(lines, ["按住滑鼠右鍵拖曳，或用 WASD/方向鍵，可以看看農場其他地方。"])

    def test_fallback_status_line_when_nothing_else_applies(self):
        state = new_game()
        state["money"] = 0  # otherwise "afford defenses" (demoted Tier 1) still beats Tier 4
        from src.tutorial import TUTORIAL_STEPS
        state["tutorial"] = {"unlocked": {s["id"]: True for s in TUTORIAL_STEPS}, "flags": {}}

        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=None)
        self.assertTrue(lines[0].startswith(f"第 {state['day_count']} 天"))


class TestThoughtDemotion(unittest.TestCase):
    def test_action_till_demotes_in_priority_once_hoe_is_learned(self):
        state = new_game()
        # Give the player something else Tier-1-actionable to compete with:
        # a sellable crop in inventory (action_sell_crops).
        state["inventory"]["radish"]["normal"] = 1

        # Before "hoe" is learned: hovering tillable ground with the hoe
        # out (priority 10) should still beat "you have crops to sell"
        # (priority 15).
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡似乎可以開墾成農田。"])

        # Learn "hoe" (till something once), which also happens to leave
        # (5, 5) itself tilled -- hover a different untilled cell instead
        # so the till-hint's *condition* is still true, only its learned
        # status changed.
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertGreater(len(state["farm"]["farmland"]), 0)

        # Now action_till should be demoted below action_sell_crops.
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(8, 8))
        self.assertEqual(lines, ["背包裡有收成了，按 B 打開商店可以賣掉換錢。"])


if __name__ == '__main__':
    unittest.main()
