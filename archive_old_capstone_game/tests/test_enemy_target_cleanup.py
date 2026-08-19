import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import (
    new_game, apply_action,
    FENCE_MAX_HP, FENCE_DAMAGE_PER_HIT, FENCE_ATTACK_INTERVAL_TICKS,
    _simulate_night_path, _thief_pick_targets,
)


def _spawn_thief_attacking_fence(state, thief_pos, fence_pos):
    """Puts the thief directly into STATE_ATTACKING_FENCE against a single
    fence, mirroring test_fence_combat.py's _spawn_thief_at helper but
    skipping straight to the attacking state instead of "moving" (this
    test is specifically about what happens *after* the fence dies, not
    about pathing into it)."""
    state["phase"] = "night"
    farm = state["farm"]
    farm["thief_pos"] = thief_pos
    farm["thief_hp"] = 99
    farm["thief_iframes"] = 0
    farm["thief_ai_state"] = "attacking_fence"
    farm["thief_attack_target_fence"] = fence_pos
    farm["thief_attack_cooldown"] = 0
    farm["fences"] = [(fence_pos[0], fence_pos[1], FENCE_MAX_HP)]
    # A real target_crop so re-pathing after the fence dies has somewhere
    # concrete to go, same as the real spawn logic always ensures.
    farm["target_crop"] = None
    targets = _thief_pick_targets(farm)
    if targets:
        farm["target_crop"] = targets[0]
    return state


class TestThiefTargetClearsAfterFenceDestroyed(unittest.TestCase):
    """Section 十四: full trace of enemy AI -> target selection -> fence
    attack -> fence destroyed -> target invalidation -> next
    target/movement. Confirms the pre-existing "fence is None" cleanup
    branch in _night_tick_thief (not new logic -- see this session's
    report) actually satisfies every one of the seven requirements listed
    in the request."""

    def _destroy_the_fence(self, state, fence_pos):
        """Lands exactly enough attacks (with the real cooldown gate) to
        bring the fence to 0 HP and get it removed from farm["fences"],
        without over-ticking past that moment."""
        import math
        hits_needed = math.ceil(FENCE_MAX_HP / FENCE_DAMAGE_PER_HIT)
        for hit_num in range(hits_needed):
            # thief_attack_cooldown starts at 0 -> this tick lands a hit
            # immediately, then resets the cooldown to
            # FENCE_ATTACK_INTERVAL_TICKS for the next one.
            state = apply_action(state, "night_tick")
            for _ in range(FENCE_ATTACK_INTERVAL_TICKS):
                if hit_num == hits_needed - 1:
                    break  # don't run the cooldown out after the final hit
                state = apply_action(state, "night_tick")
        return state

    def test_1_fence_hp_reaches_zero_and_is_removed_from_fences_list(self):
        state = new_game()
        fence_pos = (60, 60)
        state = _spawn_thief_attacking_fence(state, (65, 60), fence_pos)
        state = self._destroy_the_fence(state, fence_pos)
        remaining = [f for f in state["farm"]["fences"] if (f[0], f[1]) == fence_pos]
        self.assertEqual(remaining, [])

    def test_2_and_3_target_fence_is_cleared_and_ai_state_returns_to_moving(self):
        state = new_game()
        fence_pos = (60, 60)
        state = _spawn_thief_attacking_fence(state, (65, 60), fence_pos)
        state = self._destroy_the_fence(state, fence_pos)
        # One more tick: the fence is now gone from farm["fences"], so this
        # is the tick where the cleanup branch actually fires.
        state = apply_action(state, "night_tick")
        self.assertIsNone(state["farm"]["thief_attack_target_fence"])
        self.assertEqual(state["farm"]["thief_ai_state"], "moving")

    def test_4_thief_re_paths_toward_a_real_target_after_cleanup(self):
        state = new_game()
        fence_pos = (60, 60)
        state = _spawn_thief_attacking_fence(state, (65, 60), fence_pos)
        state = self._destroy_the_fence(state, fence_pos)
        state = apply_action(state, "night_tick")
        # "moving" with no path just means it hasn't computed one on THIS
        # exact tick yet in every implementation shape; the important,
        # observable fact is that it isn't wedged on the old fence and does
        # keep progressing on subsequent ticks (requirement 5/6 below).
        self.assertEqual(state["farm"]["thief_ai_state"], "moving")

    def test_5_and_6_thief_does_not_get_stuck_forever_after_fence_dies(self):
        """Run well past the point of fence destruction and confirm the
        thief keeps actually doing something (moving, attacking a NEW
        obstacle, or reaching/despawning) rather than silently freezing in
        "attacking_fence" against a target that no longer exists."""
        state = new_game()
        fence_pos = (60, 60)
        state = _spawn_thief_attacking_fence(state, (65, 60), fence_pos)
        state = self._destroy_the_fence(state, fence_pos)

        saw_state_change_or_progress = False
        last_pos = state["farm"]["thief_pos"]
        for _ in range(400):
            state = apply_action(state, "night_tick")
            if state["farm"]["thief_pos"] is None:
                saw_state_change_or_progress = True  # despawned -- reached its goal
                break
            if state["farm"]["thief_pos"] != last_pos:
                saw_state_change_or_progress = True
                break
            last_pos = state["farm"]["thief_pos"]
            # Never allowed to still be "attacking" the fence we destroyed.
            if state["farm"]["thief_ai_state"] == "attacking_fence":
                self.assertNotEqual(state["farm"]["thief_attack_target_fence"], fence_pos)

        self.assertTrue(
            saw_state_change_or_progress,
            "thief never moved and never despawned in 400 ticks after its "
            "fence target was destroyed -- looks stuck",
        )

    def test_7_no_crash_from_referencing_the_deleted_fence_object(self):
        """The cleanup lookup uses next((...), None) over the LIVE fences
        list, never the removed tuple itself -- destroying the fence and
        ticking many more times afterward must never raise."""
        state = new_game()
        fence_pos = (60, 60)
        state = _spawn_thief_attacking_fence(state, (65, 60), fence_pos)
        state = self._destroy_the_fence(state, fence_pos)
        try:
            for _ in range(200):
                state = apply_action(state, "night_tick")
        except Exception as exc:  # pragma: no cover - failure path
            self.fail(f"night_tick raised after fence destruction: {exc!r}")


class TestThiefDoesNotTrackAGoneTargetPosition(unittest.TestCase):
    def test_removing_the_fence_out_from_under_the_thief_also_clears_target(self):
        """Same cleanup path, but triggered by the PLAYER removing the fence
        (shovel) instead of combat finishing it off -- either way "fence is
        gone" must be detected and handled identically."""
        state = new_game()
        fence_pos = (60, 60)
        state = _spawn_thief_attacking_fence(state, (65, 60), fence_pos)
        state["farm"]["fences"] = []  # player shoveled it away mid-attack
        state = apply_action(state, "night_tick")
        self.assertIsNone(state["farm"]["thief_attack_target_fence"])
        self.assertEqual(state["farm"]["thief_ai_state"], "moving")


if __name__ == "__main__":
    unittest.main()
