"""
夜巡農場 (Nightwatch Farm) - 像素素材精靈提取與轉換器 (Pixel Asset Generator)
從 workspace 的 assets/ 資料夾中提取 Sprout Lands、Sunnyside World、Farm RPG、Mystic Woods 等像素精靈，
轉換為 nightwatch_farm 專屬的點陣像素圖案。
"""

import os
import sys
import pygame

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

pygame.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)



WORKSPACE_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
NIGHTWATCH_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))

for folder in ["crops", "decorations", "defenses", "characters", "tiles", "ui"]:
    os.makedirs(os.path.join(NIGHTWATCH_ASSETS, folder), exist_ok=True)


def load_raw(rel_path: str) -> pygame.Surface:
    full = os.path.join(WORKSPACE_ASSETS, rel_path)
    if os.path.exists(full):
        return pygame.image.load(full).convert_alpha()
    return None


def get_sub(surf: pygame.Surface, x: int, y: int, w: int, h: int, target_size=(50, 50)) -> pygame.Surface:
    if surf is None:
        s = pygame.Surface(target_size, pygame.SRCALPHA)
        return s
    sw, sh = surf.get_size()
    if x + w > sw or y + h > sh:
        w = min(w, sw - x)
        h = min(h, sh - y)
    sub = surf.subsurface(pygame.Rect(x, y, w, h))
    return pygame.transform.scale(sub, target_size)


