import pygame
import random
import time
import math

# 初始化 Pygame
pygame.init()

# --- 顏色與基本設定 ---
WIDTH, HEIGHT = 950, 600
GRID_SIZE = 10
CELL_SIZE = 50
GRID_OFFSET_X = 40
GRID_OFFSET_Y = 40

# 色彩盤 (精緻化)
C_GRASS_1 = (144, 201, 120)
C_GRASS_2 = (134, 191, 110)
C_PANEL = (245, 247, 250)
C_TEXT = (44, 62, 80)
C_GOLD = (241, 196, 15)
C_NIGHT_OVERLAY = (10, 14, 35)
C_FENCE = (139, 90, 43)
C_WHITE = (255, 255, 255)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("夜巡農場 (Nightwatch Farm) - 高級視覺版")

# 字體設定 (支援中文)
try:
    font_sm = pygame.font.Font(pygame.font.match_font('microsoftjhenghei'), 16)
    font_md = pygame.font.Font(pygame.font.match_font('microsoftjhenghei'), 20)
    font_lg = pygame.font.Font(pygame.font.match_font('microsoftjhenghei'), 28)
except:
    font_sm = pygame.font.Font(None, 20)
    font_md = pygame.font.Font(None, 28)
    font_lg = pygame.font.Font(None, 36)

