import sys
import os
import random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pygame
from src.capstone_contract import new_game, apply_action, is_terminal, ITEM_SIZE, GRID_W, GRID_H

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

images["thief"] = load_image("thief.jpg")
images["fence"] = load_image("fence.jpg")
images["dog"] = load_image("dog.jpg")
images["cat"] = load_image("cat.jpg")
images["goose"] = load_image("goose.jpg")
images["owl"] = load_image("owl.jpg")

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
    "tomato": "番茄種子", "carrot": "紅蘿蔔種子", "corn": "玉米種子", "pumpkin": "南瓜種子",
    "fence": "木圍欄", "scarecrow": "稻草人",
    "dog": "看門狗", "cat": "招財貓", "goose": "大白鵝", "owl": "貓頭鷹",
    "fertilizer": "魔法肥料", "shovel": "鐵鏟"
}

def draw_board(state, current_tool, mouse_pos, shop_open, active_tab):
    screen.fill(BLACK)
    
    # 讓草地填滿整個螢幕，不受限於世界邊界
    for y in range(- (camera_y % 200), HEIGHT, 200):
        for x in range(- (camera_x % 200), WIDTH, 200):
            screen.blit(grass_pattern, (x, y))
            
    # 畫出世界邊界
    world_rect = pygame.Rect(-camera_x, -camera_y, WORLD_W, WORLD_H)
    pygame.draw.rect(screen, (50, 100, 50), world_rect, 5)
    
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

    # Draw Crops
    for crop in state["crops"]:
        data = state["crop_data"].get(crop)
        if not data: continue
        cx = crop[0] * CELL_SIZE - camera_x
        cy = crop[1] * CELL_SIZE - camera_y
        
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT:
            continue
            
        rect = pygame.Rect(cx, cy, ITEM_PX, ITEM_PX)
        pygame.draw.rect(screen, (101, 67, 33), rect) # Dirt
        pygame.draw.rect(screen, (80, 50, 20), rect, 2)
        
        stage = data["stage"]
        max_stage = data["max_stage"]
        ctype = data["type"]
        
        center = rect.center
        if stage == 0:
            # Seedling
            pygame.draw.circle(screen, (144, 238, 144), (center[0]-8, center[1]+8), 6)
            pygame.draw.circle(screen, (144, 238, 144), (center[0]+8, center[1]+8), 6)
        elif stage > 0 and stage < max_stage:
            # Growing
            pygame.draw.circle(screen, (50, 205, 50), (center[0], center[1]), 12)
            pygame.draw.circle(screen, (50, 205, 50), (center[0]-12, center[1]+10), 10)
            pygame.draw.circle(screen, (50, 205, 50), (center[0]+12, center[1]+10), 10)
        else:
            # Mature
            if ctype == "tomato":
                pygame.draw.circle(screen, (255, 99, 71), center, 18)
                pygame.draw.circle(screen, (34, 139, 34), (center[0], center[1]-15), 5)
            elif ctype == "carrot":
                pygame.draw.polygon(screen, (255, 140, 0), [(center[0], center[1]+18), (center[0]-10, center[1]-12), (center[0]+10, center[1]-12)])
                pygame.draw.circle(screen, (34, 139, 34), (center[0], center[1]-18), 6)
            elif ctype == "corn":
                pygame.draw.ellipse(screen, (255, 215, 0), (center[0]-10, center[1]-18, 20, 36))
                pygame.draw.polygon(screen, (154, 205, 50), [(center[0], center[1]+18), (center[0]-15, center[1]), (center[0]-5, center[1]+18)])
            elif ctype == "pumpkin":
                pygame.draw.circle(screen, (255, 127, 80), center, 22)
                pygame.draw.arc(screen, (200, 100, 50), (center[0]-18, center[1]-18, 36, 36), 0, 3.14, 2)
                pygame.draw.rect(screen, (34, 139, 34), (center[0]-2, center[1]-26, 4, 8))

    # Draw Scarecrows
    for sc in state.get("scarecrows", []):
        cx = sc[0] * CELL_SIZE - camera_x
        cy = sc[1] * CELL_SIZE - camera_y
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT:
            continue
        rect = pygame.Rect(cx, cy, ITEM_PX, ITEM_PX)
        center = rect.center
        pygame.draw.rect(screen, (139, 69, 19), (center[0]-3, center[1]-15, 6, 30))
        pygame.draw.rect(screen, (139, 69, 19), (center[0]-15, center[1]-5, 30, 4))
        pygame.draw.circle(screen, (245, 222, 179), (center[0], center[1]-20), 10)
        pygame.draw.polygon(screen, (100, 100, 100), [(center[0]-12, center[1]-25), (center[0]+12, center[1]-25), (center[0], center[1]-40)])

    if state["thief_pos"][0] >= 0: 
        draw_obj(state["thief_pos"], images["thief"], RED, "circle")
        tx, ty = state["thief_pos"]
        screen_x = int(tx * CELL_SIZE) - camera_x
        screen_y = int(ty * CELL_SIZE) - camera_y
        if 0 <= screen_x <= WIDTH and 0 <= screen_y <= HEIGHT:
            hp = state.get("thief_hp", 3)
            pygame.draw.rect(screen, RED, (screen_x, screen_y - 10, ITEM_PX, 6))
            pygame.draw.rect(screen, (0, 255, 0), (screen_x, screen_y - 10, ITEM_PX * (hp / max(1, hp, 3)), 6))

    for fence in state["fences"]: 
        draw_obj((fence[0], fence[1]), images["fence"], (139, 69, 19))

    for dog in state["dogs"]: draw_obj(dog, images["dog"], YELLOW, "circle")
    for cat in state.get("cats", []): draw_obj(cat, images["cat"], (255,165,0))
    for goose in state.get("geese", []): draw_obj(goose, images["goose"], WHITE)
    for owl in state.get("owls", []): draw_obj(owl, images["owl"], (139,69,19))
    
    if state['phase'] == "day" and mouse_pos and not shop_open:
        mx, my = mouse_pos
        if my >= 0 and my < HEIGHT:
            gx = (mx + camera_x - ITEM_PX // 2) // CELL_SIZE
            gy = (my + camera_y - ITEM_PX // 2) // CELL_SIZE
            gx = max(0, min(GRID_W - ITEM_SIZE, gx))
            gy = max(0, min(GRID_H - ITEM_SIZE, gy))
            
            screen_x = gx * CELL_SIZE - camera_x
            screen_y = gy * CELL_SIZE - camera_y
            
            s = pygame.Surface((ITEM_PX, ITEM_PX))
            s.set_alpha(128)
            
            if current_tool == "fertilizer":
                s.fill((173, 255, 47))
            elif current_tool == "shovel":
                s.fill((169, 169, 169))
            else:
                s.fill(WHITE)
                preview_img = images.get(current_tool)
                if preview_img: 
                    s.blit(pygame.transform.scale(preview_img, (ITEM_PX, ITEM_PX)), (0, 0))
                else:
                    # Text fallback for cursor
                    tool_name = TOOL_NAMES.get(current_tool, current_tool)[:2]
                    txt = font_small.render(tool_name, True, BLACK)
                    s.blit(txt, (ITEM_PX//2 - txt.get_width()//2, ITEM_PX//2 - txt.get_height()//2))
                
            screen.blit(s, (screen_x, screen_y))

    # Top Panel
    top_panel = pygame.Surface((WIDTH - 40, 60), pygame.SRCALPHA)
    pygame.draw.rect(top_panel, (0, 0, 0, 180), top_panel.get_rect(), border_radius=15)
    screen.blit(top_panel, (20, 20))
    
    phase_text = f"第 {state['day_count']} 天 - 白天 ({state['time_left']}秒)" if state['phase'] == "day" else "夜晚結算中..."
    text_surf = font_large.render(phase_text, True, WHITE)
    screen.blit(text_surf, (40, 30))
    
    money_surf = font_small.render(f"資金: ${state['money']}", True, YELLOW)
    screen.blit(money_surf, (WIDTH - 150, 35))
    
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
    
    indicator = font_small.render(f"裝備中: {TOOL_NAMES.get(current_tool, current_tool)}", True, WHITE)
    screen.blit(indicator, (WIDTH - indicator.get_width() - 40, HEIGHT - 85))
    
    # Shop UI
    if shop_open:
        shop_surf = pygame.Surface((WIDTH, HEIGHT))
        shop_surf.set_alpha(150)
        shop_surf.fill(BLACK)
        screen.blit(shop_surf, (0, 0))
        
        shop_rect = pygame.Rect(50, 50, WIDTH - 100, HEIGHT - 100)
        pygame.draw.rect(screen, (245, 245, 250), shop_rect, border_radius=15)
        
        # Tabs
        tab_w = (shop_rect.width - 90) // 4
        tab_seed = pygame.Rect(70, 70, tab_w, 40)
        tab_def = pygame.Rect(70 + tab_w + 10, 70, tab_w, 40)
        tab_pet = pygame.Rect(70 + (tab_w + 10)*2, 70, tab_w, 40)
        tab_tool = pygame.Rect(70 + (tab_w + 10)*3, 70, tab_w, 40)
        
        pygame.draw.rect(screen, BLUE if active_tab == "seed" else GRAY, tab_seed, border_radius=10)
        pygame.draw.rect(screen, BLUE if active_tab == "def" else GRAY, tab_def, border_radius=10)
        pygame.draw.rect(screen, BLUE if active_tab == "pet" else GRAY, tab_pet, border_radius=10)
        pygame.draw.rect(screen, BLUE if active_tab == "tool" else GRAY, tab_tool, border_radius=10)
        
        ts1 = font_small.render("種子商店", True, WHITE)
        ts2 = font_small.render("防禦建築", True, WHITE)
        ts3 = font_small.render("寵物商店", True, WHITE)
        ts4 = font_small.render("實用工具", True, WHITE)
        screen.blit(ts1, (tab_seed.centerx - ts1.get_width()//2, tab_seed.centery - ts1.get_height()//2))
        screen.blit(ts2, (tab_def.centerx - ts2.get_width()//2, tab_def.centery - ts2.get_height()//2))
        screen.blit(ts3, (tab_pet.centerx - ts3.get_width()//2, tab_pet.centery - ts3.get_height()//2))
        screen.blit(ts4, (tab_tool.centerx - ts4.get_width()//2, tab_tool.centery - ts4.get_height()//2))
        
        items = []
        if active_tab == "seed":
            items = [
                {"id": "tomato", "name": "番茄種子", "price": 30, "desc": "1天熟，收益$60"},
                {"id": "carrot", "name": "紅蘿蔔種子", "price": 50, "desc": "2天熟，收益$120"},
                {"id": "corn", "name": "玉米種子", "price": 100, "desc": "2天熟，收益$250"},
                {"id": "pumpkin", "name": "南瓜種子", "price": 200, "desc": "3天熟，收益$600"}
            ]
        elif active_tab == "def":
            items = [
                {"id": "fence", "name": "木圍欄", "price": 100, "desc": "絕對路障，小偷需繞路"},
                {"id": "scarecrow", "name": "稻草人", "price": 150, "desc": "放在田裡當誘餌"}
            ]
        elif active_tab == "pet":
            items = [
                {"id": "dog", "name": "看門狗", "price": "FREE" if state.get("free_dog") else 200, "desc": "夜晚咬退小偷"},
                {"id": "cat", "name": "招財貓", "price": 150, "desc": "白天隨機撿錢"},
                {"id": "goose", "name": "大白鵝", "price": 300, "desc": "全域緩速小偷"},
                {"id": "owl", "name": "貓頭鷹", "price": 250, "desc": "機率嚇跑小偷"}
            ]
        elif active_tab == "tool":
            items = [
                {"id": "fertilizer", "name": "魔法肥料", "price": 80, "desc": "瞬間成熟"},
                {"id": "shovel", "name": "鐵鏟", "price": "FREE", "desc": "移除物件 (免費)"}
            ]
            
        y_offset = 130
        for item in items:
            card_rect = pygame.Rect(70, y_offset, shop_rect.width - 40, 70)
            pygame.draw.rect(screen, WHITE, card_rect, border_radius=10)
            
            img = images.get(item["id"])
            if img:
                screen.blit(pygame.transform.scale(img, (50, 50)), (card_rect.x + 10, card_rect.y + 10))
            else:
                pygame.draw.rect(screen, (220, 220, 220), (card_rect.x + 10, card_rect.y + 10, 50, 50), border_radius=5)
                fb_text = font_tiny.render(item["name"][:2], True, (100, 100, 100))
                screen.blit(fb_text, (card_rect.x + 35 - fb_text.get_width()//2, card_rect.y + 35 - fb_text.get_height()//2))
                
            n_surf = font_small.render(item["name"], True, BLACK)
            screen.blit(n_surf, (card_rect.x + 70, card_rect.y + 10))
            
            d_surf = font_tiny.render(item["desc"], True, GRAY)
            screen.blit(d_surf, (card_rect.x + 70, card_rect.y + 35))
            
            p_surf = font_small.render(f"${item['price']}" if isinstance(item['price'], int) else item['price'], True, YELLOW if item['price'] != "FREE" else RED)
            screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))
            
            if card_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)
            
            y_offset += 85
            
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
    current_tool = "tomato"
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
                
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not is_terminal(state):
                    mx, my = event.pos
                    
                    if shop_open:
                        shop_rect = pygame.Rect(50, 50, WIDTH - 100, HEIGHT - 100)
                        if not shop_rect.collidepoint(mx, my):
                            shop_open = False
                        else:
                            tab_w = (shop_rect.width - 90) // 4
                            tab_seed = pygame.Rect(70, 70, tab_w, 40)
                            tab_def = pygame.Rect(70 + tab_w + 10, 70, tab_w, 40)
                            tab_pet = pygame.Rect(70 + (tab_w + 10)*2, 70, tab_w, 40)
                            tab_tool = pygame.Rect(70 + (tab_w + 10)*3, 70, tab_w, 40)
                            
                            if tab_seed.collidepoint(mx, my): active_tab = "seed"
                            elif tab_def.collidepoint(mx, my): active_tab = "def"
                            elif tab_pet.collidepoint(mx, my): active_tab = "pet"
                            elif tab_tool.collidepoint(mx, my): active_tab = "tool"
                            
                            y_offset = 130
                            items_len = 4 if active_tab in ["seed", "pet"] else 2
                            for i in range(items_len):
                                card_rect = pygame.Rect(70, y_offset, shop_rect.width - 40, 70)
                                if card_rect.collidepoint(mx, my):
                                    if active_tab == "seed": current_tool = ["tomato", "carrot", "corn", "pumpkin"][i]
                                    elif active_tab == "def": current_tool = ["fence", "scarecrow"][i]
                                    elif active_tab == "pet": current_tool = ["dog", "cat", "goose", "owl"][i]
                                    elif active_tab == "tool": current_tool = ["fertilizer", "shovel"][i]
                                    shop_open = False
                                    break
                                y_offset += 85
                    else:
                        if my >= MARGIN_TOP and my < HEIGHT - MARGIN_BOTTOM:
                            gx = (mx + camera_x - ITEM_PX // 2) // CELL_SIZE
                            gy = (my - MARGIN_TOP + camera_y - ITEM_PX // 2) // CELL_SIZE
                            
                            tx, ty = state["thief_pos"]
                            if state["phase"] == "night" and tx <= gx + ITEM_SIZE//2 < tx + ITEM_SIZE and ty <= gy + ITEM_SIZE//2 < ty + ITEM_SIZE:
                                state = apply_action(state, f"click_{tx}_{ty}")
                            else:
                                if current_tool == "fence": state = apply_action(state, f"build_fence_{gx}_{gy}")
                                elif current_tool == "scarecrow": state = apply_action(state, f"build_scarecrow_{gx}_{gy}")
                                elif current_tool in ["tomato", "carrot", "corn", "pumpkin"]: state = apply_action(state, f"plant_crop_{current_tool}_{gx}_{gy}")
                                elif current_tool == "fertilizer": state = apply_action(state, f"use_fertilizer_{gx}_{gy}")
                                elif current_tool == "shovel": state = apply_action(state, f"use_shovel_{gx}_{gy}")
                                elif current_tool == "dog": state = apply_action(state, f"place_dog_{gx}_{gy}")
                                elif current_tool == "cat": state = apply_action(state, f"place_cat_{gx}_{gy}")
                                elif current_tool == "goose": state = apply_action(state, f"place_goose_{gx}_{gy}")
                                elif current_tool == "owl": state = apply_action(state, f"place_owl_{gx}_{gy}")
                            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not is_terminal(state): state = apply_action(state, "start_night")
                elif event.key == pygame.K_r: state = new_game()
                elif event.key == pygame.K_b: shop_open = not shop_open
                elif event.key == pygame.K_1: current_tool = "fence"
                elif event.key == pygame.K_2: current_tool = "dog"
                elif event.key == pygame.K_3: current_tool = "tomato"

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
            
        # 如果螢幕比世界還大，將視角置中，否則限制在邊界內
        if WORLD_W < WIDTH:
            camera_x = (WORLD_W - WIDTH) // 2
        else:
            camera_x = max(0, min(WORLD_W - WIDTH, camera_x))
            
        if WORLD_H < HEIGHT:
            camera_y = (WORLD_H - HEIGHT) // 2
        else:
            camera_y = max(0, min(WORLD_H - HEIGHT, camera_y))
        
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
