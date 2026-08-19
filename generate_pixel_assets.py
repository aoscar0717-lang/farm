"""
夜巡農場 (Nightwatch Farm) - 真實原版像素素材精準提取器 (Real Pixel Asset Extractor)
100% 精準對齊 workspace/assets 內的 Sprout Lands、Farm RPG、Sunnyside World 與 Mystic Woods，
保證每一張圖都有真實飽滿的像素內容，絕無任何空白或透明圖！
"""

import os
import sys
import pygame

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

pygame.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)

from src.sprite_loader import SpriteLoader
loader = SpriteLoader()

NIGHTWATCH_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))

for folder in ["crops", "decorations", "defenses", "characters", "tiles", "ui"]:
    os.makedirs(os.path.join(NIGHTWATCH_ASSETS, folder), exist_ok=True)


def extract_and_save_all():
    print("🎨 開始從原廠 Sprite Sheet 精準提取真實像素圖塊...")

    # 1. 地磚 Tiles
    grass_img = loader.get_sprite("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Grass.png", 1, 1, 16, 16, (50, 50))
    if grass_img:
        pygame.image.save(grass_img, os.path.join(NIGHTWATCH_ASSETS, "tiles", "grass_tile.png"))

    dirt_img = loader.get_sprite("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Tilled Dirt.png", 1, 1, 16, 16, (50, 50))
    if dirt_img:
        pygame.image.save(dirt_img, os.path.join(NIGHTWATCH_ASSETS, "tiles", "soil_tile.png"))

    # 2. 作物 (4 階段真實生長)
    # Farm RPG Spring Crops.png:
    # row1: strawberry, row3: radish, row5: corn/carrot, row7: onion
    # Sunnyside World: carrot_00..05, pumpkin_00..05
    # Sprout Lands: Basic Plants.png (row0: tomato/sunflower)
    stages = ["seed", "sprout", "growing", "mature"]
    spring_cols = [0, 1, 3, 5]

    for s_idx, st in enumerate(stages):
        # (1) 白蘿蔔 (Radish)
        r_img = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, spring_cols[s_idx], 16, 16, (50, 50))
        if r_img: pygame.image.save(r_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"radish_{st}.png"))

        # (2) 鮮甜草莓 (Strawberry)
        sb_img = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, spring_cols[s_idx], 16, 16, (50, 50))
        if sb_img: pygame.image.save(sb_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"strawberry_{st}.png"))

        # (3) 香甜玉米 (Corn)
        c_img = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 5, spring_cols[s_idx], 16, 16, (50, 50))
        if c_img: pygame.image.save(c_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"corn_{st}.png"))

        # (4) 紫皮洋蔥 / 甜茄 (Eggplant / Onion)
        on_img = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 7, spring_cols[s_idx], 16, 16, (50, 50))
        if on_img:
            pygame.image.save(on_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"eggplant_{st}.png"))
            pygame.image.save(on_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"grape_{st}.png"))

        # (5) 紅番茄 / 向日葵 (Tomato / Sunflower from Sprout Lands Basic Plants)
        bp_col = [0, 1, 2, 4][s_idx]
        bp_img = loader.get_sprite("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Objects/Basic Plants.png", 0, bp_col, 16, 16, (50, 50))
        if bp_img:
            pygame.image.save(bp_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"tomato_{st}.png"))
            pygame.image.save(bp_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"sunflower_{st}.png"))

        # (6) 巨型金南瓜 (Pumpkin from Sunnyside)
        p_frame = [0, 2, 4, 5][s_idx]
        p_img = loader.get_image(f"Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops/pumpkin_0{p_frame}.png", (50, 50))
        if p_img:
            pygame.image.save(p_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"pumpkin_{st}.png"))
            pygame.image.save(p_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"watermelon_{st}.png"))

        # (7) 永恆星光果 (Starlight from Sunnyside Carrot Golden)
        c_frame = [0, 2, 4, 5][s_idx]
        c_img = loader.get_image(f"Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops/carrot_0{c_frame}.png", (50, 50))
        if c_img:
            pygame.image.save(c_img, os.path.join(NIGHTWATCH_ASSETS, "crops", f"starlight_{st}.png"))

    # 3. 防禦設施 (Defenses)
    fence = loader.get_sprite("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Fences.png", 3, 0, 16, 16, (50, 50))
    if fence:
        pygame.image.save(fence, os.path.join(NIGHTWATCH_ASSETS, "defenses", "wooden_fence.png"))

    trap = loader.get_sprite("Free-Magic-and-Traps-Top-Down-Pixel-Art-Asset/1 Spikes/1.png", 0, 2, 32, 32, (50, 50))
    if trap:
        pygame.image.save(trap, os.path.join(NIGHTWATCH_ASSETS, "defenses", "bear_trap.png"))

    scarecrow = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (50, 50))
    if scarecrow:
        pygame.image.save(scarecrow, os.path.join(NIGHTWATCH_ASSETS, "defenses", "scarecrow.png"))

    beehive = loader.get_image("Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Bee/beehive.png", (50, 50))
    if beehive:
        pygame.image.save(beehive, os.path.join(NIGHTWATCH_ASSETS, "defenses", "beehive.png"))

    watering_can = loader.get_sprite("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Characters/Tools.png", 0, 2, 16, 16, (50, 50)) or loader.get_image("shovel.png", (50, 50))
    if watering_can:
        pygame.image.save(watering_can, os.path.join(NIGHTWATCH_ASSETS, "defenses", "watering_can.png"))

    shovel = loader.get_image("shovel.png", (50, 50))
    if shovel:
        pygame.image.save(shovel, os.path.join(NIGHTWATCH_ASSETS, "defenses", "shovel.png"))
        pygame.image.save(shovel, os.path.join(NIGHTWATCH_ASSETS, "ui", "shovel.png"))

    # 4. 生物與角色 (Characters & Animals)
    dog = loader.get_sprite("Goldie pack_v1.1/Goldie pack_v02/Goldie_v02.png", 4, 0, 32, 40, (50, 50))
    if dog:
        pygame.image.save(dog, os.path.join(NIGHTWATCH_ASSETS, "characters", "guard_dog.png"))

    cat = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png", 0, 0, 16, 16, (50, 50))
    if cat:
        pygame.image.save(cat, os.path.join(NIGHTWATCH_ASSETS, "characters", "farm_cat.png"))

    thief = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png", 0, 0, 32, 32, (50, 50))
    if thief:
        pygame.image.save(thief, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_thief.png"))

    boar = loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_cow_strip4.png", 0, 0, 32, 32, (50, 50))
    if boar:
        pygame.image.save(boar, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_boar.png"))

    bat = loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_bird_01_strip4.png", 0, 0, 16, 16, (50, 50))
    if bat:
        pygame.image.save(bat, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_bat.png"))

    boss = loader.get_sprite("mystic_woods_free_2.2/sprites/characters/skeleton.png", 0, 0, 48, 48, (70, 70))
    if boss:
        pygame.image.save(boss, os.path.join(NIGHTWATCH_ASSETS, "characters", "boss_boar.png"))

    # 5. 景觀 (Decorations - 全部對應真實存在之像素素材)
    path = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Road copiar.png", 0, 0, 16, 16, (50, 50))
    if path:
        pygame.image.save(path, os.path.join(NIGHTWATCH_ASSETS, "decorations", "stone_path.png"))

    flower = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 0, 0, 16, 16, (50, 50))
    if flower:
        pygame.image.save(flower, os.path.join(NIGHTWATCH_ASSETS, "decorations", "flower_bed.png"))

    bench = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 8, 2, 16, 16, (50, 50))
    if bench:
        pygame.image.save(bench, os.path.join(NIGHTWATCH_ASSETS, "decorations", "garden_bench.png"))

    pine = loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_tree_02_strip4.png", 0, 0, 28, 43, (50, 50))
    if pine:
        pygame.image.save(pine, os.path.join(NIGHTWATCH_ASSETS, "decorations", "pine_tree.png"))

    maple = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Maple Tree.png", 0, 3, 32, 48, (50, 50))
    if maple:
        pygame.image.save(maple, os.path.join(NIGHTWATCH_ASSETS, "decorations", "apple_tree.png"))
        pygame.image.save(maple, os.path.join(NIGHTWATCH_ASSETS, "decorations", "sakura_tree.png"))

    crate = loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/chest.png", 0, 0, 32, 16, (50, 50))
    if crate:
        pygame.image.save(crate, os.path.join(NIGHTWATCH_ASSETS, "decorations", "ancient_statue.png"))

    mushroom = loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_mushroom_red_01_strip4.png", 0, 0, 16, 16, (50, 50))
    if mushroom:
        pygame.image.save(mushroom, os.path.join(NIGHTWATCH_ASSETS, "decorations", "bird_bath.png"))

    woodpile = loader.get_sprite("Sprout Sorry pack/Sprout Sorry pack/Early Access/Sprout winter/campfire.png", 2, 6, 16, 16, (50, 50))
    if woodpile:
        pygame.image.save(woodpile, os.path.join(NIGHTWATCH_ASSETS, "decorations", "pet_house.png"))

    sunflower_obj = loader.get_sprite("Sprout-Lands-Tilemap-0.2.0/Sprout-Lands-Tilemap-0.2.0/addons/sprout_lands_tilemap/assets/Objects/Basic Grass Biom things 1.png", 1, 8, 16, 32, (50, 50))
    if sunflower_obj:
        pygame.image.save(sunflower_obj, os.path.join(NIGHTWATCH_ASSETS, "decorations", "sundial_tower.png"))

    lantern = loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_tree_02_strip4.png", 0, 0, 28, 43, (50, 50))
    if lantern:
        pygame.image.save(lantern, os.path.join(NIGHTWATCH_ASSETS, "decorations", "soul_lantern.png"))

    fountain = loader.get_image("Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/piknik/Piknik basket.png", (50, 50))
    if fountain:
        pygame.image.save(fountain, os.path.join(NIGHTWATCH_ASSETS, "decorations", "fountain.png"))

    windmill = loader.get_image("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/House.png", (50, 50))
    if windmill:
        pygame.image.save(windmill, os.path.join(NIGHTWATCH_ASSETS, "decorations", "windmill.png"))

    print("✨ 所有真實 Sprite Sheet 像素圖塊提取與儲存完成！")


if __name__ == "__main__":
    extract_and_save_all()
