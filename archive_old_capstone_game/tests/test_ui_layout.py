import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
pygame.init()

from src import ui_layout


def _rects_overlap(a, b):
    x_overlap = a.left < b.right and b.left < a.right
    y_overlap = a.top < b.bottom and b.top < a.bottom
    return x_overlap and y_overlap


class TestNoMajorUIComponentsOverlap(unittest.TestCase):
    """Section 十七: full UI layout audit + regression test. Every rect
    checked here comes from ui_layout.py -- if two of them ever start
    overlapping, it means a shared-geometry change broke the "derive from
    the actual neighbor" invariant this module is built on, not that two
    independently hand-picked coordinates happened to clash (there aren't
    supposed to be any of those left)."""

    def _named_rects(self):
        hb = ui_layout.hotbar_layout()
        return {
            "top_panel": ui_layout.top_panel_rect(),
            "daynight_bar": ui_layout.daynight_bar_rect(),
            "shop_button": ui_layout.shop_button_rect(),
            "tutorial_sidebar": ui_layout.tutorial_sidebar_rect(),
            "hotbar_panel": hb["panel_rect"],
            "bottom_hint_area": ui_layout.bottom_hint_area(),
        }

    # The shop button is deliberately drawn as a floating badge anchored to
    # the top-right corner of (visually on top of) the top panel's own
    # background (see ui.py's _draw_top_panel_and_zone_buttons /
    # _draw_shop_button draw order and shop_button_rect()'s docstring) --
    # this is intentional layering, not two unrelated opaque panels
    # clashing, so it's excluded from the "must be fully disjoint" check
    # below rather than silently ignored.
    _EXPECTED_INTENTIONAL_OVERLAPS = {frozenset({"top_panel", "shop_button"})}

    def test_no_pair_of_named_chrome_rects_overlaps(self):
        rects = self._named_rects()
        names = list(rects.keys())
        offending = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a_name, b_name = names[i], names[j]
                if frozenset({a_name, b_name}) in self._EXPECTED_INTENTIONAL_OVERLAPS:
                    continue
                if _rects_overlap(rects[a_name], rects[b_name]):
                    offending.append((a_name, b_name))
        self.assertEqual(offending, [], f"overlapping UI rects: {offending}")

    def test_zone_toggle_buttons_stay_inside_top_panel(self):
        top = ui_layout.top_panel_rect()
        toggles = ui_layout.zone_toggle_button_rects()
        for name, rect in toggles.items():
            self.assertGreaterEqual(rect.left, top.left, f"{name} toggle left of top panel")
            self.assertLessEqual(rect.right, top.right, f"{name} toggle right of top panel")
            self.assertGreaterEqual(rect.top, top.top, f"{name} toggle above top panel")
            self.assertLessEqual(rect.bottom, top.bottom, f"{name} toggle below top panel")

    def test_zone_toggle_buttons_do_not_overlap_each_other(self):
        toggles = ui_layout.zone_toggle_button_rects()
        self.assertFalse(_rects_overlap(toggles["farm"], toggles["decor"]))

    def test_money_readout_does_not_overlap_shop_button(self):
        money = ui_layout.money_readout_rect()
        shop = ui_layout.shop_button_rect()
        self.assertFalse(_rects_overlap(money, shop))

    def test_hotbar_slots_do_not_overlap_each_other(self):
        hb = ui_layout.hotbar_layout()
        slots = [s["rect"] for s in hb["slots"]]
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                self.assertFalse(_rects_overlap(slots[i], slots[j]))

    def test_bottom_stack_orders_toolbar_hint_toast_thought_without_overlap(self):
        """toolbar -> hint -> toast -> thought, each stacked strictly above
        the previous one's top edge (see ui_layout.py's own module
        docstring for this ordering)."""
        toolbar = ui_layout.bottom_toolbar_area()
        hint = ui_layout.bottom_hint_area()
        toast_bottom = ui_layout.bottom_toast_bottom_y()
        thought_bottom = ui_layout.bottom_thought_bottom_y()

        self.assertLessEqual(hint.bottom + ui_layout.BOTTOM_AREA_GAP, toolbar.top + 1)
        self.assertLessEqual(toast_bottom, hint.top)
        self.assertLess(thought_bottom, toast_bottom)

    def test_tutorial_sidebar_stays_within_screen_bounds(self):
        rect = ui_layout.tutorial_sidebar_rect()
        self.assertGreaterEqual(rect.left, 0)
        self.assertLessEqual(rect.right, ui_layout.WIDTH)
        self.assertGreaterEqual(rect.top, 0)
        self.assertLessEqual(rect.bottom, ui_layout.HEIGHT)

    def test_top_panel_stats_row_stays_within_top_panel(self):
        top = ui_layout.top_panel_rect()
        stats = ui_layout.top_panel_stats_row_rect()
        self.assertGreaterEqual(stats.top, top.top)
        self.assertLessEqual(stats.bottom, top.bottom + 4)  # small render-padding tolerance


if __name__ == "__main__":
    unittest.main()
