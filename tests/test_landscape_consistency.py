"""Cross-file consistency checks for the landscape expansion, both rounds:
round 1 (scarecrow/crate/bush/rock/sunflower/pine_tree/big_tree) and round 2
(stump/mushroom/picnic_basket/woodpile/picnic_blanket/beehive/garden_table/
fruit_tree).

These don't exercise game logic (that's test_contract.py /
test_thought.py's job) -- they verify the *wiring*: every new decor id is
registered consistently across every file that needs to know about it
(assets.py sprite registration, config.py display name, ui.py shop card,
ui_layout.py shop tab membership, capstone_contract.py price/prosperity +
display name, input_handler.py placement dispatch, thought.py Thought
entries). A typo or missed file in any one of these would silently break
one part of the feature (e.g. item buyable but invisible, or placeable but
mute under F) without any exception being raised -- exactly the class of
bug source-level cross-referencing catches that a runtime test might miss
if it only exercises the "happy path" ids.

assets.py itself is NOT imported here (it calls pygame.display.set_mode at
import time, which needs a real display) -- instead its source is read as
text and inspected via regex, mirroring the registration-call-inspection
approach used for prior asset-audit rounds this session.
"""

import re
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import TOOL_NAMES
from src.ui import SHOP_ITEM_DETAILS
from src import ui_layout
from src.capstone_contract import DECOR_INFO, DECOR_NAMES
from src.thought import THOUGHT_ENTRIES

ROUND1_DECOR_IDS = [
    "scarecrow", "crate", "bush", "rock", "sunflower", "pine_tree", "big_tree",
]
ROUND2_DECOR_IDS = [
    "stump", "mushroom", "picnic_basket", "woodpile",
    "picnic_blanket", "beehive", "garden_table", "fruit_tree",
]
NEW_DECOR_IDS = ROUND1_DECOR_IDS + ROUND2_DECOR_IDS
ORIGINAL_DECOR_IDS = ["stone_path", "flower", "bench", "fountain"]
ALL_DECOR_IDS = ORIGINAL_DECOR_IDS + NEW_DECOR_IDS

_SRC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))


def _read_src(filename):
    with open(os.path.join(_SRC_DIR, filename), encoding="utf-8") as f:
        return f.read()


class TestAssetsRegistration(unittest.TestCase):
    """assets.py source-text check: every new id has exactly one
    _register_sprite(...), _register_image(...), or _register_sprite_region(...)
    call registering it."""

    def setUp(self):
        self.src = _read_src("assets.py")
        # Matches _register_sprite("id", ...), _register_image("id", ...),
        # or _register_sprite_region("id", ...) -- the alternation tries
        # "sprite_region" before "sprite" so a call like
        # _register_sprite_region(...) isn't mistaken for _register_sprite
        # followed by a stray "_region" (regex backtracking would sort it
        # out either way, but this reads clearer).
        self.registered_ids = set(re.findall(r'_register_(?:sprite_region|sprite|image)\(\s*"([^"]+)"', self.src))

    def test_all_new_ids_registered(self):
        for item_id in NEW_DECOR_IDS:
            self.assertIn(item_id, self.registered_ids, f"{item_id} has no _register_sprite/_register_image call in assets.py")

    def test_leafy_tree_was_deliberately_dropped_not_registered(self):
        """A "leafy_tree" candidate (Sunnyside spr_deco_tree_01_strip4.png)
        was investigated in round 2 and dropped -- that exact file is
        already used by renderer.py's _draw_trees() for the farm zone's
        wild obstacle trees. Confirms it never got registered as a decor
        item after all (i.e. the decision stuck)."""
        self.assertNotIn("leafy_tree", self.registered_ids)

    def test_no_duplicate_registration_of_new_ids(self):
        for item_id in NEW_DECOR_IDS:
            count = len(re.findall(r'_register_(?:sprite_region|sprite|image)\(\s*"' + re.escape(item_id) + r'"', self.src))
            self.assertEqual(count, 1, f"{item_id} registered {count} times, expected exactly 1")

    def test_scarecrow_reuses_preexisting_registration_not_a_new_duplicate(self):
        """scarecrow already existed before this pass (vestigial feature) --
        confirm we didn't accidentally add a second competing registration
        for it."""
        count = len(re.findall(r'_register_(?:sprite|image)\(\s*"scarecrow"', self.src))
        self.assertLessEqual(count, 1)


