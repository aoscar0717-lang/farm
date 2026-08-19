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
    不在本次改動範圍內，留給下一階段的建築放置系統一起做。"""
    FURNACE = "FURNACE"                  # 熔爐：金屬礦 -> 金屬錠（下一階段）
    OVEN = "OVEN"                        # 烤箱：小麥 -> 麵包（下一階段）
    HAMSTER_WHEEL = "HAMSTER_WHEEL"      # 倉鼠滾輪：消耗糧食產生電池/科技點數（下一階段）


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
RESOURCE_KEYS = ["wood", "charcoal", "metal_ore", "metal_ingot", "bread", "battery"]

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
    3: {"name": "繁花莊園", "min_prosperity": 100, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.BLUEBERRY, CropType.WHEAT]},
    4: {"name": "璀璨莊園", "min_prosperity": 200, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.BLUEBERRY, CropType.WHEAT, CropType.ROYAL_GRAPE]},
    5: {"name": "傳奇仙境", "min_prosperity": 350, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CARROT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.BLUEBERRY, CropType.WHEAT, CropType.ROYAL_GRAPE, CropType.STARLIGHT_FRUIT]},
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
    DecorationType.WINDMILL: {
        "name": "彩虹風車磨坊",
        "cost": 300,
        "prosperity_score": 220,
        "walkable": True,
        "asset_key": "windmill",
    }
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
class Tile:
    x: int
    y: int
    zone: ZoneType
    crop: Optional[Crop] = None
    decoration: Optional[Decoration] = None
    defense: Optional[DefenseStructure] = None
    
    @property
    def is_empty(self) -> bool:
        return self.crop is None and self.decoration is None and self.defense is None
    
    @property
    def is_walkable(self) -> bool:
        if self.defense is not None and not self.defense.is_walkable:
            return False
        if self.decoration is not None and not self.decoration.is_walkable:
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
