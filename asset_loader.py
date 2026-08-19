"""
夜巡農場 (Nightwatch Farm) - 素材圖像載入器 (AssetLoader)
自動載入 assets/ 目錄下的所有透明 PNG 圖片（10種作物、13種景觀、防禦與生物）。
"""

import os
import pygame
from typing import Dict, Tuple

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")

# ---- 血月首領 (pig_chroma.png) 精靈圖設定 --------------------------------
# 實測 assets/characters/pig_chroma.png 目前是 1024x1024、5 欄 x 5 列
# (每格 204x204) 的網格圖，不是原本假設的「4方向 x 3~4幀」乾淨走路循環圖
# ——25 格內容看起來都是同一隻豬皇的姿勢/表情小變化，沒辦法明確分出
# 上下左右 4 個方向。如果之後重新輸出/裁切出方向差異明顯的版本，
# 改下面這兩個數字 + BOSS_ROW_DIRECTIONS 就好，不用動切圖或渲染邏輯。
BOSS_FRAME_COLS = 5   # 每列有幾幀動畫（橫向、欄數）
BOSS_FRAME_ROWS = 5   # 有幾列（縱向、列數）
# 由上而下，每一「列」對應哪個方向。目前設成 None，代表「不分方向」：
# 25 格全部攤平成同一組動畫，走路時四個方向都播放同一份幀，先讓血月
# 首領有移動動畫可看。之後如果有清楚的方向素材，改成類似
# ["down", "left", "right", "up"] 這樣的 list（依你實際的列數與順序調整），
# 下面 load_all() 裡會自動改成依方向查表。
BOSS_ROW_DIRECTIONS = None
# pig_chroma.png 實測本身就有真正的 PNG alpha 透明背景（角落像素
# alpha=0），不是純色去背 (Chroma Key)，所以預設 None = 不做 Chroma Key，
# 直接用 convert_alpha() 保留原本的半透明邊緣（畫質比去背更平滑）。
# 如果之後換成背景是純色（例如螢光洋紅/綠幕）的圖，才把這裡改成該顏色
# RGB，例如 (255, 0, 255)，程式會改用 set_colorkey 去背。
BOSS_CHROMA_KEY = None


