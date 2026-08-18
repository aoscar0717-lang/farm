import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import (
    new_game, apply_action, fence_damage_state,
    FENCE_MAX_HP, FENCE_DAMAGE_PER_HIT, FENCE_ATTACK_INTERVAL_TICKS,
    BOAR_FENCE_DAMAGE_PER_HIT, BOAR_FENCE_ATTACK_INTERVAL_TICKS,
    _simulate_night_path, _thief_pick_targets,
)


def _build_sealed_room(state, crop_pos=(55, 55)):
    """A crop in a fully-enclosed 20x20 room made of realistic, 10-unit-
    build-grid fences -- the thief has no possible detour and must
    eventually attack. Mirrors tests/test_contract.py's
    test_invalid_placement ring, minus the piece that would make the
    engine itself reject the last placement (we want it complete here)."""
    state["farm"]["crops"].append(crop_pos)
    state["farm"]["crop_data"][crop_pos] = {
        "type": "radish", "stage": 5, "max_stage": 5, "fertilized": False, "growth_timer": 0,
    }
    ring = [
        (40, 40), (50, 40), (60, 40), (70, 40),
        (40, 50), (70, 50),
        (40, 60), (70, 60),
        (40, 70), (50, 70), (60, 70), (70, 70),
    ]
    for pos in ring:
        state["farm"]["fences"].append((pos[0], pos[1], FENCE_MAX_HP))
    return state


def _spawn_thief_at(state, pos):
    """Mirrors what real spawn logic does (see _night_tick_thief's spawn
    branch) but at a hand-picked position: sets AI state to "moving" and
    computes a real path/target via the same helpers the game itself uses,
    instead of leaving thief_path/target_crop at their new_game() defaults
    ([] / None) -- an empty path with no target_crop makes the thief think
    it has already arrived (see the "STATE_MOVING, no path" branch), which
    just despawns it instantly rather than exercising the fence-encounter
    logic these tests are actually about."""
    state["phase"] = "night"
    farm = state["farm"]
    farm["thief_pos"] = pos
    farm["thief_hp"] = 99  # don't let the thief die mid-test
    farm["thief_ai_state"] = "moving"
    farm["thief_attack_cooldown"] = 0
    farm["thief_attack_target_fence"] = None
    targets = _thief_pick_targets(farm)
    farm["thief_path"], farm["target_crop"] = _simulate_night_path(farm, pos, targets)
    return state


class TestFenceHPAndCooldown(unittest.TestCase):
    """Scenarios 1 & 2 from the request: a thief attacking a fence it can't
    get around should hit it roughly once a second for 8 damage, not every
    frame, and should take roughly 12.5s (100 HP / 8 dmg/hit @ 1 hit/s) to
    bring it down."""

    def test_1_and_2_full_wall_takes_about_12_point_5_seconds_with_gated_damage(self):
        state = new_game()
        state = _build_sealed_room(state)
        state = _spawn_thief_at(state, (65, 40))  # right up against the top wall

        hp_history = []
        ticks = 0
        max_ticks = 2000  # generous safety cap so a bug can't hang the test
        target_fence_gone = False
        while ticks < max_ticks:
            state = apply_action(state, "night_tick")
            ticks += 1
            fence = next((f for f in state["farm"]["fences"] if f[0] == 60 and f[1] == 40), None)
            if fence is not None:
                hp_history.append(fence[2])
            elif hp_history:  # was present, now gone -> destroyed
                target_fence_gone = True
                break

        self.assertTrue(target_fence_gone, "the targeted fence should eventually be destroyed")

        # HP must never go negative-looking or jump by more than one hit's
        # worth, and must actually decrease (not stay flat / not vanish
        # instantly).
        self.assertGreater(len(hp_history), 1)
        for prev, cur in zip(hp_history, hp_history[1:]):
            self.assertIn(cur, (prev, prev - FENCE_DAMAGE_PER_HIT))

        # Damage must be cooldown-gated, not per-frame: with 30 ticks/hit
        # and 100 HP, there's no way it drops on every single tick.
        unchanged_ticks = sum(1 for prev, cur in zip(hp_history, hp_history[1:]) if cur == prev)
        self.assertGreater(unchanged_ticks, 0)

        # ~12.5s at 30 ticks/sec (main.py's night_tick cadence) is ~375
        # ticks; allow a generous window since the first hit lands almost
        # immediately rather than after a full interval.
        self.assertGreater(ticks, 300)
        self.assertLess(ticks, 450)

    def test_no_damage_before_the_first_cooldown_elapses(self):
        state = new_game()
        state = _build_sealed_room(state)
        state = _spawn_thief_at(state, (65, 40))

        # First tick: still "moving", detects the blockage, fails to
        # detour (fully sealed room), transitions to attacking_fence with
        # cooldown 0 -- no hit lands on *this* tick.
        state = apply_action(state, "night_tick")
        self.assertEqual(state["farm"]["thief_ai_state"], "attacking_fence")
        fence = next(f for f in state["farm"]["fences"] if f[0] == 60 and f[1] == 40)
        self.assertEqual(fence[2], FENCE_MAX_HP)

        # Second tick: cooldown was 0 -> the first hit lands now.
        state = apply_action(state, "night_tick")
        fence = next(f for f in state["farm"]["fences"] if f[0] == 60 and f[1] == 40)
        self.assertEqual(fence[2], FENCE_MAX_HP - FENCE_DAMAGE_PER_HIT)

        # Third tick: cooldown was just reset to FENCE_ATTACK_INTERVAL_TICKS
        # -- no second hit yet.
        state = apply_action(state, "night_tick")
        fence = next(f for f in state["farm"]["fences"] if f[0] == 60 and f[1] == 40)
        self.assertEqual(fence[2], FENCE_MAX_HP - FENCE_DAMAGE_PER_HIT)


