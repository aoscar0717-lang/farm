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
    SWEET_CORN = "SWEET_CORN"            # 甜玉米 (Lv.2)
    CRYSTAL_EGGPLANT = "CRYSTAL_EGGPLANT"# 紫水晶茄子 (Lv.2)
    SWEET_STRAWBERRY = "SWEET_STRAWBERRY"# 鮮甜草莓 (Lv.2)
    MAGIC_PUMPKIN = "MAGIC_PUMPKIN"      # 魔法南瓜 (Lv.3)
    CRISP_WATERMELON = "CRISP_WATERMELON"# 冰爽西瓜 (Lv.3)
    GOLDEN_SUNFLOWER = "GOLDEN_SUNFLOWER"# 金色向日葵 (Lv.3)
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
    
    GAME_OVER = "GAME_OVER"


# ==========================================
# 數值平衡設定
# ==========================================

MAP_CONFIG = {
    "GRID_WIDTH": 18,
    "GRID_HEIGHT": 11,
    "FARM_X_RANGE": (4, 13),
    "FARM_Y_RANGE": (2, 8),
    "VAULT_POS": (8, 5),
    "DAY_DURATION": 20.0,
    "NIGHT_DURATION": 18.0,
    "INITIAL_GOLD": 300,
    "DAILY_TAX_BASE": 15,
    "DAILY_TAX_PER_DAY": 5,
    "FLASHLIGHT_COOLDOWN": 3.0,  # 3 秒強光手電筒冷卻時間
}


FARM_LEVELS = {
    1: {"name": "初級農莊", "min_prosperity": 0, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO]},
    2: {"name": "興旺莊園", "min_prosperity": 40, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CRYSTAL_EGGPLANT, CropType.SWEET_STRAWBERRY]},
    3: {"name": "繁花莊園", "min_prosperity": 100, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CRYSTAL_EGGPLANT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.CRISP_WATERMELON, CropType.GOLDEN_SUNFLOWER]},
    4: {"name": "璀璨莊園", "min_prosperity": 200, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CRYSTAL_EGGPLANT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.CRISP_WATERMELON, CropType.GOLDEN_SUNFLOWER, CropType.ROYAL_GRAPE]},
    5: {"name": "傳奇仙境", "min_prosperity": 350, "unlocked_crops": [CropType.WHITE_RADISH, CropType.RED_TOMATO, CropType.SWEET_CORN, CropType.CRYSTAL_EGGPLANT, CropType.SWEET_STRAWBERRY, CropType.MAGIC_PUMPKIN, CropType.CRISP_WATERMELON, CropType.GOLDEN_SUNFLOWER, CropType.ROYAL_GRAPE, CropType.STARLIGHT_FRUIT]},
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
        "name": "甜玉米",
        "unlock_level": 2,
        "seed_cost": 40,
        "grow_time": 10.0,
        "harvest_reward": 88,
        "theft_gold_loss": 50,
        "asset_key": "corn",
    },
    CropType.CRYSTAL_EGGPLANT: {
        "name": "紫晶茄子",
        "unlock_level": 2,
        "seed_cost": 55,
        "grow_time": 12.0,
        "harvest_reward": 130,
        "theft_gold_loss": 65,
        "asset_key": "eggplant",
    },
    CropType.SWEET_STRAWBERRY: {
        "name": "鮮甜草莓",
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
    CropType.CRISP_WATERMELON: {
        "name": "冰爽西瓜",
        "unlock_level": 3,
        "seed_cost": 110,
        "grow_time": 18.0,
        "harvest_reward": 310,
        "theft_gold_loss": 140,
        "asset_key": "watermelon",
    },
    CropType.GOLDEN_SUNFLOWER: {
        "name": "金色向日葵",
        "unlock_level": 3,
        "seed_cost": 130,
        "grow_time": 20.0,
        "harvest_reward": 380,
        "theft_gold_loss": 160,
        "asset_key": "sunflower",
    },
    CropType.ROYAL_GRAPE: {
        "name": "皇家紫葡萄",
        "unlock_level": 4,
        "seed_cost": 160,
        "grow_time": 22.0,
        "harvest_reward": 490,
        "theft_gold_loss": 200,
        "asset_key": "grape",
    },
    CropType.STARLIGHT_FRUIT: {
        "name": "永恆星光果",
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
        "damage": 120,
        "walkable": True,
        "asset_key": "bear_trap",
    },
    DefenseType.SCARECROW: {
        "name": "農田稻草人",
        "cost": 35,
        "scare_radius": 3.0,
        "walkable": False,
        "asset_key": "scarecrow",
    },
    DefenseType.BEEHIVE: {
        "name": "蜜蜂守衛巢",
        "cost": 85,
        "attack_range": 4.0,
        "attack_power": 18,
        "attack_cooldown": 1.2,
        "walkable": False,
        "asset_key": "beehive",
    }
}

DOG_CONFIG = {
    "cost": 100,
    "speed": 3.0,
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
    is_armed: bool = True
    cooldown_timer: float = 0.0
    hp: float = 80.0
    max_hp: float = 80.0
    
    def __post_init__(self):
        self.max_hp = float(self.config.get("max_hp", 80.0))
        self.hp = self.max_hp

    @property
    def config(self) -> dict:
        return DEFENSE_DATA[self.defense_type]
    
    @property
    def is_walkable(self) -> bool:
        return self.config["walkable"]
    
    def trigger_trap(self) -> float:
        if self.defense_type == DefenseType.BEAR_TRAP and self.is_armed:
            self.is_armed = False
            return self.config["damage"]
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