# --- 遊戲資料狀態 ---
class GameState:
    def __init__(self):
        self.gold = 150
        self.phase = "day" # 'day' or 'night'
        self.phase_start_time = time.time()
        self.day_duration = 20   # 測試用：白天 20 秒
        self.night_duration = 15 # 測試用：夜晚 15 秒
        self.round = 1
        
        # 網格狀態: 0=空地, 1=生長中, 2=成熟, 3=圍欄
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.crop_progress = [[0.0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        self.thieves = []
        self.pets = []
        self.messages = []
        
        self.selected_tool = "plant" # 目前在商店選中的工具
        self.transition_alpha = 0    # 日夜交替的黑夜透明度

state = GameState()

# --- 商店設定 ---
SHOP_ITEMS = [
    {"id": "plant", "name": "番茄種子", "cost": 10, "icon": "🍅"},
    {"id": "fence", "name": "木製圍欄", "cost": 20, "icon": "🚧"},
    {"id": "dog", "name": "看門狗", "cost": 60, "icon": "🐶"}
]

# --- 繪圖輔助函數 (用程式畫出高級感圖形) ---
def draw_rounded_rect(surface, color, rect, radius=10):
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_crop(surface, x, y, progress, mature):
    # 畫泥土
    pygame.draw.ellipse(surface, (101, 67, 33), (x+5, y+30, 40, 15))
    if not mature:
        # 生長中：小綠苗
        h = int(20 * progress)
        pygame.draw.line(surface, (34, 139, 34), (x+25, y+40), (x+25, y+40-h), 4)
    else:
        # 成熟番茄
        pygame.draw.line(surface, (34, 139, 34), (x+25, y+40), (x+25, y+15), 4) # 莖
        pygame.draw.circle(surface, (220, 20, 60), (x+25, y+20), 12) # 番茄

def draw_fence(surface, x, y):
    # 木柵欄
    pygame.draw.rect(surface, C_FENCE, (x+10, y+10, 8, 40))
    pygame.draw.rect(surface, C_FENCE, (x+32, y+10, 8, 40))
    pygame.draw.rect(surface, C_FENCE, (x+5, y+15, 40, 6))
    pygame.draw.rect(surface, C_FENCE, (x+5, y+30, 40, 6))

def draw_thief(surface, x, y):
    # 畫小偷 (滑順動畫座標)
    pygame.draw.circle(surface, (30, 30, 30), (int(x+25), int(y+25)), 16) # 身體
    pygame.draw.rect(surface, (100, 100, 100), (int(x+11), int(y+20), 28, 8)) # 面罩
    pygame.draw.circle(surface, C_WHITE, (int(x+18), int(y+24)), 3) # 左眼
    pygame.draw.circle(surface, C_WHITE, (int(x+32), int(y+24)), 3) # 右眼

def draw_dog(surface, x, y):
    # 畫狗狗
    pygame.draw.rect(surface, (210, 150, 50), (x+10, y+20, 30, 20), border_radius=5) # 身體
    pygame.draw.circle(surface, (210, 150, 50), (x+35, y+15), 10) # 頭
    pygame.draw.rect(surface, (139, 69, 19), (x+32, y+5, 6, 12), border_radius=3) # 耳朵
    pygame.draw.rect(surface, (139, 69, 19), (x+5, y+20, 8, 4)) # 尾巴

# --- 遊戲邏輯函數 ---
def add_message(text, pos, color=(220, 20, 60)):
    state.messages.append({"text": text, "pos": list(pos), "time": time.time(), "color": color})

def get_grid_pos(mouse_x, mouse_y):
    col = (mouse_x - GRID_OFFSET_X) // CELL_SIZE
    row = (mouse_y - GRID_OFFSET_Y) // CELL_SIZE
    if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
        return row, col
    return None

def spawn_thief():
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top": pos = [random.randint(0, GRID_SIZE-1), -1]
    elif edge == "bottom": pos = [random.randint(0, GRID_SIZE-1), GRID_SIZE]
    elif edge == "left": pos = [-1, random.randint(0, GRID_SIZE-1)]
    else: pos = [GRID_SIZE, random.randint(0, GRID_SIZE-1)]
    
    targets = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if state.grid[r][c] in [1, 2]]
    target = random.choice(targets) if targets else (GRID_SIZE//2, GRID_SIZE//2)
    state.thieves.append({
        "logic_pos": pos,         # 網格邏輯位置 (row, col)
        "draw_pos": [pos[0], pos[1]], # 繪圖用平滑位置
        "target": target,
        "last_move": time.time()
    })

# --- 主迴圈 ---
running = True
clock = pygame.time.Clock()

shop_buttons = [] # 儲存商店按鈕的點擊區域

while running:
    current_time = time.time()
    dt = clock.tick(60) / 1000.0 # 幀率 60FPS，計算時間差 (Delta time)
    
    # 1. 處理日夜切換 & 作物生長
    elapsed = current_time - state.phase_start_time
    if state.phase == "day":
        state.transition_alpha = max(0, state.transition_alpha - 2) # 天亮漸變
        
        # 白天作物生長
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if state.grid[r][c] == 1:
                    state.crop_progress[r][c] += dt / 10.0 # 10秒長大
                    if state.crop_progress[r][c] >= 1.0:
                        state.grid[r][c] = 2 # 成熟
        
        if elapsed > state.day_duration:
            state.phase = "night"
            state.phase_start_time = current_time
            
    elif state.phase == "night":
        state.transition_alpha = min(180, state.transition_alpha + 2) # 天黑漸變
        
        # 夜晚小偷生成與移動
        if random.random() < 0.015 and len(state.thieves) < 4:
            spawn_thief()
            
        for thief in state.thieves[:]:
            # 計算平滑移動
            tr, tc = thief["target"]
            lr, lc = thief["logic_pos"]
            dr, dc = thief["draw_pos"]
            
            # 每 0.8 秒邏輯移動一格
            if current_time - thief["last_move"] > 0.8:
                next_r, next_c = lr, lc
                if lr < tr: next_r += 1
                elif lr > tr: next_r -= 1
                elif lc < tc: next_c += 1
                elif lc > tc: next_c -= 1
                
                # 檢查障礙物 (圍欄)
                if 0 <= next_r < GRID_SIZE and 0 <= next_c < GRID_SIZE:
                    if state.grid[next_r][next_c] == 3:
                        state.grid[next_r][next_c] = 0 # 破壞圍欄
                        add_message("柵欄被破壞!", (GRID_OFFSET_X + next_c*CELL_SIZE, GRID_OFFSET_Y + next_r*CELL_SIZE), C_WHITE)
                        thief["last_move"] = current_time
                        continue
                        
                thief["logic_pos"] = [next_r, next_c]
                thief["last_move"] = current_time
                
                # 偷竊判定
                if thief["logic_pos"][0] == tr and thief["logic_pos"][1] == tc:
                    if 0 <= tr < GRID_SIZE and 0 <= tc < GRID_SIZE and state.grid[tr][tc] in [1, 2]:
                        state.grid[tr][tc] = 0
                        add_message("作物被偷了!", (GRID_OFFSET_X + tc*CELL_SIZE, GRID_OFFSET_Y + tr*CELL_SIZE))
                    state.thieves.remove(thief)
            
            # 視覺平滑靠近邏輯位置
            thief["draw_pos"][0] += (thief["logic_pos"][0] - thief["draw_pos"][0]) * 0.1
            thief["draw_pos"][1] += (thief["logic_pos"][1] - thief["draw_pos"][1]) * 0.1

        if elapsed > state.night_duration:
            state.phase = "day"
            state.phase_start_time = current_time
            state.round += 1
            state.thieves.clear()

    # 狗狗自動巡邏 (簡單的視覺移動)
    for pet in state.pets:
        if random.random() < 0.02:
            pet["logic_pos"][0] = min(max(0, pet["logic_pos"][0] + random.choice([-1, 0, 1])), GRID_SIZE-1)
            pet["logic_pos"][1] = min(max(0, pet["logic_pos"][1] + random.choice([-1, 0, 1])), GRID_SIZE-1)
        pet["draw_pos"][0] += (pet["logic_pos"][0] - pet["draw_pos"][0]) * 0.05
        pet["draw_pos"][1] += (pet["logic_pos"][1] - pet["draw_pos"][1]) * 0.05
        
        # 狗狗夜晚自動趕小偷
        if state.phase == "night" and current_time - pet.get("last_bark", 0) > 2.0:
            for thief in state.thieves:
                if abs(thief["logic_pos"][0] - pet["logic_pos"][0]) <= 1 and abs(thief["logic_pos"][1] - pet["logic_pos"][1]) <= 1:
                    add_message("汪汪! 趕走小偷!", (GRID_OFFSET_X + pet["logic_pos"][1]*CELL_SIZE, GRID_OFFSET_Y + pet["logic_pos"][0]*CELL_SIZE), C_WHITE)
                    state.thieves.remove(thief)
                    state.gold += 5 # 狗狗擊退獎勵
                    pet["last_bark"] = current_time
                    break

    # 2. 處理玩家輸入事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # 檢查點擊商店按鈕
            for btn in shop_buttons:
                if btn["rect"].collidepoint(mx, my):
                    if btn["id"] == "dog" and state.phase == "day":
                        if state.gold >= 60:
                            state.gold -= 60
                            # 隨機放一隻狗
                            r, c = random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1)
                            state.pets.append({"logic_pos": [r, c], "draw_pos": [r, c], "last_bark": current_time})
                    else:
                        state.selected_tool = btn["id"]
            
            # 檢查點擊農田
            pos = get_grid_pos(mx, my)
            if pos:
                r, c = pos
                
                # --- 白天操作 ---
                if state.phase == "day":
                    # 收成 (點擊成熟作物，無視目前選什麼工具都可以收)
                    if state.grid[r][c] == 2:
                        state.gold += 35
                        state.grid[r][c] = 0
                        state.crop_progress[r][c] = 0.0
                        add_message("+35 💰", (mx, my-20), C_GOLD)
                        
                    # 種植或蓋圍欄 (只能在空地)
                    elif state.grid[r][c] == 0:
                        if state.selected_tool == "plant" and state.gold >= 10:
                            state.gold -= 10
                            state.grid[r][c] = 1 # 種下
                            state.crop_progress[r][c] = 0.0
                        elif state.selected_tool == "fence" and state.gold >= 20:
                            state.gold -= 20
                            state.grid[r][c] = 3 # 圍欄
                            
                # --- 夜晚操作 ---
                elif state.phase == "night":
                    # 專題核心機制：點擊小偷無效並嘲諷
                    clicked_thief = False
                    for thief in state.thieves:
                        tr, tc = thief["logic_pos"]
                        if tr == r and tc == c:
                            add_message("Haha! Miss!", (mx-10, my-20), C_WHITE)
                            clicked_thief = True
                            break
                    if not clicked_thief:
                        add_message("晚上無法務農！", (mx, my-10), C_WHITE)

    # 3. 畫面渲染
    screen.fill(C_GRASS_1) # 背景草地
    
    # 畫棋盤格草地
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            color = C_GRASS_1 if (r+c)%2 == 0 else C_GRASS_2
            rect = pygame.Rect(GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, color, rect)
            
            # 畫物件
            val = state.grid[r][c]
            if val in [1, 2]:
                draw_crop(screen, rect.x, rect.y, state.crop_progress[r][c], val == 2)
            elif val == 3:
                draw_fence(screen, rect.x, rect.y)

    # 畫寵物
    for pet in state.pets:
        px = GRID_OFFSET_X + pet["draw_pos"][1] * CELL_SIZE
        py = GRID_OFFSET_Y + pet["draw_pos"][0] * CELL_SIZE
        draw_dog(screen, px, py)

    # 畫小偷
    for thief in state.thieves:
        tx = GRID_OFFSET_X + thief["draw_pos"][1] * CELL_SIZE
        ty = GRID_OFFSET_Y + thief["draw_pos"][0] * CELL_SIZE
        draw_thief(screen, tx, ty)

    # 畫夜晚半透明遮罩
    if state.transition_alpha > 0:
        overlay = pygame.Surface((GRID_SIZE*CELL_SIZE, GRID_SIZE*CELL_SIZE), pygame.SRCALPHA)
        overlay.fill((C_NIGHT_OVERLAY[0], C_NIGHT_OVERLAY[1], C_NIGHT_OVERLAY[2], state.transition_alpha))
        screen.blit(overlay, (GRID_OFFSET_X, GRID_OFFSET_Y))

    # --- 畫右側高級商店 UI ---
    shop_rect = pygame.Rect(580, 0, 370, HEIGHT)
    pygame.draw.rect(screen, C_PANEL, shop_rect)
    pygame.draw.line(screen, (200, 210, 220), (580, 0), (580, HEIGHT), 2)
    
    # 狀態標題
    title_text = font_lg.render("夜巡農場 (Nightwatch)", True, C_TEXT)
    screen.blit(title_text, (600, 30))
    
    round_text = font_md.render(f"📅 第 {state.round} 回合", True, C_TEXT)
    screen.blit(round_text, (600, 80))
    
    # 資金顯示 (帶有背景框)
    gold_bg = pygame.Rect(600, 115, 140, 40)
    draw_rounded_rect(screen, C_WHITE, gold_bg, 8)
    gold_text = font_md.render(f"💰 {state.gold} G", True, (212, 175, 55))
    screen.blit(gold_text, (615, 122))
    
    # 日夜倒數
    time_left = int(state.day_duration - elapsed) if state.phase == 'day' else int(state.night_duration - elapsed)
    phase_str = "☀️ 白天" if state.phase == "day" else "🌙 夜晚"
    phase_color = (230, 126, 34) if state.phase == "day" else (41, 128, 185)
    phase_text = font_md.render(f"{phase_str} - 剩餘 {max(0, time_left)}s", True, phase_color)
    screen.blit(phase_text, (600, 170))
    
    # 商店列表
    shop_label = font_md.render("🛒 商店與裝備", True, C_TEXT)
    screen.blit(shop_label, (600, 230))
    
    shop_buttons = [] # 清空重新計算
    mx, my = pygame.mouse.get_pos()
    
    for i, item in enumerate(SHOP_ITEMS):
        btn_y = 270 + i * 70
        btn_rect = pygame.Rect(600, btn_y, 300, 60)
        
        # 判斷滑鼠懸停與選中狀態
        is_hover = btn_rect.collidepoint(mx, my)
        is_selected = state.selected_tool == item["id"]
        
        btn_color = C_WHITE
        if is_selected: btn_color = (220, 235, 255) # 淡藍色選中
        elif is_hover: btn_color = (240, 240, 240)
        
        draw_rounded_rect(screen, btn_color, btn_rect, 12)
        
        # 如果是選中狀態，畫一個藍色邊框
        if is_selected:
            pygame.draw.rect(screen, (76, 110, 245), btn_rect, 2, border_radius=12)
            
        # 按鈕內容
        icon_text = font_lg.render(item["icon"], True, C_TEXT)
        name_text = font_md.render(item["name"], True, C_TEXT)
        cost_text = font_md.render(f"{item['cost']} G", True, C_GOLD)
        
        screen.blit(icon_text, (615, btn_y + 12))
        screen.blit(name_text, (660, btn_y + 18))
        screen.blit(cost_text, (820, btn_y + 18))
        
        shop_buttons.append({"id": item["id"], "rect": btn_rect})

    # 畫浮動文字 (動畫向上飄)
    for msg in state.messages[:]:
        msg["pos"][1] -= float(dt) * 40.0 # 根據幀率向上浮動
        txt_surf = font_md.render(msg["text"], True, msg["color"])
        # 加入簡單的陰影讓字體更明顯
        shadow = font_md.render(msg["text"], True, (30,30,30))
        screen.blit(shadow, (msg["pos"][0]+1, msg["pos"][1]+1))
        screen.blit(txt_surf, msg["pos"])
        
        if current_time - msg["time"] > 1.2:
            state.messages.remove(msg)

    pygame.display.flip()

pygame.quit()
