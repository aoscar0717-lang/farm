"""
夜巡農場 (Nightwatch Farm) - 核心配置
包含：5級農莊升級、10種農作物、13種莊園景觀、5秒強光冷卻、金庫防線與塔防。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict, Any


class GamePhase(Enum):
    DAY = "DAY"
    NIGHT = "NIGHT"


class ZoneType(Enum):
    FARM_ZONE = "FARM_ZONE"              # 中央：純色高架農田
    DECORATION_ZONE = "DECORATION_ZONE"  # 四周：純色莊園景觀區


class CropType(Enum):
    WHITE_RADISH = "WHITE_RADISH"        # 白蘿蔔 (Lv.1)
    RED_TOMATO = "RED_TOMATO"            # 紅番茄 (Lv.1)
    SWEET_CORN = "SWEET_CORN"            # 香甜玉米 (Lv.2)
    CARROT = "CARROT"                    # 胡蘿蔔 (Lv.2)  -- 原 CRYSTAL_EGGPLANT (紫晶茄子) 改名
    SWEET_STRAWBERRY = "SWEET_STRAWBERRY"# 鮮甜草莓 (Lv.2)
    MAGIC_PUMPKIN = "MAGIC_PUMPKIN"      # 魔法南瓜 (Lv.3)
    BLUEBERRY = "BLUEBERRY"              # 藍莓 (Lv.3)     -- 原 CRISP_WATERMELON (冰爽西瓜) 改名
    WHEAT = "WHEAT"                      # 小麥 (Lv.3)     -- 原 GOLDEN_SUNFLOWER (金黃向日葵) 改名
    ROYAL_GRAPE = "ROYAL_GRAPE"          # 皇家紫葡萄 (Lv.4)
    STARLIGHT_FRUIT = "STARLIGHT_FRUIT"  # 永恆星光果 (Lv.5)
    # 系統大重構 Phase 7：取代原本的 MINE（礦場）建築成為 metal_ore 的
    # 新來源——礦場被移除後，metal_ore 完全沒有任何產出管道，熔爐
    # (FURNACE) 的「metal_ore x2 -> metal_ingot」配方會直接卡死。改用
    # 「種在田裡的作物」取代「蓋在莊園景觀區的建築」來產出同一種原料，
    # 這是使用者這次明確要求的設計方向（"以全新的「富鐵花」取代原本的
    # 「礦場」"），不是我自己的取捨。
    IRON_FLOWER = "IRON_FLOWER"          # 富鐵花 (Lv.3)：採收後產出 metal_ore，不是金幣


class CropStage(Enum):
    SEED = "SEED"
    SPROUT = "SPROUT"
    GROWING = "GROWING"
    MATURE = "MATURE"
    STOLEN = "STOLEN"


class DecorationType(Enum):
    STONE_PATH = "STONE_PATH"            # 石板花徑
    FLOWER_BED = "FLOWER_BED"            # 鮮花花壇
    GARDEN_BENCH = "GARDEN_BENCH"        # 休閒木長椅
    PINE_TREE = "PINE_TREE"              # 莊園松柏樹
    APPLE_TREE = "APPLE_TREE"            # 蘋果果樹
    SOUL_LANTERN = "SOUL_LANTERN"        # 守護路燈
    SAKURA_TREE = "SAKURA_TREE"          # 浪漫櫻花樹
    BIRD_BATH = "BIRD_BATH"              # 石砌鳥浴水盆
    ANCIENT_STATUE = "ANCIENT_STATUE"    # 莊園雕像
    PET_HOUSE = "PET_HOUSE"              # 寵物小屋
    CRYSTAL_FOUNTAIN = "CRYSTAL_FOUNTAIN"# 圓形噴泉
    SUNDIAL_TOWER = "SUNDIAL_TOWER"      # 天使日晷鐘塔
    WINDMILL = "WINDMILL"                # 彩虹風車磨坊


class DefenseType(Enum):
    WOODEN_FENCE = "WOODEN_FENCE"        # 刺藤木柵
    BEAR_TRAP = "BEAR_TRAP"              # 鋼鐵捕獸夾
    SCARECROW = "SCARECROW"              # 農田稻草人
    BEEHIVE = "BEEHIVE"                  # 蜜蜂守衛巢


class BuildingType(Enum):
    """【Phase 1 預留】生產線建築常數。這一階段只先把「有哪些建築」的
    類型定義出來，讓 game_state.py 的訂單/資源系統可以先假設這些建築
    未來會存在；實際「怎麼把它們放到農田/莊園格子上、怎麼把原料轉換成
    產物」的邏輯（例如 FURNACE 把 metal_ore 煉成 metal_ingot）刻意
    不在本次改動範圍內，留給下一階段的建築放置系統一起做。
    【視覺升級：熔爐 Sprite Sheet 動畫階段，整批移除 OVEN / KILN】
    使用者確認熔爐貼圖+動畫做好之後，決定直接整個砍掉 OVEN（烤箱）跟
    KILN（炭窯）這兩個建築，含衍生邏輯——不是只從建造選單隱藏。KILN
    被砍掉之後，木炭 (charcoal) 完全沒有任何生產來源了，連帶讓 FURNACE
    原本「metal_ore + charcoal -> metal_ingot」的配方裡 charcoal 這個
    原料變成永遠拿不到、卡死配方，所以這裡把 FURNACE 的配方一併改成
    只需要 metal_ore（見下方 BUILDING_DATA 的說明），讓「礦場產
    metal_ore -> 熔爐煉 metal_ingot」這條生產鏈維持完整可用，不會因為
    拿掉 KILN 而斷鏈。"""
    FURNACE = "FURNACE"                  # 熔爐：金屬礦 -> 金屬錠
    HAMSTER_WHEEL = "HAMSTER_WHEEL"      # 倉鼠滾輪：消耗糧食產生電池/科技點數（下一階段）
    # Phase 4 新增：被動永久生效的自動化農業科技，跟熔爐這種「開關-配方
    # -倒數」機台是完全不同的互動模型（見 BUILDING_DATA 裡的說明）。
    SPRINKLER = "SPRINKLER"              # 自動灑水器：加速周圍 3x3 作物生長
    AUTO_HARVESTER = "AUTO_HARVESTER"    # 自動採收機：自動採收周圍 3x3 成熟作物
    # Phase 4.5 新增：最上游的基礎原料生產設施，「純資本工業流」——花
    # 金幣蓋下去、開關切成 ON，之後不消耗任何原料、無限期自動產出。
    # 走的仍然是熔爐那套「開關-配方-倒數」模型 (is_active/
    # is_processing)，只是 recipe 是空字典（見 BUILDING_DATA 說明）。
    LUMBERYARD = "LUMBERYARD"            # 伐木場：無消耗，定期產出 wood
    # 【系統更新：藍頂木屋 2x2 建築】使用者要求把 decorations/House_1_
    # Wood_Base_Blue.png 這張圖實作成一棟「完整的 2x2 建築」，明確指定
    # 要用 BUILDING_DATA（而不是既有的 DecorationType/DECORATION_DATA
    # 系統）——但這張同一張圖其實在更早的任務裡已經被拿來重新蒙皮
    # DecorationType.WINDMILL（商店卡片顯示為「莊園木屋」，1x1，
    # +220繁榮/+66G/天 被動收益），架構上是完全不同的兩套系統：
    # Decoration 一律 1x1、沒有 "size" 欄位、靠 tile.decoration.
    # prosperity_score 貢獻 recalculate_prosperity() 帶動莊園等級跟
    # 每日金幣分紅；Building 才支援多格 "size"、開關/配方/被動效果，
    # 但完全沒有對應的「被動繁榮/金幣分紅」機制。這裡照使用者的字面
    # 需求新增一個獨立的 BuildingType.BLUE_WOOD_HOUSE，讓它成為貨真
    # 價實的 2x2 建築（見下方 BUILDING_DATA 定義），不去動既有的
    # WINDMILL 裝飾——兩者會共用同一張來源圖但屬於商店裡兩張不同的
    # 卡片（「莊園木屋」1x1 裝飾 vs.「藍頂木屋」2x2 建築），是刻意保留
    # 的設計，不是重複資料的疏漏。因為 Building 系統目前沒有被動繁榮/
    # 金幣分紅的介面，這棟「藍頂木屋」建築本身不會複製 WINDMILL 那組
    # +220繁榮/+66G/天 的效果，純粹是一棟裝飾用途的 2x2 建築（走跟
    # AUTO_HARVESTER 一樣的 passive_effect 分支、但完全不做任何事，
    # 見 BUILDING_DATA 的 "passive_effect": "STATIC" 說明）——如果日後
    # 需要讓它也產生被動收益，需要另外幫 Building 系統補上對應機制，
    # 不在本次改動範圍內。
    BLUE_WOOD_HOUSE = "BLUE_WOOD_HOUSE"  # 藍頂木屋：純裝飾用途的 2x2 建築
    # 系統大重構 Phase 7：MINE（礦場）整批移除——使用者要求以全新的
    # 「富鐵花」(CropType.IRON_FLOWER) 農作物取代，metal_ore 改由採收
    # 富鐵花取得，不再由建築產出。詳見 CROP_DATA[IRON_FLOWER] 與
    # GameState.harvest_crop() 的說明。


class EnemyType(Enum):
    THIEF = "THIEF"                      # 敏捷小偷
    WILD_BOAR = "WILD_BOAR"              # 狂暴野豬
    SHADOW_BAT = "SHADOW_BAT"            # 暗夜魔蝠
    BOSS_BOAR_KING = "BOSS_BOAR_KING"    # 【血月首領】野豬巨獸


class EnemyState(Enum):
    SPAWNING = "SPAWNING"
    MOVING = "MOVING"
    STUNNED = "STUNNED"
    ACTING = "ACTING"
    FLEEING = "FLEEING"
    DEAD = "DEAD"


class DogState(Enum):
    PATROL = "PATROL"
    CHASING = "CHASING"
    ATTACKING = "ATTACKING"
    COMMANDED = "COMMANDED"
    RETURNING = "RETURNING"


class EventType(Enum):
    PHASE_CHANGED = "PHASE_CHANGED"
    DAY_STARTED = "DAY_STARTED"
    NIGHT_STARTED = "NIGHT_STARTED"
    BLOOD_MOON_WARNING = "BLOOD_MOON_WARNING"
    DAILY_TAX_PAID = "DAILY_TAX_PAID"
    PROSPERITY_DIVIDEND = "PROSPERITY_DIVIDEND"
    VAULT_RAIDED = "VAULT_RAIDED"
    
    CROP_PLANTED = "CROP_PLANTED"
    CROP_GROW_STAGE = "CROP_GROW_STAGE"
    CROP_MATURED = "CROP_MATURED"
    CROP_HARVESTED = "CROP_HARVESTED"
    CROP_WATERED = "CROP_WATERED"
    
    DECORATION_PLACED = "DECORATION_PLACED"
    DEFENSE_PLACED = "DEFENSE_PLACED"
    PET_BOUGHT = "PET_BOUGHT"
    CAT_BONUS = "CAT_BONUS"
    
    FARM_LEVEL_UP = "FARM_LEVEL_UP"
    FARM_LEVEL_DOWN = "FARM_LEVEL_DOWN"
    
    ENEMY_SPAWNED = "ENEMY_SPAWNED"
    ENEMY_STUNNED = "ENEMY_STUNNED"
    ENEMY_DAMAGED = "ENEMY_DAMAGED"
    ENEMY_DEFEATED = "ENEMY_DEFEATED"
    TRAP_TRIGGERED = "TRAP_TRIGGERED"
    SCARECROW_SCARE = "SCARECROW_SCARE"
    BEE_ATTACK = "BEE_ATTACK"
    DOG_BARK = "DOG_BARK"
    DOG_ATTACK = "DOG_ATTACK"
    DOG_WHISTLE = "DOG_WHISTLE"
    
    CROP_STOLEN = "CROP_STOLEN"
    FENCE_ATTACKED = "FENCE_ATTACKED"
    FENCE_DESTROYED = "FENCE_DESTROYED"
    TILE_CLEARED = "TILE_CLEARED"

    ORDERS_GENERATED = "ORDERS_GENERATED"
    ORDER_FULFILLED = "ORDER_FULFILLED"

    BUILDING_PLACED = "BUILDING_PLACED"
    BUILDING_STARTED = "BUILDING_STARTED"
    BUILDING_COLLECTED = "BUILDING_COLLECTED"
    # Phase 3：開關式自動化新增的事件。BUILDING_READY（Phase 2 的「完成
    # 待手動採收」通知）已經不會再被 emit——完成的當下直接自動採收，
    # 併進 BUILDING_COLLECTED 裡了，但列舉值本身保留不刪，避免任何
    # 還沒重新載入的舊程式碼/測試對到不存在的 enum 成員而噴例外。
    BUILDING_READY = "BUILDING_READY"
    BUILDING_TOGGLED = "BUILDING_TOGGLED"
    BUILDING_STOPPED = "BUILDING_STOPPED"

    GAME_OVER = "GAME_OVER"



# ==========================================
# 數值平衡設定
# ==========================================

MAP_CONFIG = {
    "GRID_WIDTH": 15,   # 原本 18，裁 3 格換取格子等比放大 (50px -> 60px)，
                        # 最後 1 格是犧牲右側景觀區換商店寬度 (294px)
    "GRID_HEIGHT": 11,  # 原本 13，裁 2 行同上
    # 農田範圍往左移 1 格 (原本 4-13)，搭配寬度縮減，讓左右佈景邊界維持
    # 對稱（各 3 格），不是單純從右邊硬砍。GRID_WIDTH/HEIGHT 只會從右側/
    # 下側裁切（兩者都是絕對格子座標），要維持左右對稱就得同步調整
    # FARM_X_RANGE 起點；高度是從下方裁，起點不用動就能維持上下對稱。
    "FARM_X_RANGE": (3, 12),
    "FARM_Y_RANGE": (2, 8),
    "VAULT_POS": (8, 5),
    "DAY_DURATION": 20.0,
    "DAY_1_DURATION": 30.0,     # 第 1 天給予 30 秒充裕時間供新手閱讀引導與播種
    "NIGHT_DURATION": 18.0,
    "INITIAL_GOLD": 300,
    "DAILY_TAX_BASE": 15,
    "DAILY_TAX_PER_DAY": 5,
    "PROSPERITY_DIVIDEND_RATE": 0.3,  # 每點繁榮度、每天清晨結算發放的分紅金幣

    "FLASHLIGHT_COOLDOWN": 3.0,  # 3 秒強光手電筒冷卻時間
}


# ==========================================
# 生產線 / 科技樹 終局系統 (Phase 1：資源背包 + 每日訂單)
# ==========================================

# 除了金幣以外的原料/半成品資源種類。這一階段只先建立「有這些資源、
# 數量從 0 開始」的背包欄位，實際「怎麼取得 wood/charcoal/metal_ore」
# （採集？副產物？）與「怎麼用 FURNACE/OVEN 把它們加工成
# metal_ingot/bread」的邏輯是下一階段建築放置系統要做的事，本次不實作。
# 視覺升級：熔爐動畫階段整批移除 OVEN/KILN 之後，"bread"（只有 OVEN
# 產出）跟 "charcoal"（只有 KILN 產出、FURNACE 舊配方消耗）已經沒有
# 任何建築會讀寫這兩個 key，一併從 RESOURCE_KEYS 移除，不留兩個永遠
# 卡在 0、沒有意義的背包欄位。
RESOURCE_KEYS = ["wood", "metal_ore", "metal_ingot", "battery"]

# 訂單需求裡用來指定「要交多少個某種作物」的簡短代稱，對應到實際的
# CropType。用簡短代稱（而不是直接用 CropType.value，例如 RED_TOMATO）
# 是因為訂單資料本來就該是「玩家看得懂的簡單字串」，且部分作物的
# enum 名稱跟中文顯示名稱其實對不太上（例如 CARROT 顯示成「紅蘿蔔」、
# ROYAL_GRAPE 顯示成「櫻桃小蘿蔔」——歷史命名緣故），直接用 enum 名稱
# 當訂單 key 反而更容易搞混，所以額外建一份對照表。
ORDER_CROP_ALIASES: Dict[str, "CropType"] = {
    "radish": CropType.WHITE_RADISH,
    "tomato": CropType.RED_TOMATO,
    "corn": CropType.SWEET_CORN,
    "carrot": CropType.CARROT,
    "strawberry": CropType.SWEET_STRAWBERRY,
    "pumpkin": CropType.MAGIC_PUMPKIN,
    "blueberry": CropType.BLUEBERRY,
    "wheat": CropType.WHEAT,
    "grape": CropType.ROYAL_GRAPE,
    "starlight": CropType.STARLIGHT_FRUIT,
}

ORDER_CONFIG = {
    "MIN_ORDERS_PER_DAY": 1,
    "MAX_ORDERS_PER_DAY": 3,
    "MIN_ITEM_KINDS": 1,          # 每張訂單最少要求幾種不同的作物
    "MAX_ITEM_KINDS": 2,          # 每張訂單最多要求幾種不同的作物
    "MIN_QTY_PER_ITEM": 2,
    "MAX_QTY_PER_ITEM": 6,
    # reward_gold 的算法：Σ(單項數量 × 該作物 harvest_reward) × 這個比例，
    # 四捨五入取整。比例故意設在 1.0 以下（訂單換算成金幣比直接採收
    # 賣掉的報酬略低），這樣訂單系統的價值主要來自 reward_tech（科技
    # 點數只能透過訂單取得，形成「用作物換終局進度」的核心迴圈），而不
    # 是變成比直接採收還划算的純金幣農場，破壞既有的採收經濟平衡。
    "GOLD_REWARD_RATIO": 0.55,
    "TECH_REWARD_BASE": 5,        # 每張訂單至少給的科技點數
    "TECH_REWARD_PER_ITEM_KIND": 4,  # 每多一種需求作物，科技點數額外 +N（含隨機微調）
}



FARM_LEVELS = {
    1: {"name": "初級農莊", "min_prosperity": 0, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO]},
    2: {"name": "興旺莊園", "min_prosperity": 40, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY]},
    3: {"name": "繁花莊園", "min_prosperity": 100, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.BLUEBERRY, CropType.WHEAT, CropType.IRON_FLOWER]},
    4: {"name": "璀璨莊園", "min_prosperity": 200, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.BLUEBERRY, CropType.WHEAT, CropType.IRON_FLOWER, CropType.ROYAL_GRAPE]},
    5: {"name": "傳奇仙境", "min_prosperity": 350, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.BLUEBERRY, CropType.WHEAT, CropType.IRON_FLOWER, CropType.ROYAL_GRAPE, CropType.STARLIGHT_FRUIT]},
}

CROP_DATA = {
    CropType.WHITE_RADISH: {
        "name": "白蘿蔔",
        "unlock_level": 1,
        "seed_cost": 10,
        "grow_time": 4.0,
        "harvest_reward": 18,
        "theft_gold_loss": 15,
        "asset_key": "radish",
    },
    CropType.RED_TOMATO: {
        "name": "紅番茄",
        "unlock_level": 1,
        "seed_cost": 20,
        "grow_time": 6.0,
        "harvest_reward": 38,
        "theft_gold_loss": 25,
        "asset_key": "tomato",
    },
    CropType.SWEET_CORN: {
        "name": "香甜玉米",
        "unlock_level": 2,
        "seed_cost": 40,
        "grow_time": 10.0,
        "harvest_reward": 88,
        "theft_gold_loss": 50,
        "asset_key": "corn",
    },
    CropType.CARROT: {
        "name": "紅蘿蔔",  # 原「胡蘿蔔」的「胡」不在精簡字型子集裡，會顯示成缺字方塊，改用同義的常見別名
        "unlock_level": 2,
        "seed_cost": 55,
        "grow_time": 12.0,
        "harvest_reward": 130,
        "theft_gold_loss": 65,
        "asset_key": "carrot",
    },
    CropType.SWEET_STRAWBERRY: {
        "name": "漿果灌木",
        "unlock_level": 2,
        "seed_cost": 70,
        "grow_time": 14.0,
        "harvest_reward": 175,
        "theft_gold_loss": 85,
        "asset_key": "strawberry",
    },
    CropType.MAGIC_PUMPKIN: {
        "name": "魔法南瓜",
        "unlock_level": 3,
        "seed_cost": 90,
        "grow_time": 16.0,
        "harvest_reward": 240,
        "theft_gold_loss": 110,
        "asset_key": "pumpkin",
    },
    CropType.BLUEBERRY: {
        "name": "藍莓",
        "unlock_level": 3,
        "seed_cost": 110,
        "grow_time": 18.0,
        "harvest_reward": 310,
        "theft_gold_loss": 140,
        "asset_key": "blueberry",
    },
    CropType.WHEAT: {
        "name": "小麥",
        "unlock_level": 3,
        "seed_cost": 130,
        "grow_time": 20.0,
        "harvest_reward": 380,
        "theft_gold_loss": 160,
        # 沒有新的小麥素材，asset_key 先保留 "sunflower"，繼續沿用原本
        # 向日葵的圖（seed/sprout/growing/mature 都還是舊圖），只有名稱
        # 顯示改成「小麥」。之後如果有真的小麥素材，把這裡改成新的
        # asset_key，並在 asset_loader.py 補上對應圖檔即可。
        "asset_key": "sunflower",
    },
    # 系統大重構 Phase 7：富鐵花，取代 MINE（礦場）成為 metal_ore 的
    # 產出來源。跟其餘 10 種作物最大的不同是採收後不直接給金幣、而是
    # 給原料背包物品——harvest_reward 刻意設為 0，實際輸出改在
    # GameState.harvest_crop() 裡讀 output_key/output_qty 這兩個新欄位
    # 特別處理（其餘 10 種作物都沒有這兩個欄位，harvest_crop() 對它們
    # 的行為完全不變）。unlock_level 訂為 3，跟 FURNACE（熔爐，也是
    # unlock_level 3）同一階解鎖，確保玩家蓋得起熔爐的那一刻，田裡也已
    # 經能種富鐵花取得 metal_ore 原料，不會出現「熔爐蓋好了但沒有任何
    # 管道取得 metal_ore」的斷鏈空窗期。seed_cost/grow_time 直接採用
    # 使用者規格給的 150 / 15.0；theft_gold_loss 沿用其餘作物「約
    # seed_cost 的 1.2~1.27 倍」這個既有比例抓 185（150*1.233≈185），
    # 即使富鐵花被偷不會讓玩家平白損失原料產出的邏輯意義，也要有個跟
    # 其他作物一致、合理的「失竊代價」數字，不留 0 這種特例。
    CropType.IRON_FLOWER: {
        # 【系統修復與文本重構】原本充滿工業感的「富鐵花」改名為
        # 「晨露高麗菜」，呼應遊戲從「硬派外星求生」轉型為「溫馨奇幻
        # 農場」的世界觀；CropType.IRON_FLOWER 這個 enum 成員本身、
        # output_key（仍是 metal_ore）都維持不變，只換玩家看得到的
        # 名稱，理由跟下面 asset_key 保留 "iron_flower" 相同——這是
        # 內部識別字，不是玩家看到的文字，改了反而會牽動存檔相容性、
        # asset_loader.py 的貼圖 key、測試等一大串跟這次「文本替換」
        # 無關的東西。
        # 【使用者回饋：熔爐/伐木場/富鐵花 保留】上一版把「富鐵花」改名
        # 成「晨露高麗菜」，這次使用者明確要求把這三個名字改回原本的
        # 「熔爐/伐木場/富鐵花」——只還原名稱本身，其餘（商店卡片描述、
        # 其他名詞的溫馨化文本、劇情、任務引導）維持上一版的修改。
        "name": "富鐵花",
        "unlock_level": 3,
        "seed_cost": 150,
        "grow_time": 15.0,
        "harvest_reward": 0,
        "theft_gold_loss": 185,
        "output_key": "metal_ore",
        "output_qty": 1,
        # 使用者說明會在本地端自行對應 16x16 Sprite Sheet 檔名，這裡先
        # 用跟其餘作物一致的命名慣例（asset_loader.py 的
        # crops 清單會用這個 key 去找 crops/iron_flower_{stage}.png），
        # 檔案還沒放進 assets/ 時，AssetLoader._load_image() 既有的
        # generate_placeholder() 後備機制會自動生成一張有底色區分的
        # 佔位圖，不會讓遊戲壞掉——這就是規格裡要求的「安全圖檔路徑」。
        "asset_key": "iron_flower",
    },
    CropType.ROYAL_GRAPE: {
        "name": "櫻桃小蘿蔔",
        "unlock_level": 4,
        "seed_cost": 160,
        "grow_time": 22.0,
        "harvest_reward": 490,
        "theft_gold_loss": 200,
        "asset_key": "grape",
    },
    CropType.STARLIGHT_FRUIT: {
        "name": "星光大南瓜",
        "unlock_level": 5,
        "seed_cost": 280,
        "grow_time": 28.0,
        "harvest_reward": 950,
        "theft_gold_loss": 350,
        "asset_key": "starlight",
    }
}

DECORATION_DATA = {
    DecorationType.STONE_PATH: {
        "name": "石板花徑",
        "cost": 20,
        "prosperity_score": 10,
        "walkable": True,
        "asset_key": "stone_path",
    },
    DecorationType.FLOWER_BED: {
        "name": "鮮花花壇",
        "cost": 35,
        "prosperity_score": 20,
        "walkable": True,
        "asset_key": "flower_bed",
    },
    DecorationType.GARDEN_BENCH: {
        "name": "休閒木長椅",
        "cost": 45,
        "prosperity_score": 30,
        "walkable": True,
        "asset_key": "garden_bench",
    },
    DecorationType.PINE_TREE: {
        "name": "莊園松柏樹",
        "cost": 50,
        "prosperity_score": 35,
        "walkable": True,
        "asset_key": "pine_tree",
    },
    DecorationType.APPLE_TREE: {
        "name": "蘋果果樹",
        "cost": 60,
        "prosperity_score": 40,
        "walkable": True,
        "asset_key": "apple_tree",
    },
    DecorationType.SOUL_LANTERN: {
        "name": "守護路燈",
        "cost": 75,
        "prosperity_score": 50,
        "walkable": True,
        "asset_key": "soul_lantern",
    },
    DecorationType.SAKURA_TREE: {
        "name": "浪漫櫻花樹",
        "cost": 85,
        "prosperity_score": 55,
        "walkable": True,
        "asset_key": "sakura_tree",
    },
    DecorationType.BIRD_BATH: {
        "name": "石砌鳥浴水盆",
        "cost": 95,
        "prosperity_score": 65,
        "walkable": True,
        "asset_key": "bird_bath",
    },
    DecorationType.ANCIENT_STATUE: {
        "name": "莊園雕像",
        "cost": 110,
        "prosperity_score": 75,
        "walkable": True,
        "asset_key": "ancient_statue",
    },
    DecorationType.PET_HOUSE: {
        "name": "寵物小屋",
        "cost": 130,
        "prosperity_score": 90,
        "walkable": True,
        "asset_key": "pet_house",
    },
    DecorationType.CRYSTAL_FOUNTAIN: {
        "name": "圓形噴泉",
        "cost": 160,
        "prosperity_score": 110,
        "walkable": True,
        "asset_key": "fountain",
    },
    DecorationType.SUNDIAL_TOWER: {
        "name": "天使日晷鐘塔",
        "cost": 220,
        "prosperity_score": 160,
        "walkable": True,
        "asset_key": "sundial_tower",
    },
    # 【系統邏輯修正：讓藍頂木屋繼承並替換原有的「莊園木屋」】使用者確認
    # 最終需求是「藍頂木屋直接取代並繼承莊園木屋的所有資料與功能」，不是
    # 單純隱藏——但 Decoration 系統架構上就是每格固定 1x1（DECORATION_DATA
    # 完全沒有 "size" 欄位，place_decoration() 也只會佔用單一格），沒辦法
    # 直接把這筆資料改成 2x2；2x2 的「繼承者」已經是新增的
    # BuildingType.BLUE_WOOD_HOUSE（見下方 BUILDING_DATA，這次補上原本
    # 屬於這裡的 unlock_level/cost/prosperity_score，讓它真正繼承莊園
    # 木屋的資料與功能）。這裡把原本的 DecorationType.WINDMILL 這筆
    # BUILDING_DATA 設定註解掉（不是刪除 DecorationType.WINDMILL 這個
    # enum 成員本身），做法比照先前 AUTO_HARVESTER 隱藏時的「只註解掉
    # 資料/商店卡片，enum 成員跟其餘參照程式碼不動」慣例，避免商店裡
    # 同時看到「莊園木屋」跟「藍頂木屋」兩張外觀相同但機制不同的卡片。
    # DecorationType.WINDMILL: {
    #     "name": "彩虹風車磨坊",
    #     "cost": 300,
    #     "prosperity_score": 220,
    #     "walkable": True,
    #     "asset_key": "windmill",
    # }
}

DEFENSE_DATA = {
    DefenseType.WOODEN_FENCE: {
        "name": "刺藤木柵",
        "cost": 15,
        "max_hp": 80.0,
        "walkable": False,
        "asset_key": "wooden_fence",
    },
    DefenseType.BEAR_TRAP: {
        "name": "鋼鐵捕獸夾",
        "cost": 20,
        # 從「一次性大傷害後失效」改成永久性的持續傷害 (DoT) 陷阱：
        # damage 現在的單位是「每秒傷害 (DPS)」，不是一次性爆發傷害，
        # 敵人只要站在陷阱格上就會每幀持續受傷 (見 DefenseStructure.
        # tick_trap_damage())。原本一次性 120 傷害調降成 15 DPS，站
        # 滿 1 秒的總傷害量大約是原本的 1/8，但陷阱永久有效，敵人如果
        # 停留在原地（例如被其他敵人卡住路徑）會持續流血，長期蹲一個
        # 陷阱格反而更痛。
        "damage": 15,
        # 持續傷害的視覺/音效脈動間隔（秒）：實際扣血還是每幀照 dt
        # 精確計算、不受這個值影響，這個只是節流「觸發特效」的頻率，
        # 避免 60 FPS 下每一幀都噴粒子跟浮動文字，畫面會爆炸。
        "dot_tick_interval": 0.4,
        "walkable": True,
        "asset_key": "bear_trap",
    },
    DefenseType.SCARECROW: {
        "name": "農田稻草人",
        "cost": 35,
        "scare_radius": 1.5,  # 原本 3.0，縮小為一半
        "walkable": False,
        "asset_key": "scarecrow",
    },
    DefenseType.BEEHIVE: {
        "name": "蜜蜂守衛巢",
        "cost": 85,
        "attack_range": 2.0,  # 原本 4.0，縮小為一半
        "attack_power": 18,
        "attack_cooldown": 1.2,
        "walkable": False,
        "asset_key": "beehive",
    }
}


# ==========================================
# 加工建築 (Phase 2：生產線機台)
# ==========================================
# 只實作 BuildingType 裡的 FURNACE 一種（HAMSTER_WHEEL 維持
# Phase 1 就說明過的「留給下一階段」，這次仍然不動它）。
#
# recipe 的 key 沿用訂單系統已經在用的同一份物品命名空間：crop 用
# ORDER_CROP_ALIASES 的簡短代稱（"wheat"）、原料/半成品用 RESOURCE_KEYS
# 的名稱（"metal_ore"/"metal_ingot"/...），兩邊沒有重複的 key，可以直接
# 共用 GameState._get_item_count()/_consume_item()（訂單系統 Phase 1
# 就寫好的通用查詢/扣除工具），不用另外為建築寫一份查庫存邏輯。
#
# 【視覺升級：熔爐動畫階段，整批移除 OVEN/KILN 後的配方調整】
# 原本 FURNACE 的配方是「metal_ore + charcoal -> metal_ingot」，charcoal
# 唯一的生產來源是 KILN（炭窯）。使用者這次要求把 OVEN、KILN 連同衍生
# 邏輯整個刪除，KILN 一拿掉，charcoal 就變成永遠拿不到的原料，FURNACE
# 的配方會卡死、玩家永遠煉不出 metal_ingot。這裡把配方改成單純
# 「metal_ore -> metal_ingot」（份量從 1 調成 2，維持原本「用兩份上游
# 資源換一份精煉物」的比例感，process_time 維持 20 秒不變），讓
# 「礦場產 metal_ore -> 熔爐煉 metal_ingot -> 灑水器/自動採收機」這條
# 生產鏈不必依賴任何已經被刪除的建築。
BUILDING_DATA = {
    BuildingType.FURNACE: {
        # 【系統修復與文本重構】「熔爐」改名為「磚造烤窯」，enum 成員
        # BuildingType.FURNACE、recipe（metal_ore x2 -> metal_ingot）
        # 都維持不變，只換名稱文字。
        # 【使用者回饋：熔爐/伐木場/富鐵花 保留】名稱改回原本的「熔爐」。
        "name": "熔爐",
        "unlock_level": 3,
        "build_cost_gold": 200,
        "build_cost_tech": 18,
        "recipe": {"metal_ore": 2},
        "output_key": "metal_ingot",
        "output_qty": 1,
        "process_time": 20.0,
        "walkable": False,
        "asset_key": "furnace",
        # 系統大重構 Phase 7：蒸汽龐克風 Sprite Sheet 改成 2x2 尺寸。
        # 這是新增欄位，沒有 "size" 的建築（SPRINKLER/AUTO_HARVESTER）
        # 在讀取端一律用 .get("size", (1, 1)) 取值，維持原本的 1x1 footprint，
        # 不用把這個欄位補到每一個建築定義上。
        "size": (2, 2),
    },
    # Phase 4：自動化農業科技。跟烤箱/熔爐不同，這兩種機台「蓋下去就
    # 永久被動生效」，完全不需要 is_active/is_processing 那套開關-配方-
    # 倒數循環，所以 BUILDING_DATA 裡刻意不給它們 recipe/output_key/
    # process_time 這幾個 Phase 2/3 專屬的欄位——GameState._update_buildings()
    # 會先看 "passive_effect" 這個 key 決定要不要整個跳過開關式自動化
    # 邏輯，兩者互不干擾。build_cost_items 是這裡新增的欄位：跟
    # build_cost_gold/build_cost_tech 一樣是「建造時一次性扣除」，但
    # 扣的是背包物品（這裡固定是 metal_ingot）而不是金幣/科技點數，
    # place_building() 已經改成通用邏輯，任何建築只要在這裡填了
    # build_cost_items 就會被檢查/扣除，不用另外為這兩種機台寫專用
    # 分支。
    #
    # 【原「已知限制」已隨生產鏈補齊而解除】metal_ingot 現在的取得管道
    # 是：礦場 (MINE) 產 metal_ore -> 熔爐 (FURNACE) 消耗 metal_ore
    # 煉出 metal_ingot，兩者都已經是可以直接蓋、可以直接運作的建築，
    # 不再是「摸不到」的狀態。
    # 【系統更新：自動灑水器 2x2 建築邏輯】SPRINKLER 這次從「蓋下去就
    # 永久被動生效、沒有開關」的模型（Phase 4 原始設計，見下面
    # "toggleable" 這個新欄位的說明）改成「跟 FURNACE/LUMBERYARD 一樣
    # 可以開關、需要玩家手動啟動才會運作」，同時佔地從 1x1 放大成
    # 2x2、加成方式從「每幀持續疊加生長速度」改成「每隔一段時間對周圍
    # 作物一次性『自動澆水』」——三項改動理由分別是：
    #   1. size=(2,2)：呼應新的 1x4 Sprite Sheet 素材（灑水器.png），
    #      跟 FURNACE/LUMBERYARD 用同一套 2x2 footprint 規格。
    #   2. toggleable=True：新增的旗標，讓 Building.is_passive（見
    #      Building dataclass 的說明）在 SPRINKLER 身上回傳 False，
    #      GameState.toggle_building() 因此不會再擋下玩家對它的點擊
    #      開關——AUTO_HARVESTER 沒有這個旗標，維持原本「蓋下去就永久
    #      生效、點擊無效」的行為不變。
    #   3. 加成方式改成「週期性自動澆水」：GameState._update_buildings()
    #      的 SPRINKLER 分支現在只在 is_active=True 時才生效，每隔
    #      water_interval 秒對 effect_radius 範圍內每一格未成熟的作物
    #      各執行一次「自動版 water_crop()」（growth_timer 直接加上
    #      grow_time * water_boost_ratio，不扣金幣），並 emit 跟玩家
    #      手動點擊澆水壺完全相同的 EventType.CROP_WATERED 事件（沿用
    #      既有的 💧 浮動文字/音效 UI 回饋，不用另外寫一套）。這取代了
    #      舊版「每幀持續疊加 dt」的連續加成模型，也是舊版
    #      _get_sprinkler_boosted_tiles()/growth_bonus_dt_mult 這兩個
    #      東西在 game_state.py 裡被移除的原因。
    BuildingType.SPRINKLER: {
        "name": "自動灑水器",
        "unlock_level": 4,   # 比熔爐(3)高一階，符合「高階科技」的定位
        "build_cost_gold": 0,
        "build_cost_tech": 0,
        "build_cost_items": {"metal_ingot": 2},
        "recipe": {},  # 開關式機台的既有介面需要這個欄位（跟 LUMBERYARD
                        # 一樣「無消耗」），toggle_building() 開啟前的
                        # 原料預檢查會讀它；SPRINKLER 本身不會真的走
                        # is_processing/tick() 那套投料倒數迴圈（見下方
                        # passive_effect 分支的說明），純粹是介面相容。
        "passive_effect": "SPRINKLER",  # 仍然用來讓 _update_buildings()
                                          # 跳過一般開關機台的投料/倒數
                                          # 迴圈，改走自己專屬的週期性
                                          # 自動澆水分支。
        "toggleable": True,   # 新增旗標：跟 AUTO_HARVESTER 不同，這台
                               # 可以被玩家開關。
        "effect_radius": 1,   # 以自身為中心的 3x3（radius=1 代表左右
                               # 上下各 1 格；未來想擴大成 5x5 只要把這
                               # 個值改成 2）。
        "water_interval": 8.0,      # 每隔幾秒自動澆水一次
        "water_boost_ratio": 0.5,   # 每次澆水疊加 grow_time 的比例，
                                     # 跟玩家手動點擊 water_crop() 的
                                     # 加成幅度（grow_time * 0.5）一致。
        "walkable": False,
        "asset_key": "sprinkler",
        "size": (2, 2),
    },
    # 【系統邏輯更新：隱藏「收割機」建築】使用者確認目前不需要自動採收
    # 機，這裡整組 BUILDING_DATA 設定註解掉（不是刪除 BuildingType.
    # AUTO_HARVESTER 這個 enum 成員本身，也不動 game_state.py 裡
    # passive_effect == "AUTO_HARVESTER" 那個分支——之後想恢復，只要
    # 把這段取消註解、商店卡片那行也取消註解即可，不用重寫任何邏輯）。
    # 拿掉之後 place_building(x, y, BuildingType.AUTO_HARVESTER) 會因為
    # BUILDING_DATA 查不到這個 key 直接 KeyError——這是刻意的：商店卡片
    # 移除後玩家已經完全無法從 UI 觸發這個呼叫，如果還有任何程式碼路徑
    # 意外呼叫到它，直接讓它壞掉遠比「悄悄允許建造一個已經隱藏的建築」
    # 更安全，能第一時間發現問題而不是被吃掉。
    # BuildingType.AUTO_HARVESTER: {
    #     "name": "自動採收機",
    #     "unlock_level": 5,   # 比灑水器(4)更高階——「自動幫你賺錢」理應是最終期科技
    #     "build_cost_gold": 0,
    #     "build_cost_tech": 100,
    #     "build_cost_items": {"metal_ingot": 5},
    #     "passive_effect": "AUTO_HARVESTER",
    #     "effect_radius": 1,  # 同樣是以自身為中心的 3x3
    #     "scan_interval": 1.0,  # 每 1 秒掃描一次周圍成熟作物，不用每幀掃，省效能
    #     "walkable": False,
    #     "asset_key": "auto_harvester",
    # },
    # Phase 4.5：打通上游生產線。伐木場/礦場刻意沿用熔爐那套
    # 「開關-配方-倒數」模型（is_active/is_processing/toggle_building()/
    # GameState._update_buildings() 既有的那段迴圈），而不是像 SPRINKLER/
    # AUTO_HARVESTER 那樣走 passive_effect 分支——因為使用者的規格描述
    # 本來就是「ON 時自動投料、倒數、產出，循環不止；OFF 就停止」，這正
    # 好就是 Phase 3 開關式自動化的定義，唯一差別只在於「配方 (recipe)
    # 是空字典，不消耗任何東西」。GameState._update_buildings() 對
    # recipe 的處理本來就是「用 _check_recipe_shortfall(recipe) 檢查、
    # 不夠就不開始」——recipe={} 時這個檢查天生就會回傳空列表 (沒有任何
    # 項目需要檢查)，等於「永遠視為原料充足」，後面的
    # `for item_key, need_qty in recipe.items(): self._consume_item(...)`
    # 也因為 recipe 是空字典而完全不會執行、不扣任何東西。也就是說，
    # 完全不需要為這兩座建築寫任何特例分支，只要 recipe 給空字典，
    # 「無消耗、ON 了就會自動不斷循環生產」這個效果就會自動成立，跟
    # 熔爐共用同一套已經測試過、正確處理「這一輪跑完才停工」的
    # 邏輯，不會有第二套邏輯路徑需要單獨維護/單獨測試。
    #
    # 【視覺升級：熔爐動畫階段，KILN 已隨這次改動整個移除】木炭
    # (charcoal) 生產線（伐木場產 wood -> 炭窯燒成 charcoal）原本是
    # 為了配合 FURNACE「metal_ore + charcoal -> metal_ingot」的舊配方
    # 而在 Phase 4.75 補上的。這次使用者要求整個刪除 KILN，FURNACE 的
    # 配方也同步改成單純「metal_ore -> metal_ingot」（見上方 FURNACE
    # 定義），所以「伐木場產 wood」這個環節目前純粹是給玩家囤木頭用
    # （未來要接其他消耗 wood 的機制），不再是熔煉金屬錠這條生產鏈的
    # 必要前置——目前完整生產鏈簡化為「礦場產 metal_ore -> 熔爐煉
    # metal_ingot -> 灑水器/自動採收機」。
    BuildingType.LUMBERYARD: {
        # 【系統修復與文本重構】「伐木場」改名為「風車磨坊」，enum 成員
        # BuildingType.LUMBERYARD、output_key（仍是 wood）都維持不變，
        # 只換名稱文字。
        # 【使用者回饋：熔爐/伐木場/富鐵花 保留】名稱改回原本的「伐木場」。
        "name": "伐木場",
        "unlock_level": 1,   # 最基礎的原料來源，刻意設成遊戲一開局就能蓋，不卡關
        "build_cost_gold": 50,
        "build_cost_tech": 0,
        "recipe": {},              # 無消耗——見上方說明
        "output_key": "wood",
        "output_qty": 1,
        "process_time": 10.0,
        "walkable": False,
        "asset_key": "lumberyard",
        "size": (2, 2),  # 系統大重構 Phase 7：同 FURNACE，改成 2x2 佔地
    },
    # 【系統更新：藍頂木屋 2x2 建築】見上方 BuildingType.BLUE_WOOD_HOUSE
    # enum 成員的說明。走跟 AUTO_HARVESTER 相同的 "passive_effect" 分支
    # （GameState._update_buildings() 迴圈最前面看到 passive_effect 就
    # continue 跳過一般開關-配方-倒數邏輯），避免它去讀根本不存在的
    # "recipe"/"output_key" 而噴 KeyError；但 passive_effect 給的是全新
    # 值 "STATIC"（不是複用 "AUTO_HARVESTER"/"SPRINKLER"），
    # _update_buildings() 對應新增一個「什麼都不做、純粹跳過」的分支，
    # 確保這棟建築不會意外觸發自動採收/自動澆水的邏輯。沒有
    # "toggleable" 旗標，所以 Building.is_passive 為 True——渲染層
    # 因此不會畫 ON/OFF 指示燈/進度條（那些只對開關式機台有意義），
    # 玩家也不能點擊切換它，符合「純裝飾用途、蓋好就定住不動」的定位。
    # 【系統邏輯修正：讓藍頂木屋繼承並替換原有的「莊園木屋」】原本這棟
    # 建築是「純裝飾用途，不繼承任何被動收益」（見上一版註解），這次使用
    # 者明確要求要「繼承並替換」原本 DecorationType.WINDMILL（莊園木屋）
    # 的解鎖等級、價格、跟被動繁榮/金幣分紅功能，而不是只沿用外觀。
    #   - unlock_level：莊園木屋原本沒有 unlock_level 這個概念
    #     （DECORATION_DATA 裡沒有這個欄位，place_decoration() 只檢查
    #     金幣，不檢查等級），這裡維持 Lv.1（等同「沒有等級門檻」）。
    #   - build_cost_gold：莊園木屋原本的 "cost" 是 300，剛好跟藍頂木屋
    #     原本就有的 build_cost_gold 一致，不用調整金額。
    #   - "prosperity_score": 220：新增欄位，繼承莊園木屋原本的
    #     prosperity_score。Building 系統原本沒有這個概念（只有
    #     Decoration 才有），這次同步在 game_state.py
    #     recalculate_prosperity() 補上「也讀取 tile.building.config 的
    #     prosperity_score」這條路徑（見該函式的說明），讓這棟建築真正
    #     繼承「+220繁榮 -> 帶動每日金幣分紅」的完整功能，不是只有外觀
    #     沿用。
    BuildingType.BLUE_WOOD_HOUSE: {
        "name": "藍頂莊園木屋",
        "unlock_level": 1,
        "build_cost_gold": 300,
        "build_cost_tech": 0,
        "passive_effect": "STATIC",
        "prosperity_score": 220,
        "walkable": False,
        "asset_key": "blue_wood_house",
        "size": (2, 2),
    },
    # 系統大重構 Phase 7：BuildingType.MINE（礦場）連同這筆 BUILDING_DATA
    # 一併整批移除——使用者要求以全新的富鐵花 (CropType.IRON_FLOWER)
    # 農作物取代礦場成為 metal_ore 的產出來源，做法跟先前 OVEN/KILN
    # 的整批移除一致（不是只從商店隱藏，是連 enum 成員、資料、UI 卡片/
    # 點擊處理/鎖卡判定/圖示對照表全部刪乾淨）。
}

DOG_CONFIG = {
    "cost": 100,
    "speed": 1.8,  # 原本 3.0，調降為 0.6 倍 -- 追擊/指揮衝刺/返回崗位
                   # 三種移動都是從這個值乘出來的 (game_state.py 的
                   # _update_dog())，改這一個數字就整體等比例變慢。
    "detection_radius": 5.5,
    "attack_range": 0.9,
    "attack_power": 50,
    "attack_cooldown": 0.8,
    "home_pos": (8, 5),
    "asset_key": "guard_dog",
}

CAT_CONFIG = {
    "cost": 80,
    "speed": 1.5,
    "bonus_interval": 5.0,
    "bonus_gold": 12,
    "home_pos": (9, 5),
    "asset_key": "farm_cat",
}

ENEMY_DATA = {
    EnemyType.THIEF: {
        "name": "敏捷小偷",
        "max_hp": 60,
        "speed": 1.8,
        "fence_dps": 22.0,
        "action_duration": 1.2,
        "asset_key": "enemy_thief",
    },
    EnemyType.WILD_BOAR: {
        "name": "狂暴野豬",
        "max_hp": 160,
        "speed": 1.3,
        "fence_dps": 48.0,
        "action_duration": 1.5,
        "asset_key": "enemy_boar",
    },
    EnemyType.SHADOW_BAT: {
        "name": "暗夜魔蝠",
        "max_hp": 45,
        "speed": 2.2,
        "fence_dps": 10.0,
        "action_duration": 0.9,
        "asset_key": "enemy_bat",
    },
    EnemyType.BOSS_BOAR_KING: {
        "name": "【血月首領】野豬巨獸",
        "max_hp": 600,
        "speed": 0.85,
        "fence_dps": 85.0,
        "action_duration": 2.5,
        "asset_key": "boss_boar",
    }
}



# ==========================================
# 實體數據模型
# ==========================================

@dataclass
class Crop:
    crop_type: CropType
    growth_timer: float = 0.0
    stage: CropStage = CropStage.SEED
    is_moonlight_boosted: bool = False
    
    @property
    def config(self) -> dict:
        return CROP_DATA[self.crop_type]
    
    @property
    def grow_time(self) -> float:
        return self.config["grow_time"]
    
    @property
    def is_mature(self) -> bool:
        return self.stage == CropStage.MATURE
    
    def update_growth(self, dt: float) -> Optional[CropStage]:
        if self.stage in (CropStage.MATURE, CropStage.STOLEN):
            return None
        
        old_stage = self.stage
        self.growth_timer += dt
        ratio = self.growth_timer / self.grow_time
        
        if ratio >= 1.0:
            self.stage = CropStage.MATURE
        elif ratio >= 0.6:
            self.stage = CropStage.GROWING
        elif ratio >= 0.25:
            self.stage = CropStage.SPROUT
        else:
            self.stage = CropStage.SEED
            
        return self.stage if self.stage != old_stage else None


@dataclass
class Decoration:
    decoration_type: DecorationType
    
    @property
    def config(self) -> dict:
        return DECORATION_DATA[self.decoration_type]
    
    @property
    def prosperity_score(self) -> int:
        return self.config["prosperity_score"]
    
    @property
    def is_walkable(self) -> bool:
        return self.config["walkable"]


@dataclass
class DefenseStructure:
    defense_type: DefenseType
    # 舊版一次性捕獸夾用來記錄「已經觸發過、彈簧鬆了」的欄位。地刺陷阱
    # 改成永久性 DoT 之後不會再讀寫這個欄位，繼續保留是為了不動到既有
    # 存檔/資料結構（如果之後有存檔機制的話），沒有其他用途。
    is_armed: bool = True
    cooldown_timer: float = 0.0
    hp: float = 80.0
    max_hp: float = 80.0
    # 地刺陷阱 DoT 特效節流計時器：只用來控制「多久觸發一次視覺/音效
    # 脈動」，跟實際扣血量無關（扣血每幀都精確按 dt 計算）。預設 0，
    # 讓敵人一站上陷阱就立刻有第一次脈動回饋。
    dot_tick_timer: float = 0.0

    def __post_init__(self):
        self.max_hp = float(self.config.get("max_hp", 80.0))
        self.hp = self.max_hp

    @property
    def config(self) -> dict:
        return DEFENSE_DATA[self.defense_type]

    @property
    def is_walkable(self) -> bool:
        return self.config["walkable"]

    def tick_trap_damage(self, dt: float) -> float:
        """地刺陷阱是永久性設施，敵人每一幀站在陷阱格上就會受到持續
        傷害 (Damage over Time)。回傳這一幀應該造成的傷害量
        (每秒傷害 damage * dt)，乘上 dt 確保總傷害量不會因為 FPS
        高低而不穩定。跟舊版 trigger_trap() 不同，這裡不會把陷阱設成
        失效，陷阱會永久留在場上，直到玩家自己用鏟子拆除。"""
        if self.defense_type == DefenseType.BEAR_TRAP:
            return self.config["damage"] * dt
        return 0.0

    def take_damage(self, amount: float) -> bool:
        """Returns True if the defense structure is destroyed."""
        self.hp -= amount
        return self.hp <= 0.0


@dataclass
class Building:
    """加工機台實體（烤箱/熔爐）。跟 DefenseStructure 不同的地方是這裡
    額外存了 x/y——防禦設施只透過 tile.defense 反向存取，因為更新/渲染
    防禦時本來就是逐格掃 self.grid；但 Phase 2 的需求明確要求
    GameState 要有一個 self.buildings 陣列可以直接遍歷做每幀狀態更新
    (_update_buildings)，不用每幀重新掃一次整張地圖找機台，所以這裡
    採用「tile.building 反向參照 + self.buildings 陣列直接持有」雙軌
    並存的寫法：擺放/拆除時兩邊要同步增減，這件事全部封裝在
    GameState.place_building()/demolish_tile() 裡，UI 層跟其他呼叫端
    不用自己操心兩邊同步的問題。

    Phase 3 改成「開關式自動化」：is_active 是玩家點擊切換的開關，
    is_processing 是「這一輪配方是否正在倒數」——兩者刻意分開，這樣
    「玩家關閉開關時，正在跑的這一輪會自然跑完才真正停工」不需要額外
    的第三個旗標：tick() 完全不看 is_active，只看 is_processing 決定
    要不要繼續倒數；is_active 只在「這一輪跑完之後，還要不要自動開始
    下一輪」這件事上發揮作用，而這個判斷留給 GameState._update_buildings()
    做（因為要不要開始下一輪，取決於玩家背包夠不夠原料，這件事只有
    GameState 才查得到，Building 這個資料結構本身不持有、也不該持有
    inventory 的參照——維持這個專案從 Phase 1 就一路遵守的分工：
    game_config.py 的資料結構只管自己的狀態機，不碰玩家背包）。
    已經移除舊版 Phase 2 的 ready_to_collect「等待手動採收」狀態卡點；
    完成的當下由 GameState._update_buildings() 直接把產出加進背包。

    Phase 4 新增 SPRINKLER/AUTO_HARVESTER 這兩種「蓋下去就永久被動生
    效」的機台，完全不用 is_active/is_processing 這套開關-配方-倒數
    循環（玩家點擊它們也不會觸發 toggle_building 的開關切換——
    GameState.toggle_building() 會先檢查 config 裡有沒有 passive_effect，
    有的話直接拒絕切換並回覆提示，見該方法的說明）。scan_timer 是專門
    給 AUTO_HARVESTER 用的內建冷卻計時器（每 scan_interval 秒才掃描一
    次周圍成熟作物，不用每幀都掃，省效能——這是使用者原始需求就明確
    要求的做法）；SPRINKLER 完全不需要任何額外狀態，它的加成邏輯是
    GameState._update_crops_growth() 每幀直接讀 self.buildings 現算，
    不需要在 Building 身上存任何東西。這個欄位對 OVEN/FURNACE 完全沒
    有意義，預設 0.0、永遠不會被用到，維持這個資料結構是所有機台共用
    的單一 dataclass 這個既有設計，不用為了兩種新機台另外拆一個
    PassiveBuilding 子類別。"""
    building_type: BuildingType
    x: int
    y: int
    is_active: bool = False        # 開關：True=自動運作中，False=關閉（預設關閉）——對 OVEN/FURNACE/
                                    # LUMBERYARD 跟現在可開關的 SPRINKLER 都有意義（見 is_passive 的說明）
    is_processing: bool = False    # 目前這一輪配方是否正在倒數——只對 OVEN/FURNACE/LUMBERYARD 有意義，
                                    # SPRINKLER 走自己的 passive_effect 分支，不會用到這個欄位
    processing_time_left: float = 0.0
    scan_timer: float = 0.0        # 泛用的「這種被動機台自己的週期計時器」：AUTO_HARVESTER 用它累積到
                                    # scan_interval 就掃描一次周圍作物，SPRINKLER 【系統更新：自動灑水器
                                    # 2x2 建築邏輯】之後也改用同一個欄位累積到 water_interval 就自動澆水
                                    # 一次，兩者互不影響（各自的 Building 實例各有一份）

    @property
    def config(self) -> dict:
        return BUILDING_DATA[self.building_type]

    @property
    def is_walkable(self) -> bool:
        return self.config.get("walkable", False)

    @property
    def is_passive(self) -> bool:
        """True 代表這是「蓋下去就永久生效、沒有開關，玩家點擊無效」的
        自動化科技機台 (AUTO_HARVESTER)；False 代表這台可以被
        toggle_building() 開關——包含原本 Phase 3 那套開關式自動化機台
        (OVEN/FURNACE/LUMBERYARD)，以及【系統更新：自動灑水器 2x2
        建築邏輯】之後也改成可開關的 SPRINKLER。

        判斷邏輯：config 裡有 "passive_effect" 代表這台走
        GameState._update_buildings() 裡專屬的被動分支（跳過一般的
        投料/倒數迴圈）；但這不再直接等於「不能開關」——多檢查一個
        "toggleable" 旗標，True 的話（目前只有 SPRINKLER）代表雖然走
        專屬分支，玩家仍然可以點擊切換 is_active，只是關閉時不會像
        AUTO_HARVESTER 那樣被完全擋下。"""
        return bool(self.config.get("passive_effect")) and not self.config.get("toggleable", False)

    def start_processing(self):
        self.is_processing = True
        self.processing_time_left = float(self.config["process_time"])

    def tick(self, dt: float) -> bool:
        """只管這一輪的倒數計時，完全不碰任何背包邏輯（原料夠不夠、
        扣原料、把產出加進背包，這些全部留給 GameState._update_buildings()
        處理，因為只有那裡才拿得到 crop_inventory/inventory）。回傳
        這一幀是否剛好倒數完成（True）；沒有在跑 (is_processing=False)
        的時候呼叫，直接回傳 False，不會報錯也不會誤觸發。"""
        if not self.is_processing:
            return False
        self.processing_time_left -= dt
        if self.processing_time_left <= 0.0:
            self.processing_time_left = 0.0
            self.is_processing = False
            return True
        return False

    def toggle(self) -> bool:
        """切換開關並回傳切換後的新狀態。刻意只改 is_active，完全不去
        動 is_processing/processing_time_left——如果玩家在機台正在跑的
        當下點擊關閉，這一輪不會被打斷，會自然跑完（tick() 只認
        is_processing，不認 is_active），下一幀 _update_buildings() 看到
        is_active 已經是 False 就不會再啟動下一輪，效果就是「優雅地在
        這一輪結束後停工」，不用額外的 pending_shutdown 旗標。"""
        self.is_active = not self.is_active
        return self.is_active


@dataclass
class Tile:
    x: int
    y: int
    zone: ZoneType
    crop: Optional[Crop] = None
    decoration: Optional[Decoration] = None
    defense: Optional[DefenseStructure] = None
    building: Optional[Building] = None

    @property
    def is_empty(self) -> bool:
        return (self.crop is None and self.decoration is None
                and self.defense is None and self.building is None)

    @property
    def is_walkable(self) -> bool:
        if self.defense is not None and not self.defense.is_walkable:
            return False
        if self.decoration is not None and not self.decoration.is_walkable:
            return False
        if self.building is not None and not self.building.is_walkable:
            return False
        return True


@dataclass
class GuardDog:
    x: float = field(default_factory=lambda: float(DOG_CONFIG["home_pos"][0]))
    y: float = field(default_factory=lambda: float(DOG_CONFIG["home_pos"][1]))
    target_pos: Optional[Tuple[float, float]] = None
    state: DogState = DogState.PATROL
    target_enemy_id: Optional[str] = None
    attack_cooldown_timer: float = 0.0
    facing_direction: str = "down"  # 'down'/'left'/'right'/'up' -- 跟
    # Enemy.facing_direction 同一套慣例，由 game_state.py 在移動時透過
    # direction_from_delta() 更新，供渲染層播放對應方向的走路動畫用。
    
    @property
    def speed(self) -> float:
        return DOG_CONFIG["speed"]
    
    @property
    def detection_radius(self) -> float:
        return DOG_CONFIG["detection_radius"]


@dataclass
class FarmCat:
    x: float = field(default_factory=lambda: float(CAT_CONFIG["home_pos"][0]))
    y: float = field(default_factory=lambda: float(CAT_CONFIG["home_pos"][1]))
    timer: float = 0.0


def direction_from_delta(dx: float, dy: float) -> str:
    """
    把一段移動位移 (dx, dy) 轉成 4 方向精靈圖用的方向字串。
    取位移量較大的軸決定朝向（左右 vs 上下），平手時預設看下面。
    game_state.py 在每次真正移動 enemy.x / enemy.y 之前就已經算好
    (dx, dy) 了，所以直接呼叫這個函式寫回 enemy.facing_direction 即可，
    不需要額外記錄「上一幀座標」。
    """
    if dx == 0 and dy == 0:
        return "down"
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


@dataclass
class Enemy:
    id: str
    enemy_type: EnemyType
    x: float
    y: float
    hp: float = field(init=False)
    state: EnemyState = EnemyState.SPAWNING
    target_grid: Optional[Tuple[int, int]] = None
    path: List[Tuple[int, int]] = field(default_factory=list)
    action_timer: float = 0.0
    stun_timer: float = 0.0
    is_targeting_vault: bool = False
    attacking_fence: Optional[Tuple[int, int]] = None
    facing_direction: str = "down"  # 'down' / 'left' / 'right' / 'up' -- 由 game_state.py 在移動時更新，供渲染層播放對應方向的動畫用

    def __post_init__(self):
        self.hp = ENEMY_DATA[self.enemy_type]["max_hp"]

    @property
    def config(self) -> dict:
        return ENEMY_DATA[self.enemy_type]
    
    @property
    def speed(self) -> float:
        return self.config["speed"]
    
    @property
    def max_hp(self) -> float:
        return self.config["max_hp"]
    
    def take_damage(self, amount: float) -> bool:
        self.hp -= amount
        if self.hp <= 0:
            self.state = EnemyState.DEAD
            return True
        return False



@dataclass
class GameEvent:
    event_type: EventType
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class Order:
    """一張每日訂單。requirements 的 key 是 ORDER_CROP_ALIASES 裡的簡短
    代稱字串（例如 "wheat"、"tomato"），value 是需要的數量；未來如果
    訂單也能要求 wood/bread 這類加工資源，一樣是同一個 requirements
    字典裡多加一個 key（RESOURCE_KEYS 裡的名稱），fulfill_order() 的
    檢查/扣除邏輯已經是通用的，不用改資料結構。"""
    order_id: int
    requirements: Dict[str, int]
    reward_gold: int
    reward_tech: int
    is_fulfilled: bool = False