class TestSpriteSliceBoundsAreWithinSheetRealDimensions(unittest.TestCase):
    """Regression guard for two out-of-range sprite-slice bugs found while
    independently verifying every registered sprite's slice coordinates:

    - fruit_tree: assets.py had `_register_sprite("fruit_tree",
      "...Trees, stumps and bushes v2.png", 5, 0, 32, 32, ...)`, but that
      sheet is only 192x128px -- sliced at 32x32 that's only 4 valid rows
      (0-3), so row=5 was out of range.
    - garden_table: assets.py had `_register_sprite("garden_table",
      "...Interior.png", 7, 4, 32, 32, ...)`, but that sheet is only
      192x144px -- sliced at 32x32 that's also only 4 valid rows (0-3), so
      row=7 was out of range.

    In both cases sprite_loader.get_sprite() was silently returning None
    the whole time (images[asset_id] stayed None; nothing was ever drawn).
    Both were fixed by switching to _register_sprite_region() with the
    exact pixel rect of the real artwork (confirmed by cropping and
    visually inspecting it in each case).

    This sandboxed test environment has no real asset files on disk
    (pygame.image.load is a stub here, see tests' PYTHONPATH setup) -- so
    the bug can't be caught by actually loading images and checking for
    None. Instead this hardcodes each referenced sheet's REAL pixel
    dimensions (confirmed via PIL against the actual project asset files)
    and checks every _register_sprite(row,col,sprite_w,sprite_h) /
    _register_sprite_region(x,y,w,h) call against them directly from
    assets.py's source text -- so any future row/col/rect mistake against
    one of these already-verified sheets is caught without needing the
    real PNGs present in this sandbox."""

    # filename -> real (width, height) in pixels, confirmed via PIL against
    # the actual asset files (not guessed). This covers every sheet
    # referenced by a _register_sprite/_register_sprite_region call in
    # assets.py as of this pass -- i.e. an exhaustive sweep, not a sample.
    SHEET_DIMENSIONS = {
        "Trees, stumps and bushes v2.png": (192, 128),
        "spr_deco_tree_02_strip4.png": (112, 43),
        "spr_deco_mushroom_red_01_strip4.png": (64, 16),
        "Maple Tree.png": (160, 48),
        "chest.png": (32, 32),
        "Walk.png": (192, 96),
        "campfire.png": (112, 48),
        "Fences.png": (64, 64),
        "spr_deco_windmill_strip9.png": (1008, 112),
        "Interior.png": (192, 144),
        "Basic Grass Biom things 1.png": (144, 80),
        "Road copiar.png": (80, 64),
        "Spring Crops.png": (224, 128),
        "1.png": (192, 32),
        "Goldie_v02.png": (128, 320),
        "rpgItems.png": (128, 128),
        "Basic_tools_and_meterials.png": (48, 32),
        "Baby Chicken Yellow.png": (64, 48),
        "Chicken Red.png": (64, 32),
        "Chicken Blonde  Green.png": (64, 32),
    }

    def setUp(self):
        self.src = _read_src("assets.py")

    def test_register_sprite_row_col_within_real_sheet_bounds(self):
        pattern = re.compile(
            r'_register_sprite\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,'
        )
        checked = 0
        for asset_id, path, row, col, sprite_w, sprite_h in pattern.findall(self.src):
            filename = path.split("/")[-1]
            if filename not in self.SHEET_DIMENSIONS:
                continue
            sheet_w, sheet_h = self.SHEET_DIMENSIONS[filename]
            row, col, sprite_w, sprite_h = int(row), int(col), int(sprite_w), int(sprite_h)
            max_row = sheet_h // sprite_h - 1
            max_col = sheet_w // sprite_w - 1
            self.assertLessEqual(
                row, max_row,
                f"{asset_id}: row={row} exceeds max valid row {max_row} for {filename} "
                f"({sheet_w}x{sheet_h} sliced at {sprite_w}x{sprite_h}) -- this is the fruit_tree bug's signature",
            )
            self.assertLessEqual(
                col, max_col,
                f"{asset_id}: col={col} exceeds max valid col {max_col} for {filename} "
                f"({sheet_w}x{sheet_h} sliced at {sprite_w}x{sprite_h})",
            )
            checked += 1
        self.assertGreater(checked, 0, "no _register_sprite calls matched a known sheet -- SHEET_DIMENSIONS or the regex went stale")

    def test_register_sprite_region_rect_within_real_sheet_bounds(self):
        pattern = re.compile(
            r'_register_sprite_region\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,'
        )
        checked = 0
        for asset_id, path, x, y, w, h in pattern.findall(self.src):
            filename = path.split("/")[-1]
            if filename not in self.SHEET_DIMENSIONS:
                continue
            sheet_w, sheet_h = self.SHEET_DIMENSIONS[filename]
            x, y, w, h = int(x), int(y), int(w), int(h)
            self.assertLessEqual(x + w, sheet_w, f"{asset_id}: region x+w={x + w} exceeds real sheet width {sheet_w}")
            self.assertLessEqual(y + h, sheet_h, f"{asset_id}: region y+h={y + h} exceeds real sheet height {sheet_h}")
            checked += 1
        self.assertEqual(checked, 2, "expected exactly two _register_sprite_region calls (fruit_tree, garden_table) -- did a fix get reverted or duplicated?")

    def test_fruit_tree_and_garden_table_specifically_use_register_sprite_region_not_the_old_out_of_range_call(self):
        for asset_id in ("fruit_tree", "garden_table"):
            self.assertIn(f'_register_sprite_region("{asset_id}",', self.src)
            self.assertNotRegex(
                self.src, r'_register_sprite\(\s*"' + re.escape(asset_id) + r'"',
                f"{asset_id} is still registered via the old row/col _register_sprite call",
            )