class TestFenceDamageVisualTiers(unittest.TestCase):
    """Scenario 3: intact -> damaged -> critical thresholds. Pure function,
    no rendering needed -- renderer.py calls this same helper."""

    def test_thresholds(self):
        self.assertEqual(fence_damage_state(100), "intact")
        self.assertEqual(fence_damage_state(60), "intact")
        self.assertEqual(fence_damage_state(59), "damaged")
        self.assertEqual(fence_damage_state(30), "damaged")
        self.assertEqual(fence_damage_state(29), "critical")
        self.assertEqual(fence_damage_state(1), "critical")


class TestThiefDetourBehavior(unittest.TestCase):
    """Scenarios 4 & 5: detour when possible, attack only when truly
    boxed in. (Scenario 6, limiting concurrent attackers per fence, is
    skipped here -- the farm zone only ever has one thief active at a
    time (thief_pos is a single point, not a list), so "10 goblins piling
    on one fence" can't happen with the current architecture. Confirmed
    with the user to leave this for a future multi-thief architecture
    change rather than force it into V2.)"""

    def test_4_detours_when_a_side_route_exists(self):
        state = new_game()
        state["farm"]["fences"].append((10, 10, FENCE_MAX_HP))
        state["farm"]["crops"].append((15, 15))
        state = _spawn_thief_at(state, (9.5, 10))
        state["farm"]["thief_path"] = [(15, 15)]
        state["farm"]["target_crop"] = (15, 15)

        state = apply_action(state, "night_tick")

        self.assertEqual(state["farm"]["fences"][0][2], FENCE_MAX_HP)  # untouched
        self.assertEqual(state["farm"]["thief_ai_state"], "moving")

    def test_5_attacks_once_truly_boxed_in(self):
        state = new_game()
        state = _build_sealed_room(state)
        state = _spawn_thief_at(state, (65, 40))
        # No thief_path set -- spawn logic isn't used here (we're injecting
        # the thief directly), so drive one movement tick to establish it
        # via the normal path-following code, same as test_1_and_2 does.
        # Instead, set a path heading straight at the wall to mirror how a
        # real path-follow would arrive here.
        state["farm"]["thief_path"] = [(65, 40)]
        state["farm"]["target_crop"] = (55, 55)

        for _ in range(5):
            state = apply_action(state, "night_tick")
            if state["farm"]["thief_ai_state"] == "attacking_fence":
                break

        self.assertEqual(state["farm"]["thief_ai_state"], "attacking_fence")
        self.assertIsNotNone(state["farm"]["thief_attack_target_fence"])


