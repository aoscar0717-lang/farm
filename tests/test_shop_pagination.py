import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, CROP_INFO
from src import ui_layout
from src.input_handler import handle_mouse_click, _handle_shop_click, _handle_shop_wheel
from src.thought import get_contemplation_lines


class _FakeEvent:
    def __init__(self, button, pos):
        self.button = button
        self.pos = pos


class TestShopPaginationGeometry(unittest.TestCase):
    """Section: 商店分頁機制. The bug this fixes: a card column had no cap,
    so a tab with enough items (pet's 19) laid out more rows than the shop
    panel's background could contain -- the extra cards drew (and were
    clickable) past the panel edge. shop_page_slice caps every column's
    input at SHOP_ITEMS_PER_PAGE so that can't happen structurally."""

    def test_page_count_ceils_and_is_never_zero(self):
        self.assertEqual(ui_layout.shop_page_count(0), 1)
        self.assertEqual(ui_layout.shop_page_count(1), 1)
        self.assertEqual(ui_layout.shop_page_count(ui_layout.SHOP_ITEMS_PER_PAGE), 1)
        self.assertEqual(ui_layout.shop_page_count(ui_layout.SHOP_ITEMS_PER_PAGE + 1), 2)
        self.assertEqual(ui_layout.shop_page_count(len(ui_layout.SHOP_ITEM_IDS["pet"])), 2)

    def test_page_slice_never_exceeds_per_page_cap(self):
        ids = ui_layout.SHOP_ITEM_IDS["pet"]
        for page in range(ui_layout.shop_page_count(len(ids))):
            sliced = ui_layout.shop_page_slice(ids, page)
            self.assertLessEqual(len(sliced), ui_layout.SHOP_ITEMS_PER_PAGE)

    def test_page_slice_covers_every_item_exactly_once_across_all_pages(self):
        ids = ui_layout.SHOP_ITEM_IDS["pet"]
        seen = []
        for page in range(ui_layout.shop_page_count(len(ids))):
            seen.extend(ui_layout.shop_page_slice(ids, page))
        self.assertEqual(seen, ids)

    def test_clamp_page_handles_out_of_range_and_shrinking_lists(self):
        self.assertEqual(ui_layout.shop_clamp_page(5, 3), 0)   # only 1 page exists
        self.assertEqual(ui_layout.shop_clamp_page(-1, 19), 0)
        self.assertEqual(ui_layout.shop_clamp_page(1, 19), 1)

    def test_pagination_bar_sits_above_the_worst_case_card_column_bottom(self):
        """The tightest case: buy page's LEFT column, which starts lower
        than the others (room for the seed/def/pet sub-tabs above it) --
        confirms the Prev/Next bar's y is still below (greater y than) the
        last possible card row's bottom, i.e. they never overlap."""
        page_x, start_y = ui_layout.shop_column_start(is_sell=False, column="left")
        last_row_bottom = start_y + ui_layout.SHOP_ITEMS_PER_PAGE // 2 * 75
        bar_rects = ui_layout.shop_pagination_rects()
        self.assertGreaterEqual(bar_rects["prev"].y, last_row_bottom)


