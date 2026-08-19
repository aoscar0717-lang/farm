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


# ---------------------------------------------------------------------------
# Section 十一: explicit WORLD_THOUGHT_TARGETS / UI_THOUGHT_TARGETS coverage
# registries + loop-based assertions. Each entry is name -> a zero-arg
# builder returning (state, kwargs_for_get_contemplation_lines, check_fn).
# The point is COVERAGE, not re-pinning exact strings (test_thought.py /
# test_thought_tiers.py already do that for the handful of entries with a
# stable pinned string) -- check_fn just has to confirm the line that came
# back is actually about the thing being hovered, not the generic ambient
# fallback.
# ---------------------------------------------------------------------------

def _hoe_state():
    state = new_game()
    _skip_beginner_intros(state)
    state["money"] = 0
    return state


def _planted_state(crop, ticks_after_plant=3):
    state = _hoe_state()
    state["farm"]["farmland"].append((5, 5))
    state["farm"]["crops"].append((5, 5))
    from src.capstone_contract import CROP_INFO
    state["farm"]["crop_data"][(5, 5)] = {
        "type": crop, "stage": 0, "max_stage": CROP_INFO[crop]["growth_time"],
        "fertilized": False, "growth_timer": 0,
    }
    return state


def _mature_state(crop="radish", learned=False, tool=None):
    state = _hoe_state() if learned else new_game()
    from src.capstone_contract import CROP_INFO
    state["farm"]["crops"].append((5, 5))
    state["farm"]["crop_data"][(5, 5)] = {
        "type": crop, "stage": CROP_INFO[crop]["growth_time"], "max_stage": CROP_INFO[crop]["growth_time"],
        "fertilized": False, "growth_timer": 0,
    }
    if learned:
        state["inventory"].setdefault(crop, {})["normal"] = 1
        from src.tutorial import update_unlocks
        update_unlocks(state)
    return state


