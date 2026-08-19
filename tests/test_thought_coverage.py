import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, DECOR_INFO
from src.thought import THOUGHT_ENTRIES, get_contemplation_lines
from src import ui_layout


def _entry_ids():
    return {e["id"] for e in THOUGHT_ENTRIES}


def _skip_beginner_intros(state):
    """Mirrors test_thought.py's own helper: Tier-2 "haven't learned this
    yet" entries (move/shop/zone switch) are unconditional the moment a
    fresh game starts and outrank Tier-3+/UI-hover entries by design --
    marking them pre-learned isolates whatever's actually under test."""
    state["tutorial"] = {
        "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
        "flags": {}, "seen_counts": {},
    }
    return state


class TestWorldObjectCoverage(unittest.TestCase):
    """Section 六: every important world object must have at least one
    Thought entry that can fire for it. This doesn't re-verify every
    entry's exact text (test_thought.py already pins the pre-existing
    ones) -- it verifies *coverage*: the id exists and is reachable."""

    def test_farmland_tillable_and_plantable_covered(self):
        ids = _entry_ids()
        self.assertIn("action_till", ids)
        self.assertIn("action_plant", ids)

    def test_crop_growing_and_mature_covered(self):
        ids = _entry_ids()
        self.assertIn("info_growing_crop", ids)
        self.assertIn("action_harvest", ids)
        self.assertIn("info_no_harvestable_crop", ids)

    def test_fence_covered(self):
        ids = _entry_ids()
        self.assertIn("action_fence_place", ids)
        self.assertIn("info_fence_nearby", ids)

    def test_trap_covered(self):
        ids = _entry_ids()
        self.assertIn("action_trap_place", ids)
        self.assertIn("info_trap_nearby", ids)

    def test_dog_covered(self):
        ids = _entry_ids()
        self.assertIn("action_dog_place", ids)
        self.assertIn("info_dog_nearby", ids)

    def test_enemies_covered(self):
        ids = _entry_ids()
        self.assertIn("danger_thief_present", ids)
        self.assertIn("danger_boar_present", ids)
        self.assertIn("danger_fence_under_attack", ids)

    def test_every_decor_type_has_place_and_nearby_entries(self):
        """DECOR_INFO is the authoritative list of decor sub-types (section
        十六's "auto-discover from the real contract, don't hardcode a
        stale list") -- every one of them must have both an "about to
        place" and an "already placed, hovering it" Thought."""
        ids = _entry_ids()
        for decor_id in DECOR_INFO.keys():
            self.assertIn(
                f"action_{decor_id}_place", ids,
                f"missing action_{decor_id}_place Thought entry",
            )
            self.assertIn(
                f"info_{decor_id}_nearby", ids,
                f"missing info_{decor_id}_nearby Thought entry",
            )

    def test_windmill_thoughts_use_fountain_internal_id_but_say_feng_che(self):
        place = next(e for e in THOUGHT_ENTRIES if e["id"] == "action_fountain_place")
        nearby = next(e for e in THOUGHT_ENTRIES if e["id"] == "info_fountain_nearby")
        state = new_game()
        place_text = place["text"](state, {"current_tool": "fountain"}) if callable(place["text"]) else place["text"]
        nearby_text = nearby["text"](state, {}) if callable(nearby["text"]) else nearby["text"]
        self.assertIn("風車", place_text)
        self.assertIn("風車", nearby_text)
        self.assertNotIn("噴泉", place_text)
        self.assertNotIn("噴泉", nearby_text)