class TestShopPaginationClicks(unittest.TestCase):
    def _open_pet_tab(self):
        state = new_game()
        state["money"] = 10000
        return state

    def test_only_current_page_items_are_clickable(self):
        state = self._open_pet_tab()
        active_tab = "pet"
        ids = ui_layout.SHOP_ITEM_IDS["pet"]
        page1_ids = ui_layout.shop_page_slice(ids, 0)
        page2_ids = ui_layout.shop_page_slice(ids, 1)
        self.assertNotEqual(page1_ids, page2_ids)

        # An item that only exists on page 2 must not be clickable while
        # page 1 is showing -- nothing at its (would-be) page-1 rect index
        # resolves to it.
        left_ids = page1_ids[:(len(page1_ids) + 1) // 2]
        rects = ui_layout.shop_column_rects(len(left_ids), is_sell=False, column="left")
        clicked_ids = set()
        for item_id, rect in zip(left_ids, rects):
            state2, tool, shop_open, tab = _handle_shop_click(
                dict(state), rect.center[0], rect.center[1], True, active_tab, None,
            )
            clicked_ids.add(tool)
        self.assertTrue(clicked_ids.issubset(set(page1_ids)))

    def test_next_button_advances_page_and_is_reflected_in_state(self):
        state = self._open_pet_tab()
        rects = ui_layout.shop_pagination_rects()
        state, tool, shop_open, active_tab = _handle_shop_click(
            state, rects["next"].center[0], rects["next"].center[1], True, "pet", None,
        )
        self.assertEqual(state["shop_page"][ui_layout.shop_page_key("pet")], 1)

    def test_next_button_does_not_advance_past_the_last_page(self):
        state = self._open_pet_tab()
        state["shop_page"] = {ui_layout.shop_page_key("pet"): 1}  # already on the last page
        rects = ui_layout.shop_pagination_rects()
        state, tool, shop_open, active_tab = _handle_shop_click(
            state, rects["next"].center[0], rects["next"].center[1], True, "pet", None,
        )
        self.assertEqual(state["shop_page"][ui_layout.shop_page_key("pet")], 1)

    def test_prev_button_does_not_go_below_page_zero(self):
        state = self._open_pet_tab()
        rects = ui_layout.shop_pagination_rects()
        state, tool, shop_open, active_tab = _handle_shop_click(
            state, rects["prev"].center[0], rects["prev"].center[1], True, "pet", None,
        )
        self.assertEqual(state.get("shop_page", {}).get(ui_layout.shop_page_key("pet"), 0), 0)

    def test_mouse_wheel_pages_the_shop(self):
        state = self._open_pet_tab()
        state = _handle_shop_wheel(state, 5, "pet")  # scroll down = next page
        self.assertEqual(state["shop_page"][ui_layout.shop_page_key("pet")], 1)
        state = _handle_shop_wheel(state, 4, "pet")  # scroll up = previous page
        self.assertEqual(state["shop_page"][ui_layout.shop_page_key("pet")], 0)

    def test_wheel_via_handle_mouse_click_only_pages_while_shop_is_open(self):
        state = self._open_pet_tab()
        event = _FakeEvent(button=5, pos=(500, 500))
        state, tool, shop_open, active_tab, zone = handle_mouse_click(
            state, event, None, True, "pet", 0, 0, "farm",
        )
        self.assertEqual(state["shop_page"][ui_layout.shop_page_key("pet")], 1)
        self.assertTrue(shop_open)  # wheel never closes the shop

    def test_each_tab_remembers_its_own_page_independently(self):
        state = self._open_pet_tab()
        state = _handle_shop_wheel(state, 5, "pet")
        state = _handle_shop_wheel(state, 5, "sell")  # sell has <=12 items -> still page 0 after 1 page
        self.assertEqual(state["shop_page"][ui_layout.shop_page_key("pet")], 1)
        self.assertEqual(state["shop_page"].get(ui_layout.shop_page_key("sell"), 0), 0)


class TestShopPaginationHoverMatchesClick(unittest.TestCase):
    """F Hover (thought.py) must describe exactly the card that's actually
    visible/clickable on the current page -- not silently fall back to
    page 1's items once the player has paged forward."""

    def test_hover_on_page_2_describes_a_page_2_item_not_a_page_1_item(self):
        state = new_game()
        state["tutorial"] = {
            "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
            "flags": {}, "seen_counts": {},
        }
        state["money"] = 0
        state["shop_page"] = {ui_layout.shop_page_key("pet"): 1}

        page2_ids = ui_layout.shop_page_slice(ui_layout.SHOP_ITEM_IDS["pet"], 1)
        left_ids = page2_ids[:(len(page2_ids) + 1) // 2]
        rect = ui_layout.shop_column_rects(len(left_ids), is_sell=False, column="left")[0]

        lines = get_contemplation_lines(
            state, "farm", None, True, mouse_pos=rect.center, active_tab="pet",
        )
        from src.ui import SHOP_ITEM_DETAILS
        expected_name = SHOP_ITEM_DETAILS[left_ids[0]]["name"]
        self.assertTrue(any(expected_name in l for l in lines))


if __name__ == "__main__":
    unittest.main()