def generate_all_pixel_assets():
    print("🎨 開始提取與建立《夜巡農場》經典像素風素材...")

    # 1. 耕地與草地 Tiles
    grass_sheet = load_raw("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Grass.png")
    dirt_sheet = load_raw("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Tilled Dirt.png")
    
    if grass_sheet:
        grass_tile = get_sub(grass_sheet, 16, 16, 16, 16, (50, 50))
        pygame.image.save(grass_tile, os.path.join(NIGHTWATCH_ASSETS, "tiles", "grass_tile.png"))
    if dirt_sheet:
        dirt_tile = get_sub(dirt_sheet, 16, 16, 16, 16, (50, 50))
        pygame.image.save(dirt_tile, os.path.join(NIGHTWATCH_ASSETS, "tiles", "soil_tile.png"))

    # 2. 作物 (10 種 x 4 階段)
    spring_crops = load_raw("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png")
    basic_plants = load_raw("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Objects/Basic Plants.png")

    crop_rows = {
        "strawberry": (spring_crops, 1, 16),
        "radish": (spring_crops, 3, 16),
        "corn": (spring_crops, 5, 16),
        "eggplant": (spring_crops, 2, 16),
        "pumpkin": (spring_crops, 4, 16),
        "tomato": (spring_crops, 0, 16),
        "watermelon": (spring_crops, 6, 16),
        "sunflower": (basic_plants, 0, 16) if basic_plants else (spring_crops, 7, 16),
        "grape": (spring_crops, 6, 16),
        "starlight": (spring_crops, 4, 16),
    }

    stages = ["seed", "sprout", "growing", "mature"]
    stage_cols = [0, 1, 2, 3]

    for cname, (sheet, row, cell_sz) in crop_rows.items():
        for s_idx, sname in enumerate(stages):
            col = stage_cols[s_idx]
            if sheet:
                sprite = get_sub(sheet, col * cell_sz, row * cell_sz, cell_sz, cell_sz, (50, 50))
                pygame.image.save(sprite, os.path.join(NIGHTWATCH_ASSETS, "crops", f"{cname}_{sname}.png"))

    # 3. 防禦設施 (Defenses)
    fence_sheet = load_raw("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Fences.png")
    if fence_sheet:
        fence_img = get_sub(fence_sheet, 0, 48, 16, 16, (50, 50))
        pygame.image.save(fence_img, os.path.join(NIGHTWATCH_ASSETS, "defenses", "wooden_fence.png"))

    spikes_img = load_raw("Free-Magic-and-Traps-Top-Down-Pixel-Art-Asset/1 Spikes/1.png")
    if spikes_img:
        trap = pygame.transform.scale(spikes_img, (50, 50))
        pygame.image.save(trap, os.path.join(NIGHTWATCH_ASSETS, "defenses", "bear_trap.png"))

    if spring_crops:
        scarecrow = get_sub(spring_crops, 13 * 16, 1 * 16, 16, 16, (50, 50))
        pygame.image.save(scarecrow, os.path.join(NIGHTWATCH_ASSETS, "defenses", "scarecrow.png"))

    # 蜂巢、水壺、鏟子
    shovel_img = load_raw("shovel.png") or load_raw("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/UI/shovel.png")
    if shovel_img:
        pygame.image.save(pygame.transform.scale(shovel_img, (50, 50)), os.path.join(NIGHTWATCH_ASSETS, "defenses", "shovel.png"))
        pygame.image.save(pygame.transform.scale(shovel_img, (50, 50)), os.path.join(NIGHTWATCH_ASSETS, "ui", "shovel.png"))

    # 4. 生物與怪物 (Characters)
    dog_sheet = load_raw("Goldie pack_v1.1/Goldie pack_v02/Goldie_v02.png")
    if dog_sheet:
        dog_img = get_sub(dog_sheet, 0, 128, 32, 32, (50, 50))
        pygame.image.save(dog_img, os.path.join(NIGHTWATCH_ASSETS, "characters", "guard_dog.png"))

    cat_sheet = load_raw("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png")
    if cat_sheet:
        cat_img = get_sub(cat_sheet, 0, 0, 16, 16, (50, 50))
        pygame.image.save(cat_img, os.path.join(NIGHTWATCH_ASSETS, "characters", "farm_cat.png"))

    goblin_walk = load_raw("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Characters/Goblin/PNG/spr_walk_strip8.png") or load_raw("Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png")
    if goblin_walk:
        thief_img = get_sub(goblin_walk, 0, 0, 32, 32 if goblin_walk.get_width() > 100 else 16, (50, 50))
        pygame.image.save(thief_img, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_thief.png"))

    cow_sheet = load_raw("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_cow_strip4.png") or load_raw("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Male Cow Brown.png")
    if cow_sheet:
        boar_img = get_sub(cow_sheet, 0, 0, 32, 32, (50, 50))
        pygame.image.save(boar_img, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_boar.png"))

    bird_sheet = load_raw("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_bird_01_strip4.png")
    if bird_sheet:
        bat_img = get_sub(bird_sheet, 0, 0, 16, 16, (50, 50))
        pygame.image.save(bat_img, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_bat.png"))

    skeleton = load_raw("mystic_woods_free_2.2/sprites/characters/skeleton.png")
    if skeleton:
        boss_img = get_sub(skeleton, 0, 0, 48, 48, (70, 70))
        pygame.image.save(boss_img, os.path.join(NIGHTWATCH_ASSETS, "characters", "boss_boar.png"))

    # 5. 景觀 (Decorations)
    road_sheet = load_raw("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Road copiar.png")
    if road_sheet:
        path_img = get_sub(road_sheet, 0, 0, 16, 16, (50, 50))
        pygame.image.save(path_img, os.path.join(NIGHTWATCH_ASSETS, "decorations", "stone_path.png"))

    tree_sheet = load_raw("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Maple Tree.png")
    if tree_sheet:
        tree_img = get_sub(tree_sheet, 0, 0, 32, 48, (50, 50))
        pygame.image.save(tree_img, os.path.join(NIGHTWATCH_ASSETS, "decorations", "pine_tree.png"))
        pygame.image.save(tree_img, os.path.join(NIGHTWATCH_ASSETS, "decorations", "apple_tree.png"))
        pygame.image.save(tree_img, os.path.join(NIGHTWATCH_ASSETS, "decorations", "sakura_tree.png"))

    print("✨ 所有像素素材提取完畢！")


if __name__ == "__main__":
    generate_all_pixel_assets()
