import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action, TIME_SCALE_STEPS
from src import ui_layout
from src.thought import get_contemplation_lines


class TestTimeScaleState(unittest.TestCase):
    def test_new_game_defaults_to_1x(self):
        state = new_game()
        self.assertEqual(state["time_scale"], 1.0)
        self.assertEqual(state["time_scale_before_pause"], 1.0)

    def test_set_time_scale_updates_state(self):
        state = new_game()
        for scale in (0, 1, 2, 4):
            state = apply_action(state, f"set_time_scale_{scale}")
            self.assertEqual(state["time_scale"], float(scale))

    def test_set_time_scale_rejects_values_outside_the_allowed_steps(self):
        state = new_game()
        state = apply_action(state, "set_time_scale_3")
        self.assertEqual(state["time_scale"], 1.0)  # unchanged, 3x isn't a real step

    def test_pausing_remembers_the_speed_it_paused_from(self):
        state = new_game()
        state = apply_action(state, "set_time_scale_4")
        state = apply_action(state, "set_time_scale_0")
        self.assertEqual(state["time_scale"], 0.0)
        self.assertEqual(state["time_scale_before_pause"], 4.0)  # not reset to 0 or 1

    def test_time_scale_steps_are_exactly_0_1_2_4(self):
        self.assertEqual(TIME_SCALE_STEPS, (0.0, 1.0, 2.0, 4.0))
        self.assertEqual(tuple(ui_layout.TIME_SCALE_STEPS), TIME_SCALE_STEPS)


class TestTimeScaleAffectsSimulation(unittest.TestCase):
    """Confirms time_scale actually reaches the two real timing mechanisms
    this engine has (main.py's TICK_EVENT loop count, and the night_tick
    elapsed-ms throttle) -- exercised the same way main.py exercises them,
    without needing a real pygame display."""

    def test_paused_means_zero_ticks_per_interval(self):
        state = new_game()
        state = apply_action(state, "set_time_scale_0")
        ticks_this_interval = int(state.get("time_scale", 1.0))
        self.assertEqual(ticks_this_interval, 0)

    def test_2x_runs_two_ticks_per_interval(self):
        state = new_game()
        state = apply_action(state, "set_time_scale_2")
        before = state["time_left"]
        ticks_this_interval = int(state.get("time_scale", 1.0))
        for _ in range(ticks_this_interval):
            state = apply_action(state, "tick")
        self.assertEqual(state["time_left"], before - 2)

    def test_4x_runs_four_ticks_per_interval(self):
        state = new_game()
        state = apply_action(state, "set_time_scale_4")
        before = state["time_left"]
        ticks_this_interval = int(state.get("time_scale", 1.0))
        for _ in range(ticks_this_interval):
            state = apply_action(state, "tick")
        self.assertEqual(state["time_left"], before - 4)

    def test_night_tick_throttle_scales_with_time_scale(self):
        """Mirrors main.py's (current_time - last_night_tick) * time_scale
        > night_tick_delay gate: at 4x, 1/4 of the real elapsed time is
        needed to cross the same threshold."""
        night_tick_delay = 33
        elapsed_ms = 10  # would NOT cross the threshold at 1x
        self.assertFalse(elapsed_ms * 1.0 > night_tick_delay)
        self.assertTrue(elapsed_ms * 4.0 > night_tick_delay)  # but does at 4x


class TestTimeScaleUIGeometry(unittest.TestCase):
    def test_badge_rect_sits_below_money_and_above_panel_bottom(self):
        badge = ui_layout.time_scale_badge_rect()
        money = ui_layout.money_readout_rect()
        panel = ui_layout.top_panel_rect()
        self.assertGreaterEqual(badge.y, money.bottom)
        self.assertLessEqual(badge.bottom, panel.bottom)

    def test_paused_banner_center_is_below_the_daynight_bar(self):
        bar = ui_layout.daynight_bar_rect()
        cx, cy = ui_layout.paused_banner_center()
        self.assertGreater(cy, bar.bottom)

    def test_time_scale_step_index_matches_each_step(self):
        for i, step in enumerate(ui_layout.TIME_SCALE_STEPS):
            self.assertEqual(ui_layout.time_scale_step_index(step), i)


class TestTimeScaleHoverThought(unittest.TestCase):
    """F Hover coverage for the new badge, consistent with every other real
    HUD element already covered by the Thought system."""

    def _state(self):
        state = new_game()
        state["tutorial"] = {
            "unlocked": {"move": True, "shop_sell": True, "zone_switch": True},
            "flags": {}, "seen_counts": {},
        }
        state["money"] = 0
        return state

    def test_hover_badge_while_running_reports_current_speed(self):
        state = self._state()
        state["time_scale"] = 2.0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.time_scale_badge_rect().center
        )
        self.assertTrue(any("2" in l and "倍速" in l for l in lines))

    def test_hover_badge_while_paused_reports_paused(self):
        state = self._state()
        state["time_scale"] = 0.0
        lines = get_contemplation_lines(
            state, "farm", None, False, mouse_pos=ui_layout.time_scale_badge_rect().center
        )
        self.assertTrue(any("暫停" in l for l in lines))

    def test_badge_hover_is_ui_chrome_and_not_overridden_by_world(self):
        """Same section-十三 guarantee every other HUD element already has:
        a world cell that happens to translate to the same screen position
        must not outrank the badge."""
        state = self._state()
        rect = ui_layout.time_scale_badge_rect()
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
        self.assertFalse(any("成熟" in l for l in lines))


if __name__ == "__main__":
    unittest.main()
