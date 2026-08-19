import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
pygame.init()

from src.capstone_contract import new_game
from src.tutorial import note_event, update_unlocks
from src import ui
from src import ui_layout


class TestSidebarGeometry(unittest.TestCase):
    """ui_layout.tutorial_sidebar_rect() is the single source of truth both
    ui.py's draw call and input_handler.py's click-passthrough guard read
    from -- geometry correctness here is what keeps both in sync."""

    def test_sidebar_sits_on_the_right_edge(self):
        rect = ui_layout.tutorial_sidebar_rect()
        self.assertEqual(rect.right, ui_layout.WIDTH - ui_layout.UI_MARGIN)
        self.assertEqual(rect.w, ui_layout.TUTORIAL_SIDEBAR_WIDTH)

    def test_sidebar_does_not_overlap_top_panel(self):
        sidebar = ui_layout.tutorial_sidebar_rect()
        top = ui_layout.top_panel_rect()
        self.assertGreaterEqual(sidebar.top, top.bottom)

    def test_sidebar_does_not_overlap_daynight_bar(self):
        sidebar = ui_layout.tutorial_sidebar_rect()
        bar = ui_layout.daynight_bar_rect()
        # Either they don't share a y-range, or they don't share an x-range.
        y_overlap = sidebar.top < bar.bottom and bar.top < sidebar.bottom
        x_overlap = sidebar.left < bar.right and bar.left < sidebar.right
        self.assertFalse(y_overlap and x_overlap)

    def test_sidebar_does_not_overlap_bottom_hint_hotbar_stack(self):
        sidebar = ui_layout.tutorial_sidebar_rect()
        hint = ui_layout.bottom_hint_area()
        self.assertLessEqual(sidebar.bottom, hint.top)

    def test_sidebar_has_a_sane_minimum_height(self):
        rect = ui_layout.tutorial_sidebar_rect()
        self.assertGreaterEqual(rect.h, 160)


class TestSidebarClickPassthroughGuard(unittest.TestCase):
    """Section 一's explicit "側欄不可讓滑鼠點擊穿透到世界" requirement --
    a click landing inside the sidebar rect must be swallowed by
    input_handler.py before it ever reaches _handle_world_click."""

    def test_click_inside_sidebar_does_not_apply_a_world_action(self):
        from src.input_handler import handle_mouse_click

        class FakeEvent:
            button = 1
            pos = None

        state = new_game()
        rect = ui_layout.tutorial_sidebar_rect()
        event = FakeEvent()
        event.pos = rect.center

        before_msg = state.get("last_msg")
        result_state, tool, shop_open, tab, zone = handle_mouse_click(
            state, event, "hoe", False, "seed", 0, 0, "farm",
        )
        # A world click with "hoe" equipped would normally start a
        # building_task or set last_msg -- neither should happen here.
        self.assertEqual(len(result_state["farm"]["building_tasks"]), 0)
        self.assertEqual(result_state.get("last_msg"), before_msg)


class TestSidebarDrawSmoke(unittest.TestCase):
    """Not a pixel-perfect render test (no real pygame in this sandbox --
    see tests/test_sprite_loader.py's own notes on that) -- just confirms
    draw_tutorial_sidebar runs without raising for a range of quest-progress
    states, using the project's existing pygame stub."""

    def _screen(self):
        return pygame.Surface((ui_layout.WIDTH, ui_layout.HEIGHT))

    def test_draws_without_error_on_fresh_game(self):
        state = new_game()
        ui.draw_tutorial_sidebar(self._screen(), state)  # must not raise

    def test_draws_without_error_partway_through(self):
        state = new_game()
        note_event(state, "camera_moved")
        note_event(state, "f_thought_used")
        update_unlocks(state)
        ui.draw_tutorial_sidebar(self._screen(), state)  # must not raise

    def test_draws_without_error_when_everything_complete(self):
        from src.tutorial import TUTORIAL_STEPS
        state = new_game()
        state["tutorial"] = {
            "unlocked": {s["id"]: True for s in TUTORIAL_STEPS},
            "flags": {}, "seen_counts": {},
        }
        ui.draw_tutorial_sidebar(self._screen(), state)  # must not raise

    def test_title_reflects_completion_state(self):
        """Section 一: must not say "新手教學" forever -- becomes "農場指南"
        once every quest task is done. Exercised indirectly via
        get_quest_progress since the stub can't inspect rendered pixels."""
        from src.tutorial_quests import get_quest_progress
        from src.tutorial import TUTORIAL_STEPS

        fresh = new_game()
        self.assertIsNotNone(get_quest_progress(fresh)["current_task"])

        done = new_game()
        done["tutorial"] = {
            "unlocked": {s["id"]: True for s in TUTORIAL_STEPS},
            "flags": {}, "seen_counts": {},
        }
        self.assertIsNone(get_quest_progress(done)["current_task"])


if __name__ == "__main__":
    unittest.main()
