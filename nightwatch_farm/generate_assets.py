"""
夜巡農場 (Nightwatch Farm) - 純色扁平極簡風 (Flat Minimalist) 完整素材生成器
生成 10 種農作物（各4階段）、13 種莊園景觀、防禦工事、蜜蜂巢（與向日葵完全區分）及生物。
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

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")
for cat in ["crops", "decorations", "defenses", "characters", "ui"]:
    os.makedirs(os.path.join(ASSET_ROOT, cat), exist_ok=True)


def save_surface(surface: pygame.Surface, category: str, filename: str):
    path = os.path.join(ASSET_ROOT, category, filename)
    pygame.image.save(surface, path)


def create_blank(size=(64, 64)) -> pygame.Surface:
    return pygame.Surface(size, pygame.SRCALPHA)


# ==========================================
# 1. 農作物 (10 種作物，各 4 階段生長)
# ==========================================
def gen_crops():
    # 1. 白蘿蔔 (Lv.1)
    for stage, name in enumerate(["radish_seed", "radish_sprout", "radish_growing", "radish_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.ellipse(s, (141, 110, 99), (cx - 5, cy + 10, 10, 8))
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy + 2), 4)
            pygame.draw.circle(s, (129, 199, 132), (cx - 6, cy + 2), 6)
            pygame.draw.circle(s, (129, 199, 132), (cx + 6, cy + 2), 6)
        elif stage == 2:
            pygame.draw.polygon(s, (245, 245, 245), [(cx-7, cy+6), (cx+7, cy+6), (cx, cy+22)])
            pygame.draw.polygon(s, (76, 175, 80), [(cx, cy+4), (cx-12, cy-8), (cx-4, cy-2)])
            pygame.draw.polygon(s, (76, 175, 80), [(cx, cy+4), (cx+12, cy-8), (cx+4, cy-2)])
        else:
            pygame.draw.ellipse(s, (250, 250, 250), (cx - 13, cy - 2, 26, 30))
            pygame.draw.polygon(s, (56, 142, 60), [(cx, cy-2), (cx-14, cy-18), (cx-4, cy-8)])
            pygame.draw.polygon(s, (56, 142, 60), [(cx, cy-2), (cx+14, cy-18), (cx+4, cy-8)])
            pygame.draw.polygon(s, (76, 175, 80), [(cx, cy-2), (cx, cy-22), (cx+4, cy-10)])
        save_surface(s, "crops", f"{name}.png")

    # 2. 紅番茄 (Lv.1)
    for stage, name in enumerate(["tomato_seed", "tomato_sprout", "tomato_growing", "tomato_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.circle(s, (139, 69, 19), (cx, cy + 10), 6)
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy), 4)
            pygame.draw.circle(s, (129, 199, 132), (cx - 6, cy - 4), 6)
        elif stage == 2:
            pygame.draw.circle(s, (102, 187, 106), (cx - 8, cy + 6), 9)
            pygame.draw.circle(s, (102, 187, 106), (cx + 8, cy + 6), 9)
            pygame.draw.circle(s, (139, 195, 74), (cx, cy - 4), 8)
        else:
            pygame.draw.circle(s, (239, 83, 80), (cx - 10, cy + 6), 13)
            pygame.draw.circle(s, (239, 83, 80), (cx + 10, cy + 6), 13)
            pygame.draw.circle(s, (255, 138, 128), (cx - 13, cy + 3), 4)
            pygame.draw.circle(s, (255, 138, 128), (cx + 7, cy + 3), 4)
            pygame.draw.circle(s, (46, 125, 50), (cx, cy - 8), 12)
        save_surface(s, "crops", f"{name}.png")

    # 3. 甜玉米 (Lv.2)
    for stage, name in enumerate(["corn_seed", "corn_sprout", "corn_growing", "corn_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.circle(s, (255, 193, 7), (cx, cy + 10), 6)
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy - 4), 4)
            pygame.draw.polygon(s, (129, 199, 132), [(cx, cy), (cx - 10, cy - 10), (cx - 2, cy - 2)])
        elif stage == 2:
            pygame.draw.line(s, (56, 142, 60), (cx, cy + 18), (cx, cy - 12), 5)
            pygame.draw.polygon(s, (102, 187, 106), [(cx, cy-2), (cx - 14, cy - 12), (cx - 2, cy - 4)])
            pygame.draw.polygon(s, (102, 187, 106), [(cx, cy+2), (cx + 14, cy - 8), (cx + 2, cy)])
        else:
            pygame.draw.line(s, (56, 142, 60), (cx, cy + 20), (cx, cy - 18), 5)
            pygame.draw.ellipse(s, (255, 214, 0), (cx - 9, cy - 14, 18, 30))
            pygame.draw.polygon(s, (76, 175, 80), [(cx-9, cy+6), (cx-14, cy-8), (cx-4, cy-3)])
            pygame.draw.polygon(s, (76, 175, 80), [(cx+9, cy+6), (cx+14, cy-8), (cx+4, cy-3)])
        save_surface(s, "crops", f"{name}.png")

    # 4. 紫水晶茄子 (Lv.2 - 新增)
    for stage, name in enumerate(["eggplant_seed", "eggplant_sprout", "eggplant_growing", "eggplant_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.ellipse(s, (100, 50, 120), (cx - 5, cy + 10, 10, 7))
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy), 4)
            pygame.draw.circle(s, (156, 39, 176), (cx, cy - 2), 6)
        elif stage == 2:
            pygame.draw.ellipse(s, (123, 31, 162), (cx - 7, cy - 2, 14, 22))
            pygame.draw.polygon(s, (56, 142, 60), [(cx-6, cy-2), (cx+6, cy-2), (cx, cy-10)])
        else:
            # 飽滿純紫茄子 + 翠綠頂帽
            pygame.draw.ellipse(s, (74, 20, 140), (cx - 11, cy - 6, 22, 34))
            pygame.draw.ellipse(s, (142, 36, 170), (cx - 8, cy - 3, 10, 24))
            pygame.draw.polygon(s, (46, 125, 50), [(cx-10, cy-6), (cx+10, cy-6), (cx, cy-16)])
        save_surface(s, "crops", f"{name}.png")

    # 5. 鮮甜草莓 (Lv.2 - 新增)
    for stage, name in enumerate(["strawberry_seed", "strawberry_sprout", "strawberry_growing", "strawberry_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.circle(s, (211, 47, 47), (cx, cy + 10), 5)
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy + 2), 3)
            pygame.draw.circle(s, (129, 199, 132), (cx - 5, cy), 5)
            pygame.draw.circle(s, (129, 199, 132), (cx + 5, cy), 5)
        elif stage == 2:
            pygame.draw.polygon(s, (229, 115, 115), [(cx-10, cy), (cx+10, cy), (cx, cy+18)])
            pygame.draw.circle(s, (76, 175, 80), (cx, cy-4), 6)
        else:
            # 亮麗心形紅草莓 + 黃色種子斑點
            pygame.draw.polygon(s, (229, 57, 53), [(cx - 14, cy - 4), (cx + 14, cy - 4), (cx, cy + 20)])
            pygame.draw.circle(s, (229, 57, 53), (cx - 7, cy - 4), 9)
            pygame.draw.circle(s, (229, 57, 53), (cx + 7, cy - 4), 9)
            # 種子點
            for sx, sy in [(-5, 0), (5, 0), (0, 8), (-4, 6), (4, 6)]:
                pygame.draw.circle(s, (255, 235, 59), (cx + sx, cy + sy), 1)
            pygame.draw.circle(s, (56, 142, 60), (cx, cy - 10), 6)
        save_surface(s, "crops", f"{name}.png")

    # 6. 魔法南瓜 (Lv.3)
    for stage, name in enumerate(["pumpkin_seed", "pumpkin_sprout", "pumpkin_growing", "pumpkin_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.ellipse(s, (93, 64, 55), (cx - 6, cy + 8, 12, 8))
        elif stage == 1:
            pygame.draw.circle(s, (76, 175, 80), (cx - 6, cy + 8), 6)
            pygame.draw.circle(s, (76, 175, 80), (cx + 6, cy + 8), 6)
        elif stage == 2:
            pygame.draw.ellipse(s, (67, 160, 71), (cx - 14, cy, 28, 20))
        else:
            pygame.draw.ellipse(s, (255, 140, 0), (cx - 22, cy - 8, 44, 34))
            pygame.draw.ellipse(s, (255, 167, 38), (cx - 14, cy - 8, 28, 34))
            pygame.draw.ellipse(s, (255, 183, 77), (cx - 6, cy - 7, 12, 30))
            pygame.draw.rect(s, (93, 64, 55), (cx - 4, cy - 16, 8, 10), border_radius=3)
            pygame.draw.circle(s, (255, 235, 59), (cx, cy - 18), 4)
        save_surface(s, "crops", f"{name}.png")

    # 7. 冰爽西瓜 (Lv.3 - 新增)
    for stage, name in enumerate(["watermelon_seed", "watermelon_sprout", "watermelon_growing", "watermelon_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.ellipse(s, (40, 40, 40), (cx - 5, cy + 10, 10, 6))
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy), 4)
            pygame.draw.circle(s, (102, 187, 106), (cx - 6, cy - 2), 6)
        elif stage == 2:
            pygame.draw.circle(s, (46, 125, 50), (cx, cy + 4), 14)
        else:
            # 圓滾深綠西瓜 + 翠綠紋路
            pygame.draw.circle(s, (27, 94, 32), (cx, cy + 2), 20)
            pygame.draw.ellipse(s, (76, 175, 80), (cx - 14, cy - 10, 8, 24))
            pygame.draw.ellipse(s, (76, 175, 80), (cx + 6, cy - 10, 8, 24))
            pygame.draw.ellipse(s, (76, 175, 80), (cx - 4, cy - 12, 8, 28))
            pygame.draw.line(s, (139, 69, 19), (cx, cy - 18), (cx + 4, cy - 24), 3)
        save_surface(s, "crops", f"{name}.png")

    # 8. 金色向日葵 (Lv.3) - 與蜜蜂完全區分（巨大金色花盤與高挺花莖）
    for stage, name in enumerate(["sunflower_seed", "sunflower_sprout", "sunflower_growing", "sunflower_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.circle(s, (40, 40, 40), (cx, cy + 10), 5)
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy), 4)
            pygame.draw.circle(s, (102, 187, 106), (cx - 5, cy - 2), 5)
        elif stage == 2:
            pygame.draw.line(s, (56, 142, 60), (cx, cy + 18), (cx, cy - 10), 5)
            pygame.draw.circle(s, (139, 195, 74), (cx, cy - 10), 10)
        else:
            pygame.draw.line(s, (56, 142, 60), (cx, cy + 20), (cx, cy - 8), 5)
            # 翠綠大葉片
            pygame.draw.polygon(s, (76, 175, 80), [(cx-4, cy+10), (cx-18, cy+2), (cx-4, cy+2)])
            pygame.draw.polygon(s, (76, 175, 80), [(cx+4, cy+14), (cx+18, cy+6), (cx+4, cy+6)])
            # 放射狀金黃花瓣
            for a in range(0, 360, 30):
                rad = math.radians(a)
                px = cx + math.cos(rad) * 14
                py = cy - 8 + math.sin(rad) * 14
                pygame.draw.circle(s, (255, 193, 7), (int(px), int(py)), 6)
            pygame.draw.circle(s, (255, 214, 0), (cx, cy - 8), 12)
            pygame.draw.circle(s, (78, 52, 46), (cx, cy - 8), 8) # 深褐花心
        save_surface(s, "crops", f"{name}.png")

    # 9. 皇家紫葡萄 (Lv.4 - 新增)
    for stage, name in enumerate(["grape_seed", "grape_sprout", "grape_growing", "grape_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.circle(s, (74, 20, 140), (cx, cy + 10), 5)
        elif stage == 1:
            pygame.draw.line(s, (76, 175, 80), (cx, cy + 16), (cx, cy), 3)
            pygame.draw.circle(s, (156, 39, 176), (cx, cy - 2), 6)
        elif stage == 2:
            pygame.draw.circle(s, (123, 31, 162), (cx - 5, cy + 2), 7)
            pygame.draw.circle(s, (123, 31, 162), (cx + 5, cy + 2), 7)
            pygame.draw.circle(s, (123, 31, 162), (cx, cy + 10), 6)
        else:
            # 晶瑩串串紫葡萄 + 藤蔓捲鬚
            pygame.draw.line(s, (109, 76, 65), (cx, cy - 18), (cx, cy - 8), 4)
            pygame.draw.polygon(s, (76, 175, 80), [(cx-2, cy-12), (cx-14, cy-18), (cx-8, cy-8)])
            for gx, gy in [(-8, -4), (0, -4), (8, -4), (-4, 4), (4, 4), (0, 12)]:
                pygame.draw.circle(s, (74, 20, 140), (cx + gx, cy + gy), 7)
                pygame.draw.circle(s, (171, 71, 188), (cx + gx - 2, cy + gy - 2), 3)
        save_surface(s, "crops", f"{name}.png")

    # 10. 永恆星光果 (Lv.5 - 傳奇神聖作物 - 新增)
    for stage, name in enumerate(["starlight_seed", "starlight_sprout", "starlight_growing", "starlight_mature"]):
        s = create_blank()
        cx, cy = 32, 32
        if stage == 0:
            pygame.draw.circle(s, (0, 229, 255), (cx, cy + 10), 6)
        elif stage == 1:
            pygame.draw.line(s, (0, 229, 255), (cx, cy + 16), (cx, cy), 3)
            pygame.draw.circle(s, (224, 247, 250), (cx, cy - 2), 6)
        elif stage == 2:
            pygame.draw.polygon(s, (0, 188, 212), [(cx, cy-10), (cx+12, cy+4), (cx-12, cy+4)])
        else:
            # 璀璨星芒光輝水晶果
            pygame.draw.circle(s, (0, 229, 255, 100), (cx, cy), 20)
            # 五角星
            points = []
            for i in range(10):
                r = 18 if i % 2 == 0 else 8
                ang = i * math.pi / 5 - math.pi / 2
                points.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
            pygame.draw.polygon(s, (0, 229, 255), points)
            pygame.draw.polygon(s, (255, 255, 255), [(p[0]*0.5 + cx*0.5, p[1]*0.5 + cy*0.5) for p in points])
        save_surface(s, "crops", f"{name}.png")


# ==========================================
# 2. 莊園景觀 (13 種豐富佈置)
# ==========================================
def gen_decorations():
    # 1. 石板花徑
    s = create_blank()
    pygame.draw.rect(s, (189, 195, 199), (6, 6, 52, 52), border_radius=10)
    pygame.draw.rect(s, (236, 240, 241), (10, 10, 20, 20), border_radius=6)
    pygame.draw.rect(s, (236, 240, 241), (34, 34, 20, 20), border_radius=6)
    save_surface(s, "decorations", "stone_path.png")

    # 2. 鮮花花壇
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (149, 165, 166), (cx, cy), 22)
    pygame.draw.circle(s, (233, 30, 99), (cx - 8, cy - 4), 9)
    pygame.draw.circle(s, (156, 39, 176), (cx + 8, cy - 4), 9)
    pygame.draw.circle(s, (255, 193, 7), (cx, cy + 6), 8)
    save_surface(s, "decorations", "flower_bed.png")

    # 3. 休閒木長椅 (新增)
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (121, 85, 72), (cx - 20, cy + 8, 6, 16), border_radius=2)
    pygame.draw.rect(s, (121, 85, 72), (cx + 14, cy + 8, 6, 16), border_radius=2)
    pygame.draw.rect(s, (161, 136, 127), (cx - 22, cy + 4, 44, 8), border_radius=3)
    pygame.draw.rect(s, (141, 110, 99), (cx - 22, cy - 10, 44, 12), border_radius=3)
    save_surface(s, "decorations", "garden_bench.png")

    # 4. 莊園松柏樹 (新增)
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (109, 76, 65), (cx - 3, cy + 8, 6, 20), border_radius=2)
    pygame.draw.polygon(s, (27, 94, 32), [(cx - 20, cy + 8), (cx + 20, cy + 8), (cx, cy - 4)])
    pygame.draw.polygon(s, (46, 125, 50), [(cx - 16, cy - 2), (cx + 16, cy - 2), (cx, cy - 14)])
    pygame.draw.polygon(s, (76, 175, 80), [(cx - 12, cy - 12), (cx + 12, cy - 12), (cx, cy - 24)])
    save_surface(s, "decorations", "pine_tree.png")

    # 5. 蘋果果樹
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (121, 85, 72), (cx - 4, cy, 8, 28), border_radius=3)
    pygame.draw.circle(s, (46, 125, 50), (cx, cy - 12), 22)
    pygame.draw.circle(s, (76, 175, 80), (cx - 4, cy - 14), 16)
    pygame.draw.circle(s, (239, 83, 80), (cx - 8, cy - 10), 4)
    pygame.draw.circle(s, (239, 83, 80), (cx + 8, cy - 10), 4)
    pygame.draw.circle(s, (239, 83, 80), (cx, cy - 20), 4)
    save_surface(s, "decorations", "apple_tree.png")

    # 6. 浪漫櫻花樹
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (109, 76, 65), (cx - 4, cy, 8, 28), border_radius=3)
    pygame.draw.circle(s, (244, 143, 177), (cx, cy - 12), 22)
    pygame.draw.circle(s, (248, 187, 208), (cx - 4, cy - 14), 16)
    save_surface(s, "decorations", "sakura_tree.png")

    # 7. 守護路燈
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (52, 73, 94), (cx - 3, cy - 12, 6, 40), border_radius=3)
    pygame.draw.circle(s, (255, 235, 59), (cx, cy - 14), 10)
    pygame.draw.circle(s, (255, 255, 255), (cx, cy - 14), 4)
    save_surface(s, "decorations", "soul_lantern.png")

    # 8. 石砌鳥浴水盆 (新增)
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (149, 165, 166), (cx - 4, cy - 4, 8, 28), border_radius=3)
    pygame.draw.rect(s, (189, 195, 199), (cx - 12, cy + 18, 24, 6), border_radius=3)
    pygame.draw.ellipse(s, (189, 195, 199), (cx - 20, cy - 16, 40, 16))
    pygame.draw.ellipse(s, (3, 169, 244), (cx - 16, cy - 14, 32, 12))
    save_surface(s, "decorations", "bird_bath.png")

    # 9. 莊園雕像
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (149, 165, 166), (cx - 14, cy + 10, 28, 8), border_radius=3)
    pygame.draw.polygon(s, (189, 195, 199), [(cx - 10, cy + 10), (cx + 10, cy + 10), (cx, cy - 16)])
    pygame.draw.circle(s, (236, 240, 241), (cx, cy - 8), 8)
    save_surface(s, "decorations", "ancient_statue.png")

    # 10. 圓形噴泉
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (149, 165, 166), (cx, cy), 24)
    pygame.draw.circle(s, (3, 169, 244), (cx, cy), 18)
    pygame.draw.circle(s, (179, 229, 252), (cx, cy), 10)
    pygame.draw.circle(s, (0, 229, 255), (cx, cy), 4)
    save_surface(s, "decorations", "fountain.png")

    # 11. 寵物小屋
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (211, 84, 0), (cx - 16, cy - 6, 32, 26), border_radius=4)
    pygame.draw.polygon(s, (192, 57, 43), [(cx - 20, cy - 6), (cx + 20, cy - 6), (cx, cy - 20)])
    pygame.draw.rect(s, (44, 62, 80), (cx - 7, cy + 4, 14, 16), border_radius=7)
    save_surface(s, "decorations", "pet_house.png")

    # 12. 天使日晷鐘塔 (新增)
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (236, 240, 241), (cx - 8, cy - 12, 16, 36), border_radius=3)
    pygame.draw.polygon(s, (255, 193, 7), [(cx - 12, cy - 12), (cx + 12, cy - 12), (cx, cy - 24)])
    pygame.draw.circle(s, (0, 229, 255), (cx, cy - 2), 5)
    save_surface(s, "decorations", "sundial_tower.png")

    # 13. 彩虹風車磨坊 (新增)
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.polygon(s, (141, 110, 99), [(cx - 14, cy + 24), (cx + 14, cy + 24), (cx + 8, cy - 10), (cx - 8, cy - 10)])
    pygame.draw.circle(s, (211, 47, 47), (cx, cy - 10), 10)
    # 4 扇風車葉片
    for ang in [0, 90, 180, 270]:
        rad = math.radians(ang)
        bx = cx + math.cos(rad) * 16
        by = cy - 10 + math.sin(rad) * 16
        pygame.draw.line(s, (255, 255, 255), (cx, cy - 10), (int(bx), int(by)), 4)
    save_surface(s, "decorations", "windmill.png")


# ==========================================
# 3. 防禦設施與塔防 (包含全新設計的蜜蜂巢)
# ==========================================
def gen_defenses():
    # 刺藤木柵
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (141, 110, 99), (cx - 18, cy - 16, 8, 34), border_radius=3)
    pygame.draw.rect(s, (141, 110, 99), (cx + 10, cy - 16, 8, 34), border_radius=3)
    pygame.draw.rect(s, (109, 76, 65), (cx - 22, cy - 6, 44, 6), border_radius=3)
    pygame.draw.rect(s, (109, 76, 65), (cx - 22, cy + 6, 44, 6), border_radius=3)
    save_surface(s, "defenses", "wooden_fence.png")

    # 捕獸夾
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (149, 165, 166), (cx, cy), 18, 4)
    pygame.draw.circle(s, (231, 76, 60), (cx, cy), 6)
    save_surface(s, "defenses", "bear_trap.png")

    # 稻草人
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (141, 110, 99), (cx - 3, cy - 16, 6, 36))
    pygame.draw.rect(s, (141, 110, 99), (cx - 18, cy - 4, 36, 4))
    pygame.draw.circle(s, (255, 235, 156), (cx, cy - 10), 8)
    pygame.draw.polygon(s, (211, 84, 0), [(cx - 12, cy - 10), (cx + 12, cy - 10), (cx, cy - 20)])
    save_surface(s, "defenses", "scarecrow.png")

    # 蜜蜂守衛巢 - 【全新獨特外觀】：深木懸臂支架 + 條紋六角琥珀木蜂巢柱 + 環繞黑色條紋小蜜蜂（與向日葵絕不混淆！）
    s = create_blank()
    cx, cy = 32, 32
    # 1. 堅固木造支架
    pygame.draw.rect(s, (93, 64, 55), (cx - 4, cy - 20, 8, 44), border_radius=2)
    pygame.draw.rect(s, (93, 64, 55), (cx - 4, cy - 20, 24, 6), border_radius=2)
    # 2. 懸掛式橢圓/六角蜂巢柱 (琥珀色+深色條紋)
    pygame.draw.ellipse(s, (217, 119, 6), (cx + 4, cy - 16, 22, 28))
    pygame.draw.ellipse(s, (245, 158, 11), (cx + 6, cy - 13, 18, 22))
    # 橫向蜂巢紋理
    pygame.draw.line(s, (180, 83, 9), (cx + 6, cy - 7), (cx + 24, cy - 7), 2)
    pygame.draw.line(s, (180, 83, 9), (cx + 6, cy - 1), (cx + 24, cy - 1), 2)
    # 蜂巢出入口洞穴 (黑洞)
    pygame.draw.circle(s, (30, 20, 15), (cx + 15, cy + 2), 4)
    # 3. 飛行的黑黃相間守衛蜜蜂
    for bx, by in [(cx - 12, cy - 10), (cx - 16, cy + 6), (cx + 18, cy - 20)]:
        pygame.draw.ellipse(s, (255, 235, 59), (bx, by, 7, 5))
        pygame.draw.line(s, (20, 20, 20), (bx + 3, by), (bx + 3, by + 5), 2) # 黑色條紋
        pygame.draw.circle(s, (224, 247, 250), (bx + 3, by - 2), 2) # 透明白翅膀
    save_surface(s, "defenses", "beehive.png")

    # 黃金水壺
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.rect(s, (255, 193, 7), (cx - 9, cy - 5, 18, 16), border_radius=4)
    pygame.draw.line(s, (255, 215, 0), (cx - 9, cy - 3), (cx - 16, cy - 9), 4)
    pygame.draw.line(s, (255, 215, 0), (cx + 9, cy + 3), (cx + 16, cy - 7), 4)
    pygame.draw.circle(s, (33, 150, 243), (cx + 16, cy - 7), 3)
    save_surface(s, "defenses", "watering_can.png")


# ==========================================
# 4. 生物角色
# ==========================================
def gen_characters():
    # 柴犬
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (243, 156, 18), (cx, cy), 14)
    pygame.draw.circle(s, (253, 237, 211), (cx, cy + 3), 8)
    pygame.draw.polygon(s, (211, 84, 0), [(cx - 10, cy - 8), (cx - 3, cy - 16), (cx - 2, cy - 8)])
    pygame.draw.polygon(s, (211, 84, 0), [(cx + 2, cy - 8), (cx + 3, cy - 16), (cx + 10, cy - 8)])
    pygame.draw.circle(s, (44, 62, 80), (cx - 4, cy - 2), 2)
    pygame.draw.circle(s, (44, 62, 80), (cx + 4, cy - 2), 2)
    pygame.draw.circle(s, (44, 62, 80), (cx, cy + 2), 2)
    save_surface(s, "characters", "guard_dog.png")

    # 招財貓
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (255, 167, 38), (cx, cy), 13)
    pygame.draw.circle(s, (255, 255, 255), (cx, cy + 3), 7)
    pygame.draw.polygon(s, (230, 81, 0), [(cx - 9, cy - 6), (cx - 3, cy - 14), (cx - 2, cy - 6)])
    pygame.draw.polygon(s, (230, 81, 0), [(cx + 2, cy - 6), (cx + 3, cy - 14), (cx + 9, cy - 6)])
    pygame.draw.circle(s, (46, 125, 50), (cx - 4, cy - 2), 2)
    pygame.draw.circle(s, (46, 125, 50), (cx + 4, cy - 2), 2)
    save_surface(s, "characters", "farm_cat.png")

    # 小偷
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (44, 62, 80), (cx, cy), 14)
    pygame.draw.rect(s, (236, 240, 241), (cx - 6, cy - 3, 12, 4), border_radius=2)
    pygame.draw.circle(s, (231, 76, 60), (cx - 3, cy - 1), 2)
    pygame.draw.circle(s, (231, 76, 60), (cx + 3, cy - 1), 2)
    save_surface(s, "characters", "enemy_thief.png")

    # 狂暴野豬
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (109, 76, 65), (cx, cy), 16)
    pygame.draw.circle(s, (231, 76, 60), (cx + 6, cy - 3), 3)
    pygame.draw.polygon(s, (255, 255, 255), [(cx + 12, cy + 2), (cx + 18, cy - 4), (cx + 14, cy + 4)])
    save_surface(s, "characters", "enemy_boar.png")

    # 暗夜魔蝠
    s = create_blank()
    cx, cy = 32, 32
    pygame.draw.circle(s, (52, 73, 94), (cx, cy), 8)
    pygame.draw.polygon(s, (44, 62, 80), [(cx, cy), (cx - 16, cy - 8), (cx - 8, cy + 6)])
    pygame.draw.polygon(s, (44, 62, 80), [(cx, cy), (cx + 16, cy - 8), (cx + 8, cy + 6)])
    pygame.draw.circle(s, (231, 76, 60), (cx - 2, cy - 2), 2)
    pygame.draw.circle(s, (231, 76, 60), (cx + 2, cy - 2), 2)
    save_surface(s, "characters", "enemy_bat.png")

    # 【血月首領】野豬巨獸
    s = create_blank((80, 80))
    cx, cy = 40, 40
    pygame.draw.circle(s, (198, 40, 40, 100), (cx, cy), 36)
    pygame.draw.circle(s, (62, 39, 35), (cx, cy), 28)
    pygame.draw.circle(s, (255, 23, 68), (cx + 10, cy - 6), 5)
    pygame.draw.polygon(s, (255, 255, 255), [(cx + 18, cy + 4), (cx + 32, cy - 8), (cx + 22, cy + 8)])
    save_surface(s, "characters", "boss_boar.png")


if __name__ == "__main__":
    print("🎨 生成擴展 10 種作物、13 種景觀與全新蜂巢素材...")
    gen_crops()
    gen_decorations()
    gen_defenses()
    gen_characters()
    print("✅ 素材生成完成！")