WORLD_THOUGHT_TARGETS = {
    "empty_tilled_farmland": lambda: (
        (lambda s: (
            s["farm"]["farmland"].append((5, 5)),
            s
        )[-1])(_hoe_state()),
        {"active_zone": "farm", "current_tool": "hoe", "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("土地" in l for l in lines),
    ),
    "untilled_ground_with_hoe": lambda: (
        new_game(),
        {"active_zone": "farm", "current_tool": "hoe", "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("開墾" in l for l in lines),
    ),
    "growing_radish": lambda: (
        _planted_state("radish"),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("白蘿蔔" in l for l in lines),
    ),
    "growing_carrot": lambda: (
        _planted_state("carrot"),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("胡蘿蔔" in l for l in lines),
    ),
    "growing_pumpkin": lambda: (
        _planted_state("pumpkin"),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("南瓜" in l for l in lines),
    ),
    "near_maturity_carrot": lambda: (
        (lambda s: (
            s["farm"]["crop_data"][(5, 5)].__setitem__("stage", 1),
            s
        )[-1])(_planted_state("carrot")),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("快要成熟" in l for l in lines),
    ),
    "mature_crop_not_learned": lambda: (
        _mature_state("radish", learned=False),
        {"active_zone": "farm", "current_tool": "scythe", "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("成熟" in l for l in lines),
    ),
    "mature_crop_learned_with_scythe": lambda: (
        _mature_state("radish", learned=True),
        {"active_zone": "farm", "current_tool": "scythe", "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("使用鐮刀收割" in l for l in lines),
    ),
    "mature_crop_learned_other_tool": lambda: (
        _mature_state("radish", learned=True),
        {"active_zone": "farm", "current_tool": "hoe", "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("換成鐮刀收割" in l for l in lines),
    ),
    "fence_nearby": lambda: (
        (lambda s: (s["farm"]["fences"].append((5, 5)), s)[-1])(_hoe_state()),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("圍欄" in l for l in lines),
    ),
    "trap_nearby": lambda: (
        (lambda s: (s["farm"]["traps"].append((5, 5)), s)[-1])(_hoe_state()),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("陷阱" in l for l in lines),
    ),
    "dog_nearby": lambda: (
        (lambda s: (s["farm"]["dogs"].append((5, 5)), s)[-1])(_hoe_state()),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("狗" in l for l in lines),
    ),
    "fountain_decor_nearby": lambda: (
        (lambda s: (s["decor"]["decorations"].append((5, 5, "fountain", 100)), s)[-1])(_hoe_state()),
        {"active_zone": "decor", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("風車" in l for l in lines),
    ),
    "thief_present": lambda: (
        (lambda s: (s.__setitem__("phase", "night"), s["farm"].__setitem__("thief_pos", (10, 10)), s)[-1])(new_game()),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": None},
        lambda lines: any("小偷" in l for l in lines),
    ),
    "boar_present": lambda: (
        (lambda s: (s.__setitem__("phase", "night"), s["decor"].__setitem__("boar_pos", (10, 10)), s)[-1])(new_game()),
        {"active_zone": "decor", "current_tool": None, "shop_open": False, "hover_pos": None},
        lambda lines: any("野豬" in l for l in lines),
    ),
    "thief_attacking_hovered_fence": lambda: (
        (lambda s: (
            s.__setitem__("phase", "night"),
            s["farm"].__setitem__("thief_ai_state", "attacking_fence"),
            s["farm"].__setitem__("thief_attack_target_fence", (5, 5)),
            s
        )[-1])(new_game()),
        {"active_zone": "farm", "current_tool": None, "shop_open": False, "hover_pos": (5, 5)},
        lambda lines: any("正在攻擊這座柵欄" in l for l in lines),
    ),
}


def _sidebar_state():
    """A state where chapter 1's first task ("move") is already done and
    the second ("f_thought") is current -- and every Tier-2 "haven't
    learned this yet" beginner-intro entry that would otherwise outrank a
    Tier-3 sidebar hover is pre-satisfied, same as _skip_beginner_intros."""
    state = new_game()
    state["tutorial"] = {
        "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
        "flags": {}, "seen_counts": {},
    }
    state["money"] = 0  # keep "afford defenses" (Tier 1) from outranking sidebar hover
    return state


UI_THOUGHT_TARGETS = {
    "shop_button": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.shop_button_rect().center},
        lambda lines: any("商店" in l for l in lines),
    ),
    "money_readout": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.money_readout_rect().center},
        lambda lines: any("$0" in l for l in lines),
    ),
    "prosperity_stats_row": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.top_panel_stats_row_rect().center},
        lambda lines: any("繁榮度" in l for l in lines),
    ),
    "daynight_bar": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.daynight_bar_rect().center},
        lambda lines: any(("夜晚" in l or "白天" in l) for l in lines),
    ),
    "zone_toggle": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.zone_toggle_button_rects()["decor"].center},
        lambda lines: any(("TAB" in l or "佈置區" in l) for l in lines),
    ),
    "hotbar": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.hotbar_layout()["panel_rect"].center},
        lambda lines: any("快捷" in l for l in lines),
    ),
    "tutorial_sidebar_current_task": lambda: (
        _sidebar_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.tutorial_sidebar_task_rects(_sidebar_state())[1][1].center},
        lambda lines: any("你現在的目標" in l for l in lines),
    ),
    "tutorial_sidebar_completed_task": lambda: (
        _sidebar_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": False,
         "mouse_pos": ui_layout.tutorial_sidebar_task_rects(_sidebar_state())[0][1].center},
        lambda lines: any("✓ 已完成" in l for l in lines),
    ),
    "shop_buy_tab": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": True, "active_tab": "seed",
         "mouse_pos": ui_layout.shop_page_geometry()["tab_buy"].center},
        lambda lines: any("種植或建造" in l for l in lines),
    ),
    "shop_sell_tab": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": True, "active_tab": "sell",
         "mouse_pos": ui_layout.shop_page_geometry()["tab_sell"].center},
        lambda lines: any("出售" in l for l in lines),
    ),
    "shop_subtab_seed": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": True, "active_tab": "seed",
         "mouse_pos": ui_layout.shop_subtab_rects()["seed"].center},
        lambda lines: any("種子" in l for l in lines),
    ),
    "shop_item_card_buy_radish": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": True, "active_tab": "seed",
         "mouse_pos": ui_layout.shop_column_rects(2, is_sell=False, column="left")[0].center},
        lambda lines: any("白蘿蔔" in l for l in lines),
    ),
    "shop_close_hint": lambda: (
        _hoe_state(),
        {"active_zone": "farm", "current_tool": None, "shop_open": True, "active_tab": "seed",
         "mouse_pos": (5, 5)},
        lambda lines: any("關閉商店" in l for l in lines),
    ),
}


class TestWorldAndUIHoverTargetRegistries(unittest.TestCase):
    """Section 十一: loop over the registries above and confirm every
    listed target produces a Thought that's actually about the thing being
    hovered (not just "some non-empty text")."""

    def test_every_world_hover_target_produces_a_meaningful_thought(self):
        for name, builder in WORLD_THOUGHT_TARGETS.items():
            with self.subTest(target=name):
                state, kwargs, check = builder()
                lines = get_contemplation_lines(state, **kwargs)
                self.assertTrue(lines, f"{name}: produced no Thought at all")
                self.assertTrue(check(lines), f"{name}: unexpected Thought text: {lines}")

    def test_every_ui_hover_target_produces_a_meaningful_thought(self):
        for name, builder in UI_THOUGHT_TARGETS.items():
            with self.subTest(target=name):
                state, kwargs, check = builder()
                lines = get_contemplation_lines(state, **kwargs)
                self.assertTrue(lines, f"{name}: produced no Thought at all")
                self.assertTrue(check(lines), f"{name}: unexpected Thought text: {lines}")


if __name__ == "__main__":
    unittest.main()
