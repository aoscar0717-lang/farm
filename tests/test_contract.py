import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action

class TestCapstoneContract(unittest.TestCase):
    def test_new_game(self):
        state = new_game()
        self.assertEqual(state["day_count"], 1)
        self.assertEqual(state["phase"], "day")
        self.assertEqual(state["money"], 500)
        self.assertTrue("inventory" in state)
        self.assertEqual(len(state["crops"]), 0)

    def test_plant_crop(self):
        state = new_game()
        # Create farmland at (50, 50) => 5_5
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertIn((5, 5), state["farmland"])
        
        # Plant a radish
        state = apply_action(state, "plant_crop_radish_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        
        self.assertIn((5, 5), state["crops"])
        self.assertEqual(state["crop_data"][(5, 5)]["type"], "radish")
        self.assertEqual(state["crop_data"][(5, 5)]["stage"], 0)
        self.assertEqual(state["money"], 500 - 30)

    def test_insufficient_funds_plant_crop(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state["money"] = 10
        # Try to plant a radish (costs 30)
        state = apply_action(state, "plant_crop_radish_5_5")
        self.assertNotIn((5, 5), state["crops"])
        self.assertEqual(state["money"], 10)

    def test_build_fence(self):
        state = new_game()
        state = apply_action(state, "build_fence_0_0")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        
        fences = state.get("fences", [])
        self.assertEqual(len(fences), 1)
        self.assertEqual(fences[0][0], 0)
        self.assertEqual(fences[0][1], 0)
        self.assertEqual(fences[0][2], 3) # Max HP is 3
        self.assertEqual(state["money"], 500 - 20)

    def test_harvest_crop(self):
        state = new_game()
        state["crops"].append((5, 5))
        state["crop_data"][(5, 5)] = {"type": "radish", "stage": 5, "max_stage": 5, "watered": False, "fertilized": False}
        
        # Harvest with scythe
        state = apply_action(state, "use_scythe_5_5")
        
        self.assertNotIn((5, 5), state["crops"])
        total_radishes = sum(state["inventory"]["radish"].values())
        self.assertEqual(total_radishes, 1)

    def test_night_tick_thief_spawns(self):
        state = new_game()
        state["day_count"] = 2  # Make sure thief spawns
        state = apply_action(state, "start_night")
        state["thief_spawn_cooldown"] = 0
        
        state = apply_action(state, "night_tick")
        
        self.assertIsNotNone(state["thief_pos"])
        
    def test_tool_validation_shovel(self):
        state = new_game()
        # Shovel on a tree should fail
        if state["trees"]:
            tx, ty = state["trees"][0]
            action = f"use_shovel_{tx}_{ty}"
            state = apply_action(state, action)
            self.assertIn((tx, ty), state["trees"]) # Tree should not be removed
            self.assertIn("無法用鐵鏟移除", state.get("last_msg", ""))

    def test_tool_validation_hoe(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        
        # Try to hoe again on the same farmland spot
        state = apply_action(state, "use_hoe_5_5")
        # Should not append another farmland task
        tasks = [t for t in state["building_tasks"] if t["type"] == "farmland" and t["pos"] == (5, 5)]
        self.assertEqual(len(tasks), 0) # Ignored because it's already farmland

    def test_thief_and_trap(self):
        state = new_game()
        state = apply_action(state, "place_trap_1_1")
        state = apply_action(state, "tick") # traps take 1 tick to build
        self.assertIn((1, 1), state["traps"])
        
        # Force a thief to spawn on the trap
        state["day_count"] = 2
        state = apply_action(state, "start_night")
        state["thief_spawn_cooldown"] = 0
        state = apply_action(state, "night_tick")
        
        # Manually move thief to trap
        state["thief_pos"] = (1, 1)
        state = apply_action(state, "night_tick") # This tick should trigger the trap damage
        
        self.assertEqual(state["thief_hp"], 0)
        self.assertNotIn((1, 1), state["traps"]) # Trap is consumed

    def test_dog_defense(self):
        state = new_game()
        # Give free dog
        state["free_dog"] = True
        state = apply_action(state, "place_dog_2_2")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertIn((2, 2), state["dogs"])
        
        # Spawn thief
        state["phase"] = "night"
        state["thief_pos"] = (2, 2)
        state["thief_hp"] = 3
        state["thief_iframes"] = 0
        
        # Night tick should cause the dog to move toward the thief or attack
        state = apply_action(state, "night_tick")
        # If dog is close, it attacks and gives thief iframes
        self.assertTrue(state.get("thief_iframes", 0) > 0 or state["thief_pos"] != (2, 2))

    def test_prosperity_and_level_up(self):
        state = new_game()
        initial_level = state["farm_level"]
        
        # Build a stone_path
        state = apply_action(state, "build_decor_stone_path_60_10")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        
        # Decor should increase prosperity score
        self.assertTrue(state["prosperity_score"] > 0)
        
        # Force prosperity to level 3 threshold by manually adding 3 fountains
        state["decorations"].extend([
            (60, 11, "fountain", 3),
            (60, 12, "fountain", 3),
            (60, 13, "fountain", 3)
        ])
        
        # Build one more decor to trigger the recalculation
        state["money"] = 1000
        state = apply_action(state, "build_decor_flower_60_14")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        
        self.assertGreater(state["farm_level"], initial_level)
        self.assertEqual(state["farm_level"], 3)

    def test_use_fertilizer(self):
        state = new_game()
        state["crops"].append((1, 1))
        state["crop_data"][(1, 1)] = {"type": "radish", "stage": 0, "max_stage": 5, "watered": False, "fertilized": False}
        
        # Use fertilizer
        state = apply_action(state, "use_fertilizer_1_1")
        self.assertTrue(state["crop_data"][(1, 1)]["fertilized"])
        
        # Fertilizer should speed up growth (stage incremented by 2 instead of 1) during night transition
        state = apply_action(state, "start_night")
        self.assertEqual(state["crop_data"][(1, 1)]["stage"], 2)

    def test_use_shovel_to_remove(self):
        state = new_game()
        state["crops"].append((2, 2))
        state["crop_data"][(2, 2)] = {"type": "radish"}
        state["fences"].append((3, 3, 3))
        state["traps"].append((4, 4))
        state["dogs"].append((5, 5))
        state["decorations"].append((6, 6, "stone_path", 3))

        # Test shovel removing different items
        state = apply_action(state, "use_shovel_2_2")
        self.assertNotIn((2, 2), state["crops"])

        state = apply_action(state, "use_shovel_3_3")
        self.assertEqual(len(state["fences"]), 0)

        state = apply_action(state, "use_shovel_4_4")
        self.assertNotIn((4, 4), state["traps"])

        state = apply_action(state, "use_shovel_5_5")
        self.assertNotIn((5, 5), state["dogs"])

        state = apply_action(state, "use_shovel_6_6")
        self.assertEqual(len(state["decorations"]), 0)

    def test_thief_stealing_crop(self):
        state = new_game()
        state["crops"].append((10, 10))
        state["crop_data"][(10, 10)] = {"type": "radish", "stage": 3, "max_stage": 5}
        
        state["phase"] = "night"
        state["thief_pos"] = (10, 10)
        state["thief_hp"] = 3
        state["target_crop"] = (10, 10)

        # Night tick should cause thief to steal crop (removes it entirely)
        state = apply_action(state, "night_tick")
        
        # Crop removed
        self.assertNotIn((10, 10), state["crops"])

    def test_thief_attacking_fence(self):
        state = new_game()
        state["fences"].append((10, 10, 3))  # Fence at 10,10 with 3 HP
        state["crops"].append((15, 15))      # Crop target so thief moves
        
        state["phase"] = "night"
        state["thief_pos"] = (10, 10)        # Thief is on the fence
        state["thief_hp"] = 3
        state["target_crop"] = (10, 10)      # Must set target to the fence position to trigger attack

        # Night tick should cause thief to attack fence instead of moving
        state = apply_action(state, "night_tick")
        
        # Fence HP reduced by 1
        self.assertEqual(state["fences"][0][2], 2)

    def test_boar_attacking_decor(self):
        state = new_game()
        state["day_count"] = 5  # Boars start spawning day 5
        state["decorations"].append((10, 10, "stone_path", 3))
        
        state["phase"] = "night"
        state["boar_pos"] = (10, 10)
        state["boar_hp"] = 5
        state["target_decor"] = (10, 10)

        # Night tick should cause boar to attack decor (destroys it immediately)
        state = apply_action(state, "night_tick")
        
        # Decor removed
        self.assertEqual(len(state["decorations"]), 0)

    def test_click_enemy_damage(self):
        state = new_game()
        state["phase"] = "night"
        
        # Setup Thief
        state["thief_pos"] = (10, 10)
        state["thief_hp"] = 3
        state["thief_iframes"] = 0

        # Setup Boar
        state["boar_pos"] = (20, 20)
        state["boar_hp"] = 5
        state["boar_iframes"] = 0

        # Attack thief
        state = apply_action(state, "click_10_10")
        self.assertEqual(state["thief_hp"], 2)

        # Attack boar
        state = apply_action(state, "click_20_20")
        self.assertEqual(state["boar_hp"], 4)

    def test_game_over_rent(self):
        state = new_game()
        state["money"] = 10
        state["day_count"] = 1
        state["phase"] = "night"
        # Rent is 20 + (day - 1) * 10 = 20
        # Will end night, subtract rent (10 - 20 = -10)
        
        # Directly call tick to finish night
        state["time_left"] = 0
        state = apply_action(state, "tick")
        
        # Deducts rent
        self.assertEqual(state["money"], -10)
        # Sets status to game_over
        self.assertEqual(state["status"], "game_over")
        # Game over state retains night phase
        self.assertEqual(state["phase"], "night")

    def test_terminal_state_rejection(self):
        state = new_game()
        state["status"] = "game_over"
        state["money"] = 100
        
        state = apply_action(state, "use_hoe_10_10")
        # Since game is over, it shouldn't allow building tasks
        self.assertEqual(len(state["building_tasks"]), 0)

    def test_invalid_placement(self):
        state = new_game()
        # Add farm
        state["crops"].append((10, 10))
        
        # Enclose it tightly with fences to block pathfinding (8 directions)
        positions = [(10, 5), (10, 15), (5, 10), (5, 5), (15, 15), (5, 15), (15, 5)]
        for pos in positions:
            state = apply_action(state, f"build_fence_{pos[0]}_{pos[1]}")
            state = apply_action(state, "tick")
            state = apply_action(state, "tick")
        
        # Attempt to place the last piece
        state = apply_action(state, "build_fence_15_10")
        self.assertIn("不能將農田完全封死", state.get("last_msg", ""))

    def test_camera_movement(self):
        import pygame
        from src.input_handler import update_camera
        
        # Test normal movement
        keys = {pygame.K_d: True}
        cx, cy = update_camera(0, 0, False, (0, 0), keys, 1000, 1000, 800, 600, "farm")
        self.assertEqual(cx, 15)  # Moved right by 15
        
        # Test mouse drag
        cx, cy = update_camera(100, 100, True, (50, -50), {}, 1000, 1000, 800, 600, "farm")
        self.assertEqual(cx, 50)   # 100 - 50 = 50
        self.assertEqual(cy, 150)  # 100 - (-50) = 150
        
        # Test loose margin boundaries
        cx, cy = update_camera(2000, 0, False, (0, 0), {pygame.K_d: True}, 1000, 1000, 800, 600, "farm")
        self.assertEqual(cx, 800) # (1600 - 800)
        
        # Test Decor zone snapping bounds
        cx, cy = update_camera(2000, 0, False, (0, 0), {pygame.K_d: True}, 100 * 32, 1000, 800, 600, "decor")
        self.assertEqual(cx, 2015)  # Can move right in decor zone

if __name__ == '__main__':
    unittest.main()

