import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action, is_terminal, FENCE_MAX_HP

class TestCapstoneContract(unittest.TestCase):
    def test_new_game(self):
        state = new_game()
        self.assertEqual(state["day_count"], 1)
        self.assertEqual(state["phase"], "day")
        self.assertEqual(state["money"], 500)
        self.assertTrue("inventory" in state)
        # Farm and decor are two independent maps living under their own keys.
        self.assertEqual(len(state["farm"]["crops"]), 0)
        self.assertEqual(len(state["decor"]["decorations"]), 0)
        # Uncapped lifetime stat starts at zero and only ever goes up.
        self.assertEqual(state["enemies_defeated"], 0)

    def test_plant_crop(self):
        state = new_game()
        # apply_action defaults to zone="farm", so these don't need an explicit zone.
        # Create farmland at (50, 50) => 5_5
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertIn((5, 5), state["farm"]["farmland"])

        # Plant a radish
        state = apply_action(state, "plant_crop_radish_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")

        self.assertIn((5, 5), state["farm"]["crops"])
        self.assertEqual(state["farm"]["crop_data"][(5, 5)]["type"], "radish")
        self.assertEqual(state["farm"]["crop_data"][(5, 5)]["stage"], 0)
        self.assertEqual(state["money"], 500 - 30)

    def test_insufficient_funds_plant_crop(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state["money"] = 10
        # Try to plant a radish (costs 30)
        state = apply_action(state, "plant_crop_radish_5_5")
        self.assertNotIn((5, 5), state["farm"]["crops"])
        self.assertEqual(state["money"], 10)

    def test_build_fence(self):
        state = new_game()
        state = apply_action(state, "build_fence_0_0")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")

        fences = state["farm"].get("fences", [])
        self.assertEqual(len(fences), 1)
        self.assertEqual(fences[0][0], 0)
        self.assertEqual(fences[0][1], 0)
        self.assertEqual(fences[0][2], FENCE_MAX_HP)  # V2: fences now have real HP, not a 3-hit counter
        self.assertEqual(state["money"], 500 - 20)

    def test_harvest_crop(self):
        state = new_game()
        state["farm"]["crops"].append((5, 5))
        state["farm"]["crop_data"][(5, 5)] = {"type": "radish", "stage": 5, "max_stage": 5, "watered": False, "fertilized": False}

        # Harvest with scythe
        state = apply_action(state, "use_scythe_5_5")

        self.assertNotIn((5, 5), state["farm"]["crops"])
        total_radishes = sum(state["inventory"]["radish"].values())
        self.assertEqual(total_radishes, 1)

    def test_night_tick_thief_spawns(self):
        state = new_game()
        state["day_count"] = 2  # Make sure thief spawns
        state = apply_action(state, "start_night")
        state["farm"]["thief_spawn_cooldown"] = 0

        state = apply_action(state, "night_tick")

        self.assertIsNotNone(state["farm"]["thief_pos"])

    def test_tool_validation_shovel(self):
        state = new_game()
        # Shovel on a tree should fail
        if state["farm"]["trees"]:
            tx, ty = state["farm"]["trees"][0]
            action = f"use_shovel_{tx}_{ty}"
            state = apply_action(state, action)
            self.assertIn((tx, ty), state["farm"]["trees"]) # Tree should not be removed
            self.assertIn("無法用鐵鏟移除", state.get("last_msg", ""))

    def test_tool_validation_hoe(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")

        # Try to hoe again on the same farmland spot
        state = apply_action(state, "use_hoe_5_5")
        # Should not append another farmland task
        tasks = [t for t in state["farm"]["building_tasks"] if t["type"] == "farmland" and t["pos"] == (5, 5)]
        self.assertEqual(len(tasks), 0) # Ignored because it's already farmland

    def test_thief_and_trap(self):
        state = new_game()
        state = apply_action(state, "place_trap_1_1")
        state = apply_action(state, "tick") # traps take 1 tick to build
        self.assertIn((1, 1), state["farm"]["traps"])

        # Force a thief to spawn on the trap
        state["day_count"] = 2
        state = apply_action(state, "start_night")
        state["farm"]["thief_spawn_cooldown"] = 0
        state = apply_action(state, "night_tick")

        # Manually move thief to trap
        state["farm"]["thief_pos"] = (1, 1)
        state = apply_action(state, "night_tick") # This tick should trigger the trap damage

        self.assertEqual(state["farm"]["thief_hp"], 0)
        self.assertNotIn((1, 1), state["farm"]["traps"]) # Trap is consumed

    def test_dog_defense(self):
        state = new_game()
        # Give free dog
        state["free_dog"] = True
        state = apply_action(state, "place_dog_2_2")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertIn((2, 2), state["farm"]["dogs"])

        # Spawn thief
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (2, 2)
        state["farm"]["thief_hp"] = 3
        state["farm"]["thief_iframes"] = 0

        # Night tick should cause the dog to move toward the thief or attack
        state = apply_action(state, "night_tick")
        # If dog is close, it attacks and gives thief iframes
        self.assertTrue(state["farm"].get("thief_iframes", 0) > 0 or state["farm"]["thief_pos"] != (2, 2))

    def test_prosperity_and_level_up(self):
        state = new_game()
        initial_level = state["farm_level"]

        # Build a stone_path -- decor actions need zone="decor" explicitly,
        # since apply_action defaults to zone="farm".
        state = apply_action(state, "build_decor_stone_path_60_10", zone="decor")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")

        # Decor should increase prosperity score
        self.assertTrue(state["prosperity_score"] > 0)

        # Force prosperity to level 3 threshold by manually adding 3 fountains
        state["decor"]["decorations"].extend([
            (60, 11, "fountain", 3),
            (60, 12, "fountain", 3),
            (60, 13, "fountain", 3)
        ])

        # Build one more decor to trigger the recalculation
        state["money"] = 1000
        state = apply_action(state, "build_decor_flower_60_14", zone="decor")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")

        self.assertGreater(state["farm_level"], initial_level)
        self.assertEqual(state["farm_level"], 3)

    def test_use_fertilizer(self):
        state = new_game()
        state["farm"]["crops"].append((1, 1))
        state["farm"]["crop_data"][(1, 1)] = {"type": "radish", "stage": 0, "max_stage": 5, "watered": False, "fertilized": False}

        # Use fertilizer
        state = apply_action(state, "use_fertilizer_1_1")
        self.assertTrue(state["farm"]["crop_data"][(1, 1)]["fertilized"])

        # Fertilizer should speed up growth (stage incremented by 2 instead of 1) during night transition
        state = apply_action(state, "start_night")
        self.assertEqual(state["farm"]["crop_data"][(1, 1)]["stage"], 2)

    def test_use_shovel_to_remove(self):
        state = new_game()
        state["farm"]["crops"].append((2, 2))
        state["farm"]["crop_data"][(2, 2)] = {"type": "radish"}
        state["farm"]["fences"].append((3, 3, 3))
        state["farm"]["traps"].append((4, 4))
        state["farm"]["dogs"].append((5, 5))
        state["decor"]["decorations"].append((6, 6, "stone_path", 3))

        # Test shovel removing different items
        state = apply_action(state, "use_shovel_2_2")
        self.assertNotIn((2, 2), state["farm"]["crops"])

        state = apply_action(state, "use_shovel_3_3")
        self.assertEqual(len(state["farm"]["fences"]), 0)

        state = apply_action(state, "use_shovel_4_4")
        self.assertNotIn((4, 4), state["farm"]["traps"])

        state = apply_action(state, "use_shovel_5_5")
        self.assertNotIn((5, 5), state["farm"]["dogs"])

        # Decoration lives in the decor map, so this shovel use needs zone="decor".
        state = apply_action(state, "use_shovel_6_6", zone="decor")
        self.assertEqual(len(state["decor"]["decorations"]), 0)

    def test_thief_stealing_crop(self):
        state = new_game()
        state["farm"]["crops"].append((10, 10))
        state["farm"]["crop_data"][(10, 10)] = {"type": "radish", "stage": 3, "max_stage": 5}

        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)
        state["farm"]["thief_hp"] = 3
        state["farm"]["target_crop"] = (10, 10)

        # Night tick should cause thief to steal crop (removes it entirely)
        state = apply_action(state, "night_tick")

        # Crop removed
        self.assertNotIn((10, 10), state["farm"]["crops"])

    def test_thief_detours_around_a_single_isolated_fence(self):
        # V2 behavior: a lone fence cell with open ground on either side is
        # exactly the case the thief should route around rather than fight
        # through -- see tests/test_fence_combat.py for the "genuinely
        # walled in -> attacks" case instead.
        state = new_game()
        state["farm"]["fences"].append((10, 10, FENCE_MAX_HP))  # Fence at grid (10,10)
        state["farm"]["crops"].append((15, 15))      # Crop target

        state["phase"] = "night"
        # Thief is at grid (9.5, 10), moving to (15, 15).
        # Fence is at grid (10, 10). Width is ITEM_SIZE=10.
        state["farm"]["thief_pos"] = (9.5, 10)        # Overlaps with (10, 10)
        state["farm"]["thief_path"] = [(15, 15)]    # Pathing towards crop
        state["farm"]["thief_hp"] = 3
        state["farm"]["target_crop"] = (15, 15)

        # Night tick should cause the thief to look for a way around
        # instead of immediately attacking.
        state = apply_action(state, "night_tick")

        self.assertEqual(state["farm"]["fences"][0][2], FENCE_MAX_HP)  # untouched
        self.assertEqual(state["farm"]["thief_ai_state"], "moving")

    def test_boar_attacking_decor(self):
        # V1.1 balance fix: decorations were always created with hp=3 but
        # the boar used to ignore it and destroy whatever it arrived at in
        # a single hit. Now it lands the same kind of cooldown-gated,
        # gradual damage the thief lands on fences -- see
        # capstone_contract.py's DECOR_MAX_HP / DECOR_DAMAGE_PER_HIT /
        # DECOR_ATTACK_INTERVAL_TICKS and the "attacking decor" branch of
        # _night_tick_boar.
        state = new_game()
        state["day_count"] = 5  # Boars start spawning day 5
        state["decor"]["decorations"].append((10, 10, "stone_path", 3))

        state["phase"] = "night"
        state["decor"]["boar_pos"] = (10, 10)
        state["decor"]["boar_hp"] = 5
        state["decor"]["target_decor"] = (10, 10)

        # night_tick's "both zones are quiet -> end the night early"
        # shortcut (see apply_action) would otherwise fire the moment the
        # farm zone's default thief (untouched by this test, but still
        # live in `state`) finishes its own spawn/despawn cycle against an
        # empty farm with no crops to steal -- ending the whole night
        # (state["phase"] flips back to "day") long before the collapse
        # animation below has had time to count down, and silently freezing
        # every decor-side assertion after that point. Keeping the farm
        # zone perpetually "still trying to spawn" sidesteps that shortcut
        # so this test can keep advancing night_tick for as long as it
        # needs, independent of decor's own state.
        state["farm"]["max_thieves"] = 999999

        # First tick: boar is already standing on its target with cooldown
        # 0, so the first hit lands immediately (mirrors the thief's
        # attacking_fence "first hit lands almost immediately" timing) --
        # hp 3 -> 2, not yet destroyed.
        state = apply_action(state, "night_tick")
        decor_match = next(d for d in state["decor"]["decorations"] if d[0] == 10 and d[1] == 10)
        self.assertEqual(decor_match[3], 2)
        self.assertEqual(len(state["decor"]["collapsing_decorations"]), 0)

        # Keep ticking through the cooldown-gated hits until it's actually
        # destroyed -- a generous cap so a regression can't hang the test.
        destroyed = False
        for _ in range(200):
            state = apply_action(state, "night_tick")
            if not any(d[0] == 10 and d[1] == 10 for d in state["decor"]["decorations"]):
                destroyed = True
                break
        self.assertTrue(destroyed, "the decoration should eventually be destroyed")

        # Destroyed decorations don't just vanish -- they linger in
        # collapsing_decorations for their collapse animation first, then
        # actually disappear once that countdown runs out.
        collapsing = [c for c in state["decor"]["collapsing_decorations"] if c[0] == 10 and c[1] == 10]
        self.assertEqual(len(collapsing), 1)
        ticks_left = collapsing[0][3]
        for _ in range(ticks_left + 2):
            state = apply_action(state, "night_tick")
        self.assertEqual(
            [c for c in state["decor"]["collapsing_decorations"] if c[0] == 10 and c[1] == 10], []
        )

    def test_click_enemy_damage(self):
        state = new_game()
        state["phase"] = "night"

        # Setup Thief (farm map)
        state["farm"]["thief_pos"] = (10, 10)
        state["farm"]["thief_hp"] = 3
        state["farm"]["thief_iframes"] = 0

        # Setup Boar (decor map)
        state["decor"]["boar_pos"] = (20, 20)
        state["decor"]["boar_hp"] = 5
        state["decor"]["boar_iframes"] = 0

        # Attack thief -- click needs zone="farm" since that's the thief's map
        state = apply_action(state, "click_10_10", zone="farm")
        self.assertEqual(state["farm"]["thief_hp"], 2)

        # Attack boar -- click needs zone="decor" since that's the boar's map
        state = apply_action(state, "click_20_20", zone="decor")
        self.assertEqual(state["decor"]["boar_hp"], 4)

    def test_night_end_no_rent_no_game_over(self):
        # Confirmed design decision: rent and Game Over are both removed.
        # A night ending should never touch money and should never be able
        # to end the run, no matter how poor or empty-handed the player is.
        state = new_game()
        state["money"] = 0
        state["day_count"] = 1
        state["phase"] = "night"
        # No crops, no decorations, no money -- the emptiest possible state,
        # which used to be exactly the bankruptcy Game Over trigger.
        state["time_left"] = 0
        state = apply_action(state, "tick")

        # Money is untouched -- there is no rent to deduct anymore.
        self.assertEqual(state["money"], 0)
        # Never ends the run.
        self.assertEqual(state["status"], "playing")
        self.assertFalse(is_terminal(state))
        # Night ends and rolls straight into the next day.
        self.assertEqual(state["phase"], "day")
        self.assertEqual(state["day_count"], 2)
        self.assertEqual(state["time_left"], 120)

    def test_endless_day_progression(self):
        # The player should be able to keep cycling day -> night -> day
        # indefinitely (Day 1, 2, 3, ... 100, ...) with no ending.
        state = new_game()
        for _ in range(10):
            state = apply_action(state, "start_night")
            state["time_left"] = 0
            state = apply_action(state, "tick")
        self.assertEqual(state["day_count"], 11)
        self.assertEqual(state["phase"], "day")
        self.assertEqual(state["status"], "playing")
        self.assertFalse(is_terminal(state))

    def test_enemies_defeated_is_lifetime_and_uncapped(self):
        # The lifetime "累積擊退敵人數" stat should increment on a genuine
        # defeat (hp reaches 0) and never reset across nights.
        # Clicking damages the thief; the defeat itself (removing the thief
        # and incrementing the counter) is finalized on the next night_tick,
        # same as the rest of the thief's HP-reaches-0 handling.
        state = new_game()
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)
        state["farm"]["thief_hp"] = 1
        state["farm"]["thief_iframes"] = 0

        state = apply_action(state, "click_10_10", zone="farm")
        self.assertEqual(state["farm"]["thief_hp"], 0)

        state = apply_action(state, "night_tick")
        self.assertEqual(state["enemies_defeated"], 1)
        self.assertIsNone(state["farm"]["thief_pos"])

        # Ending the night (and starting a new one) must not reset it.
        state["time_left"] = 0
        state = apply_action(state, "tick")
        self.assertEqual(state["enemies_defeated"], 1)

    def test_terminal_state_rejection(self):
        state = new_game()
        state["status"] = "game_over"
        state["money"] = 100

        state = apply_action(state, "use_hoe_10_10")
        # Since game is over, it shouldn't allow building tasks
        self.assertEqual(len(state["farm"]["building_tasks"]), 0)

    def test_invalid_placement(self):
        state = new_game()
        # Crop sits inside a 20x20 room; fences are ITEM_SIZE=10 wide and
        # placed at realistic build-grid (10-unit) positions, same as a
        # real player clicking the hotbar could actually place -- unlike
        # this test's previous version, which used off-grid (5-unit
        # multiple) positions that only "sealed" the crop by exploiting a
        # pathfinding sampling gap. That gap is now fixed (see _is_obstacle
        # -- fence obstacle checks used to be exact-point-equality, which
        # under-detected a fence's real 10-wide footprint at the 5-unit
        # resolution pathfinding samples at); a real 10-unit-spaced ring
        # correctly seals now, which is the whole point of this test.
        state["farm"]["crops"].append((55, 55))

        ring = [
            (40, 40), (50, 40), (60, 40), (70, 40),
            (40, 50), (70, 50),
            (40, 60), (70, 60),
            (40, 70), (50, 70), (60, 70),
        ]
        for pos in ring:
            state = apply_action(state, f"build_fence_{pos[0]}_{pos[1]}")
            state = apply_action(state, "tick")
            state = apply_action(state, "tick")

        # Attempt to place the last piece, sealing the room shut.
        state = apply_action(state, "build_fence_70_70")
        self.assertIn("不能將農田完全封死", state.get("last_msg", ""))

    def test_camera_movement(self):
        import pygame
        from src.input_handler import update_camera

        # Test normal movement
        keys = {pygame.K_d: True}
        cx, cy = update_camera(0, 0, False, (0, 0), keys, 5000, 5000, 800, 600, "farm")
        self.assertEqual(cx, 15)  # Moved right by 15

        # Test mouse drag
        cx, cy = update_camera(100, 100, True, (50, -50), {}, 5000, 5000, 800, 600, "farm")
        self.assertEqual(cx, 50)   # 100 - 50 = 50
        self.assertEqual(cy, 150)  # 100 - (-50) = 150

        # Farm and decor are now independent maps: each camera is clamped to
        # its own zone's FULL world bounds, starting at (0, 0) -- there is no
        # shared halfway line between them anymore.
        cx, cy = update_camera(6000, 0, False, (0, 0), {pygame.K_d: True}, 5000, 5000, 800, 600, "farm")
        self.assertEqual(cx, 4200)  # Clamped to WORLD_W - WIDTH = 5000 - 800 = 4200

        # Decor zone clamps identically and independently -- it is NOT offset
        # to start where the farm zone's range ends, because it isn't sharing
        # a coordinate line with the farm map at all.
        cx, cy = update_camera(6000, 0, False, (0, 0), {pygame.K_d: True}, 5000, 5000, 800, 600, "decor")
        self.assertEqual(cx, 4200)

if __name__ == '__main__':
    unittest.main()