class TestToolNames(unittest.TestCase):
    def test_all_new_ids_have_display_names(self):
        for item_id in NEW_DECOR_IDS:
            self.assertIn(item_id, TOOL_NAMES, f"{item_id} missing from config.TOOL_NAMES")
            self.assertTrue(TOOL_NAMES[item_id], f"{item_id} has an empty display name")

    def test_fountain_still_says_windmill_not_fountain(self):
        self.assertEqual(TOOL_NAMES["fountain"], "風車")


class TestShopItemDetails(unittest.TestCase):
    def test_all_new_ids_have_shop_card_details(self):
        for item_id in NEW_DECOR_IDS:
            self.assertIn(item_id, SHOP_ITEM_DETAILS, f"{item_id} missing from ui.SHOP_ITEM_DETAILS")
            details = SHOP_ITEM_DETAILS[item_id]
            self.assertIn("name", details)
            self.assertIn("price", details)
            self.assertIn("desc", details)

    def test_shop_card_price_matches_decor_info_price(self):
        """The price shown on the shop card and the price actually charged
        by capstone_contract.py's DECOR_INFO must agree -- a mismatch here
        would mean the shop lies about what the player will pay."""
        for item_id in ALL_DECOR_IDS:
            self.assertEqual(
                SHOP_ITEM_DETAILS[item_id]["price"], DECOR_INFO[item_id]["price"],
                f"{item_id}: shop card price != DECOR_INFO price",
            )

    def test_shop_card_prosperity_desc_matches_decor_info(self):
        for item_id in ALL_DECOR_IDS:
            expected = f"繁榮度 +{DECOR_INFO[item_id]['prosperity']}"
            self.assertEqual(
                SHOP_ITEM_DETAILS[item_id]["desc"], expected,
                f"{item_id}: shop card desc doesn't match DECOR_INFO prosperity",
            )


class TestShopItemIds(unittest.TestCase):
    def test_pet_tab_has_exactly_nineteen_items(self):
        self.assertEqual(len(ui_layout.SHOP_ITEM_IDS["pet"]), 19)

    def test_pet_tab_contains_all_decor_ids_no_typos_no_dupes(self):
        pet_ids = ui_layout.SHOP_ITEM_IDS["pet"]
        self.assertEqual(set(pet_ids), set(ALL_DECOR_IDS))
        self.assertEqual(len(pet_ids), len(set(pet_ids)), "duplicate id in SHOP_ITEM_IDS['pet']")

    def test_seed_and_def_tabs_untouched(self):
        self.assertEqual(ui_layout.SHOP_ITEM_IDS["seed"], ["radish", "carrot", "pumpkin"])
        self.assertEqual(ui_layout.SHOP_ITEM_IDS["def"], ["fence", "trap", "dog", "cat", "goose", "sheep", "bull", "owl"])



