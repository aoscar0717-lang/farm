import sys
import os
import random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
from src.capstone_contract import new_game, apply_action, is_terminal, ITEM_SIZE, GRID_W, GRID_H, CROP_INFO
from src.sprite_loader import SpriteLoader

sprite_loader = SpriteLoader()

pygame.init()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GREEN = (34, 139, 34)
GRASS_GREEN = (143, 188, 143)
RED = (220, 20, 60)
BLUE = (65, 105, 225)
YELLOW = (255, 215, 0)

CELL_SIZE = 10
MARGIN_TOP = 0
MARGIN_BOTTOM = 0

info = pygame.display.Info()
WIDTH = info.current_w
HEIGHT = info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("農場防禦 - 開放世界沙盒版")

ITEM_PX = CELL_SIZE * ITEM_SIZE
WORLD_W = GRID_W * CELL_SIZE
WORLD_H = GRID_H * CELL_SIZE
bg_surf_left = None
bg_surf_right = None

def get_bg_surfs():
    global bg_surf_left, bg_surf_right
    if bg_surf_left is None:
        TILE_W = 40
        TILE_H = 40
        chunk_w = 400
        chunk_h = 400
        
        # Left: Grass / Dirt
        bg_surf_left = pygame.Surface((chunk_w, chunk_h))
        t_center_left = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Tileset/Tileset Spring.png", 2, 9, 16, 16, (TILE_W, TILE_H))
        
        if t_center_left:
            t_center_var1 = t_center_left.copy()
            pygame.draw.rect(t_center_var1, (90, 150, 60), (10, 10, 4, 2))
            t_center_var2 = t_center_left.copy()
            pygame.draw.circle(t_center_var2, (255, 215, 0), (15, 20), 2)
            t_centers = [t_center_left, t_center_left, t_center_left, t_center_var1, t_center_var2]
            
            random.seed(42)
            for r in range(chunk_h // TILE_H):
                for c in range(chunk_w // TILE_W):
                    bg_surf_left.blit(random.choice(t_centers), (c * TILE_W, r * TILE_H))
            random.seed()
        else:
            bg_surf_left.fill((50, 100, 50))
            
        # Right: Yard / Stone
        bg_surf_right = pygame.Surface((chunk_w, chunk_h))
        
        if t_center_left:
            t_center_right = t_center_left.copy()
            # Tint it darker to look like dirt/stone
            t_center_right.fill((180, 150, 120), special_flags=pygame.BLEND_RGBA_MULT)
            
            t_centers_r = [t_center_right]
            for r in range(chunk_h // TILE_H):
                for c in range(chunk_w // TILE_W):
                    bg_surf_right.blit(random.choice(t_centers_r), (c * TILE_W, r * TILE_H))
        else:
            bg_surf_right.fill((120, 100, 70))

    return bg_surf_left, bg_surf_right

try:
    font_large = pygame.font.SysFont("microsoftjhenghei", 36)
    font_small = pygame.font.SysFont("microsoftjhenghei", 24)
    font_tiny = pygame.font.SysFont("microsoftjhenghei", 18)
except:
    font_large = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 32)
    font_tiny = pygame.font.Font(None, 24)

TICK_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(TICK_EVENT, 1000)

assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)

images = {}

def load_image(filename, target_size=(ITEM_PX, ITEM_PX)):
    filepath = os.path.join(assets_dir, filename)
    if os.path.exists(filepath):
        img = pygame.image.load(filepath).convert_alpha()
        img = pygame.transform.scale(img, target_size)
        width, height = img.get_size()
        visited = set()
        queue = [(0, 0), (width-1, 0), (0, height-1), (width-1, height-1)]
        while queue:
            x, y = queue.pop(0)
            if (x, y) in visited: continue
            if x < 0 or x >= width or y < 0 or y >= height: continue
            visited.add((x, y))
            r, g, b, a = img.get_at((x, y))
            if r > 240 and g > 240 and b > 240:
                img.set_at((x, y), (255, 255, 255, 0))
                queue.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        return img
    return None

images["thief"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png", 0, 0, 32, 32, (60, 60))
images["fence"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Fence's copiar.png", 0, 0, 16, 16, (60, 60))
images["dog"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Male Cow Brown.png", 0, 0, 32, 32, (60, 60))
images["cat"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png", 0, 0, 16, 16, (60, 60))
images["goose"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Chicken Red.png", 0, 0, 16, 16, (60, 60))
images["owl"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Chicken Blonde  Green.png", 0, 0, 16, 16, (60, 60))
images["scarecrow"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (60, 60))
images["strawberry"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 5, 16, 16, (60, 60))
images["radish"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, 5, 16, 16, (60, 60))
images["carrot"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 5, 5, 16, 16, (60, 60))
images["onion"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 7, 5, 16, 16, (60, 60))
tool_sprite = "Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Objects/Basic_tools_and_meterials.png"
images["hoe"] = sprite_loader.get_sprite(tool_sprite, 0, 0, 16, 16, (60, 60))
images["axe"] = sprite_loader.get_sprite(tool_sprite, 0, 1, 16, 16, (60, 60))
images["pickaxe"] = sprite_loader.get_sprite(tool_sprite, 0, 2, 16, 16, (60, 60))
images["shovel"] = sprite_loader.get_sprite(tool_sprite, 0, 3, 16, 16, (60, 60))
images["scythe"] = sprite_loader.get_sprite(tool_sprite, 0, 4, 16, 16, (60, 60))
images["wood"] = sprite_loader.get_sprite(tool_sprite, 1, 0, 16, 16, (60, 60))
images["fertilizer"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, 12, 16, 16, (60, 60))

shop_bg_path = os.path.join(assets_dir, "Sprout Lands UI Pack/Sprout Lands - UI Pack - Basic pack/Sprite sheets/Setting menu.png")
if os.path.exists(shop_bg_path):
    try:
        images["shop_bg"] = pygame.image.load(shop_bg_path).convert_alpha()
    except:
        pass

grass_pattern = pygame.Surface((200, 200))
grass_pattern.fill((168, 213, 117))
for _ in range(15):
    gx = random.randint(0, 199)
    gy = random.randint(0, 199)
    pygame.draw.circle(grass_pattern, (148, 195, 97), (gx, gy), random.randint(5, 12))
for _ in range(20):
    fx = random.randint(0, 199)
    fy = random.randint(0, 199)
    f_color = (255, 215, 0) if random.random() > 0.5 else (255, 255, 255)
    pygame.draw.circle(grass_pattern, f_color, (fx, fy), 2)
for _ in range(20):
    sx = random.randint(0, 199)
    sy = random.randint(0, 199)
    pygame.draw.rect(grass_pattern, (150, 150, 150), (sx, sy, 3, 2))

camera_x = (WORLD_W - WIDTH) // 2
camera_y = (WORLD_H - HEIGHT) // 2

TOOL_NAMES = {
    "radish": "白蘿蔔種子", "corn": "甜玉米種子", "pumpkin": "魔法南瓜種子",
    "stone_path": "石板路", "flower": "鮮花盆栽", "bench": "木製長椅", "fountain": "小型噴泉",
    "fence": "木圍欄", "trap": "捕獸夾",
    "dog": "看門狗", 
    "fertilizer": "魔法肥料", "shovel": "鐵鏟 (免費)", "axe": "斧頭", "pickaxe": "十字鎬",
    "hoe": "鋤頭 (開墾)", "scythe": "鐮刀 (收割)"
}

def is_cell_occupied(state, gx, gy):
    pos = (gx, gy)
    if pos in state.get("crops", []): return True
    if any(f[0] == gx and f[1] == gy for f in state.get("fences", [])): return True
    if pos in state.get("trees", []): return True
    if pos in state.get("rocks", []): return True
    if pos in state.get("dogs", []): return True
    if pos in state.get("traps", []): return True
    if any(d[0] == gx and d[1] == gy for d in state.get("decorations", [])): return True
    for t in state.get("building_tasks", []):
        if t["pos"] == pos: return True
    return False

def draw_board(state, current_tool, mouse_pos, shop_open, active_tab):
    screen.fill(BLACK)
    
    bg_left, bg_right = get_bg_surfs()
    pw, ph = bg_left.get_size()
    
    split_screen_x = 50 * CELL_SIZE * (ITEM_PX // CELL_SIZE) - camera_x
    # ITEM_PX = CELL_SIZE * ITEM_SIZE = 10 * 10 = 100
    # Wait, 50 * 10 = 500. So 500 * (10) = 5000? 
    # Let me check: x is 0..100. screen_x = x * CELL_SIZE - camera_x.
    # Ah, x is actual grid cell (0, 10, 20...). But in contract x goes up to GRID_W=100.
    # So split is x=50. screen_x = 50 * CELL_SIZE - camera_x.
    split_screen_x = 50 * CELL_SIZE - camera_x
    
    if split_screen_x > 0:
        left_rect = pygame.Rect(0, 0, min(WIDTH, split_screen_x), HEIGHT)
        screen.set_clip(left_rect)
        for y in range(- (camera_y % ph), HEIGHT, ph):
            for x in range(- (camera_x % pw), WIDTH, pw):
                screen.blit(bg_left, (x, y))
                
    if split_screen_x < WIDTH:
        right_rect = pygame.Rect(max(0, split_screen_x), 0, WIDTH - max(0, split_screen_x), HEIGHT)
        screen.set_clip(right_rect)
        for y in range(- (camera_y % ph), HEIGHT, ph):
            for x in range(- (camera_x % pw), WIDTH, pw):
                screen.blit(bg_right, (x, y))
                
    screen.set_clip(None)
    
    # 畫出楚河漢界 (中線)
    if 0 <= split_screen_x <= WIDTH:
        pygame.draw.line(screen, (200, 150, 50), (split_screen_x, 0), (split_screen_x, HEIGHT), 4)
    
    def draw_obj(pos, img, backup_color, shape="rect"):
        x, y = pos
        screen_x = x * CELL_SIZE - camera_x
        screen_y = y * CELL_SIZE - camera_y
        
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
    tree_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Maple Tree.png", 0, 3, 32, 48, (int(ITEM_PX * 1.5), int(ITEM_PX * 2.25)))
    for tx, ty in state.get("trees", []):
        screen_x = tx * CELL_SIZE - camera_x
        screen_y = ty * CELL_SIZE - camera_y
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
    rock_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 0, 0, 16, 16, (ITEM_PX, ITEM_PX))
    for rx, ry in state.get("rocks", []):
        screen_x = rx * CELL_SIZE - camera_x
        screen_y = ry * CELL_SIZE - camera_y
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            if rock_img:
                screen.blit(rock_img, (screen_x, screen_y))
            else:
                rect = pygame.Rect(screen_x + 10, screen_y + 30, ITEM_PX - 20, ITEM_PX - 30)
                pygame.draw.ellipse(screen, (105, 105, 105), rect)

    # Draw Farmland (beneath crops)
    for fx, fy in state.get("farmland", []):
        cx = fx * CELL_SIZE - camera_x
        cy = fy * CELL_SIZE - camera_y
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT: continue
        rect = pygame.Rect(cx, cy, ITEM_PX, ITEM_PX)
        pygame.draw.rect(screen, (101, 67, 33), rect) # Dirt
        pygame.draw.rect(screen, (80, 50, 20), rect, 2)

    # Draw Crops
    for crop in state["crops"]:
        data = state["crop_data"].get(crop)
        if not data: continue
        cx = crop[0] * CELL_SIZE - camera_x
        cy = crop[1] * CELL_SIZE - camera_y
        
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT:
            continue
            
        c_type = data.get("type", "strawberry")
        img_row = {"strawberry": 1, "radish": 3, "carrot": 5, "onion": 7}.get(c_type, 1)
        
        # Calculate visual stage based on days passed + current day progress
        max_stage = data.get("max_stage", 1)
        current_day_progress = 0.0
        if state["phase"] == "day" and data["stage"] < max_stage:
            current_day_progress = max(0.0, min(1.0, (120 - state.get("time_left", 120)) / 120.0))
        elif data["stage"] >= max_stage:
            current_day_progress = 0.0
            
        total_progress = min(max_stage, data["stage"] + current_day_progress)
        cstage = int((total_progress / max(1, max_stage)) * 5)
        cstage = max(0, min(5, cstage))
        
        crop_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", img_row, cstage, 16, 16, (ITEM_PX, ITEM_PX))
        
        if crop_img:
            screen.blit(crop_img, (cx, cy))
        else:
            # Fallback
            c_color = RED if c_type == "strawberry" else (WHITE if c_type == "radish" else ((255, 165, 0) if c_type == "carrot" else (200, 200, 100)))
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
    scarecrow_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (ITEM_PX, ITEM_PX))
    for sx, sy in state.get("scarecrows", []):
        cx = sx * CELL_SIZE - camera_x
        cy = sy * CELL_SIZE - camera_y
        if scarecrow_img:
            screen.blit(scarecrow_img, (cx, cy))

    # Draw Fences
    fence_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Fence's copiar.png", 0, 0, 16, 16, (ITEM_PX, ITEM_PX))
    for fx, fy in state.get("fences", []):
        screen_x = fx * CELL_SIZE - camera_x
        screen_y = fy * CELL_SIZE - camera_y
        if fence_img:
            screen.blit(fence_img, (screen_x, screen_y))
        else:
            pygame.draw.rect(screen, (139, 69, 19), (screen_x + 5, screen_y + 5, ITEM_PX - 10, ITEM_PX - 10))
            pygame.draw.rect(screen, (160, 82, 45), (screen_x + 10, screen_y + 10, ITEM_PX - 20, ITEM_PX - 20))

    # 畫出陷阱
    for tx, ty in state.get("traps", []):
        screen_x = tx * CELL_SIZE - camera_x
        screen_y = ty * CELL_SIZE - camera_y
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            pygame.draw.rect(screen, (100, 100, 100), (screen_x + 10, screen_y + ITEM_PX - 20, ITEM_PX - 20, 20))
            pygame.draw.line(screen, (200, 0, 0), (screen_x + 20, screen_y + ITEM_PX - 10), (screen_x + ITEM_PX - 20, screen_y + ITEM_PX - 10), 3)
            
    # 畫出景觀物
    for d in state.get("decorations", []):
        dx, dy, dtype, hp = d
        screen_x = dx * CELL_SIZE - camera_x
        screen_y = dy * CELL_SIZE - camera_y
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            if dtype == "stone_path":
                pygame.draw.rect(screen, (150, 150, 150), (screen_x, screen_y, ITEM_PX, ITEM_PX))
            elif dtype == "flower":
                pygame.draw.rect(screen, (139, 69, 19), (screen_x + 10, screen_y + 20, ITEM_PX - 20, ITEM_PX - 20))
                pygame.draw.circle(screen, (255, 105, 180), (screen_x + ITEM_PX // 2, screen_y + 10), 20)
            elif dtype == "bench":
                pygame.draw.rect(screen, (205, 133, 63), (screen_x + 10, screen_y + 30, ITEM_PX - 20, 20))
                pygame.draw.rect(screen, (139, 69, 19), (screen_x + 10, screen_y + 10, 10, 40))
                pygame.draw.rect(screen, (139, 69, 19), (screen_x + ITEM_PX - 20, screen_y + 10, 10, 40))
            elif dtype == "fountain":
                pygame.draw.circle(screen, (200, 200, 200), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), 40)
                pygame.draw.circle(screen, (65, 105, 225), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), 30)

    # 畫出寵物 (只保留狗，移除貓跟鵝跟貓頭鷹)
    import time
    anim_frame = int(time.time() * 4) % 4
    
    dog_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Male Cow Brown.png", 0, anim_frame, 32, 32, (int(ITEM_PX*1.5), int(ITEM_PX*1.5)))
    for dx, dy in state.get("dogs", []):
        if dog_img:
            screen.blit(dog_img, (dx * CELL_SIZE - camera_x - ITEM_PX//4, dy * CELL_SIZE - camera_y - ITEM_PX//4))
        else:
            pygame.draw.circle(screen, (205, 133, 63), (dx * CELL_SIZE - camera_x + ITEM_PX // 2, dy * CELL_SIZE - camera_y + ITEM_PX // 2), ITEM_PX // 2)

    # Draw Thief
    if state["thief_pos"] is not None:
        tx, ty = state["thief_pos"]
        screen_x = int(tx * CELL_SIZE) - camera_x
        screen_y = int(ty * CELL_SIZE) - camera_y
        
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
        
        thief_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png", thief_dir_row, int(time.time() * 6) % 6, 32, 32, (int(ITEM_PX*1.5), int(ITEM_PX*1.5)))
        if thief_img:
            if flip_x:
                thief_img = pygame.transform.flip(thief_img, True, False)
            screen.blit(thief_img, (screen_x - ITEM_PX//4, screen_y - ITEM_PX//2))
        else:
            pygame.draw.circle(screen, RED, (screen_x + ITEM_PX//2, screen_y + ITEM_PX//2), ITEM_PX // 2)
            
        hp = state.get("thief_hp", 3)
        pygame.draw.rect(screen, RED, (screen_x, screen_y - 10, ITEM_PX, 6))
    # Draw Boar
    if state.get("boar_pos"):
        bx, by = state["boar_pos"]
        screen_x = int(bx * CELL_SIZE) - camera_x
        screen_y = int(by * CELL_SIZE) - camera_y
        
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
                
        boar_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Pig Pink.png", boar_dir_row, int(time.time() * 6) % 4, 16, 16, (int(ITEM_PX*1.5), int(ITEM_PX*1.5)))
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
            
            screen_x = gx * CELL_SIZE - camera_x
            screen_y = gy * CELL_SIZE - camera_y
            
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
        
    # 畫建造中的項目
    for task in state.get("building_tasks", []):
        x, y = task["pos"]
        screen_x = x * CELL_SIZE - camera_x
        screen_y = y * CELL_SIZE - camera_y
        
        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT:
            continue
            
        rect = pygame.Rect(screen_x, screen_y, ITEM_PX, ITEM_PX)
        progress_ratio = task["progress"] / task["max_progress"]
        h = int(ITEM_PX * progress_ratio)
        if h <= 0: h = 1
        
        img = None
        t_type = task["type"]
        if t_type == "dog": img = images.get("dog")
        elif t_type == "cat": img = images.get("cat")
        elif t_type == "goose": img = images.get("goose")
        elif t_type == "owl": img = images.get("owl")
        elif t_type == "fence": img = images.get("fence")
            
        if img:
            scaled_img = pygame.transform.scale(img, (ITEM_PX, ITEM_PX))
            scaled_img.set_alpha(150)
            crop_rect = pygame.Rect(0, ITEM_PX - h, ITEM_PX, h)
            screen.blit(scaled_img, (rect.x, rect.y + ITEM_PX - h), crop_rect)
        elif t_type == "crop":
            pygame.draw.rect(screen, (101, 67, 33), (rect.x, rect.y + ITEM_PX - h, ITEM_PX, h))
            
        b_text = font_tiny.render("building", True, WHITE)
        screen.blit(b_text, (rect.centerx - b_text.get_width()//2, rect.centery - b_text.get_height()//2))

    # Top Panel
    top_panel = pygame.Surface((WIDTH - 40, 80), pygame.SRCALPHA)
    pygame.draw.rect(top_panel, (0, 0, 0, 180), top_panel.get_rect(), border_radius=15)
    screen.blit(top_panel, (20, 20))
    
    mins = state['time_left'] // 60
    secs = state['time_left'] % 60
    phase_str = "白天" if state['phase'] == "day" else "夜晚"
    phase_text = f"第 {state['day_count']} 回合 - {phase_str} ({mins:02d}:{secs:02d})"
    text_surf = font_large.render(phase_text, True, WHITE)
    screen.blit(text_surf, (40, 30))
    
    pet_stats = f"木材: {state.get('wood', 0)}   石材: {state.get('stone', 0)}   狗: {len(state.get('dogs',[]))}/10   繁榮度: {state.get('prosperity_score',0)}   農場等級: Lv{state.get('farm_level',1)}"
    pet_surf = font_small.render(pet_stats, True, (200, 200, 255))
    screen.blit(pet_surf, (40, 65))
    
    rent = 20 + (state["day_count"] - 1) * 10
    money_surf = font_small.render(f"資金: ${state['money']} (今晚租金: ${rent})", True, YELLOW)
    screen.blit(money_surf, (WIDTH - money_surf.get_width() - 40, 35))
    
    # Bottom Panel
    bottom_panel = pygame.Surface((WIDTH - 40, 80), pygame.SRCALPHA)
    pygame.draw.rect(bottom_panel, (0, 0, 0, 180), bottom_panel.get_rect(), border_radius=15)
    screen.blit(bottom_panel, (20, HEIGHT - 100))
    
    msg = state.get("last_msg", "")
    msg_surf = font_small.render(msg, True, WHITE)
    screen.blit(msg_surf, (40, HEIGHT - 85))
    
    help_text = "[空白]: 進入夜晚  [B]: 打開商店  [WASD/右鍵]: 移動視角"
    help_surf = font_tiny.render(help_text, True, (200, 200, 200))
    screen.blit(help_surf, (40, HEIGHT - 45))
    
    tool_text = f"裝備中: {TOOL_NAMES.get(current_tool, current_tool)}" if current_tool else "一般模式 (點擊右鍵/ESC取消裝備)"
    indicator = font_small.render(tool_text, True, WHITE)
    screen.blit(indicator, (WIDTH - indicator.get_width() - 40, HEIGHT - 85))
    
    # Shop UI
    if shop_open:
        shop_surf = pygame.Surface((WIDTH, HEIGHT))
        shop_surf.set_alpha(150)
        shop_surf.fill(BLACK)
        screen.blit(shop_surf, (0, 0))
        
        shop_w = 1180
        shop_h = 700
        shop_x = (WIDTH - shop_w) // 2
        shop_y = (HEIGHT - shop_h) // 2
        shop_rect = pygame.Rect(shop_x, shop_y, shop_w, shop_h)
        
        bg_img = images.get("shop_bg")
        if bg_img:
            screen.blit(pygame.transform.scale(bg_img, (shop_w, shop_h)), shop_rect.topleft)
        else:
            pygame.draw.rect(screen, (245, 245, 250), shop_rect, border_radius=15)
            
        is_sell = active_tab == "sell"
        
        left_page_x = shop_x + 90
        left_page_w = 400
        right_page_x = shop_x + 675
        right_page_w = 400
        
        tab_buy = pygame.Rect(left_page_x, shop_y + 110, left_page_w, 45)
        tab_sell = pygame.Rect(right_page_x, shop_y + 110, right_page_w, 45)
        
        # Patch out the "SETTINGS" word from the background image
        patch_rect = pygame.Rect(left_page_x, shop_y + 80, left_page_w, 80)
        pygame.draw.rect(screen, (220, 185, 138), patch_rect)
        
        pygame.draw.rect(screen, BLUE if not is_sell else GRAY, tab_buy, border_radius=10)
        pygame.draw.rect(screen, BLUE if is_sell else GRAY, tab_sell, border_radius=10)
        
        tb_surf = font_small.render("購買道具", True, WHITE)
        ts_surf = font_small.render("出售作物", True, WHITE)
        screen.blit(tb_surf, (tab_buy.centerx - tb_surf.get_width()//2, tab_buy.centery - tb_surf.get_height()//2))
        screen.blit(ts_surf, (tab_sell.centerx - ts_surf.get_width()//2, tab_sell.centery - ts_surf.get_height()//2))
        
        if not is_sell:
            sub_w = (left_page_w - 30) // 4
            tab_seed = pygame.Rect(left_page_x, shop_y + 165, sub_w, 30)
            tab_def = pygame.Rect(left_page_x + sub_w + 10, shop_y + 165, sub_w, 30)
            tab_pet = pygame.Rect(left_page_x + (sub_w + 10)*2, shop_y + 165, sub_w, 30)
            tab_tool = pygame.Rect(left_page_x + (sub_w + 10)*3, shop_y + 165, sub_w, 30)
            
            pygame.draw.rect(screen, (100, 150, 255) if active_tab == "seed" else (200,200,200), tab_seed, border_radius=5)
            pygame.draw.rect(screen, (100, 150, 255) if active_tab == "def" else (200,200,200), tab_def, border_radius=5)
            pygame.draw.rect(screen, (100, 150, 255) if active_tab == "pet" else (200,200,200), tab_pet, border_radius=5)
            pygame.draw.rect(screen, (100, 150, 255) if active_tab == "tool" else (200,200,200), tab_tool, border_radius=5)
            
            sub1 = font_tiny.render("種子", True, BLACK)
            sub2 = font_tiny.render("防禦", True, BLACK)
            sub3 = font_tiny.render("景觀", True, BLACK)
            sub4 = font_tiny.render("工具", True, BLACK)
            sub4 = font_tiny.render("工具", True, BLACK)
            screen.blit(sub1, (tab_seed.centerx - sub1.get_width()//2, tab_seed.centery - sub1.get_height()//2))
            screen.blit(sub2, (tab_def.centerx - sub2.get_width()//2, tab_def.centery - sub2.get_height()//2))
            screen.blit(sub3, (tab_pet.centerx - sub3.get_width()//2, tab_pet.centery - sub3.get_height()//2))
            screen.blit(sub4, (tab_tool.centerx - sub4.get_width()//2, tab_tool.centery - sub4.get_height()//2))
            
            items = []
            if active_tab == "seed":
                items = [
                    {"id": "radish", "name": "白蘿蔔種子", "price": 30, "desc": "1天熟，產量50"},
                    {"id": "corn", "name": "甜玉米種子", "price": 100, "desc": "Lv2解鎖，產量250"},
                    {"id": "pumpkin", "name": "魔法南瓜種子", "price": 300, "desc": "Lv3解鎖，產量1000"}
                ]
            elif active_tab == "def":
                items = [
                    {"id": "fence", "name": "木圍欄", "price": "1 木材", "desc": "實體障礙，需木材"},
                    {"id": "trap", "name": "捕獸夾", "price": 50, "desc": "對敵人造成傷害"},
                    {"id": "dog", "name": "看門狗", "price": "FREE" if state.get("free_dog") else 200, "desc": "主動攻擊附近的敵人"}
                ]
            elif active_tab == "pet":
                # Changing pet tab to "Decor" tab
                items = [
                    {"id": "stone_path", "name": "石板路", "price": 20, "desc": "繁榮度 +5"},
                    {"id": "flower", "name": "鮮花盆栽", "price": 50, "desc": "繁榮度 +15"},
                    {"id": "bench", "name": "木製長椅", "price": 100, "desc": "繁榮度 +35"},
                    {"id": "fountain", "name": "小型噴泉", "price": 300, "desc": "繁榮度 +120"}
                ]
            elif active_tab == "tool" or active_tab not in ["seed", "def", "pet"]:
                items = [
                    {"id": "hoe", "name": "鋤頭", "price": "FREE", "desc": "將草地開墾成農田(左側)"},
                    {"id": "scythe", "name": "鐮刀", "price": "FREE", "desc": "收割成熟的作物"},
                    {"id": "axe", "name": "斧頭", "price": "FREE", "desc": "砍樹獲得木材"},
                    {"id": "pickaxe", "name": "十字鎬", "price": "FREE", "desc": "敲石頭獲得石材"},
                    {"id": "shovel", "name": "鐵鏟", "price": "FREE", "desc": "移除地上的物件"},
                    {"id": "fertilizer", "name": "魔法肥料", "price": 80, "desc": "瞬間成熟"}
                ]
                
            left_items = items[:(len(items)+1)//2]
            right_items = items[(len(items)+1)//2:]
            
            for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 210), (right_items, right_page_x, shop_y + 170)]:
                y_offset = start_y
                for item in page_items:
                    card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                    card_surf = pygame.Surface((left_page_w, 65), pygame.SRCALPHA)
                    pygame.draw.rect(card_surf, (255, 255, 255, 100), card_surf.get_rect(), border_radius=10)
                    screen.blit(card_surf, card_rect.topleft)
                    
                    img = images.get(item["id"])
                    if img:
                        screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))
                    else:
                        pygame.draw.rect(screen, (220, 220, 220), (card_rect.x + 10, card_rect.y + 12, 40, 40), border_radius=5)
                        fb_text = font_tiny.render(item["name"][:2], True, (100, 100, 100))
                        screen.blit(fb_text, (card_rect.x + 30 - fb_text.get_width()//2, card_rect.y + 32 - fb_text.get_height()//2))
                        
                    n_surf = font_small.render(item["name"], True, BLACK)
                    screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))
                    
                    d_surf = font_tiny.render(item["desc"], True, (80, 80, 80))
                    screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))
                    
                    p_str = f"${item['price']}" if isinstance(item['price'], int) else str(item['price'])
                    p_surf = font_small.render(p_str, True, YELLOW if item['price'] != "FREE" else RED)
                    screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))
                    
                    if card_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)
                    
                    y_offset += 75
        else:
            grades = ["normal", "rare", "epic", "legendary"]
            grades_tw = {"normal": "一般", "rare": "稀有", "epic": "史詩", "legendary": "傳奇"}
            multipliers = {"normal": 1, "rare": 2, "epic": 3, "legendary": 5}
            
            sellable = []
            for c_id, c_name in [("radish", "白蘿蔔"), ("corn", "甜玉米"), ("pumpkin", "魔法南瓜")]:
                base_price = CROP_INFO[c_id]["yield"] if c_id in CROP_INFO else 100
                for grade in grades:
                    count = state["inventory"].get(c_id, {}).get(grade, 0)
                    if count > 0:
                        sellable.append({"id": c_id, "name": f"{c_name} ({grades_tw[grade]})", "count": count, "price": base_price * multipliers[grade], "grade": grade})
                        
            left_items = sellable[:6]
            right_items = sellable[6:12]
            
            for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 170), (right_items, right_page_x, shop_y + 170)]:
                y_offset = start_y
                for item in page_items:
                    card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                    card_surf = pygame.Surface((left_page_w, 65), pygame.SRCALPHA)
                    pygame.draw.rect(card_surf, (255, 255, 255, 100), card_surf.get_rect(), border_radius=10)
                    screen.blit(card_surf, card_rect.topleft)
                    
                    img = images.get(item["id"])
                    if img:
                        screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))
                    
                    n_surf = font_small.render(f"{item['name']} x{item['count']}", True, BLACK)
                    screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))
                    
                    d_surf = font_tiny.render("點擊賣出 1 個", True, (80, 80, 80))
                    screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))
                    
                    p_surf = font_small.render(f"+${item['price']}", True, (50, 205, 50))
                    screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))
                    
                    if card_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)
                    
                    y_offset += 75
            
    if is_terminal(state):
        s = pygame.Surface((WIDTH, HEIGHT))
        s.set_alpha(200)
        s.fill(BLACK)
        screen.blit(s, (0, 0))
        
        res_surf = font_large.render("GAME OVER", True, RED)
        res_rect = res_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
        screen.blit(res_surf, res_rect)
        
        info_surf = font_small.render(f"你總共生存了 {state['day_count'] - 1} 天", True, WHITE)
        info_rect = info_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        screen.blit(info_surf, info_rect)

def play():
    global camera_x, camera_y
    state = new_game()
    clock = pygame.time.Clock()
    current_tool = None
    shop_open = False
    active_tab = "seed"
    
    pygame.mouse.get_rel()
    
    last_night_tick = 0
    night_tick_delay = 33
    
    night_filter = pygame.Surface((WIDTH, HEIGHT - MARGIN_TOP - MARGIN_BOTTOM))
    night_filter.set_alpha(100)
    night_filter.fill((0, 0, 80))
    
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
                
            if event.type == TICK_EVENT:
                if not is_terminal(state):
                    state = apply_action(state, "tick")
                
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3: # Right click to cancel tool
                    current_tool = None
                elif event.button == 1:
                    if not is_terminal(state):
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
                                        sub_w = (left_page_w - 30) // 4
                                        tab_seed = pygame.Rect(left_page_x, shop_y + 165, sub_w, 30)
                                        tab_def = pygame.Rect(left_page_x + sub_w + 10, shop_y + 165, sub_w, 30)
                                        tab_pet = pygame.Rect(left_page_x + (sub_w + 10)*2, shop_y + 165, sub_w, 30)
                                        tab_tool = pygame.Rect(left_page_x + (sub_w + 10)*3, shop_y + 165, sub_w, 30)
                                        
                                        if tab_seed.collidepoint(mx, my): active_tab = "seed"
                                        elif tab_def.collidepoint(mx, my): active_tab = "def"
                                        elif tab_pet.collidepoint(mx, my): active_tab = "pet"
                                        elif tab_tool.collidepoint(mx, my): active_tab = "tool"
                                        else:
                                            items = []
                                            if active_tab == "seed": items = [{"id": "strawberry", "name": "草莓種子", "price": 30}, {"id": "radish", "name": "櫻桃蘿蔔種子", "price": 50}, {"id": "carrot", "name": "胡蘿蔔種子", "price": 100}, {"id": "onion", "name": "洋蔥種子", "price": 200}]
                                            elif active_tab == "def": items = [{"id": "fence", "name": "木圍欄", "price": "1 木材"}, {"id": "scarecrow", "name": "稻草人", "price": 150}]
                                            elif active_tab == "pet": items = [{"id": "dog", "name": "看門狗", "price": 200}, {"id": "cat", "name": "招財貓", "price": 150}, {"id": "goose", "name": "大白鵝", "price": 300}, {"id": "owl", "name": "貓頭鷹", "price": 250}]
                                            elif active_tab == "tool" or active_tab not in ["seed", "def", "pet"]: items = [{"id": "hoe", "name": "鋤頭", "price": "FREE"}, {"id": "scythe", "name": "鐮刀", "price": "FREE"}, {"id": "axe", "name": "斧頭", "price": "FREE"}, {"id": "pickaxe", "name": "十字鎬", "price": "FREE"}, {"id": "shovel", "name": "鐵鏟", "price": "FREE"}, {"id": "fertilizer", "name": "魔法肥料", "price": 80}]
                                            
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
                                        for c_id, c_name in [("strawberry", "草莓"), ("radish", "櫻桃蘿蔔"), ("carrot", "胡蘿蔔"), ("onion", "洋蔥")]:
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
                            if my >= MARGIN_TOP and my < HEIGHT - MARGIN_BOTTOM:
                                gx = (mx + camera_x - ITEM_PX // 2) // CELL_SIZE
                                gy = (my - MARGIN_TOP + camera_y - ITEM_PX // 2) // CELL_SIZE
                                
                                if state["phase"] == "night" and state["thief_pos"] is not None:
                                    tx, ty = state["thief_pos"]
                                    if tx <= gx + ITEM_SIZE//2 < tx + ITEM_SIZE and ty <= gy + ITEM_SIZE//2 < ty + ITEM_SIZE:
                                        state = apply_action(state, f"click_{tx}_{ty}")
                                        continue
                                        
                                if current_tool == "fence": state = apply_action(state, f"build_fence_{gx}_{gy}")
                                elif current_tool == "trap": state = apply_action(state, f"place_trap_{gx}_{gy}")
                                elif current_tool in ["stone_path", "flower", "bench", "fountain"]: state = apply_action(state, f"build_decor_{current_tool}_{gx}_{gy}")
                                elif current_tool in ["radish", "corn", "pumpkin"]: state = apply_action(state, f"plant_crop_{current_tool}_{gx}_{gy}")
                                elif current_tool == "fertilizer": state = apply_action(state, f"use_fertilizer_{gx}_{gy}")
                                elif current_tool == "shovel": state = apply_action(state, f"use_shovel_{gx}_{gy}")
                                elif current_tool == "axe": state = apply_action(state, f"use_axe_{gx}_{gy}")
                                elif current_tool == "pickaxe": state = apply_action(state, f"use_pickaxe_{gx}_{gy}")
                                elif current_tool == "hoe": state = apply_action(state, f"use_hoe_{gx}_{gy}")
                                elif current_tool == "scythe": state = apply_action(state, f"use_scythe_{gx}_{gy}")
                                elif current_tool == "dog": state = apply_action(state, f"place_dog_{gx}_{gy}")
                                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_tool = None
                    shop_open = False
                elif event.key == pygame.K_SPACE:
                    if not is_terminal(state): state = apply_action(state, "start_night")
                elif event.key == pygame.K_r: state = new_game()
                elif event.key == pygame.K_b: shop_open = not shop_open
                elif event.key == pygame.K_1: current_tool = "fence"
                elif event.key == pygame.K_2: current_tool = "dog"
                elif event.key == pygame.K_3: current_tool = "radish"

        keys = pygame.key.get_pressed()
        cam_speed = 15
        if keys[pygame.K_w] or keys[pygame.K_UP]: camera_y -= cam_speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: camera_y += cam_speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: camera_x -= cam_speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: camera_x += cam_speed
        
        mouse_buttons = pygame.mouse.get_pressed()
        if mouse_buttons[2]:
            mx, my = pygame.mouse.get_rel()
            camera_x -= mx
            camera_y -= my
        else:
            pygame.mouse.get_rel()
            
        # 在開放世界中不再限制相機邊界，相機可以無限移動
        
        if state["phase"] == "night" and not is_terminal(state):
            current_time = pygame.time.get_ticks()
            if current_time - last_night_tick > night_tick_delay:
                state = apply_action(state, "night_tick")
                last_night_tick = current_time

        draw_board(state, current_tool, mouse_pos, shop_open, active_tab)
        
        if state["phase"] == "night":
            screen.blit(night_filter, (0, 0))
            
        pygame.display.flip()
        clock.tick(30)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    play()
