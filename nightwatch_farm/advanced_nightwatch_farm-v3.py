"""
夜巡農場 (Nightwatch Farm) - 純色扁平極簡風 (Flat Minimalist) 客戶端
核心升級：
1. 【5級莊園等級系統】擴展至 10 種農作物、13 種莊園景觀佈置！
2. 【5 秒強光手電筒充能】即時 CD 倒數顯示，戰術更具節奏感！
3. 【蜂巢與向日葵清晰區分】蜂巢採用深木吊掛支架與六角琥珀木條紋巢柱，向日葵為金色向陽大花盤！
4. 【防偷懶機制】空田過夜將洗劫中央金庫 35% 金幣，守護作物過夜享 +50% 月光滋養金幣加成！
"""

import sys
import os
import math
import random
from typing import List, Tuple, Optional, Dict, Any
import pygame


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from game_config import (
    GamePhase, ZoneType, CropType, CropStage, DecorationType,
    DefenseType, EnemyType, EnemyState, DogState, EventType,
    MAP_CONFIG, FARM_LEVELS, CROP_DATA, DECORATION_DATA, DEFENSE_DATA,
    DOG_CONFIG, CAT_CONFIG, ENEMY_DATA, GameEvent
)
from game_state import GameState
from sound_manager import SoundManager
from asset_loader import AssetLoader

pygame.init()
pygame.font.init()

# ==========================================
# 視覺尺寸與純色扁平調色盤 (Flat Color Palette)
# ==========================================
SCREEN_WIDTH = 1260
SCREEN_HEIGHT = 800
FPS = 60

CELL_SIZE = 50
GRID_X = 24
GRID_Y = 86

# 扁平現代色彩
C_MEADOW_BG = (174, 213, 129)       # 純色柔和綠草地
C_FARM_SOIL = (215, 178, 138)        # 純色溫暖農田底色
C_FARM_SHADOW = (180, 142, 102)      # 農田投影
C_FARM_BORDER = (156, 116, 78)       # 苗圃外框色

C_NAVY_TOP = (38, 50, 56)           # 頂部導航底色
C_WHITE = (255, 255, 255)
C_CARD_BG = (255, 255, 255)
C_CARD_BORDER = (224, 224, 224)

C_TEXT_MAIN = (33, 33, 33)
C_TEXT_MUTED = (117, 117, 117)
C_GOLD = (255, 193, 7)
C_GREEN = (76, 175, 80)
C_RED = (239, 83, 80)
C_BLUE = (33, 150, 243)
C_PURPLE = (156, 39, 176)
C_CYAN = (0, 188, 212)
C_ORANGE = (255, 152, 0)
C_BLOOD_RED = (211, 47, 47)


def get_font(size: int, bold: bool = False):
    for fn in ['microsoftjhenghei', 'simhei', 'pingfang', 'segoeui', 'arial']:
        try:
            match = pygame.font.match_font(fn)
            if match:
                return pygame.font.Font(match, size)
        except Exception:
            pass
    return pygame.font.SysFont('arial', size, bold=bold)

FONT_XS = get_font(12)
FONT_SM = get_font(14)
FONT_MD = get_font(16, bold=True)
FONT_LG = get_font(20, bold=True)
FONT_TITLE = get_font(26, bold=True)


# ==========================================
# 粒子與浮動文字
# ==========================================
class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: float, life: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.max_life = life
        self.life = life

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size = max(0.5, self.size * (self.life / self.max_life))
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        c = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(s, c, (int(self.size), int(self.size)), int(self.size))
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))


class FloatingText:
    def __init__(self, text: str, x: float, y: float, color=(255, 255, 255), duration: float = 1.2):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        self.y -= 24.0 * dt
        return self.elapsed < self.duration

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (1.0 - (self.elapsed / self.duration)))))
        stroke = FONT_MD.render(self.text, True, (20, 20, 20))
        stroke.set_alpha(alpha)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            surface.blit(stroke, (int(self.x + dx), int(self.y + dy)))
            
        t_surf = FONT_MD.render(self.text, True, self.color)
        t_surf.set_alpha(alpha)
        surface.blit(t_surf, (int(self.x), int(self.y)))


# ==========================================
# 扁平操作卡片 (Action Card)
# ==========================================
class ActionCard:
    def __init__(self, action_id: str, label: str, cost_text: str, tab_id: str, asset_key: str, rect: pygame.Rect):
        self.action_id = action_id
        self.label = label
        self.cost_text = cost_text
        self.tab_id = tab_id
        self.asset_key = asset_key
        self.rect = rect
        self.is_hovered = False
        self.is_locked = False
        self.lock_reason = ""

    def draw(self, surface, is_selected: bool, loader: AssetLoader):
        bg_col = (255, 255, 255)
        if self.is_locked:
            bg_col = (245, 245, 245)
        elif is_selected:
            bg_col = (255, 248, 225)
        elif self.is_hovered:
            bg_col = (250, 250, 250)

        border_col = C_ORANGE if is_selected else ((200, 200, 200) if not self.is_hovered else (100, 100, 100))
        border_w = 3 if is_selected else 1

        pygame.draw.rect(surface, bg_col, self.rect, border_radius=8)
        pygame.draw.rect(surface, border_col, self.rect, width=border_w, border_radius=8)

        icon_surf = loader.get(self.asset_key)
        if icon_surf:
            surface.blit(icon_surf, (self.rect.x + 4, self.rect.y + 3))

        lbl_col = C_TEXT_MUTED if self.is_locked else C_TEXT_MAIN
        surface.blit(FONT_MD.render(self.label, True, lbl_col), (self.rect.x + 54, self.rect.y + 6))

        cost_col = C_RED if self.is_locked else ((230, 81, 0) if self.cost_text else C_TEXT_MUTED)
        surface.blit(FONT_SM.render(self.cost_text, True, cost_col), (self.rect.x + 54, self.rect.y + 27))

        if self.is_locked:
            surface.blit(FONT_XS.render("🔒", True, C_RED), (self.rect.right - 18, self.rect.y + 6))