class TestDecorInfoAndNames(unittest.TestCase):
    def test_decor_info_and_decor_names_have_matching_keys(self):
        self.assertEqual(set(DECOR_INFO.keys()), set(DECOR_NAMES.keys()))

    def test_all_new_ids_present_with_positive_price_and_prosperity(self):
        for item_id in NEW_DECOR_IDS:
            self.assertIn(item_id, DECOR_INFO)
            self.assertGreater(DECOR_INFO[item_id]["price"], 0)
            self.assertGreater(DECOR_INFO[item_id]["prosperity"], 0)

    def test_price_curve_is_non_decreasing_with_prosperity(self):
        """Sanity check on the proportional design: nothing should cost more
        while granting less prosperity than a cheaper item (would be an
        obviously bad deal situated right next to good ones in the shop)."""
        items = sorted(DECOR_INFO.items(), key=lambda kv: kv[1]["price"])
        for (id_a, info_a), (id_b, info_b) in zip(items, items[1:]):
            self.assertLessEqual(
                info_a["prosperity"], info_b["prosperity"],
                f"{id_a} (${info_a['price']}) grants more prosperity than pricier {id_b} (${info_b['price']})",
            )


class TestInputHandlerDispatch(unittest.TestCase):
    def test_all_new_ids_in_world_click_decor_dispatch_list(self):
        src = _read_src("input_handler.py")
        # Grab the elif current_tool in [...] block that dispatches build_decor_
        match = re.search(r'elif current_tool in \[(.*?)\]:\s*\n\s*state = apply_action\(state, f"build_decor_', src, re.S)
        self.assertIsNotNone(match, "could not find the build_decor_ dispatch list in input_handler.py")
        block = match.group(1)
        ids_in_block = set(re.findall(r'"([^"]+)"', block))
        for item_id in ALL_DECOR_IDS:
            self.assertIn(item_id, ids_in_block, f"{item_id} missing from world-click decor dispatch list")


class TestThoughtCoverage(unittest.TestCase):
    def test_every_decor_id_has_a_place_and_nearby_thought(self):
        by_required_item = {}
        for e in THOUGHT_ENTRIES:
            req = e.get("required_item")
            reqs = req if isinstance(req, (list, tuple, set)) else ([req] if req else [])
            for r in reqs:
                by_required_item.setdefault(r, []).append(e["id"])
        for item_id in ALL_DECOR_IDS:
            entry_ids = by_required_item.get(item_id, [])
            self.assertTrue(
                any(eid.startswith("action_") and eid.endswith("_place") for eid in entry_ids),
                f"{item_id}: no action_..._place Thought entry",
            )
        # "nearby" entries key off decor_type inside a lambda condition, not
        # required_item, so check by id naming convention instead.
        all_ids = {e["id"] for e in THOUGHT_ENTRIES}
        for item_id in ALL_DECOR_IDS:
            self.assertIn(f"action_{item_id}_place", all_ids, f"missing action_{item_id}_place")
            self.assertIn(f"info_{item_id}_nearby", all_ids, f"missing info_{item_id}_nearby")

    def test_all_decor_thoughts_are_internal_id_keyed_not_display_name(self):
        """Regression guard for the original F-system diagnosis concern:
        confirm no THOUGHT_ENTRIES id or required_item ever uses a Chinese
        display name (e.g. "風車") instead of the internal id ("fountain")."""
        display_names = set(TOOL_NAMES.values())
        for e in THOUGHT_ENTRIES:
            req = e.get("required_item")
            reqs = req if isinstance(req, (list, tuple, set)) else ([req] if req else [])
            for r in reqs:
                self.assertNotIn(r, display_names, f"THOUGHT_ENTRIES entry {e['id']} uses a display name as required_item")


if __name__ == '__main__':
    unittest.main()
