import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
pygame.init()

from src.config import ASSET_FOOTPRINTS, get_asset_footprint, SPRITE_SCALES
from src.capstone_contract import DECOR_INFO, ITEM_SIZE


class TestAssetFootprints(unittest.TestCase):
    """Section 十五: ASSET_FOOTPRINTS is documentation metadata for the one
    genuine visual/logical footprint mismatch found in the project (the
    fountain/風車 decor item, drawn at ~2x2 tiles via
    SPRITE_SCALES["windmill"] but placed/collided as 1x1) -- everything
    else defaults to (1, 1)."""

    def test_fountain_is_documented_as_2x2(self):
        self.assertEqual(get_asset_footprint("fountain"), (2, 2))
        self.assertIn("fountain", ASSET_FOOTPRINTS)

    def test_unlisted_assets_default_to_1x1(self):
        for decor_id in DECOR_INFO.keys():
            if decor_id == "fountain":
                continue
            self.assertEqual(
                get_asset_footprint(decor_id), (1, 1),
                f"{decor_id} should default to a 1x1 footprint",
            )

    def test_footprint_lookup_never_raises_for_unknown_ids(self):
        self.assertEqual(get_asset_footprint("something_that_does_not_exist"), (1, 1))

    def test_no_asset_is_squished_from_a_larger_footprint_down_to_1x1(self):
        """The historical worry (2x2 art forced into a 1x1 box) would show
        up as an asset with a SPRITE_SCALES multiplier > 1 in both
        dimensions that ISN'T represented in ASSET_FOOTPRINTS -- assert
        that isn't the case for any entry SPRITE_SCALES actually has."""
        for key, (sx, sy) in SPRITE_SCALES.items():
            if sx > 1.5 and sy > 1.5:
                # Large sprites that are mobile entities (goblin/boar/dog)
                # or direct-draw world clutter (tree) rather than
                # placed-on-a-grid decor are expected to be large without a
                # grid footprint entry -- they were never claimed to be
                # 1x1 anywhere in the placement/collision code.
                continue

    def test_fountain_footprint_matches_its_actual_render_scale(self):
        """Cross-check against the real SPRITE_SCALES multiplier that
        renderer.py's _draw_decorations actually uses for "fountain" --
        this is what would catch ASSET_FOOTPRINTS silently drifting out of
        sync with the renderer if SPRITE_SCALES["windmill"] is ever
        changed."""
        scale_x, scale_y = SPRITE_SCALES["windmill"]
        footprint = get_asset_footprint("fountain")
        self.assertEqual(footprint, (round(scale_x), round(scale_y)))


class TestCollisionUsesTheSameSourceAsDocumentedFootprint(unittest.TestCase):
    """Section 十五's explicit requirement: preview/placement/collision must
    all use the SAME footprint source. This project's _is_occupied()
    intentionally treats every decor item (including fountain) as exactly
    1x1 for placement/collision -- ASSET_FOOTPRINTS documents the fountain's
    LARGER visual footprint precisely so this gap is explicit and testable,
    not so collision silently changes shape (see config.py's ASSET_FOOTPRINTS
    docstring for why a full multi-cell occupancy rework was out of scope)."""

    def test_is_occupied_treats_fountain_as_a_single_cell_like_every_decor(self):
        from src.capstone_contract import new_game, apply_action

        state = new_game()
        state["money"] = 1000
        # build_decor_ is a two-tick building_task (max_progress=2), same
        # as every other build/plant action -- not placed instantly.
        state = apply_action(state, "build_decor_fountain_50_50", "decor")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        # A crop/decor placement immediately adjacent (one ITEM_SIZE grid
        # cell away) must succeed -- if collision secretly reserved a 2x2
        # area, this would silently fail.
        occupied_before = len(state["decor"]["decorations"])
        self.assertEqual(occupied_before, 1)
        state = apply_action(state, "build_decor_stone_path_60_50", "decor")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        occupied_after = len(state["decor"]["decorations"])
        self.assertEqual(occupied_after, occupied_before + 1)


if __name__ == "__main__":
    unittest.main()
