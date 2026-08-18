import pygame
import time
from src.config import *
from src.assets import images, night_filter, get_bg_surfs, sprite_loader
from src.ui import draw_hud, draw_shop, draw_game_over
from src.capstone_contract import is_terminal

def is_cell_occupied(state, gx, gy):
    pos = (gx, gy)
    if pos in state.get("crops", []): return True
    if any(f[0] == gx and f[1] == gy for f in state.get("fences", [])): return True
    if pos in state.get("trees", []): return True

def draw_board(screen, state, current_tool, camera_x, camera_y, mouse_pos, shop_open, active_tab, active_zone):
    
    bg_left, bg_right = get_bg_surfs()
    bg = bg_left if active_zone == "farm" else bg_right
    pw, ph = bg.get_size()
    for y in range(-(camera_y % ph), HEIGHT, ph):
        for x in range(-(camera_x % pw), WIDTH, pw):
            screen.blit(bg, (x, y))
            
    def get_screen_coords(gx, gy):
        return gx * CELL_SIZE - camera_x, gy * CELL_SIZE - camera_y
    
    def draw_obj(pos, img, backup_color, shape="rect"):
        x, y = pos
        screen_x, screen_y = get_screen_coords(x, y)
        if screen_x is None: return
        
        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT:
            return
            
        rect = pygame.Rect(screen_x, screen_y, ITEM_PX, ITEM_PX)
        if img:
            screen.blit(img, rect)
        else:
            if shape == "circle":
                pygame.draw.circle(screen, backup_color, rect.center, ITEM_PX // 2)
            else:
                pygame.draw.rect(screen, backup_color, rect)
                
    # Draw Trees
    import time
    anim_frame = int(time.time() * 4) % 4
    tree_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_tree_01_strip4.png", 0, anim_frame, 32, 34, (int(ITEM_PX * SPRITE_SCALES["tree"][0]), int(ITEM_PX * SPRITE_SCALES["tree"][1])))
    for tx, ty in state.get("trees", []):
        screen_x, screen_y = get_screen_coords(tx, ty)
        if screen_x is None: continue
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            if tree_img:
                # Center tree base on the cell
                screen.blit(tree_img, (screen_x - ITEM_PX // 4, screen_y - int(ITEM_PX * 1.25)))
            else:
                rect = pygame.Rect(screen_x, screen_y, ITEM_PX, ITEM_PX)
                pygame.draw.rect(screen, (139, 69, 19), (rect.centerx - 10, rect.bottom - 30, 20, 30)) # Trunk
                pygame.draw.circle(screen, (34, 139, 34), (rect.centerx, rect.bottom - 40), 25) # Leaves
                pygame.draw.circle(screen, (50, 205, 50), (rect.centerx - 15, rect.bottom - 30), 20)
                pygame.draw.circle(screen, (50, 205, 50), (rect.centerx + 15, rect.bottom - 30), 20)

    # Draw Rocks
    rock_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Tileset/spr_tileset_sunnysideworld_16px.png", 61, 2, 16, 16, (int(ITEM_PX * SPRITE_SCALES["rock"][0]), int(ITEM_PX * SPRITE_SCALES["rock"][1])))
    for rx, ry in state.get("rocks", []):
        screen_x, screen_y = get_screen_coords(rx, ry)
        if screen_x is None: continue
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            if rock_img:
                screen.blit(rock_img, (screen_x, screen_y))
            else:
                rect = pygame.Rect(screen_x + 10, screen_y + 30, ITEM_PX - 20, ITEM_PX - 30)
                pygame.draw.ellipse(screen, (105, 105, 105), rect)

    # Draw Farmland (beneath crops) — seamless tilled soil
    for fx, fy in state.get("farmland", []):
        cx, cy = get_screen_coords(fx, fy)
        if cx is None: continue
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT: continue
        
        rect = pygame.Rect(cx, cy, ITEM_PX, ITEM_PX)
        # Base dirt
        pygame.draw.rect(screen, (110, 72, 38), rect)
        # Subtle cross-hatch texture
        inner = rect.inflate(-4, -4)
        pygame.draw.rect(screen, (90, 56, 24), inner, 1)
        # Small pebble dots for texture
        import random as _rnd
        _rnd.seed(fx * 1000 + fy)
        for _ in range(3):
            px = cx + _rnd.randint(6, ITEM_PX - 6)
            py = cy + _rnd.randint(6, ITEM_PX - 6)
            pygame.draw.circle(screen, (75, 46, 18), (px, py), 2)

    # Draw Crops
    for crop in state["crops"]:
        data = state["crop_data"].get(crop)
        if not data: continue
        cx, cy = get_screen_coords(crop[0], crop[1])
        if cx is None: continue
        
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT:
            continue
            
        c_type = data.get("type", "radish")
        
        # Calculate visual stage based on days passed + current day progress
        max_stage = data.get("max_stage", 5)
        current_day_progress = 0.0
        if state["phase"] == "day" and data["stage"] < max_stage:
            current_day_progress = max(0.0, min(1.0, (120 - state.get("time_left", 120)) / 120.0))
        elif data["stage"] >= max_stage:
            current_day_progress = 0.0
            
        total_progress = min(max_stage, data["stage"] + current_day_progress)
        cstage = int((total_progress / max(1, max_stage)) * 5)
        cstage = max(0, min(5, cstage))
        
        crop_img_path = f"Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops/{c_type}_{cstage:02d}.png"
        crop_img = sprite_loader.get_image(crop_img_path, (int(ITEM_PX * SPRITE_SCALES["crop"][0]), int(ITEM_PX * SPRITE_SCALES["crop"][1])))
        
        if crop_img:
            cw, ch = crop_img.get_size()
            offset_x = (ITEM_PX - cw) // 2
            offset_y = (ITEM_PX - ch) // 2
            screen.blit(crop_img, (cx + offset_x, cy + offset_y))
        else:
            # Fallback
            c_color = RED if c_type == "radish" else (WHITE if c_type == "turnip" else ((255, 165, 0) if c_type == "carrot" else (200, 200, 100)))
            size_ratio = 0.3 + 0.7 * (data["stage"] / max(1, data["max_stage"]))
            c_size = int((ITEM_PX // 2) * size_ratio)
            pygame.draw.circle(screen, c_color, (cx + ITEM_PX//2, cy + ITEM_PX//2), c_size)
        
        # Draw Progress Bar for Crops
        bar_w = ITEM_PX - 20
        bar_h = 6
        bar_x = cx + 10
        bar_y = cy + ITEM_PX - 12
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))
        
        stage = data["stage"]
        max_stage = data["max_stage"]
        if stage < max_stage and state["phase"] == "day":
            day_progress = (120 - state["time_left"]) / 120.0
        else:
            day_progress = 0
            
        if stage >= max_stage: total_progress = 1.0
        else: total_progress = (stage + day_progress) / max_stage
            
        fill_w = int(bar_w * total_progress)
        color = (50, 205, 50) if stage < max_stage else (255, 215, 0)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h))

    # Draw Scarecrows
    scarecrow_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (int(ITEM_PX * SPRITE_SCALES["scarecrow"][0]), int(ITEM_PX * SPRITE_SCALES["scarecrow"][1])))
    for sx, sy in state.get("scarecrows", []):
        cx, cy = get_screen_coords(sx, sy)
        if cx is None: continue
        if scarecrow_img:
            screen.blit(scarecrow_img, (cx, cy))

    # Draw Fences
    fence_img = images.get("fence")
    for fx, fy, fhp in state.get("fences", []):
        screen_x, screen_y = get_screen_coords(fx, fy)
        if screen_x is None: continue
        if fence_img:
            screen.blit(fence_img, (screen_x, screen_y))
        else:
            pygame.draw.rect(screen, (139, 69, 19), (screen_x + 5, screen_y + 5, ITEM_PX - 10, ITEM_PX - 10))
            pygame.draw.rect(screen, (160, 82, 45), (screen_x + 10, screen_y + 10, ITEM_PX - 20, ITEM_PX - 20))

    # 畫出陷阱
    trap_img = images.get("trap")
    for tx, ty in state.get("traps", []):
        screen_x, screen_y = get_screen_coords(tx, ty)
        if screen_x is None: continue
        if trap_img:
            screen.blit(trap_img, (screen_x, screen_y))
        elif screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            pygame.draw.rect(screen, (100, 100, 100), (screen_x + 10, screen_y + ITEM_PX - 20, ITEM_PX - 20, 20))
            pygame.draw.line(screen, (200, 0, 0), (screen_x + 20, screen_y + ITEM_PX - 10), (screen_x + ITEM_PX - 20, screen_y + ITEM_PX - 10), 3)
            
    # 畫出景觀物
    for d in state.get("decorations", []):
        dx, dy, dtype, hp = d
        screen_x, screen_y = get_screen_coords(dx, dy)
        if screen_x is None: continue
        
        if dtype == "fountain":
                anim_frame = int(time.time() * 9) % 9
                windmill_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Other/spr_deco_windmill_strip9.png", 0, anim_frame, 112, 112, (int(ITEM_PX * SPRITE_SCALES["windmill"][0]), int(ITEM_PX * SPRITE_SCALES["windmill"][1])))
                if windmill_img:
                    screen.blit(windmill_img, (screen_x - ITEM_PX//2, screen_y - ITEM_PX))
                else:
                    pygame.draw.rect(screen, (150, 150, 255), (screen_x + 5, screen_y + 5, ITEM_PX - 10, ITEM_PX - 10))
        else:
            dec_img = images.get(dtype)
            if dec_img:
                screen.blit(dec_img, (screen_x, screen_y))
            elif screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
                if dtype == "stone_path":
                    pygame.draw.rect(screen, (150, 150, 150), (screen_x, screen_y, ITEM_PX, ITEM_PX))
                elif dtype == "flower":
                    pygame.draw.rect(screen, (139, 69, 19), (screen_x + 10, screen_y + 20, ITEM_PX - 20, ITEM_PX - 20))
                    pygame.draw.circle(screen, (255, 105, 180), (screen_x + ITEM_PX // 2, screen_y + 10), 20)
                elif dtype == "bench":
                    pygame.draw.rect(screen, (205, 133, 63), (screen_x + 10, screen_y + 30, ITEM_PX - 20, 20))
                    pygame.draw.rect(screen, (139, 69, 19), (screen_x + 10, screen_y + 10, 10, 40))
                    pygame.draw.rect(screen, (139, 69, 19), (screen_x + ITEM_PX - 20, screen_y + 10, 10, 40))

    # 畫出寵物
    import time
    anim_frame = int(time.time() * 4) % 4
    # Goldie is 32x40, row 4 is walking down (4 frames)
    dog_img = sprite_loader.get_sprite("Goldie pack_v1.1/Goldie pack_v02/Goldie_v02.png", 4, anim_frame, 32, 40, (int(ITEM_PX * SPRITE_SCALES["dog"][0]), int(ITEM_PX * SPRITE_SCALES["dog"][1])))
    for dx, dy in state.get("dogs", []):
        screen_x, screen_y = get_screen_coords(dx, dy)
        if screen_x is None: continue
        if dog_img:
            screen.blit(dog_img, (screen_x - ITEM_PX//4, screen_y - ITEM_PX//4))
        else:
            pygame.draw.circle(screen, (205, 133, 63), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)

    # Draw Thief
    if state["thief_pos"] is not None:
        tx, ty = state["thief_pos"]
        screen_x, screen_y = get_screen_coords(tx, ty)
        if screen_x is None: pass
        
        thief_dir_row = 0
        flip_x = False
        
        if state.get("thief_path"):
            target = state["thief_path"][0]
            dx = target[0] - tx
            dy = target[1] - ty
            if abs(dx) > abs(dy):
                thief_dir_row = 2 # Right
                if dx < 0: flip_x = True # Left
            else:
                if dy < 0: thief_dir_row = 1 # Up
                else: thief_dir_row = 0 # Down
        
        anim_frame = int(time.time() * 8) % 8
        thief_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Characters/Goblin/PNG/spr_walk_strip8.png", 0, anim_frame, 96, 64, (int(ITEM_PX * SPRITE_SCALES["goblin"][0]), int(ITEM_PX * SPRITE_SCALES["goblin"][1])))
        if thief_img:
            if flip_x:
                thief_img = pygame.transform.flip(thief_img, True, False)
            screen.blit(thief_img, (screen_x - ITEM_PX, screen_y - ITEM_PX))
        else:
            pygame.draw.circle(screen, RED, (screen_x + ITEM_PX//2, screen_y + ITEM_PX//2), ITEM_PX // 2)
            
        hp = state.get("thief_hp", 3)
        pygame.draw.rect(screen, RED, (screen_x, screen_y - 10, ITEM_PX, 6))
    # Draw Boar
    if state.get("boar_pos"):
        bx, by = state["boar_pos"]
        screen_x, screen_y = get_screen_coords(bx, by)
        if screen_x is None: pass
        
        boar_dir_row = 0
        flip_x = False
        
        if state.get("boar_path"):
            target = state["boar_path"][0]
            dx = target[0] - bx
            dy = target[1] - by
            if abs(dx) > abs(dy):
                boar_dir_row = 2
                if dx < 0: flip_x = True
            else:
                if dy < 0: boar_dir_row = 1
                else: boar_dir_row = 0
                
        anim_frame = int(time.time() * 6) % 4
        boar_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_pig_01_strip4.png", 0, anim_frame, 32, 32, (int(ITEM_PX * SPRITE_SCALES["boar"][0]), int(ITEM_PX * SPRITE_SCALES["boar"][1])))
        if boar_img:
            if flip_x: boar_img = pygame.transform.flip(boar_img, True, False)
            # Tint it dark/black to look like a boar if possible, or just draw black circle if none
            screen.blit(boar_img, (screen_x - ITEM_PX//4, screen_y - ITEM_PX//2))
        else:
            pygame.draw.circle(screen, (50, 50, 50), (screen_x + ITEM_PX//2, screen_y + ITEM_PX//2), ITEM_PX // 2)
            
        hp = state.get("boar_hp", 5)
        pygame.draw.rect(screen, RED, (screen_x, screen_y - 10, ITEM_PX, 6))
        pygame.draw.rect(screen, (0, 255, 0), (screen_x, screen_y - 10, ITEM_PX * (hp / max(1, hp, 5)), 6))
    
    if state['phase'] == "day" and mouse_pos and not shop_open:
        mx, my = mouse_pos
        if current_tool is not None and my >= 0 and my < HEIGHT:
            gx = (mx + camera_x - ITEM_PX // 2) // CELL_SIZE
            gy = (my + camera_y - ITEM_PX // 2) // CELL_SIZE
            
            screen_x, screen_y = get_screen_coords(gx, gy)
            if screen_x is not None:
                s = pygame.Surface((ITEM_PX, ITEM_PX))
                s.set_alpha(128)
            
                occupied = is_cell_occupied(state, gx, gy)
            
                if current_tool == "fertilizer":
                    s.fill((173, 255, 47))
                elif current_tool == "shovel":
                    s.fill((169, 169, 169))
                else:
                    for dx in range(ITEM_SIZE):
                        for dy in range(ITEM_SIZE):
                            sub_x = gx + dx
                            sub_y = gy + dy
                        
                            occupant = None
                        
                            # Check water
                            for wx, wy, ww, wh in state.get("water", []):
                                if not (sub_x + 1 <= wx or wx + ww <= sub_x or sub_y + 1 <= wy or wy + wh <= sub_y):
                                    occupant = "water"
                                    break
                                
                            if not occupant:
                                for tx, ty in state.get("trees", []):
                                    if not (sub_x + 1 <= tx or tx + ITEM_SIZE <= sub_x or sub_y + 1 <= ty or ty + ITEM_SIZE <= sub_y):
                                        occupant = "tree"
                                        break
                                    
                            if not occupant:
                                for ex, ey in state.get("crops", []):
                                    if not (sub_x + 1 <= ex or ex + ITEM_SIZE <= sub_x or sub_y + 1 <= ey or ey + ITEM_SIZE <= sub_y):
                                        occupant = "crop"
                                        break
                                    
                            if not occupant:
                                all_ents = [(f[0], f[1]) for f in state.get("fences", [])] + state.get("dogs", []) + state.get("cats", []) + state.get("geese", []) + state.get("owls", [])
                                for t in state.get("building_tasks", []):
                                    if t.get("type") != "fence": all_ents.append(t["pos"])
                                for ex, ey in all_ents:
                                    if not (sub_x + 1 <= ex or ex + ITEM_SIZE <= sub_x or sub_y + 1 <= ey or ey + ITEM_SIZE <= sub_y):
                                        occupant = "entity"
                                        break

                            if current_tool == "axe":
                                color = (0, 255, 0) if occupant == "tree" else (255, 0, 0)
                            elif current_tool == "scythe":
                                color = (0, 255, 0) if occupant == "crop" else (255, 0, 0)
                            elif current_tool == "shovel":
                                color = (0, 255, 0) if occupant in ["crop", "entity"] else (255, 0, 0)
                            elif current_tool == "pickaxe":
                                color = (0, 255, 0) if occupant == "rock" else (255, 0, 0)
                            else: # Seeds, hoe, fences, pets, etc.
                                color = (255, 0, 0) if occupant else (0, 255, 0)
                            
                            rect = (dx * CELL_SIZE, dy * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                            pygame.draw.rect(s, color, rect)
                            pygame.draw.rect(s, (0, 0, 0), rect, 1) # Grid dashed/border lines
                    
                preview_img = images.get(current_tool)
                if preview_img:
                    pw, ph = preview_img.get_size()
                    s.blit(preview_img, ((ITEM_PX - pw) // 2, (ITEM_PX - ph) // 2))
                else:
                    # Text fallback for cursor
                    tool_name = TOOL_NAMES.get(current_tool, current_tool)[:2]
                    txt = font_small.render(tool_name, True, BLACK)
                    s.blit(txt, (ITEM_PX//2 - txt.get_width()//2, ITEM_PX//2 - txt.get_height()//2))
                
                screen.blit(s, (screen_x, screen_y))

    if current_tool is not None and not shop_open:
        # Draw ITEM_PX grid overlay
        grid_surf = pygame.Surface((WIDTH, HEIGHT - MARGIN_TOP - MARGIN_BOTTOM), pygame.SRCALPHA)
        start_x = - (camera_x % ITEM_PX)
        start_y = - (camera_y % ITEM_PX)
        for x in range(start_x, WIDTH, ITEM_PX):
            pygame.draw.line(grid_surf, (255, 255, 255, 40), (x, 0), (x, HEIGHT))
        for y in range(start_y, HEIGHT, ITEM_PX):
            pygame.draw.line(grid_surf, (255, 255, 255, 40), (0, y), (WIDTH, y))
        screen.blit(grid_surf, (0, MARGIN_TOP))
        
    # 畫建造中的項目（帶真實進度條）
    for task in state.get("building_tasks", []):
        x, y = task["pos"]
        screen_x, screen_y = get_screen_coords(x, y)
        if screen_x is None: continue
        
        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT:
            continue
            
        rect = pygame.Rect(screen_x, screen_y, ITEM_PX, ITEM_PX)
        progress_ratio = task["progress"] / max(1, task["max_progress"])
        
        t_type = task["type"]
        img = None
        if t_type == "dog": img = images.get("dog")
        elif t_type == "cat": img = images.get("cat")
        elif t_type == "goose": img = images.get("goose")
        elif t_type == "owl": img = images.get("owl")
        elif t_type == "fence": img = images.get("fence")
        
        # Ghost image
        ghost = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
        if img:
            scaled = pygame.transform.scale(img, (ITEM_PX, ITEM_PX)).copy()
            scaled.set_alpha(120)
            ghost.blit(scaled, (0, 0))
        else:
            pygame.draw.rect(ghost, (180, 140, 80, 120), ghost.get_rect(), border_radius=4)
        screen.blit(ghost, rect.topleft)
        
        # Progress bar at bottom of cell
        bar_h = 5
        bar_y = screen_y + ITEM_PX - bar_h - 2
        pygame.draw.rect(screen, (40, 40, 40), (screen_x + 2, bar_y, ITEM_PX - 4, bar_h), border_radius=2)
        fill_w = int((ITEM_PX - 4) * progress_ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, (80, 220, 80), (screen_x + 2, bar_y, fill_w, bar_h), border_radius=2)
        
        # Percentage label
        pct_txt = font_tiny.render(f"{int(progress_ratio*100)}%", True, WHITE)
        screen.blit(pct_txt, (rect.centerx - pct_txt.get_width()//2, screen_y + 4))



    # ── Hotbar UI (with icons + glow) ─────────────────────────────────────
    if not shop_open:
        HOTBAR_ITEMS = [
            {"id": "hoe",        "key": "1"},
            {"id": "scythe",     "key": "2"},
            {"id": "shovel",     "key": "3"},
            {"id": "fertilizer", "key": "4"},
        ]
        slot_size = 58
        slot_gap  = 8
        bar_w = len(HOTBAR_ITEMS) * slot_size + (len(HOTBAR_ITEMS) + 1) * slot_gap
        bar_x = (WIDTH - bar_w) // 2
        bar_y = HEIGHT - 82
        bar_h = slot_size + 2 * slot_gap
        
        # Panel background
        panel_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (20, 14, 8, 210), panel_surf.get_rect(), border_radius=12)
        pygame.draw.rect(panel_surf, (110, 80, 45, 200), panel_surf.get_rect(), 2, border_radius=12)
        screen.blit(panel_surf, (bar_x, bar_y))
        
        for i, item in enumerate(HOTBAR_ITEMS):
            sx = bar_x + slot_gap + i * (slot_size + slot_gap)
            sy = bar_y + slot_gap
            selected = current_tool == item["id"]
            
            # Slot background
            slot_col = (180, 140, 40) if selected else (55, 38, 18)
            slot_surf = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA)
            pygame.draw.rect(slot_surf, (*slot_col, 230), slot_surf.get_rect(), border_radius=8)
            if selected:
                # Golden glow border
                pygame.draw.rect(slot_surf, (255, 240, 80, 255), slot_surf.get_rect(), 3, border_radius=8)
            screen.blit(slot_surf, (sx, sy))
            
            # Tool sprite icon
            icon_img = images.get(item["id"])
            if icon_img:
                icon_scaled = pygame.transform.scale(icon_img, (34, 34))
                screen.blit(icon_scaled, (sx + (slot_size - 34) // 2, sy + 6))
            
            # Hotkey label
            key_surf = font_tiny.render(item["key"], True, (220, 220, 200) if not selected else (255, 255, 120))
            screen.blit(key_surf, (sx + 4, sy + slot_size - key_surf.get_height() - 3))
        
        # ── Inventory badge: show seed count next to hotbar for seed tools ──
        if current_tool in ("radish", "carrot", "pumpkin"):
            total = sum(state.get("inventory", {}).get(current_tool, {}).values())
            badge_txt = font_small.render(f"x{total}", True, (255, 255, 150))
            bx = bar_x + bar_w + 12
            by = bar_y + (bar_h - badge_txt.get_height()) // 2
            badge_bg = pygame.Surface((badge_txt.get_width() + 12, badge_txt.get_height() + 8), pygame.SRCALPHA)
            pygame.draw.rect(badge_bg, (0, 0, 0, 180), badge_bg.get_rect(), border_radius=6)
            screen.blit(badge_bg, (bx - 6, by - 4))
            screen.blit(badge_txt, (bx, by))
        
        # Mouse tooltip for current tool
        if current_tool and mouse_pos:
            tip = TOOL_NAMES.get(current_tool, current_tool)
            tip_surf = font_tiny.render(tip, True, (240, 240, 200))
            tip_bg = pygame.Surface((tip_surf.get_width() + 16, tip_surf.get_height() + 8), pygame.SRCALPHA)
            pygame.draw.rect(tip_bg, (0, 0, 0, 190), tip_bg.get_rect(), border_radius=6)
            mx_t, my_t = mouse_pos
            tx = mx_t + 18
            ty = my_t - tip_bg.get_height() - 6
            # Keep on screen
            if tx + tip_bg.get_width() > WIDTH: tx = mx_t - tip_bg.get_width() - 8
            if ty < 0: ty = my_t + 18
            screen.blit(tip_bg, (tx, ty))
            screen.blit(tip_surf, (tx + 8, ty + 4))

    # ── Highlight fully-grown (harvestable) crops with golden glow ─────────
    for crop in state.get("crops", []):
        data = state["crop_data"].get(crop)
        if data and data["stage"] >= data["max_stage"]:
            cx, cy = get_screen_coords(crop[0], crop[1])
            if cx is None: continue
            if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT: continue
            pulse = abs((time.time() * 3) % 2 - 1)
            glow_alpha = int(60 + 100 * pulse)
            glow = pygame.Surface((ITEM_PX + 8, ITEM_PX + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 215, 0, glow_alpha), glow.get_rect(), border_radius=4)
            screen.blit(glow, (cx - 4, cy - 4))

    # ── Minimap (bottom-left corner) ───────────────────────────────────────
    mm_w, mm_h = 160, 120
    mm_x, mm_y = 20, HEIGHT - mm_h - 148
    scale_x = mm_w / WORLD_W
    scale_y = mm_h / WORLD_H

    mm_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    pygame.draw.rect(mm_surf, (20, 40, 20, 200), mm_surf.get_rect(), border_radius=6)
    pygame.draw.rect(mm_surf, (80, 100, 80, 220), mm_surf.get_rect(), 1, border_radius=6)

    # Farmland patches
    for fx, fy in state.get("farmland", []):
        mmfx = int(fx * CELL_SIZE * scale_x)
        mmfy = int(fy * CELL_SIZE * scale_y)
        pygame.draw.rect(mm_surf, (110, 72, 38), (mmfx, mmfy, max(2, int(ITEM_PX * scale_x)), max(2, int(ITEM_PX * scale_y))))

    # Crops (green dots)
    for cr in state.get("crops", []):
        data = state["crop_data"].get(cr)
        col = (255, 215, 0) if (data and data["stage"] >= data.get("max_stage", 5)) else (80, 200, 80)
        mmcx = int(cr[0] * CELL_SIZE * scale_x)
        mmcy = int(cr[1] * CELL_SIZE * scale_y)
        pygame.draw.rect(mm_surf, col, (mmcx, mmcy, 3, 3))

    # Trees (dark green)
    for tx2, ty2 in state.get("trees", []):
        pygame.draw.rect(mm_surf, (30, 100, 30), (int(tx2 * CELL_SIZE * scale_x), int(ty2 * CELL_SIZE * scale_y), 3, 3))

    # Fences (brown)
    for fx2, fy2, _ in state.get("fences", []):
        pygame.draw.rect(mm_surf, (139, 90, 43), (int(fx2 * CELL_SIZE * scale_x), int(fy2 * CELL_SIZE * scale_y), 2, 2))

    # Enemies
    if state.get("thief_pos"):
        ex, ey = state["thief_pos"]
        pygame.draw.rect(mm_surf, (255, 50, 50), (int(ex * CELL_SIZE * scale_x) - 2, int(ey * CELL_SIZE * scale_y) - 2, 5, 5))
    if state.get("boar_pos"):
        bx2, by2 = state["boar_pos"]
        pygame.draw.rect(mm_surf, (200, 80, 20), (int(bx2 * CELL_SIZE * scale_x) - 2, int(by2 * CELL_SIZE * scale_y) - 2, 5, 5))

    # Camera viewport rectangle
    vp_x = int(camera_x * scale_x)
    vp_y = int(camera_y * scale_y)
    vp_w = int(WIDTH * scale_x)
    vp_h = int(HEIGHT * scale_y)
    pygame.draw.rect(mm_surf, (255, 255, 255, 160), (vp_x, vp_y, vp_w, vp_h), 1)

    screen.blit(mm_surf, (mm_x, mm_y))
    label = font_tiny.render("地圖", True, (200, 220, 200))
    screen.blit(label, (mm_x + mm_w // 2 - label.get_width() // 2, mm_y - label.get_height() - 2))

    draw_hud(screen, state, current_tool, active_zone)
    draw_shop(screen, state, shop_open, active_tab, mouse_pos)
    draw_game_over(screen, state)