class TestFenceCollapseAnimation(unittest.TestCase):
    """Scenario 7: destroyed fences don't vanish the instant HP hits 0."""

    def test_destroyed_fence_lingers_for_the_collapse_animation_then_is_removed(self):
        state = new_game()
        state = _build_sealed_room(state)
        state = _spawn_thief_at(state, (65, 40))

        # Force the targeted fence down to a sliver of HP so the very next
        # landed hit finishes it off, without looping through the whole
        # ~12.5s fight.
        state["farm"]["fences"] = [
            (60, 40, 1) if f[0] == 60 and f[1] == 40 else f
            for f in state["farm"]["fences"]
        ]

        state = apply_action(state, "night_tick")  # -> attacking_fence, cooldown 0
        state = apply_action(state, "night_tick")  # first hit lands, HP 1 - 8 <= 0

        self.assertIsNone(next((f for f in state["farm"]["fences"] if f[0] == 60 and f[1] == 40), None))
        collapsing = [c for c in state["farm"]["collapsing_fences"] if c[0] == 60 and c[1] == 40]
        self.assertEqual(len(collapsing), 1)
        ticks_left = collapsing[0][2]
        self.assertGreater(ticks_left, 0)

        # Advance through the collapse animation -- the entry should
        # count down and eventually disappear from collapsing_fences too.
        for _ in range(ticks_left + 2):
            state = apply_action(state, "night_tick")

        self.assertEqual(
            [c for c in state["farm"]["collapsing_fences"] if c[0] == 60 and c[1] == 40],
            [],
        )


class TestBoarFenceCooldown(unittest.TestCase):
    """V1.1 balance fix, user-requested test scenarios 7 & 8: the boar's
    fence attack used to have no cooldown at all (a flat -1 dmg on every
    uncooled tick it stayed blocked), taking a 100 HP fence down in ~3.3
    seconds -- almost 4x faster than the thief's post-rework ~12.5s. It now
    gates damage behind the same kind of cooldown the thief already has,
    using the boar's own existing per-hit damage value (1) unchanged, per
    the explicit instruction not to touch damage numbers this round."""

    def _boar_at_fence(self):
        state = new_game()
        state["phase"] = "night"
        decor = state["decor"]
        decor["fences"].append((60, 40, FENCE_MAX_HP))
        decor["boar_pos"] = (65, 40)  # touching the fence, like the thief tests
        decor["boar_hp"] = 99  # don't let the boar die mid-test
        decor["boar_iframes"] = 0
        decor["boar_attack_cooldown"] = 0
        decor["boar_path"] = [(65, 60)]  # straight through the fence
        return state

    def _fence_hp(self, state):
        return next(f for f in state["decor"]["fences"] if f[0] == 60 and f[1] == 40)[2]

    def test_7_boar_fence_damage_is_gated_not_per_tick(self):
        state = self._boar_at_fence()

        # First tick: cooldown starts at 0, so the first hit lands right
        # away (same "first hit is immediate" timing the thief has).
        state = apply_action(state, "night_tick")
        self.assertEqual(self._fence_hp(state), FENCE_MAX_HP - BOAR_FENCE_DAMAGE_PER_HIT)

        # The next two ticks land inside the freshly-reset cooldown window
        # -- no more damage yet. This is the actual regression check: the
        # old bug would have kept subtracting 1 on every single one of
        # these instead.
        state = apply_action(state, "night_tick")
        state = apply_action(state, "night_tick")
        self.assertEqual(self._fence_hp(state), FENCE_MAX_HP - BOAR_FENCE_DAMAGE_PER_HIT)

    def test_8_full_wall_is_nowhere_close_to_destroyed_after_a_few_seconds(self):
        state = self._boar_at_fence()

        # 150 ticks is ~5 seconds at this file's ~30 ticks/sec cadence --
        # comfortably past the ~3.3s the old uncooled bug needed to fully
        # destroy a 100 HP fence. With the cooldown fix, only a handful of
        # hits should have landed by then.
        for _ in range(150):
            state = apply_action(state, "night_tick")
        hp = self._fence_hp(state)
        self.assertGreater(hp, FENCE_MAX_HP - 10)  # nowhere near destroyed
        self.assertLess(hp, FENCE_MAX_HP)  # but it *is* still taking damage


if __name__ == '__main__':
    unittest.main()