class TestToolCoverage(unittest.TestCase):
    """Section 六: every REAL, functional tool (per capstone_contract.py's
    action-prefix list) needs Thought coverage. axe/pickaxe are
    deliberately excluded -- they're registered sprites with no apply_action
    branch and no hotbar/keybind, so writing Thought text for them would be
    describing an operation that doesn't exist (an explicit hard constraint
    in the request)."""

    def test_hoe_scythe_shovel_fertilizer_all_covered(self):
        ids = _entry_ids()
        covering = {
            "hoe": {"action_till"},
            "scythe": {"action_harvest"},
            "shovel": {"action_shovel_use"},
            "fertilizer": {"action_fertilizer_use", "info_fertilizer_no_crop"},
        }
        for tool, expected_ids in covering.items():
            self.assertTrue(
                expected_ids & ids,
                f"no Thought entry covers the real tool '{tool}'",
            )

    def test_axe_and_pickaxe_are_not_given_fabricated_thoughts(self):
        """These sprites exist but have no apply_action branch and no
        keybind -- there is genuinely no "use axe" operation in the game,
        so no Thought entry should claim to describe using one."""
        for e in THOUGHT_ENTRIES:
            req = e.get("required_item")
            items = req if isinstance(req, (list, tuple, set)) else ([req] if req else [])
            self.assertNotIn("axe", items)
            self.assertNotIn("pickaxe", items)

    def test_seed_tools_covered_via_action_plant(self):
        entry = next(e for e in THOUGHT_ENTRIES if e["id"] == "action_plant")
        req = entry["required_item"]
        for seed in ("radish", "carrot", "pumpkin"):
            self.assertIn(seed, req)


class TestUIChromeCoverage(unittest.TestCase):
    """Section 十二: hovering real HUD chrome (not the scrolling world)
    must surface a Thought too, driven by ctx["mouse_pos"] rather than
    hover_pos. Beginner-intro Tier-2 entries are skipped (see
    _skip_beginner_intros) since those are unconditional on a fresh game
    and would otherwise outrank every UI-hover entry regardless of what
    the mouse is over."""

    def test_shop_button_hover_produces_shop_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0  # keep the demoted "afford defenses" hint from winning
        rect = ui_layout.shop_button_rect()
        lines = get_contemplation_lines(state, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any("商店" in line for line in lines))

    def test_money_hover_reports_current_money_dynamically(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        rect = ui_layout.money_readout_rect()
        lines = get_contemplation_lines(state, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any("$0" in line for line in lines))

        state2 = new_game()
        _skip_beginner_intros(state2)
        # Below the $20 "afford defenses" actionable-hint threshold (Tier 1,
        # priority 16 while shop_buy_defense isn't learned yet) so that
        # entry doesn't outrank the UI money hover (Tier 3b, priority 34).
        state2["money"] = 15
        lines2 = get_contemplation_lines(state2, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any("$15" in line for line in lines2))

    def test_daynight_bar_hover_covered(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        rect = ui_layout.daynight_bar_rect()
        lines = get_contemplation_lines(state, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any(("夜晚" in line or "白天" in line) for line in lines))

    def test_zone_toggle_hover_covered(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        rect = ui_layout.zone_toggle_button_rects()["decor"]
        lines = get_contemplation_lines(state, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any("TAB" in line or "佈置區" in line for line in lines))

    def test_hotbar_hover_covered(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        rect = ui_layout.hotbar_layout()["panel_rect"]
        lines = get_contemplation_lines(state, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any("快捷" in line for line in lines))

    def test_tutorial_sidebar_hover_covered(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        rect = ui_layout.tutorial_sidebar_rect()
        lines = get_contemplation_lines(state, "farm", None, False, mouse_pos=rect.center)
        self.assertTrue(any("任務" in line for line in lines))

    def test_ui_hover_entries_require_mouse_pos_and_dont_leak_without_it(self):
        """Callers (like most of test_thought.py) that don't pass mouse_pos
        must never accidentally trigger a UI-chrome entry."""
        ui_ids = {
            "ui_shop_button", "ui_money", "ui_stats_row",
            "ui_daynight_bar", "ui_zone_toggle", "ui_hotbar", "ui_tutorial_sidebar",
        }
        for e in THOUGHT_ENTRIES:
            if e["id"] in ui_ids:
                self.assertEqual(e["trigger"], "hover")


class TestQuestGuidanceEntryExists(unittest.TestCase):
    def test_quest_guidance_entry_present(self):
        self.assertIn("quest_guidance", _entry_ids())


if __name__ == "__main__":
    unittest.main()
