"""
夜巡農場 (Nightwatch Farm) - 高級精緻像素美術生成器 (High-End Pixel Art Generator)
為所有作物、景觀、防禦、動物與魔物繪製高精緻度、具備層次陰影、高光與邊框的頂級像素圖標。
"""

import os
import sys
import math
import pygame

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

pygame.init()
pygame.display.set_mode((1, 1), pygame.NOFRAME)

NIGHTWATCH_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "assets"))

for folder in ["crops", "decorations", "defenses", "characters", "tiles", "ui"]:
    os.makedirs(os.path.join(NIGHTWATCH_ASSETS, folder), exist_ok=True)


def create_canvas(w=50, h=50) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)


def add_drop_shadow(surf: pygame.Surface, cx: int, cy: int, rw: int, rh: int):
    shadow = pygame.Surface((rw * 2, rh * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (15, 20, 30, 85), (0, 0, rw * 2, rh * 2))
    surf.blit(shadow, (cx - rw, cy - rh))


# =========================================================================
# 1. 地磚 Tiles
# =========================================================================
def generate_tiles():
    # 像素草地 (富含草叢細節與微小野花)
    grass = create_canvas(50, 50)
    grass.fill((92, 168, 65))
    # 隨機草絲斑紋
    patterns = [
        ((80, 150, 55), [(8, 8), (22, 14), (36, 10), (12, 32), (28, 40), (42, 28)]),
        ((110, 185, 78), [(10, 20), (25, 6), (40, 22), (18, 44), (34, 32), (4, 42)]),
    ]
    for col, pts in patterns:
        for x, y in pts:
            pygame.draw.rect(grass, col, (x, y, 4, 3), border_radius=1)
            pygame.draw.rect(grass, col, (x + 1, y - 2, 2, 2), border_radius=1)
    # 小黃花與小白花點綴
    for fx, fy, fcol in [(15, 18, (255, 235, 120)), (38, 38, (255, 255, 255)), (32, 12, (255, 180, 190))]:
        pygame.draw.circle(grass, fcol, (fx, fy), 2)
        pygame.draw.circle(grass, (255, 160, 0), (fx, fy), 1)
    pygame.image.save(grass, os.path.join(NIGHTWATCH_ASSETS, "tiles", "grass_tile.png"))

    # 像素耕地 (深黑沃土，具備耕犁溝槽與濕潤泥土光澤)
    soil = create_canvas(50, 50)
    soil.fill((93, 64, 55))
    # 橫向耕地陰影溝槽
    for row_y in [10, 22, 34, 46]:
        pygame.draw.rect(soil, (62, 39, 35), (2, row_y, 46, 3), border_radius=1)
        pygame.draw.rect(soil, (121, 85, 72), (2, row_y - 2, 46, 2), border_radius=1)
    # 泥土微粒
    for dx, dy in [(12, 6), (28, 18), (40, 30), (16, 42), (32, 4)]:
        pygame.draw.rect(soil, (141, 110, 99), (dx, dy, 3, 2))
    pygame.image.save(soil, os.path.join(NIGHTWATCH_ASSETS, "tiles", "soil_tile.png"))


# =========================================================================
# 2. 農作物 (10 種 x 4 階段)
# =========================================================================
CROP_COLORS = {
    "radish": {"body": (245, 245, 250), "accent": (230, 81, 0), "leaf": (76, 175, 80)},
    "tomato": {"body": (239, 83, 80), "accent": (198, 40, 40), "leaf": (56, 142, 60)},
    "corn": {"body": (255, 214, 0), "accent": (245, 127, 23), "leaf": (102, 187, 106)},
    "eggplant": {"body": (123, 31, 162), "accent": (74, 20, 140), "leaf": (67, 160, 71)},
    "strawberry": {"body": (229, 57, 53), "accent": (255, 235, 59), "leaf": (46, 125, 50)},
    "pumpkin": {"body": (255, 152, 0), "accent": (230, 81, 0), "leaf": (46, 125, 50)},
    "watermelon": {"body": (46, 125, 50), "accent": (229, 57, 53), "leaf": (129, 199, 132)},
    "sunflower": {"body": (255, 235, 59), "accent": (109, 76, 65), "leaf": (56, 142, 60)},
    "grape": {"body": (106, 27, 154), "accent": (186, 104, 200), "leaf": (46, 125, 50)},
    "starlight": {"body": (0, 229, 255), "accent": (224, 64, 251), "leaf": (100, 255, 218)},
}

def generate_crops():
    stages = ["seed", "sprout", "growing", "mature"]
    for cname, col in CROP_COLORS.items():
        # 1. Seed (種子)
        s_surf = create_canvas(50, 50)
        add_drop_shadow(s_surf, 25, 36, 10, 4)
        # 泥土堆
        pygame.draw.ellipse(s_surf, (109, 76, 65), (15, 26, 20, 10))
        # 2顆種子粒
        pygame.draw.ellipse(s_surf, (215, 180, 120), (20, 24, 5, 7))
        pygame.draw.ellipse(s_surf, (190, 150, 90), (25, 25, 6, 7))
        pygame.image.save(s_surf, os.path.join(NIGHTWATCH_ASSETS, "crops", f"{cname}_seed.png"))

        # 2. Sprout (幼苗)
        sp_surf = create_canvas(50, 50)
        add_drop_shadow(sp_surf, 25, 38, 12, 4)
        pygame.draw.ellipse(sp_surf, (109, 76, 65), (14, 30, 22, 10))
        # 莖與嫩芽
        pygame.draw.rect(sp_surf, (102, 187, 106), (23, 20, 4, 12), border_radius=2)
        pygame.draw.ellipse(sp_surf, (129, 199, 132), (15, 16, 10, 6))
        pygame.draw.ellipse(sp_surf, (129, 199, 132), (25, 16, 10, 6))
        pygame.image.save(sp_surf, os.path.join(NIGHTWATCH_ASSETS, "crops", f"{cname}_sprout.png"))

        # 3. Growing (生長中)
        gr_surf = create_canvas(50, 50)
        add_drop_shadow(gr_surf, 25, 40, 14, 5)
        # 茂密枝葉
        pygame.draw.rect(gr_surf, col["leaf"], (22, 16, 6, 20), border_radius=2)
        pygame.draw.ellipse(gr_surf, col["leaf"], (12, 14, 14, 10))
        pygame.draw.ellipse(gr_surf, col["leaf"], (24, 14, 14, 10))
        pygame.draw.ellipse(gr_surf, (139, 195, 74), (16, 8, 18, 12))
        # 微小的半成果實
        pygame.draw.circle(gr_surf, col["body"], (25, 24), 6)
        pygame.image.save(gr_surf, os.path.join(NIGHTWATCH_ASSETS, "crops", f"{cname}_growing.png"))

        # 4. Mature (成熟金光)
        mat_surf = create_canvas(50, 50)
        add_drop_shadow(mat_surf, 25, 42, 16, 6)

        # 枝葉背景
        pygame.draw.ellipse(mat_surf, col["leaf"], (10, 10, 16, 12))
        pygame.draw.ellipse(mat_surf, col["leaf"], (24, 10, 16, 12))
        pygame.draw.ellipse(mat_surf, (100, 180, 60), (16, 4, 18, 12))

        # 主體大果實 (具備像素高光與層次)
        if cname in ("radish", "strawberry"):
            pygame.draw.polygon(mat_surf, col["body"], [(25, 42), (14, 20), (36, 20)])
            pygame.draw.circle(mat_surf, col["body"], (20, 22), 8)
            pygame.draw.circle(mat_surf, col["body"], (30, 22), 8)
            # 高光
            pygame.draw.circle(mat_surf, (255, 255, 255, 220), (21, 20), 3)
        elif cname in ("corn", "eggplant"):
            pygame.draw.ellipse(mat_surf, col["body"], (17, 12, 16, 28))
            pygame.draw.ellipse(mat_surf, col["accent"], (19, 14, 12, 24))
            pygame.draw.circle(mat_surf, (255, 255, 255, 180), (22, 18), 3)
        elif cname in ("pumpkin", "watermelon"):
            pygame.draw.ellipse(mat_surf, col["body"], (11, 14, 28, 26))
            pygame.draw.ellipse(mat_surf, col["accent"], (15, 16, 20, 22))
            pygame.draw.circle(mat_surf, (255, 255, 255, 160), (18, 20), 4)
            # 瓜蒂
            pygame.draw.rect(mat_surf, (76, 175, 80), (23, 10, 4, 6), border_radius=1)
        elif cname == "sunflower":
            # 花瓣
            for a in range(8):
                rad = a * (math.pi / 4)
                fx = int(25 + math.cos(rad) * 12)
                fy = int(24 + math.sin(rad) * 12)
                pygame.draw.circle(mat_surf, col["body"], (fx, fy), 5)
            pygame.draw.circle(mat_surf, col["accent"], (25, 24), 8)
            pygame.draw.circle(mat_surf, (62, 39, 35), (25, 24), 5)
        elif cname == "grape":
            # 葡萄串
            for gx, gy in [(22, 18), (28, 18), (19, 24), (25, 24), (31, 24), (22, 30), (28, 30), (25, 36)]:
                pygame.draw.circle(mat_surf, col["body"], (gx, gy), 5)
                pygame.draw.circle(mat_surf, (255, 255, 255, 160), (gx - 1, gy - 1), 2)
        else: # starlight / tomato
            pygame.draw.circle(mat_surf, col["body"], (25, 24), 13)
            pygame.draw.circle(mat_surf, col["accent"], (25, 24), 9)
            pygame.draw.circle(mat_surf, (255, 255, 255, 220), (20, 19), 4)

        # 成熟金星光效
        pygame.draw.circle(mat_surf, (255, 215, 0), (37, 10), 3)
        pygame.draw.circle(mat_surf, (255, 255, 255), (37, 10), 1)

        pygame.image.save(mat_surf, os.path.join(NIGHTWATCH_ASSETS, "crops", f"{cname}_mature.png"))


# =========================================================================
# 3. 防禦設施與工具
# =========================================================================
def generate_defenses():
    # 刺藤木柵 (Wooden Fence)
    f_surf = create_canvas(50, 50)
    add_drop_shadow(f_surf, 25, 42, 18, 5)
    # 兩根木樁
    for post_x in [10, 32]:
        pygame.draw.rect(f_surf, (141, 110, 99), (post_x, 14, 8, 28), border_radius=2)
        pygame.draw.polygon(f_surf, (109, 76, 65), [(post_x, 14), (post_x + 4, 8), (post_x + 8, 14)])
    # 兩根橫樑
    pygame.draw.rect(f_surf, (161, 136, 127), (6, 20, 38, 6), border_radius=2)
    pygame.draw.rect(f_surf, (161, 136, 127), (6, 32, 38, 6), border_radius=2)
    # 纏繞刺藤
    pygame.draw.circle(f_surf, (76, 175, 80), (14, 23), 3)
    pygame.draw.circle(f_surf, (76, 175, 80), (36, 35), 3)
    pygame.draw.circle(f_surf, (255, 87, 34), (25, 23), 2)
    pygame.image.save(f_surf, os.path.join(NIGHTWATCH_ASSETS, "defenses", "wooden_fence.png"))

    # 鋼鐵捕獸夾 (Bear Trap)
    trap_surf = create_canvas(50, 50)
    add_drop_shadow(trap_surf, 25, 34, 16, 6)
    pygame.draw.ellipse(trap_surf, (69, 90, 100), (10, 22, 30, 16))
    pygame.draw.ellipse(trap_surf, (38, 50, 56), (14, 25, 22, 10))
    # 鋼鐵尖齒
    for tx in [14, 19, 24, 29, 34]:
        pygame.draw.polygon(trap_surf, (236, 239, 241), [(tx, 25), (tx + 2, 18), (tx + 4, 25)])
    # 核心紅色壓力踏板
    pygame.draw.ellipse(trap_surf, (211, 47, 47), (21, 28, 8, 5))
    pygame.image.save(trap_surf, os.path.join(NIGHTWATCH_ASSETS, "defenses", "bear_trap.png"))

    # 稻草人 (Scarecrow)
    sc_surf = create_canvas(50, 50)
    add_drop_shadow(sc_surf, 25, 45, 14, 4)
    # 木十字架
    pygame.draw.rect(sc_surf, (141, 110, 99), (23, 14, 4, 30))
    pygame.draw.rect(sc_surf, (141, 110, 99), (10, 20, 30, 4))
    # 藍格子上衣與草身
    pygame.draw.rect(sc_surf, (33, 150, 243), (18, 22, 14, 14), border_radius=2)
    pygame.draw.circle(sc_surf, (255, 224, 178), (25, 15), 6)
    # 草帽
    pygame.draw.ellipse(sc_surf, (255, 183, 77), (14, 11, 22, 6))
    pygame.draw.polygon(sc_surf, (255, 152, 0), [(19, 11), (25, 3), (31, 11)])
    pygame.image.save(sc_surf, os.path.join(NIGHTWATCH_ASSETS, "defenses", "scarecrow.png"))

    # 蜜蜂守衛巢 (Beehive)
    bh_surf = create_canvas(50, 50)
    add_drop_shadow(bh_surf, 25, 42, 15, 5)
    # 木箱巢體
    pygame.draw.rect(bh_surf, (255, 193, 7), (14, 18, 22, 22), border_radius=3)
    pygame.draw.rect(bh_surf, (255, 160, 0), (12, 14, 26, 6), border_radius=2)
    pygame.draw.rect(bh_surf, (62, 39, 35), (20, 28, 10, 5), border_radius=2)
    # 飛舞蜜蜂
    pygame.draw.circle(bh_surf, (255, 235, 59), (34, 12), 3)
    pygame.draw.circle(bh_surf, (33, 33, 33), (35, 12), 1)
    pygame.draw.circle(bh_surf, (255, 255, 255, 200), (32, 9), 2)
    pygame.image.save(bh_surf, os.path.join(NIGHTWATCH_ASSETS, "defenses", "beehive.png"))

    # 黃金澆水壺 (Watering Can)
    wc_surf = create_canvas(50, 50)
    pygame.draw.ellipse(wc_surf, (255, 215, 0), (14, 18, 20, 18))
    pygame.draw.rect(wc_surf, (255, 179, 0), (16, 20, 16, 14))
    # 壺嘴與水滴
    pygame.draw.polygon(wc_surf, (255, 215, 0), [(30, 22), (42, 14), (40, 12), (28, 18)])
    pygame.draw.ellipse(wc_surf, (129, 212, 250), (41, 16, 4, 6))
    # 把手
    pygame.draw.arc(wc_surf, (255, 179, 0), (6, 16, 16, 20), 1.2, 4.8, 3)
    pygame.image.save(wc_surf, os.path.join(NIGHTWATCH_ASSETS, "defenses", "watering_can.png"))

    # 鐵鏟 / 拆除 (Shovel)
    sh_surf = create_canvas(50, 50)
    # 木柄斜放
    pygame.draw.line(sh_surf, (141, 110, 99), (14, 12), (32, 32), 4)
    # 握把
    pygame.draw.circle(sh_surf, (109, 76, 65), (13, 11), 5)
    pygame.draw.circle(sh_surf, (0, 0, 0, 0), (13, 11), 2)
    # 鋼鐵鏟頭
    pygame.draw.polygon(sh_surf, (176, 190, 197), [(32, 30), (42, 38), (38, 44), (28, 36)])
    pygame.draw.polygon(sh_surf, (207, 216, 220), [(34, 32), (40, 37), (37, 41), (31, 36)])
    pygame.image.save(sh_surf, os.path.join(NIGHTWATCH_ASSETS, "defenses", "shovel.png"))
    pygame.image.save(sh_surf, os.path.join(NIGHTWATCH_ASSETS, "ui", "shovel.png"))


# =========================================================================
# 4. 生物與魔物 (Characters)
# =========================================================================
def generate_characters():
    # 看門柴犬 (Guard Dog - Shiba Inu)
    dog = create_canvas(50, 50)
    add_drop_shadow(dog, 25, 42, 15, 5)
    # 身體與腿
    pygame.draw.ellipse(dog, (230, 138, 46), (14, 20, 22, 16))
    for lx in [16, 22, 28, 32]:
        pygame.draw.rect(dog, (230, 138, 46), (lx, 32, 4, 8), border_radius=1)
        pygame.draw.rect(dog, (255, 255, 255), (lx, 38, 4, 3), border_radius=1)
    # 圓滾滾狗頭
    pygame.draw.circle(dog, (230, 138, 46), (32, 18), 10)
    pygame.draw.circle(dog, (255, 255, 255), (34, 20), 5)
    # 三角耳朵
    pygame.draw.polygon(dog, (200, 110, 30), [(26, 12), (30, 5), (33, 12)])
    pygame.draw.polygon(dog, (200, 110, 30), [(33, 12), (37, 5), (40, 12)])
    # 眼睛與鼻子
    pygame.draw.circle(dog, (33, 33, 33), (35, 16), 2)
    pygame.draw.circle(dog, (33, 33, 33), (39, 19), 2)
    # 紅色項圈與金色鈴鐺
    pygame.draw.rect(dog, (229, 57, 53), (25, 23, 8, 3), border_radius=1)
    pygame.draw.circle(dog, (255, 215, 0), (29, 26), 2)
    # 捲尾巴
    pygame.draw.arc(dog, (230, 138, 46), (8, 14, 12, 12), 0.5, 3.5, 3)
    pygame.image.save(dog, os.path.join(NIGHTWATCH_ASSETS, "characters", "guard_dog.png"))

    # 招財小貓 (Farm Cat)
    cat = create_canvas(50, 50)
    add_drop_shadow(cat, 25, 42, 14, 4)
    pygame.draw.ellipse(cat, (255, 183, 77), (16, 22, 18, 14))
    pygame.draw.circle(cat, (255, 255, 255), (28, 18), 8)
    pygame.draw.polygon(cat, (239, 108, 0), [(23, 13), (26, 7), (29, 13)])
    pygame.draw.polygon(cat, (239, 108, 0), [(29, 13), (32, 7), (35, 13)])
    pygame.draw.circle(cat, (76, 175, 80), (30, 17), 2)
    pygame.image.save(cat, os.path.join(NIGHTWATCH_ASSETS, "characters", "farm_cat.png"))

    # 小偷哥布林 (Enemy Thief)
    thief = create_canvas(50, 50)
    add_drop_shadow(thief, 25, 43, 14, 5)
    # 綠皮膚軀幹
    pygame.draw.ellipse(thief, (76, 175, 80), (16, 22, 18, 16))
    for lx in [18, 28]:
        pygame.draw.rect(thief, (93, 64, 55), (lx, 34, 5, 8), border_radius=1)
    # 尖耳頭部
    pygame.draw.circle(thief, (102, 187, 106), (25, 16), 9)
    pygame.draw.polygon(thief, (76, 175, 80), [(14, 16), (8, 12), (16, 12)])
    pygame.draw.polygon(thief, (76, 175, 80), [(34, 16), (42, 12), (36, 12)])
    # 蒙面黑眼罩
    pygame.draw.rect(thief, (33, 33, 33), (18, 14, 14, 4), border_radius=1)
    pygame.draw.circle(thief, (255, 235, 59), (22, 16), 2)
    pygame.draw.circle(thief, (255, 235, 59), (28, 16), 2)
    # 偷盜麻布袋
    pygame.draw.circle(thief, (215, 180, 120), (14, 26), 7)
    pygame.draw.circle(thief, (255, 215, 0), (14, 20), 3)
    pygame.image.save(thief, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_thief.png"))

    # 狂暴野豬 (Enemy Boar)
    boar = create_canvas(50, 50)
    add_drop_shadow(boar, 25, 42, 18, 6)
    # 棕黑厚實野豬身
    pygame.draw.ellipse(boar, (78, 52, 46), (10, 18, 30, 20))
    for lx in [12, 18, 28, 34]:
        pygame.draw.rect(boar, (62, 39, 35), (lx, 34, 4, 8), border_radius=1)
    # 剛毛背脊
    for bx in range(12, 36, 4):
        pygame.draw.polygon(boar, (38, 20, 15), [(bx, 18), (bx + 2, 12), (bx + 4, 18)])
    # 銳利獠牙
    pygame.draw.polygon(boar, (245, 245, 245), [(36, 28), (44, 22), (38, 24)])
    # 暴怒紅眼
    pygame.draw.circle(boar, (229, 57, 53), (32, 22), 2)
    pygame.image.save(boar, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_boar.png"))

    # 暗夜魔蝠 (Enemy Bat)
    bat = create_canvas(50, 50)
    # 展開雙翼
    pygame.draw.polygon(bat, (94, 53, 177), [(25, 25), (6, 12), (12, 28), (20, 25)])
    pygame.draw.polygon(bat, (94, 53, 177), [(25, 25), (44, 12), (38, 28), (30, 25)])
    pygame.draw.ellipse(bat, (49, 27, 146), (20, 18, 10, 14))
    pygame.draw.circle(bat, (255, 235, 59), (23, 22), 2)
    pygame.draw.circle(bat, (255, 235, 59), (27, 22), 2)
    pygame.image.save(bat, os.path.join(NIGHTWATCH_ASSETS, "characters", "enemy_bat.png"))

    # 野豬暴君 Boss (Boss Boar - 70x70 大體積)
    boss = create_canvas(70, 70)
    add_drop_shadow(boss, 35, 58, 26, 8)
    pygame.draw.ellipse(boss, (46, 18, 18), (12, 20, 46, 32))
    # 巨型暗金鎧甲背脊
    for bx in range(16, 52, 6):
        pygame.draw.polygon(boss, (211, 47, 47), [(bx, 20), (bx + 3, 8), (bx + 6, 20)])
    # 巨大雙獠牙
    pygame.draw.polygon(boss, (255, 255, 255), [(50, 36), (64, 24), (54, 28)])
    pygame.draw.polygon(boss, (255, 255, 255), [(46, 42), (58, 34), (48, 36)])
    # 狂暴血光之眼
    pygame.draw.circle(boss, (255, 0, 0), (44, 28), 4)
    pygame.draw.circle(boss, (255, 255, 0), (44, 28), 2)
    pygame.image.save(boss, os.path.join(NIGHTWATCH_ASSETS, "characters", "boss_boar.png"))


# =========================================================================
# 5. 景觀建築 (Decorations - 13 種)
# =========================================================================
def generate_decorations():
    # 石磚步道 (Stone Path)
    path = create_canvas(50, 50)
    for px, py, pw, ph in [(6, 6, 16, 14), (26, 8, 18, 12), (8, 24, 18, 18), (28, 22, 16, 20)]:
        pygame.draw.rect(path, (144, 164, 174), (px, py, pw, ph), border_radius=3)
        pygame.draw.rect(path, (176, 190, 197), (px + 1, py + 1, pw - 2, ph - 2), border_radius=2)
    pygame.image.save(path, os.path.join(NIGHTWATCH_ASSETS, "decorations", "stone_path.png"))

    # 繁花花圃 (Flower Bed)
    flower = create_canvas(50, 50)
    add_drop_shadow(flower, 25, 38, 18, 6)
    pygame.draw.ellipse(flower, (93, 64, 55), (8, 20, 34, 18))
    for fx, fy, col in [(16, 22, (233, 30, 99)), (25, 18, (255, 235, 59)), (34, 24, (156, 39, 176)), (25, 28, (255, 87, 34))]:
        pygame.draw.circle(flower, col, (fx, fy), 5)
        pygame.draw.circle(flower, (255, 255, 255), (fx, fy), 2)
    pygame.image.save(flower, os.path.join(NIGHTWATCH_ASSETS, "decorations", "flower_bed.png"))

    # 蘋果樹、松樹、櫻花樹 (Trees)
    for tname, leaf_col, detail_col in [
        ("pine_tree", (46, 125, 50), (129, 199, 132)),
        ("apple_tree", (67, 160, 71), (229, 57, 53)),
        ("sakura_tree", (244, 143, 177), (255, 255, 255)),
    ]:
        tree = create_canvas(50, 50)
        add_drop_shadow(tree, 25, 45, 16, 4)
        pygame.draw.rect(tree, (109, 76, 65), (21, 26, 8, 18), border_radius=2)
        # 樹冠層次
        pygame.draw.circle(tree, leaf_col, (25, 18), 16)
        pygame.draw.circle(tree, leaf_col, (16, 22), 12)
        pygame.draw.circle(tree, leaf_col, (34, 22), 12)
        pygame.draw.circle(tree, detail_col if tname != "apple_tree" else (229, 57, 53), (20, 14), 3)
        pygame.draw.circle(tree, detail_col if tname != "apple_tree" else (229, 57, 53), (30, 18), 3)
        pygame.draw.circle(tree, detail_col if tname != "apple_tree" else (229, 57, 53), (24, 24), 3)
        pygame.image.save(tree, os.path.join(NIGHTWATCH_ASSETS, "decorations", f"{tname}.png"))

    # 噴泉 (Fountain)
    ftn = create_canvas(50, 50)
    add_drop_shadow(ftn, 25, 42, 18, 6)
    pygame.draw.ellipse(ftn, (120, 144, 156), (8, 22, 34, 18))
    pygame.draw.ellipse(ftn, (41, 182, 246), (12, 25, 26, 12))
    pygame.draw.rect(ftn, (176, 190, 197), (22, 12, 6, 16), border_radius=2)
    pygame.draw.circle(ftn, (255, 255, 255), (25, 10), 4)
    pygame.draw.circle(ftn, (179, 229, 252), (25, 10), 2)
    pygame.image.save(ftn, os.path.join(NIGHTWATCH_ASSETS, "decorations", "fountain.png"))

    # 風車、長椅、古雕像、燈柱等
    for dname in ["garden_bench", "soul_lantern", "bird_bath", "ancient_statue", "pet_house", "sundial_tower", "windmill"]:
        d_surf = create_canvas(50, 50)
        add_drop_shadow(d_surf, 25, 42, 15, 5)
        if dname == "soul_lantern":
            pygame.draw.rect(d_surf, (55, 71, 79), (23, 14, 4, 30))
            pygame.draw.circle(d_surf, (255, 215, 0), (25, 14), 7)
            pygame.draw.circle(d_surf, (255, 255, 255), (25, 14), 3)
        elif dname == "windmill":
            pygame.draw.polygon(d_surf, (207, 216, 220), [(25, 8), (14, 42), (36, 42)])
            pygame.draw.line(d_surf, (141, 110, 99), (10, 12), (40, 24), 3)
            pygame.draw.line(d_surf, (141, 110, 99), (40, 12), (10, 24), 3)
        else:
            pygame.draw.rect(d_surf, (144, 164, 174), (12, 16, 26, 24), border_radius=4)
            pygame.draw.rect(d_surf, (176, 190, 197), (16, 20, 18, 16), border_radius=2)
        pygame.image.save(d_surf, os.path.join(NIGHTWATCH_ASSETS, "decorations", f"{dname}.png"))

    print("🌟 頂級精緻像素素材全部生成完畢！")


def generate_all():
    generate_tiles()
    generate_crops()
    generate_defenses()
    generate_characters()
    generate_decorations()


if __name__ == "__main__":
    generate_all()
