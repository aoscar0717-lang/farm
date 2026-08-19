import pygame
import random
import time

# 初始化 Pygame
pygame.init()

# 顏色定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)
YELLOW = (255, 215, 0)
RED = (220, 20, 60)
BLUE = (30, 144, 255)
BROWN = (139, 69, 19)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)

# 遊戲設定
WIDTH, HEIGHT = 800, 600
GRID_SIZE = 10
CELL_SIZE = 40
GRID_OFFSET_X = 50
GRID_OFFSET_Y = 100

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("夜巡農場 (Nightwatch Farm) - 雛形測試版")
font = pygame.font.SysFont("simhei", 24) # 避免中文亂碼，可用系統字體，這裡先用預設英文/數字為主，中文若沒字體可能會方塊
# 若無法顯示中文，改用預設
try:
    font = pygame.font.Font(pygame.font.match_font('microsoftjhenghei'), 24)
except:
    font = pygame.font.Font(None, 24)

class GameState:
    def __init__(self):
        self.gold = 100
        self.phase = "day" # 'day' or 'night'
        self.phase_start_time = time.time()
        self.day_duration = 30
        self.night_duration = 20
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)] 
        # 0: 空地, 1: 種子, 2: 成熟作物, 3: 圍欄
        self.thieves = []
        self.pets = []
        self.messages = [] # 浮動文字
        self.round = 1

state = GameState()

def get_grid_pos(mouse_x, mouse_y):
    col = (mouse_x - GRID_OFFSET_X) // CELL_SIZE
    row = (mouse_y - GRID_OFFSET_Y) // CELL_SIZE
    if 0 <= col < GRID_SIZE and 0 <= row < GRID_SIZE:
        return row, col
    return None

def add_message(text, pos, color=RED):
    state.messages.append({"text": text, "pos": list(pos), "time": time.time()})

