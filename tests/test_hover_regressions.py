import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, CROP_INFO
from src.thought import get_contemplation_lines
from src.tutorial import get_seen_count
from src import ui_layout


def _skip_beginner_intros(state):
    """Mirrors test_thought.py / test_thought_coverage.py's own helper:
    Tier-2 "haven't learned this yet" entries (move/shop/zone switch) are
    unconditional the moment a fresh game starts and outrank Tier-3+/UI
    hover entries by design -- marking them pre-learned isolates whatever
    scenario is actually under test."""
    state["tutorial"] = {
        "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
        "flags": {}, "seen_counts": {},
    }
    return state


class TestHoverThoughtRegressions19Scenarios(unittest.TestCase):
    """The 19 enumerated regression scenarios from the Hover Thought
    upgrade request (section 十五 -- "滑鼠 Hover 到什麼 -> F 就應該能理解
    玩家目前看到的東西"). Numbered to match the request, not necessarily in
    code-natural order."""

    # 1. 空地已開墾 hover 有 Thought
    def test_01_hover_empty_farmland_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["farmland"].append((5, 5))
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertTrue(any("土地" in l for l in lines))

    # 2. 未成熟作物 hover 有 Thought
    def test_02_hover_immature_crop_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["farmland"].append((5, 5))
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {
            "type": "radish", "stage": 0, "max_stage": 1,
            "fertilized": False, "growth_timer": 0,
        }
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertTrue(any("白蘿蔔" in l for l in lines))

    # 3. 成熟作物 hover 有 Thought
    def test_03_hover_mature_crop_produces_a_thought(self):
        state = new_game()
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {
            "type": "radish", "stage": 1, "max_stage": 1,
            "fertilized": False, "growth_timer": 0,
        }
        lines = get_contemplation_lines(state, "farm", "scythe", False, hover_pos=(5, 5))
        self.assertTrue(any("成熟" in l for l in lines))

    # 4. 胡蘿蔔專屬文字
    def test_04_carrot_specific_text(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {
            "type": "carrot", "stage": 0, "max_stage": CROP_INFO["carrot"]["growth_time"],
            "fertilized": False, "growth_timer": 0,
        }
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertTrue(any("胡蘿蔔" in l for l in lines))

    # 5. 魔法南瓜專屬文字
    def test_05_pumpkin_specific_text(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {
            "type": "pumpkin", "stage": 0, "max_stage": CROP_INFO["pumpkin"]["growth_time"],
            "fertilized": False, "growth_timer": 0,
        }
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertTrue(any("南瓜" in l for l in lines))

    # 6. 商店按鈕 hover 有 Thought
    def test_06_shop_button_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.shop_button_rect().center
        )
        self.assertTrue(any("商店" in l for l in lines))

    # 7. 商店 Buy 頁籤 hover 有 Thought
    def test_07_shop_buy_tab_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, True,
            mouse_pos=ui_layout.shop_page_geometry()["tab_buy"].center, active_tab="seed",
        )
        self.assertTrue(any("種植或建造" in l for l in lines))

    # 8. 商店 Sell 頁籤 hover 有 Thought
    def test_08_shop_sell_tab_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, True,
            mouse_pos=ui_layout.shop_page_geometry()["tab_sell"].center, active_tab="sell",
        )
        self.assertTrue(any("出售" in l for l in lines))

    # 9. 玩家資金 hover 有 Thought，且是即時數字
    def test_09_money_hover_produces_a_thought_with_live_value(self):
        state = new_game()
        _skip_beginner_intros(state)
        # 0, not some arbitrary amount -- a non-zero balance below the
        # "afford defenses" (Tier 1) threshold is fine too, but at/above it
        # that actionable hint correctly outranks the ambient UI money
        # hover (as it should: it's more useful to a player who can now
        # afford a fence). 0 keeps this test isolated to "is the money
        # hover live", not a second test of that priority interaction.
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.money_readout_rect().center
        )
        self.assertTrue(any("$0" in l for l in lines))

    # 10. 繁榮度 hover 有 Thought
    def test_10_prosperity_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.top_panel_stats_row_rect().center
        )
        self.assertTrue(any("繁榮度" in l for l in lines))

    # 11. 農場等級 hover 有 Thought，且反映真實等級/即將升級
    def test_11_farm_level_hover_produces_a_thought_with_live_level(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["prosperity_score"] = 120
        state["farm_level"] = 2
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.top_panel_stats_row_rect().center
        )
        self.assertTrue(any("等級 2" in l for l in lines))

    # 12. 日夜條 hover 有 Thought
    def test_12_daynight_bar_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.daynight_bar_rect().center
        )
        self.assertTrue(any(("夜晚" in l or "白天" in l) for l in lines))

    # 13. 快捷列 hover 有 Thought
    def test_13_hotbar_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.hotbar_layout()["panel_rect"].center
        )
        self.assertTrue(any("快捷" in l for l in lines))

    # 14. 新手任務側欄 hover 有 Thought
    def test_14_tutorial_sidebar_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=(ui_layout.tutorial_sidebar_rect().right - 10, ui_layout.tutorial_sidebar_rect().bottom - 10)
        )
        self.assertTrue(any("任務" in l for l in lines))

    # 15. 世界物件 (圍欄) hover 有 Thought
    def test_15_world_object_hover_produces_a_thought(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["fences"].append((5, 5))
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertTrue(any("圍欄" in l for l in lines))

    # 16. 危險狀態仍然優先於 Hover 特定物件文字
    def test_16_danger_still_takes_priority_over_hover_specific_text(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (5, 5)
        # The same cell also has a mature, harvestable crop with a scythe
        # equipped, which would normally win at priority ~11-32 -- the
        # active danger (priority 2) must still take priority.
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {
            "type": "radish", "stage": 1, "max_stage": 1,
            "fertilized": False, "growth_timer": 0,
        }
        lines = get_contemplation_lines(state, "farm", "scythe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])

    # 17. UI hover 不會被底下剛好重疊的世界格子覆蓋 (section 十三 的商店按鈕範例)
    def test_17_ui_hover_is_not_overridden_by_a_coincidentally_underlying_world_cell(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        rect = ui_layout.shop_button_rect()
        # Simulate main.py computing hover_pos from the raw mouse position
        # regardless of what's drawn on top -- a mature, harvestable crop
        # happens to occupy that translated world cell.
        fake_hover_pos = (5, 5)
        state["farm"]["crops"].append(fake_hover_pos)
        state["farm"]["crop_data"][fake_hover_pos] = {
            "type": "radish", "stage": 1, "max_stage": 1,
            "fertilized": False, "growth_timer": 0,
        }
        lines = get_contemplation_lines(
            state, "farm", "scythe", False,
            hover_pos=fake_hover_pos, mouse_pos=rect.center,
        )
        self.assertTrue(any("商店" in l for l in lines))
        self.assertFalse(any("成熟" in l for l in lines))

    # 18. 持續按住 F 不會每幀狂加 seen_count，但換一個真正不同的目標算新的一次
    def test_18_seen_count_does_not_spam_but_increments_on_a_genuinely_fresh_look(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["farmland"].append((5, 5))
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {
            "type": "radish", "stage": 0, "max_stage": 1,
            "fertilized": False, "growth_timer": 0,
        }
        for _ in range(10):
            get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertEqual(get_seen_count(state, "info_growing_crop"), 1)

        # Moving the hover to a different crop is a genuinely fresh look
        # (composite (id, detail) dedup key -- section 十四), even though
        # the winning entry id ("info_growing_crop") is the same.
        state["farm"]["crops"].append((6, 5))
        state["farm"]["crop_data"][(6, 5)] = {
            "type": "pumpkin", "stage": 0, "max_stage": 1,
            "fertilized": False, "growth_timer": 0,
        }
        get_contemplation_lines(state, "farm", None, False, hover_pos=(6, 5))
        self.assertEqual(get_seen_count(state, "info_growing_crop"), 2)

    # 19. 所有既有測試仍然全數通過 (本檔案內的自我檢查；完整驗證見
    #     `python3 -m unittest discover -s tests` 的 207/207 結果)
    def test_19_pre_existing_pinned_thoughts_spot_check_still_pass(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡似乎可以開墾成農田。"])

        state2 = new_game()
        state2["phase"] = "night"
        state2["farm"]["thief_pos"] = (10, 10)
        lines2 = get_contemplation_lines(state2, "farm", None, False, hover_pos=None)
        self.assertEqual(lines2, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])


if __name__ == "__main__":
    unittest.main()