class AssetLoader:
    def __init__(self, cell_size: int = 50):
        self.cell_size = cell_size
        self.images: Dict[str, pygame.Surface] = {}
        self.load_all()

    def _load_image(self, rel_path: str, size: Tuple[int, int]) -> pygame.Surface:
        full_path = os.path.join(ASSET_ROOT, rel_path)
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path).convert_alpha()
                return pygame.transform.scale(img, size)
            except Exception as e:
                print(f"[AssetLoader] 載入 {rel_path} 失敗: {e}")
        
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (200, 200, 200, 150), (4, 4, size[0] - 8, size[1] - 8), border_radius=4)
        return surf

    def _slice_spritesheet(self, rel_path: str, cols: int, rows: int,
                            frame_size: Tuple[int, int], chroma_key=None):
        """
        通用精靈圖切割函式：把一張 cols x rows 網格排列的精靈圖，切成
        rows 個方向、每個方向 cols 幀的畫格，並把每一幀縮放到 frame_size。

        回傳 List[List[Surface]]，外層 index 是第幾列 (row / 方向)，
        內層 index 是該方向第幾幀動畫。找不到檔案或載入失敗時回傳 None，
        呼叫端應該要有「退回原本靜態圖」的備援邏輯，不要讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"[AssetLoader] 找不到精靈圖 {rel_path}，動畫將退回靜態圖片。")
            return None

        try:
            if chroma_key is not None:
                # 明確指定了去背色：用 .convert() (無 alpha 通道) 載入，
                # 指定 colorkey 之後再 convert_alpha() 把去背色烤成真正的
                # per-pixel alpha，這樣切出來的每一幀才能正常半透明混合。
                sheet = pygame.image.load(full_path).convert()
                sheet.set_colorkey(chroma_key, pygame.RLEACCEL)
                sheet = sheet.convert_alpha()
            else:
                # 沒指定去背色：假設來源圖本身已經有真正的 PNG alpha
                # 透明背景（pig_chroma.png 實測就是這種），直接保留原本
                # alpha，邊緣比 Chroma Key 去背更平滑、不會有鋸齒殘影。
                sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 載入精靈圖 {rel_path} 失敗: {e}")
            return None

        sheet_w, sheet_h = sheet.get_size()
        frame_w = sheet_w // cols
        frame_h = sheet_h // rows
        if frame_w <= 0 or frame_h <= 0:
            print(f"[AssetLoader] {rel_path} 尺寸 {sheet.get_size()} 切不出 {cols}x{rows} 的畫格，動畫將退回靜態圖片。")
            return None

        frames_by_row = []
        for row in range(rows):
            row_frames = []
            for col in range(cols):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame = sheet.subsurface(rect).copy()
                frame = pygame.transform.scale(frame, frame_size)
                row_frames.append(frame)
            frames_by_row.append(row_frames)
        return frames_by_row

    def load_all(self):
        sz = (self.cell_size, self.cell_size)

        # 0. 地磚 Tiles
        self.images["grass_tile"] = self._load_image("tiles/grass_tile.png", sz)
        self.images["soil_tile"] = self._load_image("tiles/soil_tile.png", sz)
        
        # 1. 作物 (10 種)
        crops = [
            ("radish", ["seed", "sprout", "growing", "mature"]),
            ("tomato", ["seed", "sprout", "growing", "mature"]),
            ("corn", ["seed", "sprout", "growing", "mature"]),
            ("eggplant", ["seed", "sprout", "growing", "mature"]),
            ("strawberry", ["seed", "sprout", "growing", "mature"]),
            ("pumpkin", ["seed", "sprout", "growing", "mature"]),
            ("watermelon", ["seed", "sprout", "growing", "mature"]),
            ("sunflower", ["seed", "sprout", "growing", "mature"]),
            ("grape", ["seed", "sprout", "growing", "mature"]),
            ("starlight", ["seed", "sprout", "growing", "mature"]),
        ]
        for cname, stages in crops:
            for st in stages:
                key = f"{cname}_{st}"
                self.images[key] = self._load_image(f"crops/{cname}_{st}.png", sz)

        # 2. 景觀 (13 種)
        decos = [
            ("stone_path", "decorations/stone_path.png"),
            ("flower_bed", "decorations/flower_bed.png"),
            ("garden_bench", "decorations/garden_bench.png"),
            ("pine_tree", "decorations/pine_tree.png"),
            ("apple_tree", "decorations/apple_tree.png"),
            ("sakura_tree", "decorations/sakura_tree.png"),
            ("soul_lantern", "decorations/soul_lantern.png"),
            ("bird_bath", "decorations/bird_bath.png"),
            ("ancient_statue", "decorations/ancient_statue.png"),
            ("fountain", "decorations/fountain.png"),
            ("pet_house", "decorations/pet_house.png"),
            ("sundial_tower", "decorations/sundial_tower.png"),
            ("windmill", "decorations/windmill.png"),
        ]
        for key, path in decos:
            self.images[key] = self._load_image(path, sz)

        # 3. 防禦設施與工具
        defs = [
            ("wooden_fence", "defenses/wooden_fence.png"),
            ("bear_trap", "defenses/bear_trap.png"),
            ("scarecrow", "defenses/scarecrow.png"),
            ("beehive", "defenses/beehive.png"),
            ("watering_can", "defenses/watering_can.png"),
            ("shovel", "defenses/shovel.png"),
            ("flashlight", "defenses/flashlight.png"),
        ]
        for key, path in defs:
            self.images[key] = self._load_image(path, sz)


        # 4. 生物角色
        chars = [
            ("guard_dog", "characters/guard_dog.png"),
            ("farm_cat", "characters/farm_cat.png"),
            ("enemy_thief", "characters/enemy_thief.png"),
            ("enemy_boar", "characters/enemy_boar.png"),
            ("enemy_bat", "characters/enemy_bat.png"),
            ("boss_boar", "characters/boss_boar.png"),
        ]
        for key, path in chars:
            self.images[key] = self._load_image(path, sz if key != "boss_boar" else (int(sz[0]*1.4), int(sz[1]*1.4)))

        # 5. 血月首領移動動畫 (pig_chroma.png 精靈圖，4 方向 x N 幀)
        # boss_frames 跟 boss_boar 靜態圖用同一個放大倍率 (1.4x)，
        # 這樣渲染層切換兩者時大小不會突然跳動。
        boss_size = (int(sz[0] * 1.4), int(sz[1] * 1.4))
        boss_rows = self._slice_spritesheet(
            "characters/pig_chroma.png", BOSS_FRAME_COLS, BOSS_FRAME_ROWS, boss_size, BOSS_CHROMA_KEY
        )
        if boss_rows:
            if BOSS_ROW_DIRECTIONS:
                self.boss_frames: Dict[str, list] = {
                    direction: boss_rows[i]
                    for i, direction in enumerate(BOSS_ROW_DIRECTIONS)
                    if i < len(boss_rows)
                }
            else:
                # BOSS_ROW_DIRECTIONS 是 None：素材目前沒有明確的方向差異，
                # 把所有列攤平成同一組幀，四個方向都共用，先讓首領動起來。
                all_frames = [frame for row in boss_rows for frame in row]
                self.boss_frames: Dict[str, list] = {
                    d: all_frames for d in ("down", "left", "right", "up")
                }
        else:
            # pig_chroma.png 還沒放進 assets/characters/，或切圖失敗時，
            # boss_frames 就是空字典——渲染層要檢查這個並退回 boss_boar 靜態圖。
            self.boss_frames: Dict[str, list] = {}

    def get(self, key: str) -> pygame.Surface:
        return self.images.get(key)
