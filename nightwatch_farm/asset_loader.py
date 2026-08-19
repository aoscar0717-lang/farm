"""
夜巡農場 (Nightwatch Farm) - 素材圖像載入器 (AssetLoader)
自動載入 assets/ 目錄下的所有透明 PNG 圖片（10種作物、13種景觀、防禦與生物）。
"""

import os
import pygame
from typing import Dict, Tuple

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")


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
                return pygame.transform.smoothscale(img, size)
            except Exception as e:
                print(f"[AssetLoader] 載入 {rel_path} 失敗: {e}")
        
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (200, 200, 200, 150), (4, 4, size[0] - 8, size[1] - 8), border_radius=4)
        return surf

    def load_all(self):
        sz = (self.cell_size, self.cell_size)
        
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

        # 3. 防禦設施
        defs = [
            ("wooden_fence", "defenses/wooden_fence.png"),
            ("bear_trap", "defenses/bear_trap.png"),
            ("scarecrow", "defenses/scarecrow.png"),
            ("beehive", "defenses/beehive.png"),
            ("watering_can", "defenses/watering_can.png"),
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

    def get(self, key: str) -> pygame.Surface:
        return self.images.get(key)
