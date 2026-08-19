"""
夜巡農場 (Nightwatch Farm) - 素材圖像載入器 (AssetLoader)
自動載入 assets/ 目錄下的所有透明 PNG 圖片（10種作物、13種景觀、防禦與生物）。
"""

import os
import pygame
from typing import Dict, Tuple

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")

# ---- 血月首領 / 野豬王共用的 pig_chroma.png 精靈圖設定 --------------------
# 確認過的實際規格：1024x1024、5 欄 x 5 列 (SPRITE_COLS x SPRITE_ROWS)
# 的網格，每格 204x204，背景全黑 (0,0,0)。
SPRITE_COLS = 5
SPRITE_ROWS = 5
# 步行循環只取每個方向裡的 4 格，組成 [站立, 踏步1, 站立, 踏步2]，
# 站立幀出現兩次是為了讓「踏一步→回到站立→踏另一步→回到站立」的節奏
# 更自然，避免兩個踏步幀直接相接看起來像在滑步。
WALK_CYCLE_INDICES = [0, 2, 0, 3]
# 每個方向對應精靈圖的第幾「列」(row)：down=Row0、right=Row1、up=Row2。
# left 不佔額外的列，直接把 right 那組幀左右翻轉 (pygame.transform.flip)
# 取得，省素材也保證左右動作完全對稱。
BOSS_DIRECTION_ROWS = {"down": 0, "right": 1, "up": 2}
# 背景是純黑色去背 (Chroma Key)，不是 alpha 透明。
BOSS_CHROMA_KEY = (0, 0, 0)


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

    def _load_pig_chroma_frames(self):
        """
        切出 pig_chroma.png 的 4 方向步行循環 (每方向 4 幀)，回傳
        Dict[str, List[Surface]] (key 是 'down'/'right'/'up'/'left')，
        畫格維持精靈圖原始尺寸 (204x204)，縮放留給呼叫端依用途處理
        （血月首領跟野豬王要縮成不同大小，見 load_all()）。

        找不到檔案 / 切不出畫格時回傳 {}，呼叫端要自己 fallback 回
        原本的靜態圖片，不要讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, "characters/pig_chroma.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 characters/pig_chroma.png，血月首領/野豬王動畫將退回靜態圖片。")
            return {}

        try:
            # 背景是純黑色去背，不是 alpha 透明：用 .convert() (無 alpha
            # 通道) 載入，指定 colorkey 之後再 convert_alpha() 把去背色
            # 烤成真正的 per-pixel alpha。
            sheet = pygame.image.load(full_path).convert()
        except Exception as e:
            print(f"[AssetLoader] 載入 pig_chroma.png 失敗: {e}")
            return {}

        sheet.set_colorkey(BOSS_CHROMA_KEY, pygame.RLEACCEL)

        sheet_w, sheet_h = sheet.get_size()
        frame_width = sheet_w // SPRITE_COLS
        frame_height = sheet_h // SPRITE_ROWS
        if frame_width <= 0 or frame_height <= 0:
            print(f"[AssetLoader] pig_chroma.png 尺寸 {sheet.get_size()} 切不出 {SPRITE_COLS}x{SPRITE_ROWS} 的畫格。")
            return {}

        def _cut(row: int, col: int) -> pygame.Surface:
            rect = pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
            frame = sheet.subsurface(rect).copy()
            frame.set_colorkey(BOSS_CHROMA_KEY, pygame.RLEACCEL)
            return frame.convert_alpha()

        frames = {}
        for direction, row in BOSS_DIRECTION_ROWS.items():
            frames[direction] = [_cut(row, col) for col in WALK_CYCLE_INDICES]

        # left 不額外佔一列，直接把 right 的幀水平翻轉。
        frames["left"] = [pygame.transform.flip(f, True, False) for f in frames["right"]]

        return frames

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

        # 5. 血月首領 / 野豬王的移動動畫 (共用同一張 pig_chroma.png，
        # 差別只有縮放後的大小 -- 野豬王用一般格子大小，血月首領放大 1.4x)
        pig_frames_native = self._load_pig_chroma_frames()
        boss_size = (int(sz[0] * 1.4), int(sz[1] * 1.4))
        if pig_frames_native:
            self.boss_frames: Dict[str, list] = {
                d: [pygame.transform.scale(f, boss_size) for f in frames]
                for d, frames in pig_frames_native.items()
            }
            self.enemy_boar_frames: Dict[str, list] = {
                d: [pygame.transform.scale(f, sz) for f in frames]
                for d, frames in pig_frames_native.items()
            }
        else:
            # pig_chroma.png 還沒放進 assets/characters/，或切圖失敗時，
            # 兩個字典都是空的——渲染層要檢查並退回 boss_boar / enemy_boar
            # 靜態圖，不會讓遊戲壞掉。
            self.boss_frames: Dict[str, list] = {}
            self.enemy_boar_frames: Dict[str, list] = {}

    def get(self, key: str) -> pygame.Surface:
        return self.images.get(key)
