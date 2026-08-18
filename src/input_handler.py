import pygame
from src.config import *
from src.capstone_contract import apply_action, new_game, is_terminal, CROP_INFO

def handle_mouse_click(state, event, current_tool, shop_open, active_tab, camera_x, camera_y, active_zone):
    if is_terminal(state):
        return state, current_tool, shop_open, active_tab, active_zone

    if event.button == 3: # Right click to cancel tool
        return state, None, shop_open, active_tab, active_zone
        
    if event.button == 1:
        mx, my = event.pos
        if shop_open:
            shop_w = 1180
            shop_h = 700
            shop_x = (WIDTH - shop_w) // 2
            shop_y = (HEIGHT - shop_h) // 2
            shop_rect = pygame.Rect(shop_x, shop_y, shop_w, shop_h)
            
            if not shop_rect.collidepoint(mx, my):
                shop_open = False
            else:
                is_sell = active_tab == "sell"
                left_page_x = shop_x + 90
                left_page_w = 400
                right_page_x = shop_x + 675
                right_page_w = 400
                
                tab_buy = pygame.Rect(left_page_x, shop_y + 110, left_page_w, 45)
                tab_sell = pygame.Rect(right_page_x, shop_y + 110, right_page_w, 45)
                
                if tab_buy.collidepoint(mx, my): active_tab = "seed"
                elif tab_sell.collidepoint(mx, my): active_tab = "sell"
                else:
                    if not is_sell:
                        sub_w = (left_page_w - 20) // 3
                        tab_seed = pygame.Rect(left_page_x, shop_y + 165, sub_w, 30)
                        tab_def = pygame.Rect(left_page_x + sub_w + 10, shop_y + 165, sub_w, 30)
                        tab_pet = pygame.Rect(left_page_x + (sub_w + 10)*2, shop_y + 165, sub_w, 30)
                        
                        if tab_seed.collidepoint(mx, my): active_tab = "seed"
                        elif tab_def.collidepoint(mx, my): active_tab = "def"
                        elif tab_pet.collidepoint(mx, my): active_tab = "pet"
                        else:
                            items = []
                            if active_tab == "seed": items = [{"id": "radish", "price": 30}, {"id": "carrot", "price": 100}, {"id": "pumpkin", "price": 300}]
                            elif active_tab == "def": items = [{"id": "fence", "price": 20}, {"id": "trap", "price": 50}, {"id": "dog", "price": "FREE" if state.get("free_dog") else 200}]
                            elif active_tab == "pet": items = [{"id": "stone_path", "price": 20}, {"id": "flower", "price": 50}, {"id": "bench", "price": 100}, {"id": "fountain", "price": 300}]
                            else: items = []
                            
                            left_items = items[:(len(items)+1)//2]
                            right_items = items[(len(items)+1)//2:]
                            
                            clicked = False
                            for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 210), (right_items, right_page_x, shop_y + 170)]:
                                y_offset = start_y
                                for item in page_items:
                                    card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                                    if card_rect.collidepoint(mx, my):
                                        current_tool = item["id"]
                                        shop_open = False
                                        clicked = True
                                        break
                                    y_offset += 75
                                if clicked: break
                    else:
                        grades = ["normal", "rare", "epic", "legendary"]
                        grades_tw = {"normal": "一般", "rare": "稀有", "epic": "史詩", "legendary": "傳奇"}
                        multipliers = {"normal": 1, "rare": 2, "epic": 3, "legendary": 5}
                        
                        sellable = []
                        for c_id, c_name in [("radish", "白蘿蔔"), ("carrot", "胡蘿蔔"), ("pumpkin", "魔法南瓜")]:
                            base_price = CROP_INFO[c_id]["yield"] if c_id in CROP_INFO else 100
                            for grade in grades:
                                count = state["inventory"].get(c_id, {}).get(grade, 0)
                                if count > 0:
                                    sellable.append({"id": c_id, "name": f"{c_name} ({grades_tw[grade]})", "grade": grade, "count": count, "price": base_price * multipliers[grade]})
                                    
                        left_items = sellable[:6]
                        right_items = sellable[6:12]
                        
                        clicked = False
                        for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 170), (right_items, right_page_x, shop_y + 170)]:
                            y_offset = start_y
                            for item in page_items:
                                card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                                if card_rect.collidepoint(mx, my):
                                    state["inventory"][item["id"]][item["grade"]] -= 1
                                    state["money"] += item["price"]
                                    state["last_msg"] = f"成功出售 1 個 {item['name'][:4]}，獲得 ${item['price']}！"
                                    clicked = True
                                    break
                                y_offset += 75
                            if clicked: break
        else:
            # Hotbar click detection
            if not shop_open:
                slot_size = 58
                slot_gap  = 8
                bar_w = 4 * slot_size + 5 * slot_gap
                bar_x = (WIDTH - bar_w) // 2
                bar_y = HEIGHT - 82
                bar_h = slot_size + 2 * slot_gap
                if bar_y <= my <= bar_y + bar_h and bar_x <= mx <= bar_x + bar_w:
                    idx = (mx - bar_x - slot_gap) // (slot_size + slot_gap)
                    if 0 <= idx < 4:
                        tools = ["hoe", "scythe", "shovel", "fertilizer"]
                        current_tool = tools[idx]
                    return state, current_tool, shop_open, active_tab, active_zone

            toggle_rect = pygame.Rect(WIDTH // 2 - 130, 14, 220, 44)
            shop_btn_rect = pygame.Rect(WIDTH - 158, 14, 140, 44)
            
            if toggle_rect.collidepoint(mx, my):
                active_zone = "decor" if active_zone == "farm" else "farm"
                return state, current_tool, shop_open, active_tab, active_zone
            elif shop_btn_rect.collidepoint(mx, my):
                shop_open = True
                return state, current_tool, shop_open, active_tab, active_zone
                
            if current_tool:
                world_x = mx + camera_x
                world_y = my + camera_y
                # Snap to ITEM_PX grid to prevent overlapping
                ITEM_PX = CELL_SIZE * 10
                gx = int(world_x // ITEM_PX) * 10
                gy = int(world_y // ITEM_PX) * 10
                
                if current_tool == "hoe":
                    state = apply_action(state, f"use_hoe_{gx}_{gy}")
                elif current_tool == "scythe":
                    state = apply_action(state, f"use_scythe_{gx}_{gy}")
                elif current_tool == "shovel":
                    state = apply_action(state, f"use_shovel_{gx}_{gy}")
                elif current_tool == "fertilizer":
                    state = apply_action(state, f"use_fertilizer_{gx}_{gy}")
                elif current_tool in ["radish", "carrot", "pumpkin"]:
                    state = apply_action(state, f"plant_crop_{current_tool}_{gx}_{gy}")
                elif current_tool in ["stone_path", "flower", "bench", "fountain"]:
                    state = apply_action(state, f"build_decor_{current_tool}_{gx}_{gy}")
                elif current_tool == "fence":
                    state = apply_action(state, f"build_fence_{gx}_{gy}")
                elif current_tool == "trap":
                    state = apply_action(state, f"place_trap_{gx}_{gy}")
                elif current_tool == "dog":
                    state = apply_action(state, f"place_dog_{gx}_{gy}")
            else:
                world_x = mx + camera_x
                world_y = my + camera_y
                gx, gy = world_x, world_y
                state = apply_action(state, f"click_{gx}_{gy}")
                
    return state, current_tool, shop_open, active_tab, active_zone

def handle_keyboard_events(state, event, current_tool, shop_open, active_zone):
    if event.key == pygame.K_ESCAPE:
        return state, None, False, active_zone
    elif event.key == pygame.K_TAB:
        active_zone = "decor" if active_zone == "farm" else "farm"
    elif event.key == pygame.K_b:
        shop_open = not shop_open
    elif event.key == pygame.K_SPACE:
        if not is_terminal(state): 
            state = apply_action(state, "start_night")
    elif event.key == pygame.K_r: 
        state = new_game()
    elif event.key == pygame.K_1: current_tool = "hoe"
    elif event.key == pygame.K_2: current_tool = "scythe"
    elif event.key == pygame.K_3: current_tool = "shovel"
    elif event.key == pygame.K_4: current_tool = "fertilizer"
    
    return state, current_tool, shop_open, active_zone

def update_camera(camera_x, camera_y, mouse_pressed, mouse_rel, keys, WORLD_W, WORLD_H, WIDTH, HEIGHT, active_zone):
    cam_speed = 15
    if keys.get(pygame.K_w, False) or keys.get(pygame.K_UP, False): camera_y -= cam_speed
    if keys.get(pygame.K_s, False) or keys.get(pygame.K_DOWN, False): camera_y += cam_speed
    if keys.get(pygame.K_a, False) or keys.get(pygame.K_LEFT, False): camera_x -= cam_speed
    if keys.get(pygame.K_d, False) or keys.get(pygame.K_RIGHT, False): camera_x += cam_speed
    
    if mouse_pressed:
        mx, my = mouse_rel
        camera_x -= mx
        camera_y -= my
        
    # Split world into two maps: Farm (0 to 50*CELL_SIZE) and Decor (50*CELL_SIZE to WORLD_W)
    mid_x = 50 * 32  # 1600
    map_w = mid_x
    
    if active_zone == "farm":
        camera_x = max(0, min(camera_x, max(0, map_w - WIDTH)))
    else:
        camera_x = max(mid_x, min(camera_x, max(mid_x, WORLD_W - WIDTH)))
            
    camera_y = max(0, min(camera_y, max(0, WORLD_H - HEIGHT)))
        
    return camera_x, camera_y
