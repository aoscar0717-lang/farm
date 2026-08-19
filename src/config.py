import pygame
import os
from src.capstone_contract import ITEM_SIZE, GRID_W, GRID_H, CROP_INFO

pygame.init()
info = pygame.display.Info()
WIDTH = info.current_w
HEIGHT = info.current_h

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
DARK_GREEN = (34, 139, 34)
GRASS_GREEN = (143, 188, 143)
RED = (220, 20, 60)
BLUE = (65, 105, 225)
YELLOW = (255, 215, 0)

# Sprite Scale Multipliers
# 調整這裡的參數來改變圖片在遊戲內的顯示大小比例 (寬度倍率, 高度倍率)
# 基底大小為 ITEM_PX (40像素)
SPRITE_SCALES = {
    "tree": (1.5, 1.6),
    "rock": (1.0, 1.0),
    "soil": (1.0, 1.0),
    "crop": (0.3, 0.3),
    "scarecrow": (1.0, 1.0),
    "windmill": (2.0, 2.0),
    "dog": (1.2, 1.5),
    "cat": (1.0, 1.0),
    "goose": (1.1, 1.1),
    "sheep": (1.3, 1.3),
    "bull": (1.6, 1.6),
    "owl": (1.0, 1.0),
    "goblin": (2.5, 1.7),
    "boar": (1.5, 1.5)
}

# ASSET_FOOTPRINTS -- documentation metadata for section 十五 of the
# Tutorial/Thought UX upgrade ("2x2 被壓成 1x1" investigation). This maps a
# decor/world object's *visual* footprint, in grid tiles, to how many tiles
# it actually occupies for collision/placement purposes -- default (1, 1)
# for anything not listed here.
#
# After re-checking sprite_loader.py, renderer.py, assets.py, and every
# SPRITE_SCALES entry against capstone_contract.py's _is_occupied() /
# placement code, exactly ONE asset in the whole project has a visual size
# that doesn't match its logical (collision/placement) footprint: the
# "fountain" decor item (displayed name 風車) is drawn at
# SPRITE_SCALES["windmill"] = (2.0, 2.0) -- i.e. it visually spans roughly a
# 2x2 tile area, centered on its placement origin (see renderer.py's
# _draw_decorations, the "fountain" special case) -- while build_decor_ /
# _is_occupied() and every other piece of placement/collision code treats
# it as exactly 1x1 (ITEM_SIZE), identical to every other decor type. No
# other asset in the project (tree/rock/soil/crop/scarecrow/dog/goblin/
# boar, nor any of the 18 other decor items) has this mismatch -- their
# SPRITE_SCALES entries are all close to (1,1) and/or aren't tied to
# grid-occupancy at all (goblin/boar/dog are mobile entities, not
# placed-on-a-grid-cell objects).
#
# Deliberately NOT used to rearchitect _is_occupied()/collision into
# reserving multiple grid cells -- that would be a much larger, riskier
# change than what's actually broken (a single decor item's visuals
# slightly overflowing its own 1x1 placement cell into neighboring tiles,
# which is a cosmetic overlap, not a gameplay bug: nothing currently
# prevents placing something in a tile the fountain visually overlaps).
# This dict exists so the mismatch is explicit, documented, and testable
# (see tests/test_sprite_footprints.py) rather than silently living only in
# two people's heads across renderer.py and capstone_contract.py.
ASSET_FOOTPRINTS = {
    "fountain": (2, 2),
}


def get_asset_footprint(asset_id):
    """(cols, rows) footprint for `asset_id`, defaulting to (1, 1) -- the
    single lookup point tests/other modules should use instead of poking
    ASSET_FOOTPRINTS.get(...) directly everywhere."""
    return ASSET_FOOTPRINTS.get(asset_id, (1, 1))


CELL_SIZE = 10
ITEM_PX = CELL_SIZE * ITEM_SIZE
WORLD_W = GRID_W * CELL_SIZE
WORLD_H = GRID_H * CELL_SIZE

MARGIN_TOP = 0
MARGIN_BOTTOM = 0

try:
    font_large = pygame.font.SysFont("microsoftjhenghei", 36)
    font_small = pygame.font.SysFont("microsoftjhenghei", 24)
    font_tiny = pygame.font.SysFont("microsoftjhenghei", 18)
except:
    font_large = pygame.font.Font(None, 48)
    font_small = pygame.font.Font(None, 32)
    font_tiny = pygame.font.Font(None, 24)

TOOL_NAMES = {
    "radish": "白蘿蔔種子", "carrot": "胡蘿蔔種子", "pumpkin": "魔法南瓜種子",
    "stone_path": "石板路", "flower": "鮮花盆栽", "bench": "木製長椅", "fountain": "風車",
    "scarecrow": "稻草人", "crate": "木箱", "bush": "灌木叢", "rock": "庭院石",
    "sunflower": "向日葵", "pine_tree": "松樹", "big_tree": "大樹",
    "stump": "樹墩", "mushroom": "蘑菇", "picnic_basket": "野餐籃", "woodpile": "柴堆",
    "picnic_blanket": "野餐墊", "beehive": "蜂箱", "garden_table": "庭院桌", "fruit_tree": "果樹",
    "fence": "木圍欄", "trap": "捕獸夾",
    "dog": "看門狗", "cat": "招財小貓", "goose": "暴躁警戒鵝", "sheep": "棉花守護羊", "bull": "鐵壁戰鬥牛", "owl": "夜行守護鳥",
    "fertilizer": "魔法肥料", "shovel": "鐵鏟 (免費)", "axe": "斧頭", "pickaxe": "十字鎬",
    "hoe": "鋤頭 (開墾)", "scythe": "鐮刀 (收割)"
}


ANIMAL_INFO = {
    "dog": {"name": "看門狗", "price": 200, "speed": 1.0, "damage": 1, "desc": "自動攻擊靠近敵人，不會陣亡"},
    "cat": {"name": "招財小貓", "price": 150, "speed": 1.8, "damage": 1, "desc": "極速抓瞎減速敵人，白天定期摸出金幣"},
    "goose": {"name": "暴躁警戒鵝", "price": 220, "speed": 1.2, "damage": 1, "desc": "領域意識極強，憤怒衝撞將敵人擊退"},
    "sheep": {"name": "棉花守護羊", "price": 260, "speed": 0.6, "hp": 10, "desc": "厚實羊毛護盾，主動吸引敵人仇恨"},
    "bull": {"name": "鐵壁戰鬥牛", "price": 350, "speed": 0.8, "damage": 2, "desc": "體型巨大威嚴，巨角挑擊造成雙倍重傷"},
    "owl": {"name": "夜行守護鳥", "price": 280, "speed": 2.2, "damage": 1, "desc": "空中高速俯衝，有機會嚇停敵人"},
}


# Message notification system
MSG_DURATION = 3.0          # seconds a message stays fully visible
MSG_FADE_DURATION = 1.0     # seconds to fade out after MSG_DURATION

# Message color categories (detected by keywords in the message)
MSG_COLORS = {
    "error":   (255, 100, 100),   # Red  - illegal actions
    "warn":    (255, 180, 60),    # Orange - insufficient funds
    "success": (100, 230, 100),   # Green - build/plant success
    "info":    (200, 220, 255),   # Light blue - general info
}
MSG_KEYWORDS = {
    "error":   ["無法", "不能", "錯誤", "失敗"],
    "warn":    ["資金不足", "錢", "材料不足", "木材"],
    "success": ["開始", "完成", "成功", "收割", "賣出", "種植"],
}