# ==========================================
# 主遊戲視窗 (NightwatchFarmApp)
# ==========================================
class NightwatchFarmApp:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("夜巡農場 (Nightwatch Farm) - 現代極簡塔防農場")
        self.clock = pygame.time.Clock()
        
        self.game = GameState()
        self.sound = SoundManager(sfx_enabled=True)
        self.loader = AssetLoader(cell_size=CELL_SIZE)
        
        self.show_intro = True
        self.active_tab = "CROPS"
        self.selected_action = "PLANT_RADISH"
        
        self.floating_texts = []
        self.particles = []
        self.log_messages = ["🌾 歡迎來到夜巡農場！純色極簡莊園，中央為農田與金庫，四周為景觀與防禦！"]
        self.hovered_grid = None
        self.mouse_pos = (0, 0)
        self.anim_time = 0.0
        
        self._init_ui()

    def _init_ui(self):
        self.tab_buttons = [
            ("CROPS", "🌾 農田耕作 (10種)", pygame.Rect(24, 650, 175, 36)),
            ("DECO", "🌸 莊園景觀 (13種)", pygame.Rect(205, 650, 175, 36)),
            ("DEFENSE", "🛡️ 防禦與寵物 (6種)", pygame.Rect(386, 650, 185, 36)),
            ("TOOLS", "🛠️ 主動戰術工具 (4種)", pygame.Rect(577, 650, 185, 36)),
        ]

        self.cards_by_tab = {
            "CROPS": [
                ("PLANT_RADISH", "白蘿蔔", "$10 | 4s熟", "radish_mature"),
                ("PLANT_TOMATO", "紅番茄", "$20 | 6s熟", "tomato_mature"),
                ("PLANT_CORN", "甜玉米", "$40 | 10s熟", "corn_mature"),
                ("PLANT_EGGPLANT", "紫晶茄子", "$55 | 12s熟", "eggplant_mature"),
                ("PLANT_STRAWBERRY", "鮮甜草莓", "$70 | 14s熟", "strawberry_mature"),
                ("PLANT_PUMPKIN", "魔法南瓜", "$90 | 16s熟", "pumpkin_mature"),
                ("PLANT_WATERMELON", "冰爽西瓜", "$110 | 18s熟", "watermelon_mature"),
                ("PLANT_SUNFLOWER", "向日葵", "$130 | 20s熟", "sunflower_mature"),
                ("PLANT_GRAPE", "皇家紫葡萄", "$160 | 22s熟", "grape_mature"),
                ("PLANT_STARLIGHT", "永恆星光果", "$280 | 28s熟", "starlight_mature"),
            ],
            "DECO": [
                ("PLACE_PATH", "石板花徑", "$20 | +10繁榮", "stone_path"),
                ("PLACE_FLOWER", "鮮花花壇", "$35 | +20繁榮", "flower_bed"),
                ("PLACE_BENCH", "休閒長椅", "$45 | +30繁榮", "garden_bench"),
                ("PLACE_PINE", "莊園松樹", "$50 | +35繁榮", "pine_tree"),
                ("PLACE_APPLE_TREE", "蘋果果樹", "$60 | +40繁榮", "apple_tree"),
                ("PLACE_LANTERN", "守護路燈", "$75 | +50繁榮", "soul_lantern"),
                ("PLACE_SAKURA_TREE", "櫻花樹", "$85 | +55繁榮", "sakura_tree"),
                ("PLACE_BIRD_BATH", "鳥浴水盆", "$95 | +65繁榮", "bird_bath"),
                ("PLACE_STATUE", "莊園雕像", "$110 | +75繁榮", "ancient_statue"),
                ("PLACE_PET_HOUSE", "寵物小屋", "$130 | +90繁榮", "pet_house"),
                ("PLACE_FOUNTAIN", "圓形噴泉", "$160 | +110", "fountain"),
                ("PLACE_SUNDIAL", "日晷鐘塔", "$220 | +160", "sundial_tower"),
                ("PLACE_WINDMILL", "風車磨坊", "$300 | +220", "windmill"),
            ],
            "DEFENSE": [
                ("PLACE_FENCE", "刺藤木柵", "$15 | 阻擋+反傷", "wooden_fence"),
                ("PLACE_TRAP", "鋼鐵捕獸夾", "$20 | 120傷害", "bear_trap"),
                ("PLACE_SCARECROW", "農田稻草人", "$35 | 驚嚇小偷", "scarecrow"),
                ("PLACE_BEEHIVE", "蜜蜂守衛巢", "$85 | 自動射擊", "beehive"),
                ("BUY_DOG", "看門柴犬", "$100 | 夜間撲咬", "guard_dog"),
                ("BUY_CAT", "招財小貓", "$80 | 白天贈金", "farm_cat"),
            ],
            "TOOLS": [
                ("WATER_CROP", "黃金澆水壺", "$5 | 加速50%", "watering_can"),
                ("FLASHLIGHT", "強光手電筒", "就緒 | 3s充能", "soul_lantern"),
                ("WHISTLE", "守衛指揮哨", "免費 | 指揮狗狗衝刺", "guard_dog"),
            ]
        }

        self.action_cards = []
        start_x = 24

        for tab_id, items in self.cards_by_tab.items():
            count = len(items)
            cols_per_row = 7 if count > 10 else 5
            card_w = 170 if count > 10 else 235
            card_h = 50
            
            for i, (act_id, lbl, cost, asset_key) in enumerate(items):
                row = i // cols_per_row
                col = i % cols_per_row
                rx = start_x + col * (card_w + 8)
                ry = 696 if row == 0 else 746
                r = pygame.Rect(rx, ry, card_w, card_h)
                self.action_cards.append(ActionCard(act_id, lbl, cost, tab_id, asset_key, r))

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse_move(event)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and self.show_intro:
                        self.show_intro = False
                    elif event.key == pygame.K_r and self.game.game_over:
                        self.game = GameState()
                        self.log_messages.clear()
                        self.log_messages.append("🌾 遊戲已重新開始！")
                    elif event.key == pygame.K_SPACE:
                        if self.game.phase == GamePhase.NIGHT:
                            mx, my = self.mouse_pos
                            world_gx = (mx - GRID_X) / CELL_SIZE
                            world_gy = (my - GRID_Y) / CELL_SIZE
                            success, msg = self.game.use_flashlight_stun(world_gx, world_gy)
                            if success:
                                self._spawn_particles(mx, my, (255, 255, 200), count=15)
                            else:
                                self.log_messages.append(f"🔦 {msg}")
                        else:
                            self.log_messages.append("☀️ 白天請專心耕作，夜晚來臨時按空白鍵可發動手電筒強光擊暈！")



            if not self.show_intro:
                self.game.update(dt)

            self._process_events()
            self._update_card_states()

            self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]
            self.particles = [p for p in self.particles if p.update(dt)]

            self._render()

            pygame.display.flip()

        pygame.quit()

    def _handle_mouse_move(self, event):
        mx, my = event.pos
        self.mouse_pos = (mx, my)

        for card in self.action_cards:
            if card.tab_id == self.active_tab:
                card.is_hovered = card.rect.collidepoint(mx, my)

        gx = (mx - GRID_X) // CELL_SIZE
        gy = (my - GRID_Y) // CELL_SIZE
        if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
            self.hovered_grid = (gx, gy)
        else:
            self.hovered_grid = None

    def _handle_mouse_down(self, event):
        if event.button != 1:
            return
        mx, my = event.pos

        # 開場新手速成圖卡彈窗
        if self.show_intro:
            modal_w, modal_h = 840, 580
            mod_x = (SCREEN_WIDTH - modal_w) // 2
            mod_y = (SCREEN_HEIGHT - modal_h) // 2
            btn_start = pygame.Rect(mod_x + (modal_w - 280) // 2, mod_y + 500, 280, 54)
            if btn_start.collidepoint(mx, my) or not pygame.Rect(mod_x, mod_y, modal_w, modal_h).collidepoint(mx, my):
                self.show_intro = False
                self.sound.play("build")
            return


        # 遊戲結束
        if self.game.game_over:
            btn_restart = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 70, 200, 48)
            if btn_restart.collidepoint(mx, my):
                self.game = GameState()
                self.log_messages.clear()
                self.log_messages.append("🌾 遊戲已重新開始！")
                self.sound.play("harvest")
            return

        # 分頁標籤
        for tab_id, label, rect in self.tab_buttons:
            if rect.collidepoint(mx, my):
                self.active_tab = tab_id
                self.sound.play("plant")
                return

        # 卡片點擊
        for card in self.action_cards:
            if card.tab_id == self.active_tab and card.rect.collidepoint(mx, my):
                if card.action_id == "BUY_DOG":
                    success, msg = self.game.buy_guard_dog()
                    if not success:
                        self.log_messages.append(f"❌ {msg}")
                elif card.action_id == "BUY_CAT":
                    success, msg = self.game.buy_farm_cat()
                    if not success:
                        self.log_messages.append(f"❌ {msg}")
                else:
                    if not card.is_locked:
                        self.selected_action = card.action_id
                        self.sound.play("plant")
                    else:
                        self.log_messages.append(f"🔒 {card.lock_reason}")
                return

        # 地圖座標換算
        world_gx = (mx - GRID_X) / CELL_SIZE
        world_gy = (my - GRID_Y) / CELL_SIZE

        # 1. 第一優先權：若點擊格子上有「成熟作物」，無論當前選中何種工具，一律直接採收！
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            tile = self.game.get_tile(gx, gy)
            if tile and tile.crop and tile.crop.is_mature:
                success, reward, msg = self.game.harvest_crop(gx, gy)
                if not success:
                    self.log_messages.append(f"❌ {msg}")
                return

        # 2. 第二優先權：主動戰術工具 (手電筒、指揮哨)
        if self.selected_action == "FLASHLIGHT":
            if self.game.phase == GamePhase.DAY:
                self.log_messages.append("☀️ 白天無入侵敵人！已為您自動切換至農耕播種模式。")
                self.active_tab = "CROPS"
                self.selected_action = "PLANT_RADISH"
            else:
                success, msg = self.game.use_flashlight_stun(world_gx, world_gy)
                if not success:
                    self.log_messages.append(f"🔦 {msg}")
                else:
                    self._spawn_particles(mx, my, (255, 255, 200), count=15)
            return

        if self.selected_action == "WHISTLE":
            success, msg = self.game.use_dog_whistle(world_gx, world_gy)
            if not success:
                self.log_messages.append(f"🔔 {msg}")
            else:
                self._spawn_particles(mx, my, C_CYAN, count=12)
            return

        # 3. 第三優先權：地圖建築、播種、澆水操作
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            self._apply_grid_action(gx, gy)

    def _apply_grid_action(self, gx: int, gy: int):
        tile = self.game.get_tile(gx, gy)
        
        # 【一鍵直接採收】：若點擊成熟作物，一律直接採收獲取金幣，無須切換任何工具！
        if tile and tile.crop and tile.crop.is_mature:
            success, reward, msg = self.game.harvest_crop(gx, gy)
            if not success:
                self.log_messages.append(f"❌ {msg}")
            return

        act = self.selected_action

        # 作物 (10 種)
        if act == "PLANT_RADISH":
            success, msg = self.game.plant_crop(gx, gy, CropType.WHITE_RADISH)
        elif act == "PLANT_TOMATO":
            success, msg = self.game.plant_crop(gx, gy, CropType.RED_TOMATO)
        elif act == "PLANT_CORN":
            success, msg = self.game.plant_crop(gx, gy, CropType.SWEET_CORN)
        elif act == "PLANT_EGGPLANT":
            success, msg = self.game.plant_crop(gx, gy, CropType.CRYSTAL_EGGPLANT)
        elif act == "PLANT_STRAWBERRY":
            success, msg = self.game.plant_crop(gx, gy, CropType.SWEET_STRAWBERRY)
        elif act == "PLANT_PUMPKIN":
            success, msg = self.game.plant_crop(gx, gy, CropType.MAGIC_PUMPKIN)
        elif act == "PLANT_WATERMELON":
            success, msg = self.game.plant_crop(gx, gy, CropType.CRISP_WATERMELON)
        elif act == "PLANT_SUNFLOWER":
            success, msg = self.game.plant_crop(gx, gy, CropType.GOLDEN_SUNFLOWER)
        elif act == "PLANT_GRAPE":
            success, msg = self.game.plant_crop(gx, gy, CropType.ROYAL_GRAPE)
        elif act == "PLANT_STARLIGHT":
            success, msg = self.game.plant_crop(gx, gy, CropType.STARLIGHT_FRUIT)
        # 景觀 (13 種)
        elif act == "PLACE_PATH":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.STONE_PATH)
        elif act == "PLACE_FLOWER":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.FLOWER_BED)
        elif act == "PLACE_BENCH":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.GARDEN_BENCH)
        elif act == "PLACE_PINE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.PINE_TREE)
        elif act == "PLACE_APPLE_TREE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.APPLE_TREE)
        elif act == "PLACE_LANTERN":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.SOUL_LANTERN)
        elif act == "PLACE_SAKURA_TREE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.SAKURA_TREE)
        elif act == "PLACE_BIRD_BATH":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.BIRD_BATH)
        elif act == "PLACE_STATUE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.ANCIENT_STATUE)
        elif act == "PLACE_PET_HOUSE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.PET_HOUSE)
        elif act == "PLACE_FOUNTAIN":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.CRYSTAL_FOUNTAIN)
        elif act == "PLACE_SUNDIAL":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.SUNDIAL_TOWER)
        elif act == "PLACE_WINDMILL":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.WINDMILL)
        # 防禦
        elif act == "PLACE_FENCE":
            success, msg = self.game.place_defense(gx, gy, DefenseType.WOODEN_FENCE)
        elif act == "PLACE_TRAP":
            success, msg = self.game.place_defense(gx, gy, DefenseType.BEAR_TRAP)
        elif act == "PLACE_SCARECROW":
            success, msg = self.game.place_defense(gx, gy, DefenseType.SCARECROW)
        elif act == "PLACE_BEEHIVE":
            success, msg = self.game.place_defense(gx, gy, DefenseType.BEEHIVE)
        # 工具
        elif act == "HARVEST":
            success, reward, msg = self.game.harvest_crop(gx, gy)
        elif act == "WATER_CROP":
            success, msg = self.game.water_crop(gx, gy)
        else:
            success, msg = False, "未知操作"

        if not success:
            self.log_messages.append(f"❌ {msg}")

    def _spawn_particles(self, px: float, py: float, color: tuple, count: int = 8):
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(25, 90)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            self.particles.append(Particle(px, py, vx, vy, color, random.uniform(3, 6), random.uniform(0.4, 0.8)))

    def _process_events(self):
        for ev in self.game.poll_events():
            self.sound.handle_game_event(ev)
            self.log_messages.append(ev.message)
            if len(self.log_messages) > 16:
                self.log_messages.pop(0)

            if ev.event_type == EventType.CROP_HARVESTED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"+{ev.data['reward']} G", px - 15, py - 10, C_GOLD))
                self._spawn_particles(px, py, C_GOLD, count=12)
            elif ev.event_type == EventType.CROP_WATERED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"💧 加速生長！", px - 25, py - 12, C_CYAN))
                self._spawn_particles(px, py, C_CYAN, count=10)
            elif ev.event_type == EventType.VAULT_RAIDED:
                vx, vy = MAP_CONFIG["VAULT_POS"]
                px = GRID_X + vx * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + vy * CELL_SIZE
                self.floating_texts.append(FloatingText(f"🚨 金庫被洗劫 -{ev.data['gold_lost']} G！", px - 40, py - 20, C_RED, duration=2.2))
                self._spawn_particles(px, py, C_RED, count=25)
            elif ev.event_type == EventType.DAILY_TAX_PAID:
                self.floating_texts.append(FloatingText(f"🏛️ 地租維護費 -{ev.data['tax']} G", 460, 60, (239, 83, 80)))
            elif ev.event_type == EventType.ENEMY_STUNNED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                self.floating_texts.append(FloatingText("⚡ 暈眩 2.5s", px - 20, py - 15, (255, 235, 59)))
                self._spawn_particles(px, py, (255, 235, 59), count=14)
            elif ev.event_type == EventType.BEE_ATTACK:
                fx = GRID_X + ev.data["from_x"] * CELL_SIZE + CELL_SIZE // 2
                fy = GRID_Y + ev.data["from_y"] * CELL_SIZE + CELL_SIZE // 2
                tx = GRID_X + ev.data["to_x"] * CELL_SIZE + CELL_SIZE // 2
                ty = GRID_Y + ev.data["to_y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"🐝 -{int(ev.data['damage'])}", tx - 15, ty - 12, C_GOLD))
                self._spawn_particles(tx, ty, C_GOLD, count=8)
            elif ev.event_type == EventType.BLOOD_MOON_WARNING:
                self.floating_texts.append(FloatingText("🩸 血月降臨！巨型野豬首領來襲！", SCREEN_WIDTH // 2 - 120, 220, C_BLOOD_RED, duration=3.0))
                self._spawn_particles(SCREEN_WIDTH // 2, 240, C_BLOOD_RED, count=40)
            elif ev.event_type == EventType.TRAP_TRIGGERED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"💥 {int(ev.data['damage'])}", px - 15, py - 15, C_RED))
                self._spawn_particles(px, py, (220, 50, 50), count=16)
            elif ev.event_type == EventType.DOG_ATTACK:
                if self.game.guard_dog:
                    px = GRID_X + self.game.guard_dog.x * CELL_SIZE + CELL_SIZE // 2
                    py = GRID_Y + self.game.guard_dog.y * CELL_SIZE
                    self.floating_texts.append(FloatingText(f"🐕 撲咬 -{int(ev.data['damage'])}", px - 20, py - 10, C_ORANGE))
                    self._spawn_particles(px, py, C_ORANGE, count=8)
            elif ev.event_type == EventType.CAT_BONUS:
                if self.game.farm_cat:
                    px = GRID_X + self.game.farm_cat.x * CELL_SIZE
                    py = GRID_Y + self.game.farm_cat.y * CELL_SIZE - 10
                    self.floating_texts.append(FloatingText(f"🐱 +{ev.data['bonus']} G (招財)", px - 15, py, C_GOLD))
                    self._spawn_particles(px, py, C_GOLD, count=6)
            elif ev.event_type == EventType.FARM_LEVEL_UP:
                self.floating_texts.append(FloatingText(f"⭐ 莊園繁榮升級 Lv.{ev.data['new_level']}！", SCREEN_WIDTH // 2 - 90, 220, C_GOLD, duration=2.5))
                self._spawn_particles(SCREEN_WIDTH // 2, 240, C_GOLD, count=30)
            elif ev.event_type == EventType.FENCE_DESTROYED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"💥 圍籬被衝破！", px - 35, py - 18, C_RED, duration=2.5))
                self._spawn_particles(px, py, (160, 100, 60), count=25)
            elif ev.event_type == EventType.DAY_STARTED:
                if self.active_tab == "TOOLS" or self.selected_action in ("FLASHLIGHT", "WHISTLE"):
                    self.active_tab = "CROPS"
                    self.selected_action = "PLANT_RADISH"

    def _get_mascot_guide_data(self) -> Tuple[str, tuple, str, tuple, str]:
        """Returns (badge_text, badge_bg_color, main_dialogue, text_color, step_tag)"""
        if self.game.phase == GamePhase.NIGHT:
            if self.game.is_blood_moon:
                return (
                    "🩸 血月首領",
                    (211, 47, 47),
                    "【血月警報】巨型野豬巨獸即將破壞防線！請用手電筒強光擊暈，柴犬與蜜蜂塔全力集火！",
                    (255, 180, 180),
                    "[集火 Boss]"
                )
            else:
                return (
                    "🔦 夜巡夜戰",
                    (33, 150, 243),
                    "【夜間防守】入侵者來襲！游標瞄準敵人，按【空白鍵 Space】發動強光手電筒擊暈他！",
                    (179, 229, 252),
                    "[空白鍵擊暈]"
                )
        else:
            # Daytime
            crops_count = sum(1 for row in self.game.grid for tile in row if tile.crop)
            mature_count = sum(1 for row in self.game.grid for tile in row if tile.crop and tile.crop.is_mature)

            if self.game.day_count == 1:
                if crops_count == 0:
                    return (
                        "🐶 柴犬管家",
                        (255, 152, 0),
                        "領主你好！快點選下方【白蘿蔔種子】，在中央金色農田點擊 3~5 格播種賺錢！",
                        (255, 245, 157),
                        "[步驟 1/3：播種]"
                    )
                elif mature_count > 0:
                    return (
                        "🌾 採收豐收",
                        (76, 175, 80),
                        "作物成熟泛出金黃光芒了！請【直接滑鼠點擊作物】採收，換取第一桶金！",
                        (200, 230, 201),
                        "[步驟 2/3：採收]"
                    )
                elif self.game.time_in_phase > 15.0:
                    return (
                        "🛡️ 防守備戰",
                        (239, 83, 80),
                        "天色即將變暗！請點擊【防禦】分頁，購買【看門柴犬 ($100)】或【刺藤木柵】保護農田！",
                        (255, 204, 128),
                        "[步驟 3/3：防禦]"
                    )
                else:
                    return (
                        "⏳ 生長觀察",
                        (0, 188, 212),
                        "作物正在快速生長中！可點擊【黃金澆水壺】加速進度，靜候成熟採收！",
                        (220, 237, 200),
                        "[生長觀察]"
                    )
            elif self.game.day_count == 2:
                if mature_count > 0:
                    return (
                        "🌾 採收提醒",
                        (76, 175, 80),
                        "有成熟作物等待採收！天黑前記得收成，存活過夜作物更享有月光加成 +50%！",
                        (200, 230, 201),
                        "[點擊採收]"
                    )
                elif self.game.time_in_phase > 12.0:
                    return (
                        "🛡️ 防線加固",
                        (239, 83, 80),
                        "野豬即將加入夜襲！多配置幾條刺藤圍籬與捕獸夾，防止防線被衝破！",
                        (255, 204, 128),
                        "[佈置防禦]"
                    )
                else:
                    return (
                        "🌸 景觀擴建",
                        (156, 39, 176),
                        "第 2 天開始！到【景觀】分頁佈置果樹、噴泉提升繁榮度，解鎖甜玉米與草莓！",
                        (245, 245, 245),
                        "[莊園升級]"
                    )
            else:
                if mature_count > 0:
                    return (
                        "🌾 豐收時刻",
                        (76, 175, 80),
                        "請及時採收成熟作物，為莊園籌措升級資金與繳納每日領地地租！",
                        (200, 230, 201),
                        "[點擊採收]"
                    )
                else:
                    return (
                        "🏛️ 領地經營",
                        (156, 39, 176),
                        f"第 {self.game.day_count} 天莊園繁榮度: {self.game.prosperity_score}！持續佈置景觀解鎖高級魔法南瓜！",
                        (245, 245, 245),
                        f"[Lv.{self.game.farm_level}]"
                    )



    def _update_card_states(self):
        for card in self.action_cards:
            # 作物解鎖判定
            if card.action_id in ("PLANT_CORN", "PLANT_EGGPLANT", "PLANT_STRAWBERRY"):
                card.is_locked = not self.game.is_crop_unlocked(CropType.SWEET_CORN)
                card.lock_reason = "需莊園等級 Lv.2"
            elif card.action_id in ("PLANT_PUMPKIN", "PLANT_WATERMELON", "PLANT_SUNFLOWER"):
                card.is_locked = not self.game.is_crop_unlocked(CropType.MAGIC_PUMPKIN)
                card.lock_reason = "需莊園等級 Lv.3"
            elif card.action_id == "PLANT_GRAPE":
                card.is_locked = not self.game.is_crop_unlocked(CropType.ROYAL_GRAPE)
                card.lock_reason = "需莊園等級 Lv.4"
            elif card.action_id == "PLANT_STARLIGHT":
                card.is_locked = not self.game.is_crop_unlocked(CropType.STARLIGHT_FRUIT)
                card.lock_reason = "需莊園等級 Lv.5"
            elif card.action_id == "BUY_DOG":
                card.is_locked = self.game.has_dog
                card.lock_reason = "已擁有看門柴犬"
            elif card.action_id == "BUY_CAT":
                card.is_locked = self.game.has_cat
                card.lock_reason = "已擁有招財小貓"
            elif card.action_id == "FLASHLIGHT":
                if self.game.flashlight_cooldown > 0:
                    card.cost_text = f"CD: {self.game.flashlight_cooldown:.1f}s"
                else:
                    card.cost_text = "就緒 | 暈眩2.5s"

    # ==========================================
    # 純色扁平無網格渲染管道 (Flat Pipeline)
    # ==========================================
    def _render(self):
        self.screen.fill((240, 244, 248))

        self._render_header_banner()
        self._render_flat_meadow_and_farm()

        if self.game.phase == GamePhase.NIGHT:
            self._render_night_overlay()

        self._render_entities()

        for p in self.particles:
            p.draw(self.screen)
        for ft in self.floating_texts:
            ft.draw(self.screen)

        self._render_sidebar()
        self._render_tabbed_toolbar()

        if self.show_intro:
            self._render_story_modal()
        elif self.game.game_over:
            self._render_game_over_modal()

    def _render_header_banner(self):
        is_day = (self.game.phase == GamePhase.DAY)
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 70)
        pygame.draw.rect(self.screen, C_NAVY_TOP, header_rect)

        self.screen.blit(FONT_TITLE.render("🌾 夜巡農場 (Harvest & Hordes)", True, C_GOLD), (24, 8))

        if self.game.is_blood_moon and not is_day:
            phase_txt = f"🩸 第 {self.game.day_count} 天・血月首領戰！"
            phase_col = (255, 82, 82)
        else:
            phase_txt = f"☀️ 第 {self.game.day_count} 天・白天 (經營期)" if is_day else f"🌙 第 {self.game.day_count} 天・夜晚 (守衛期)"
            phase_col = (255, 235, 59) if is_day else (129, 212, 250)

        self.screen.blit(FONT_MD.render(phase_txt, True, phase_col), (24, 40))

        max_dur = self.game.day_duration if is_day else self.game.night_duration
        rem_time = max(0.0, max_dur - self.game.time_in_phase)
        prog = max(0.0, min(1.0, 1.0 - (self.game.time_in_phase / max_dur)))

        bar_r = pygame.Rect(230, 43, 140, 14)
        pygame.draw.rect(self.screen, (20, 25, 30), bar_r, border_radius=7)
        fill_w = int(bar_r.width * prog)
        fill_col = C_GREEN if is_day else (C_BLOOD_RED if self.game.is_blood_moon else C_CYAN)
        if fill_w > 0:
            pygame.draw.rect(self.screen, fill_col, (bar_r.x, bar_r.y, fill_w, bar_r.height), border_radius=7)
        self.screen.blit(FONT_XS.render(f"{rem_time:.1f}s", True, C_WHITE), (bar_r.right + 8, bar_r.y))

        # 金幣卡
        gold_rect = pygame.Rect(430, 12, 180, 44)
        pygame.draw.rect(self.screen, (55, 71, 79), gold_rect, border_radius=10)
        pygame.draw.circle(self.screen, C_GOLD, (gold_rect.x + 22, gold_rect.centery), 12)
        self.screen.blit(FONT_SM.render("G", True, (60, 40, 0)), (gold_rect.x + 17, gold_rect.centery - 8))
        self.screen.blit(FONT_LG.render(f"{self.game.gold} 金幣", True, C_GOLD), (gold_rect.x + 44, gold_rect.centery - 11))

        # 等級與繁榮度
        lvl_rect = pygame.Rect(630, 12, 606, 44)
        pygame.draw.rect(self.screen, (55, 71, 79), lvl_rect, border_radius=10)
        lvl_name = FARM_LEVELS[self.game.farm_level]["name"]
        self.screen.blit(FONT_MD.render(f"🏆 莊園等級: Lv.{self.game.farm_level} ({lvl_name})", True, C_WHITE), (lvl_rect.x + 14, lvl_rect.y + 4))

        goals = {1: 40, 2: 100, 3: 200, 4: 350, 5: 500}
        next_goal = goals.get(self.game.farm_level, 500)
        curr_p = self.game.prosperity_score
        p_ratio = min(1.0, curr_p / next_goal)

        p_bar = pygame.Rect(lvl_rect.x + 14, lvl_rect.y + 24, 430, 12)
        pygame.draw.rect(self.screen, (25, 30, 40), p_bar, border_radius=6)
        if p_ratio > 0:
            pygame.draw.rect(self.screen, C_PURPLE, (p_bar.x, p_bar.y, int(p_bar.width * p_ratio), p_bar.height), border_radius=6)
        self.screen.blit(FONT_SM.render(f"繁榮度: {curr_p} / {next_goal}", True, C_CYAN), (p_bar.right + 12, p_bar.y - 3))

    def _render_flat_meadow_and_farm(self):
        map_w = self.game.width * CELL_SIZE
        map_h = self.game.height * CELL_SIZE
        map_rect = pygame.Rect(GRID_X, GRID_Y, map_w, map_h)
        pygame.draw.rect(self.screen, C_MEADOW_BG, map_rect, border_radius=16)

        fx_min, fx_max = MAP_CONFIG["FARM_X_RANGE"]
        fy_min, fy_max = MAP_CONFIG["FARM_Y_RANGE"]
        farm_rx = GRID_X + fx_min * CELL_SIZE
        farm_ry = GRID_Y + fy_min * CELL_SIZE
        farm_rw = (fx_max - fx_min + 1) * CELL_SIZE
        farm_rh = (fy_max - fy_min + 1) * CELL_SIZE

        pygame.draw.rect(self.screen, C_FARM_SHADOW, (farm_rx - 4, farm_ry - 4, farm_rw + 8, farm_rh + 8), border_radius=20)
        pygame.draw.rect(self.screen, C_FARM_BORDER, (farm_rx - 2, farm_ry - 2, farm_rw + 4, farm_rh + 4), border_radius=18)
        pygame.draw.rect(self.screen, C_FARM_SOIL, (farm_rx, farm_ry, farm_rw, farm_rh), border_radius=16)

        # 中央農莊金庫標誌
        vx, vy = MAP_CONFIG["VAULT_POS"]
        v_px = GRID_X + vx * CELL_SIZE
        v_py = GRID_Y + vy * CELL_SIZE
        pygame.draw.circle(self.screen, (255, 215, 0, 100), (v_px + CELL_SIZE // 2, v_py + CELL_SIZE // 2), 16)
        pygame.draw.rect(self.screen, (141, 110, 99), (v_px + 12, v_py + 14, 26, 22), border_radius=4)
        pygame.draw.circle(self.screen, C_GOLD, (v_px + 25, v_py + 25), 5)

        for y in range(self.game.height):
            for x in range(self.game.width):
                tile = self.game.grid[y][x]
                px = GRID_X + x * CELL_SIZE
                py = GRID_Y + y * CELL_SIZE

                if tile.decoration:
                    dt = tile.decoration.decoration_type
                    k = DECORATION_DATA[dt].get("asset_key", "stone_path")
                    img = self.loader.get(k)
                    if img:
                        self.screen.blit(img, (px, py))

                if tile.defense:
                    df = tile.defense.defense_type
                    k = DEFENSE_DATA[df].get("asset_key", "wooden_fence")
                    img = self.loader.get(k)
                    if img:
                        self.screen.blit(img, (px, py))

                    # 圍籬耐久度血條與受損視覺反饋
                    if df == DefenseType.WOODEN_FENCE and tile.defense.hp < tile.defense.max_hp:
                        ratio = max(0.0, tile.defense.hp / tile.defense.max_hp)
                        hb_w = CELL_SIZE - 8
                        hb_h = 4
                        hb_x = px + 4
                        hb_y = py + CELL_SIZE - 6
                        pygame.draw.rect(self.screen, (40, 40, 40), (hb_x, hb_y, hb_w, hb_h), border_radius=2)
                        bar_col = (76, 175, 80) if ratio > 0.5 else ((255, 152, 0) if ratio > 0.25 else (239, 83, 80))
                        pygame.draw.rect(self.screen, bar_col, (hb_x, hb_y, int(hb_w * ratio), hb_h), border_radius=2)

                    # 若敵人正在破壞這座圍籬，繪製危險攻擊警示框
                    if any(e.attacking_fence == (x, y) for e in self.game.enemies):
                        flash_alpha = int(120 + math.sin(self.anim_time * 15.0) * 80)
                        warn_s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                        pygame.draw.rect(warn_s, (255, 50, 50, flash_alpha), (0, 0, CELL_SIZE, CELL_SIZE), width=2, border_radius=4)
                        self.screen.blit(warn_s, (px, py))

                if tile.crop:
                    ct = tile.crop.crop_type
                    base_key = CROP_DATA[ct].get("asset_key", "radish")
                    st_key = tile.crop.stage.name.lower()
                    img = self.loader.get(f"{base_key}_{st_key}")
                    if img:
                        self.screen.blit(img, (px, py))

                    if tile.crop.is_moonlight_boosted:
                        pygame.draw.circle(self.screen, (129, 212, 250), (px + 10, py + 10), 4)

                    if tile.crop.is_mature:
                        bob = math.sin(self.anim_time * 6.0) * 3
                        pygame.draw.circle(self.screen, C_GOLD, (px + CELL_SIZE - 9, int(py + 9 + bob)), 6)
                        pygame.draw.circle(self.screen, (255, 255, 255), (px + CELL_SIZE - 9, int(py + 9 + bob)), 3)
                    else:
                        ratio = min(1.0, tile.crop.growth_timer / tile.crop.grow_time)
                        pb = pygame.Rect(px + 6, py + CELL_SIZE - 6, CELL_SIZE - 12, 3)
                        pygame.draw.rect(self.screen, (0, 0, 0, 80), pb)
                        pygame.draw.rect(self.screen, (76, 175, 80), (pb.x, pb.y, int(pb.width * ratio), 3))

        # 第 1 天未播種時，農田外框呈現金色呼吸引導光效
        if self.game.day_count == 1 and sum(1 for row in self.game.grid for tile in row if tile.crop) == 0:
            pulse = (math.sin(self.anim_time * 5.0) + 1.0) * 0.5
            glow_alpha = int(120 + pulse * 135)
            guide_s = pygame.Surface((farm_rw + 8, farm_rh + 8), pygame.SRCALPHA)
            pygame.draw.rect(guide_s, (255, 215, 0, glow_alpha), (0, 0, farm_rw + 8, farm_rh + 8), width=3, border_radius=18)
            self.screen.blit(guide_s, (farm_rx - 4, farm_ry - 4))
            
            # 中央飄浮新手引導標籤
            tip_w, tip_h = 210, 26
            tip_x = farm_rx + (farm_rw - tip_w) // 2
            tip_y = farm_ry + 20
            pygame.draw.rect(self.screen, (38, 50, 56, 230), (tip_x, tip_y, tip_w, tip_h), border_radius=6)
            pygame.draw.rect(self.screen, C_GOLD, (tip_x, tip_y, tip_w, tip_h), width=1, border_radius=6)
            self.screen.blit(FONT_SM.render("👇 請在此處點擊播種白蘿蔔", True, C_GOLD), (tip_x + 14, tip_y + 4))

        if self.hovered_grid:
            gx, gy = self.hovered_grid
            cx = GRID_X + gx * CELL_SIZE + CELL_SIZE // 2
            cy = GRID_Y + gy * CELL_SIZE + CELL_SIZE // 2
            glow_s = pygame.Surface((CELL_SIZE * 2, CELL_SIZE * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 255, 255, 110), (CELL_SIZE, CELL_SIZE), 24, 3)
            self.screen.blit(glow_s, (cx - CELL_SIZE, cy - CELL_SIZE))

        # 即時情境【柴犬教官】動態新手對話框
        badge_txt, badge_bg, main_txt, txt_col, step_tag = self._get_mascot_guide_data()
        banner_h = 26
        banner_rect = pygame.Rect(GRID_X, GRID_Y - 28, map_w, banner_h)
        pygame.draw.rect(self.screen, (28, 37, 46, 235), banner_rect, border_radius=8)
        pygame.draw.rect(self.screen, (70, 85, 100), banner_rect, width=1, border_radius=8)

        # 左側膠囊徽章 (Badge)
        badge_w = 95
        badge_r = pygame.Rect(banner_rect.x + 4, banner_rect.y + 3, badge_w, banner_h - 6)
        pygame.draw.rect(self.screen, badge_bg, badge_r, border_radius=6)
        b_surf = FONT_XS.render(badge_txt, True, C_WHITE)
        self.screen.blit(b_surf, (badge_r.centerx - b_surf.get_width() // 2, badge_r.centery - b_surf.get_height() // 2))

        # 中間主引導對話
        self.screen.blit(FONT_SM.render(main_txt, True, txt_col), (badge_r.right + 12, banner_rect.y + 4))

        # 右側步驟進度標籤
        tag_surf = FONT_XS.render(step_tag, True, (176, 190, 197))
        self.screen.blit(tag_surf, (banner_rect.right - tag_surf.get_width() - 10, banner_rect.y + 5))



    def _render_night_overlay(self):
        overlay = pygame.Surface((self.game.width * CELL_SIZE, self.game.height * CELL_SIZE), pygame.SRCALPHA)
        if self.game.is_blood_moon:
            overlay.fill((80, 15, 25, 185))
        else:
            overlay.fill((15, 23, 42, 175))

        if self.game.guard_dog:
            dx = int(self.game.guard_dog.x * CELL_SIZE + CELL_SIZE // 2)
            dy = int(self.game.guard_dog.y * CELL_SIZE + CELL_SIZE // 2)
            pygame.draw.circle(overlay, (0, 0, 0, 0), (dx, dy), 75)

        for y in range(self.game.height):
            for x in range(self.game.width):
                tile = self.game.grid[y][x]
                if tile.decoration:
                    dt = tile.decoration.decoration_type
                    if dt in (DecorationType.CRYSTAL_FOUNTAIN, DecorationType.SOUL_LANTERN):
                        fx = int(x * CELL_SIZE + CELL_SIZE // 2)
                        fy = int(y * CELL_SIZE + CELL_SIZE // 2)
                        pygame.draw.circle(overlay, (0, 0, 0, 0), (fx, fy), 60)

        self.screen.blit(overlay, (GRID_X, GRID_Y))

    def _render_entities(self):
        if self.game.guard_dog:
            dog = self.game.guard_dog
            px = int(GRID_X + dog.x * CELL_SIZE)
            py = int(GRID_Y + dog.y * CELL_SIZE)
            img = self.loader.get("guard_dog")
            if img:
                self.screen.blit(img, (px, py))
            if dog.state in (DogState.CHASING, DogState.COMMANDED):
                bubble_r = pygame.Rect(px + CELL_SIZE - 6, py - 12, 26, 16)
                pygame.draw.rect(self.screen, (255, 255, 255), bubble_r, border_radius=4)
                txt = "汪!" if dog.state == DogState.CHASING else "衝!"
                self.screen.blit(FONT_XS.render(txt, True, C_RED), (bubble_r.x + 4, bubble_r.y + 1))

        if self.game.farm_cat:
            cat = self.game.farm_cat
            px = int(GRID_X + cat.x * CELL_SIZE)
            py = int(GRID_Y + cat.y * CELL_SIZE)
            img = self.loader.get("farm_cat")
            if img:
                self.screen.blit(img, (px, py))

        for enemy in self.game.enemies:
            px = int(GRID_X + enemy.x * CELL_SIZE)
            py = int(GRID_Y + enemy.y * CELL_SIZE)
            
            k = "boss_boar" if enemy.enemy_type == EnemyType.BOSS_BOAR_KING else ENEMY_DATA[enemy.enemy_type].get("asset_key", "enemy_thief")
            img = self.loader.get(k)
            if img:
                offset_y = -10 if enemy.enemy_type == EnemyType.BOSS_BOAR_KING else 0
                self.screen.blit(img, (px, py + offset_y))

            if enemy.state == EnemyState.STUNNED:
                pygame.draw.circle(self.screen, (255, 235, 59), (px + CELL_SIZE // 2, py - 12), 8)
                self.screen.blit(FONT_XS.render("⚡", True, (60, 40, 0)), (px + CELL_SIZE // 2 - 4, py - 18))

            hp_ratio = max(0.0, min(1.0, enemy.hp / enemy.max_hp))
            bar_w = CELL_SIZE - 6 if enemy.enemy_type != EnemyType.BOSS_BOAR_KING else CELL_SIZE + 16
            bar_rect = pygame.Rect(px + 3, py - 6, bar_w, 5)
            pygame.draw.rect(self.screen, (30, 30, 30), bar_rect, border_radius=2)
            pygame.draw.rect(self.screen, C_RED, (bar_rect.x, bar_rect.y, int(bar_w * hp_ratio), 5), border_radius=2)

    def _render_sidebar(self):
        sb_x = GRID_X + self.game.width * CELL_SIZE + 18
        sb_w = SCREEN_WIDTH - sb_x - 24
        sb_rect = pygame.Rect(sb_x, GRID_Y, sb_w, self.game.height * CELL_SIZE)

        pygame.draw.rect(self.screen, (255, 255, 255), sb_rect, border_radius=12)
        pygame.draw.rect(self.screen, C_CARD_BORDER, sb_rect, width=1, border_radius=12)

        self.screen.blit(FONT_MD.render("🔍 即時狀態探測", True, C_TEXT_MAIN), (sb_x + 16, GRID_Y + 14))

        info_y = GRID_Y + 40
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            tile = self.game.get_tile(gx, gy)
            zone_str = "🌾 中央農田" if tile.zone == ZoneType.FARM_ZONE else "🌸 四周莊園"
            self.screen.blit(FONT_SM.render(f"座標: ({gx}, {gy}) | {zone_str}", True, C_TEXT_MUTED), (sb_x + 16, info_y))
            info_y += 22

            if (gx, gy) == MAP_CONFIG["VAULT_POS"] and tile.crop is None:
                self.screen.blit(FONT_SM.render("🏛️ 中央農莊金庫 (若農田無作物將受襲擊)", True, (230, 81, 0)), (sb_x + 16, info_y))
                info_y += 20
            elif tile.crop:
                st_map = {"SEED": "種子", "SPROUT": "幼苗", "GROWING": "生長中", "MATURE": "✨ 已成熟(點擊採收)"}
                st_name = st_map.get(tile.crop.stage.name, "未知")
                moon_str = " (🌕月光滋養+50%)" if tile.crop.is_moonlight_boosted else ""
                self.screen.blit(FONT_SM.render(f"作物: {tile.crop.config['name']} ({st_name}){moon_str}", True, C_GREEN), (sb_x + 16, info_y))
                info_y += 20
                if not tile.crop.is_mature:
                    rem = max(0.0, tile.crop.grow_time - tile.crop.growth_timer)
                    self.screen.blit(FONT_XS.render(f"生長剩餘: {rem:.1f}s (可用水壺加速)", True, C_TEXT_MUTED), (sb_x + 16, info_y))
                    info_y += 18
            elif tile.decoration:
                self.screen.blit(FONT_SM.render(f"景觀: {tile.decoration.config['name']} (+{tile.decoration.prosperity_score} 繁榮)", True, C_PURPLE), (sb_x + 16, info_y))
                info_y += 20
            elif tile.defense:
                self.screen.blit(FONT_SM.render(f"設施: {tile.defense.config['name']}", True, C_BLUE), (sb_x + 16, info_y))
                info_y += 20
            else:
                self.screen.blit(FONT_SM.render("空地（可耕作或佈置）", True, C_TEXT_MUTED), (sb_x + 16, info_y))
                info_y += 20
        else:
            self.screen.blit(FONT_SM.render("請將游標移至地圖上查看", True, C_TEXT_MUTED), (sb_x + 16, info_y))
            info_y += 24

        pygame.draw.line(self.screen, (230, 235, 240), (sb_x + 12, info_y + 4), (sb_x + sb_w - 12, info_y + 4))
        info_y += 16

        self.screen.blit(FONT_MD.render("📜 莊園防禦日誌", True, C_TEXT_MAIN), (sb_x + 16, info_y))
        info_y += 26

        for msg in reversed(self.log_messages[-10:]):
            msg_col = C_RED if ("警告" in msg or "偷走" in msg or "洗劫" in msg or "血月" in msg or "失敗" in msg) else (C_GREEN if ("收成" in msg or "升級" in msg or "招財" in msg) else C_TEXT_MAIN)
            m_surf = FONT_XS.render(msg[:28] + "..." if len(msg) > 28 else msg, True, msg_col)
            self.screen.blit(m_surf, (sb_x + 16, info_y))
            info_y += 20

    def _render_tabbed_toolbar(self):
        for tab_id, label, rect in self.tab_buttons:
            is_active = (self.active_tab == tab_id)
            bg_col = (255, 255, 255) if is_active else (225, 230, 235)
            pygame.draw.rect(self.screen, bg_col, rect, border_top_left_radius=8, border_top_right_radius=8)
            border_col = C_ORANGE if is_active else (200, 200, 200)
            pygame.draw.rect(self.screen, border_col, rect, width=2 if is_active else 1, border_top_left_radius=8, border_top_right_radius=8)

            txt_col = C_TEXT_MAIN if is_active else C_TEXT_MUTED
            t_surf = FONT_MD.render(label, True, txt_col)
            self.screen.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.centery - t_surf.get_height() // 2))

        panel_rect = pygame.Rect(GRID_X, 686, SCREEN_WIDTH - 2 * GRID_X, 106)
        pygame.draw.rect(self.screen, (255, 255, 255), panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, C_CARD_BORDER, panel_rect, width=1, border_radius=10)

        for card in self.action_cards:
            if card.tab_id == self.active_tab:
                card.draw(self.screen, is_selected=(self.selected_action == card.action_id), loader=self.loader)

    # ==========================================
    # 開場新手速成圖卡彈窗
    # ==========================================
    def _render_story_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 235))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 840, 580
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)

        pygame.draw.rect(self.screen, (255, 255, 255), modal_rect, border_radius=18)
        pygame.draw.rect(self.screen, C_ORANGE, modal_rect, width=3, border_radius=18)

        t = FONT_TITLE.render("🌾《夜巡農場》新手速成指南 (Quickstart Guide)", True, (38, 50, 56))
        self.screen.blit(t, (mx + (modal_w - t.get_width()) // 2, my + 20))
        sub_t = FONT_SM.render("掌握 3 大核心步驟，由「柴犬管家」手把手帶您守護農莊！", True, C_TEXT_MUTED)
        self.screen.blit(sub_t, (mx + (modal_w - sub_t.get_width()) // 2, my + 56))

        # 3 個直覺新手步驟卡片
        steps = [
            (
                "🌱 步驟 1：日間耕種與採收變現",
                (76, 175, 80),
                (240, 248, 240),
                [
                    "1. 點擊下方工具列【白蘿蔔種子 ($10)】，在中央深色農田點擊播種。",
                    "2. 作物成熟長大後（泛出金黃光芒），【直接點擊作物】即可採收賺取金幣！",
                    "3. 點選【黃金澆水壺 ($5)】可為作物加速生長 50%。"
                ]
            ),
            (
                "🛡️ 步驟 2：天黑前佈置防禦防線",
                (255, 152, 0),
                (255, 248, 238),
                [
                    "1. 天黑前切換至【防禦】分頁，購買【看門柴犬 ($100)】自動撲咬敵人！",
                    "2. 在農田四周建造【刺藤木柵 ($15)】阻擋怪物，或設置【鋼鐵捕獸夾 ($20)】。",
                    "3. 存活過夜的作物隔日採收享有【月光滋養 +50% 巨額金幣】回報！"
                ]
            ),
            (
                "🔦 步驟 3：夜晚夜巡與空白鍵強光擊暈",
                (33, 150, 243),
                (240, 246, 255),
                [
                    "1. 夜晚怪物突襲時，將滑鼠游標瞄準敵人，按下【空白鍵 Space】強光擊暈！",
                    "2. 阻止小偷與野豬掠奪作物與金庫（若農田無作物，敵人將洗劫中央金庫）。",
                    "3. 黎明破曉後扣除每日領地維護費，記得到【景觀】佈置果樹升級莊園！"
                ]
            ),
        ]

        card_y = my + 88
        for title, b_col, bg_col, lines in steps:
            card_r = pygame.Rect(mx + 30, card_y, modal_w - 60, 110)
            pygame.draw.rect(self.screen, bg_col, card_r, border_radius=10)
            pygame.draw.rect(self.screen, b_col, card_r, width=2, border_radius=10)

            # 標題欄
            pygame.draw.rect(self.screen, b_col, (card_r.x, card_r.y, card_r.w, 28), border_top_left_radius=8, border_top_right_radius=8)
            self.screen.blit(FONT_MD.render(title, True, C_WHITE), (card_r.x + 12, card_r.y + 4))

            line_y = card_r.y + 34
            for l in lines:
                self.screen.blit(FONT_SM.render(l, True, (45, 55, 65)), (card_r.x + 14, line_y))
                line_y += 24

            card_y += 122

        # 底部提示文字
        bot_tip = FONT_XS.render("💡 提示：初始資金已充能為 $300 G，第 1 天提供 30 秒充裕時間，請跟隨畫面上方【柴犬管家】輕鬆遊玩！", True, (100, 115, 130))
        self.screen.blit(bot_tip, (mx + (modal_w - bot_tip.get_width()) // 2, my + 468))

        btn_start = pygame.Rect(mx + (modal_w - 280) // 2, my + 500, 280, 54)
        pygame.draw.rect(self.screen, C_GREEN, btn_start, border_radius=12)
        pygame.draw.rect(self.screen, (56, 142, 60), btn_start, width=2, border_radius=12)
        btn_txt = FONT_LG.render("🚀 我瞭解了，開始農莊冒險！", True, C_WHITE)
        self.screen.blit(btn_txt, (btn_start.centerx - btn_txt.get_width() // 2, btn_start.centery - btn_txt.get_height() // 2))


    # ==========================================
    # 遊戲結束彈窗
    # ==========================================
    def _render_game_over_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 580, 330
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)

        pygame.draw.rect(self.screen, (255, 255, 255), modal_rect, border_radius=14)
        pygame.draw.rect(self.screen, C_RED, modal_rect, width=3, border_radius=14)

        t1 = FONT_TITLE.render("💀 遊戲結束 (GAME OVER)", True, C_RED)
        self.screen.blit(t1, (mx + (modal_w - t1.get_width()) // 2, my + 30))

        r1 = FONT_MD.render("農場資金斷絕，破產淘汰！", True, C_TEXT_MAIN)
        self.screen.blit(r1, (mx + (modal_w - r1.get_width()) // 2, my + 80))

        r2 = FONT_SM.render(self.game.game_over_reason, True, C_RED)
        self.screen.blit(r2, (mx + (modal_w - r2.get_width()) // 2, my + 112))

        d1 = FONT_SM.render(f"生存天數: {self.game.day_count} 天 | 最終繁榮度: {self.game.prosperity_score}", True, C_TEXT_MUTED)
        self.screen.blit(d1, (mx + (modal_w - d1.get_width()) // 2, my + 148))

        btn_restart = pygame.Rect(mx + (modal_w - 200) // 2, my + 215, 200, 48)
        pygame.draw.rect(self.screen, C_GREEN, btn_restart, border_radius=8)
        btn_txt = FONT_MD.render("🔄 重新挑戰農場", True, C_WHITE)
        self.screen.blit(btn_txt, (btn_restart.centerx - btn_txt.get_width() // 2, btn_restart.centery - btn_txt.get_height() // 2))


if __name__ == "__main__":
    app = NightwatchFarmApp()
    app.run()