def spawn_thief():
    # 從邊緣生成小偷
    edge = random.choice(["top", "bottom", "left", "right"])
    if edge == "top":
        pos = [random.randint(0, GRID_SIZE-1), -1]
    elif edge == "bottom":
        pos = [random.randint(0, GRID_SIZE-1), GRID_SIZE]
    elif edge == "left":
        pos = [-1, random.randint(0, GRID_SIZE-1)]
    else:
        pos = [GRID_SIZE, random.randint(0, GRID_SIZE-1)]
    
    # 找目標 (成熟作物或種子)
    targets = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if state.grid[r][c] in [1, 2]:
                targets.append((r, c))
    
    target = random.choice(targets) if targets else (GRID_SIZE//2, GRID_SIZE//2)
    state.thieves.append({"pos": pos, "target": target, "last_move": time.time()})

running = True
clock = pygame.time.Clock()

# UI 按鈕區域
btn_plant = pygame.Rect(500, 100, 150, 40)
btn_fence = pygame.Rect(500, 150, 150, 40)
btn_pet = pygame.Rect(500, 200, 150, 40)
current_action = "plant" # 'plant', 'fence'

while running:
    current_time = time.time()
    
    # 處理日夜切換
    elapsed = current_time - state.phase_start_time
    if state.phase == "day" and elapsed > state.day_duration:
        state.phase = "night"
        state.phase_start_time = current_time
    elif state.phase == "night" and elapsed > state.night_duration:
        state.phase = "day"
        state.phase_start_time = current_time
        state.round += 1
        state.thieves.clear()
        
    # 小偷生成與移動邏輯 (夜晚)
    if state.phase == "night":
        if random.random() < 0.02 and len(state.thieves) < 3: # 隨機生成小偷
            spawn_thief()
            
        for thief in state.thieves[:]:
            if current_time - thief["last_move"] > 1.0: # 每秒移動一格
                r, c = thief["pos"]
                tr, tc = thief["target"]
                
                # 簡單尋路 (朝向目標)
                next_r, next_c = r, c
                if r < tr: next_r += 1
                elif r > tr: next_r -= 1
                elif c < tc: next_c += 1
                elif c > tc: next_c -= 1
                
                # 檢查障礙物 (圍欄)
                if 0 <= next_r < GRID_SIZE and 0 <= next_c < GRID_SIZE:
                    if state.grid[next_r][next_c] == 3:
                        # 撞到圍欄，破壞它
                        state.grid[next_r][next_c] = 0
                        add_message("Fence Broken!", (GRID_OFFSET_X + next_c*CELL_SIZE, GRID_OFFSET_Y + next_r*CELL_SIZE), WHITE)
                        thief["last_move"] = current_time
                        continue
                        
                thief["pos"] = [next_r, next_c]
                thief["last_move"] = current_time
                
                # 到達目標，偷取
                if thief["pos"][0] == tr and thief["pos"][1] == tc:
                    if 0 <= tr < GRID_SIZE and 0 <= tc < GRID_SIZE:
                        if state.grid[tr][tc] in [1, 2]:
                            state.grid[tr][tc] = 0
                            add_message("Stolen!", (GRID_OFFSET_X + tc*CELL_SIZE, GRID_OFFSET_Y + tr*CELL_SIZE))
                    state.thieves.remove(thief)

    # 處理事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            
            # 點擊按鈕
            if btn_plant.collidepoint(mx, my): current_action = "plant"
            if btn_fence.collidepoint(mx, my): current_action = "fence"
            if btn_pet.collidepoint(mx, my) and state.phase == "day":
                if state.gold >= 50:
                    state.gold -= 50
                    state.pets.append([random.randint(0, GRID_SIZE-1), random.randint(0, GRID_SIZE-1)])
            
            # 點擊網格
            pos = get_grid_pos(mx, my)
            if pos:
                r, c = pos
                if state.phase == "day":
                    if state.grid[r][c] == 0:
                        if current_action == "plant" and state.gold >= 10:
                            state.gold -= 10
                            state.grid[r][c] = 2 # 直接變成成熟作物測試
                        elif current_action == "fence" and state.gold >= 20:
                            state.gold -= 20
                            state.grid[r][c] = 3
                    elif state.grid[r][c] == 2: # 收成
                        state.gold += 30
                        state.grid[r][c] = 0
                        add_message("+30", (mx, my), YELLOW)
                
                elif state.phase == "night":
                    # 夜晚點擊小偷測試 (核心機制: 嘲諷無敵)
                    clicked_thief = False
                    for thief in state.thieves:
                        tr, tc = thief["pos"]
                        if tr == r and tc == c:
                            add_message("Haha! Miss!", (mx, my-20))
                            clicked_thief = True
                            break
                            
    # 畫面渲染
    screen.fill(BLACK if state.phase == "night" else (135, 206, 235))
    
    # 畫網格
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            rect = pygame.Rect(GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
            pygame.draw.rect(screen, GRAY if state.phase == "day" else DARK_GRAY, rect, 1)
            
            val = state.grid[r][c]
            if val == 2: # 作物
                pygame.draw.circle(screen, GREEN, rect.center, 15)
            elif val == 3: # 圍欄
                pygame.draw.rect(screen, BROWN, rect.inflate(-10, -10))
                
    # 畫小偷
    for thief in state.thieves:
        r, c = thief["pos"]
        rect = pygame.Rect(GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, RED, rect.inflate(-10, -10))
        
    # 畫寵物
    for pet in state.pets:
        r, c = pet
        rect = pygame.Rect(GRID_OFFSET_X + c*CELL_SIZE, GRID_OFFSET_Y + r*CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.circle(screen, BLUE, rect.center, 12)

    # 畫 UI
    info = font.render(f"Round: {state.round} | Gold: {state.gold} | Phase: {state.phase} ({int(state.day_duration if state.phase=='day' else state.night_duration - elapsed)}s)", True, WHITE)
    screen.blit(info, (20, 20))
    
    pygame.draw.rect(screen, YELLOW if current_action == "plant" else GRAY, btn_plant)
    screen.blit(font.render("Plant (-10)", True, BLACK), (btn_plant.x+10, btn_plant.y+10))
    
    pygame.draw.rect(screen, YELLOW if current_action == "fence" else GRAY, btn_fence)
    screen.blit(font.render("Fence (-20)", True, BLACK), (btn_fence.x+10, btn_fence.y+10))
    
    pygame.draw.rect(screen, GRAY, btn_pet)
    screen.blit(font.render("Buy Pet(-50)", True, BLACK), (btn_pet.x+10, btn_pet.y+10))
    
    # 畫浮動文字
    for msg in state.messages[:]:
        msg["pos"][1] -= 1 # 向上浮動
        txt_surf = font.render(msg["text"], True, msg.get("color", RED))
        screen.blit(txt_surf, msg["pos"])
        if current_time - msg["time"] > 1.5:
            state.messages.remove(msg)

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
