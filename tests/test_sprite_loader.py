"""Unit tests for SpriteLoader.get_sprite_region() -- the new arbitrary-
pixel-rect extraction helper added to fix the fruit_tree bug (see
test_landscape_consistency.py's TestSpriteSliceBoundsAreWithinSheetRealDimensions
for the full story: a _register_sprite row/col call landed on row=5 of a
sheet that only has 4 valid rows, was silently returning None forever).

These seed SpriteLoader's image cache directly with a fake Surface,
bypassing real file I/O (the sandboxed test pygame stub at
PYTHONPATH=/tmp/pygame_stub can't load real PNGs) -- get_sprite_region()
calls self.get_image(filename), which finds the cache already populated
and skips loading entirely, so the actual rect-extraction and bounds-
checking logic under test runs exactly as it would against a real sheet.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
from src.sprite_loader import SpriteLoader


class TestGetSpriteRegion(unittest.TestCase):
    def setUp(self):
        self.loader = SpriteLoader()
        self.loader.cache["image_fake_sheet.png"] = pygame.Surface((192, 128))

    def test_returns_none_for_a_file_that_does_not_exist(self):
        self.assertIsNone(self.loader.get_sprite_region("this_file_does_not_exist.png", 0, 0, 10, 10))

    def test_extracts_a_rect_fully_inside_the_sheet(self):
        # The exact rect used for the fixed fruit_tree registration.
        region = self.loader.get_sprite_region("fake_sheet.png", 0, 80, 32, 32)
        self.assertIsNotNone(region)
        self.assertEqual(region.get_size(), (32, 32))

    def test_scales_to_target_size_when_given(self):
        region = self.loader.get_sprite_region("fake_sheet.png", 0, 80, 32, 32, target_size=(100, 100))
        self.assertEqual(region.get_size(), (100, 100))

    def test_a_rect_exactly_flush_with_the_sheet_edge_is_in_bounds_not_rejected(self):
        # x+w == sheet_w / y+h == sheet_h must NOT be treated as "exceeds
        # bounds" -- this is exactly the fruit_tree shape (0,80,32,32) on a
        # sheet that is 192 wide and 112 tall would be flush on the right
        # edge at x=160.
        region = self.loader.get_sprite_region("fake_sheet.png", 160, 0, 32, 128)
        self.assertIsNotNone(region)

    def test_returns_none_when_rect_exceeds_sheet_width(self):
        self.assertIsNone(self.loader.get_sprite_region("fake_sheet.png", 170, 0, 32, 32))

    def test_returns_none_when_rect_exceeds_sheet_height(self):
        self.assertIsNone(self.loader.get_sprite_region("fake_sheet.png", 0, 110, 32, 32))

    def test_returns_none_for_negative_x_or_y(self):
        self.assertIsNone(self.loader.get_sprite_region("fake_sheet.png", -1, 0, 20, 20))
        self.assertIsNone(self.loader.get_sprite_region("fake_sheet.png", 0, -1, 20, 20))

    def test_returns_none_for_non_positive_width_or_height(self):
        self.assertIsNone(self.loader.get_sprite_region("fake_sheet.png", 0, 0, 0, 20))
        self.assertIsNone(self.loader.get_sprite_region("fake_sheet.png", 0, 0, 20, 0))

    def test_only_loads_the_sheet_once_regardless_of_how_many_regions_are_cut(self):
        """Reuses get_image()'s cache -- cutting multiple regions out of the
        same sheet (as stump/fruit_tree do) must not reload the file."""
        self.loader.get_sprite_region("fake_sheet.png", 0, 0, 16, 16)
        self.loader.get_sprite_region("fake_sheet.png", 16, 0, 16, 16)
        self.loader.get_sprite_region("fake_sheet.png", 0, 80, 32, 32)
        self.assertEqual(len(self.loader.cache), 1, "expected exactly one cache entry for the shared sheet")


if __name__ == '__main__':
    unittest.main()
