"""
夜巡農場 (Nightwatch Farm) - 素材圖像載入器 (AssetLoader)
自動載入 assets/ 目錄下的所有透明 PNG 圖片（10種作物、13種景觀、防禦與生物）。
"""

import os
import pygame
from typing import Dict, Tuple

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")

# ---- 血月首領 (pig_chroma.png) 精靈圖設定 --------------------------------
# 假設是標準「N 個方向 (列) x 每個方向 N 幀動畫 (欄)」排版。
# 如果實際的 pig_chroma.png 切法不是 3 欄 x 4 列，改這兩個數字就好，
# 下面的切圖邏輯完全不用動。
BOSS_FRAME_COLS = 3   # 每個方向有幾幀動畫（橫向、欄數）
BOSS_FRAME_ROWS = 4   # 有幾個方向（縱向、列數）
# 由上而下，每一「列」對應哪個方向——這是最常見的 RPG 素材排版慣例
# (row0=下, row1=左, row2=右, row3=上)。如果你的圖實際順序不同
# (例如 上/左/下/右)，改這個 list 的順序即可。
BOSS_ROW_DIRECTIONS = ["down", "left", "right", "up"]
# pig_chroma.png 這個檔名暗示背景是用純色去背（Chroma Key），不是真的
# alpha 透明。設成 None 時，程式會自動抓「圖片左上角那個像素」的顏色
# 當作要去除的背景色；如果自動抓色抓錯（例如左上角剛好被角色圖佔到），
# 把這裡改成實際的背景色 RGB，例如 (255, 0, 255) 螢光洋紅或 (0, 255, 0) 綠幕。
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
            # 用 .convert() 而不是 .convert_alpha()：Chroma Key 去背要先在
            # 「無 alpha 通道」的圖上用 set_colorkey 指定去背色，之後才把
            # 去背色轉成真正的 per-pixel alpha (見下面每一幀的處理)。
            sheet = pygame.image.load(full_path).convert()
        except Exception as e:
            print(f"[AssetLoader] 載入精靈圖 {rel_path} 失敗: {e}")
            return None

        key_color = chroma_key if chroma_key is not None else sheet.get_at((0, 0))

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
                # 把去背色變成真正的透明 alpha，這樣之後才能用平滑縮放
                # (smoothscale) 而不會在邊緣留下去背色的鋸齒殘影。
                frame.set_colorkey(key_color, pygame.RLEACCEL)
                frame = frame.convert_alpha()
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
            self.boss_frames: Dict[str, list] = {
                direction: boss_rows[i]
                for i, direction in enumerate(BOSS_ROW_DIRECTIONS)
                if i < len(boss_rows)
            }
        else:
            # pig_chroma.png 還沒放進 assets/characters/，或切圖失敗時，
            # boss_frames 就是空字典——渲染層要檢查這個並退回 boss_boar 靜態圖。
            self.boss_frames: Dict[str, list] = {}

    def get(self, key: str) -> pygame.Surface:
        return self.images.get(key)
