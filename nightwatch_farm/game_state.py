"""
夜巡農場 (Nightwatch Farm) - 核心狀態管理器 (GameState)
包含：金庫洗劫防偷懶、每日領地稅、月光加成、蜜蜂塔、血月首領與主動戰術。
"""

import math
import random
import uuid
from typing import List, Tuple, Optional, Dict, Any

from game_config import (
    GamePhase, ZoneType, CropType, CropStage, DecorationType,
    DefenseType, EnemyType, EnemyState, DogState, EventType,
    MAP_CONFIG, FARM_LEVELS, CROP_DATA, DECORATION_DATA, DEFENSE_DATA,
    DOG_CONFIG, CAT_CONFIG, ENEMY_DATA,
    Crop, Decoration, DefenseStructure, Tile, GuardDog, FarmCat, Enemy, GameEvent
)
from pathfinding import GridBFS


class GameState:
    def __init__(self, custom_config: Optional[dict] = None):
        self.config = MAP_CONFIG.copy()
        if custom_config:
            self.config.update(custom_config)

        self.width: int = self.config["GRID_WIDTH"]
        self.height: int = self.config["GRID_HEIGHT"]
        
        self.gold: int = self.config["INITIAL_GOLD"]
        self.prosperity_score: int = 0
        self.farm_level: int = 1
        self.day_count: int = 1
        
        self.phase: GamePhase = GamePhase.DAY
        self.time_in_phase: float = 0.0
        self.total_game_time: float = 0.0
        self.day_duration: float = self.config["DAY_DURATION"]
        self.night_duration: float = self.config["NIGHT_DURATION"]
        
        # 網格初始化 (中央農田，四周佈置)
        self.grid: List[List[Tile]] = []
        self._init_grid()
        
        self.pathfinder = GridBFS(self.width, self.height)
        
        self.enemies: List[Enemy] = []
        self.guard_dog: Optional[GuardDog] = None
        self.has_dog: bool = False
        
        self.farm_cat: Optional[FarmCat] = None
        self.has_cat: bool = False
        
        self.spawn_timer: float = 0.0
        self.spawn_interval: float = 2.0
        self.enemies_to_spawn: int = 0
        self.is_blood_moon: bool = False
        self.flashlight_cooldown: float = 0.0
        self.max_flashlight_cooldown: float = self.config.get("FLASHLIGHT_COOLDOWN", 5.0)
        
        self.event_queue: List[GameEvent] = []
        self.game_over: bool = False
        self.game_over_reason: str = ""
        
        self._emit_event(
            EventType.DAY_STARTED,
            f"☀️ 第 {self.day_count} 天開始！在中央耕種，四周建造防禦與景觀吧！",
            {"day": self.day_count, "gold": self.gold}
        )

    def _init_grid(self):
        self.grid = []
        fx_min, fx_max = self.config["FARM_X_RANGE"]
        fy_min, fy_max = self.config["FARM_Y_RANGE"]

        for y in range(self.height):
            row = []
            for x in range(self.width):
                if (fx_min <= x <= fx_max) and (fy_min <= y <= fy_max):
                    zone = ZoneType.FARM_ZONE
                else:
                    zone = ZoneType.DECORATION_ZONE
                row.append(Tile(x=x, y=y, zone=zone))
            self.grid.append(row)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return None

    def is_tile_walkable(self, x: int, y: int) -> bool:
        tile = self.get_tile(x, y)
        if tile is None:
            return False
        return tile.is_walkable

    def _emit_event(self, event_type: EventType, message: str, data: Optional[Dict[str, Any]] = None):
        event = GameEvent(
            event_type=event_type,
            message=message,
            data=data or {},
            timestamp=self.total_game_time
        )
        self.event_queue.append(event)

    def poll_events(self) -> List[GameEvent]:
        events = list(self.event_queue)
        self.event_queue.clear()
        return events

    def recalculate_prosperity(self):
        total_score = 0
        for row in self.grid:
            for tile in row:
                if tile.zone == ZoneType.DECORATION_ZONE and tile.decoration is not None:
                    total_score += tile.decoration.prosperity_score
        
        self.prosperity_score = total_score
        
        new_level = 1
        for level in sorted(FARM_LEVELS.keys(), reverse=True):
            if self.prosperity_score >= FARM_LEVELS[level]["min_prosperity"]:
                new_level = level
                break
                
        if new_level > self.farm_level:
            old_lvl = self.farm_level
            self.farm_level = new_level
            unlocked = [c.name for c in FARM_LEVELS[new_level]["unlocked_crops"]]
            self._emit_event(
                EventType.FARM_LEVEL_UP,
                f"🎉 繁榮度達到 {self.prosperity_score}！莊園升級至 Lv.{self.farm_level}（{FARM_LEVELS[new_level]['name']}）！",
                {"old_level": old_lvl, "new_level": new_level, "unlocked_crops": unlocked}
            )

    def is_crop_unlocked(self, crop_type: CropType) -> bool:
        required_lvl = CROP_DATA[crop_type]["unlock_level"]
        return self.farm_level >= required_lvl

    # =========================================================================
    # 玩家操作行為 API
    # =========================================================================

    def plant_crop(self, x: int, y: int, crop_type: CropType) -> Tuple[bool, str]:
        if self.phase == GamePhase.NIGHT:
            return False, "夜晚防守期間無法種植作物！"

        tile = self.get_tile(x, y)
        if not tile:
            return False, "座標無效！"
            
        if tile.zone != ZoneType.FARM_ZONE:
            return False, "只能在中央「農田核心區」種植作物！"
            
        if not tile.is_empty:
            return False, "該位置已被佔用，無法種植！"
            
        if not self.is_crop_unlocked(crop_type):
            req_lvl = CROP_DATA[crop_type]["unlock_level"]
            return False, f"{CROP_DATA[crop_type]['name']} 需要莊園等級 Lv.{req_lvl} 才能種植！"

        cost = CROP_DATA[crop_type]["seed_cost"]
        if self.gold < cost:
            return False, f"金幣不足！購買種子需要 {cost} 金幣，目前持有 {self.gold} 金幣。"

        self.gold -= cost
        tile.crop = Crop(crop_type=crop_type)
        self._emit_event(
            EventType.CROP_PLANTED,
            f"已種植 {CROP_DATA[crop_type]['name']}，花費 {cost} 金幣。",
            {"x": x, "y": y, "crop_type": crop_type.value, "cost": cost, "remaining_gold": self.gold}
        )
        return True, "種植成功！"

    def harvest_crop(self, x: int, y: int) -> Tuple[bool, int, str]:
        if self.phase == GamePhase.NIGHT:
            return False, 0, "夜晚防守期間無法採收！"

        tile = self.get_tile(x, y)
        if not tile or tile.crop is None:
            return False, 0, "此處沒有農作物！"

        crop = tile.crop
        if crop.stage != CropStage.MATURE:
            return False, 0, f"{crop.config['name']} 尚未成熟，無法採收！"

        reward = crop.config["harvest_reward"]
        if crop.is_moonlight_boosted:
            reward = int(reward * 1.5) # 月光加成 +50%
            
        self.gold += reward
        crop_name = crop.config["name"]
        tile.crop = None

        bonus_str = " (含月光滋養 +50%！)" if crop.is_moonlight_boosted else ""
        self._emit_event(
            EventType.CROP_HARVESTED,
            f"🌾 成功採收 {crop_name}{bonus_str}！獲得 {reward} 金幣。",
            {"x": x, "y": y, "reward": reward, "total_gold": self.gold}
        )
        return True, reward, f"採收成功，獲得 {reward} 金幣！"

    def water_crop(self, x: int, y: int) -> Tuple[bool, str]:
        if self.phase == GamePhase.NIGHT:
            return False, "夜晚無法澆水！"

        tile = self.get_tile(x, y)
        if not tile or tile.crop is None:
            return False, "此處沒有作物可澆水！"

        crop = tile.crop
        if crop.is_mature:
            return False, "作物已經成熟，請直接點擊採收！"

        water_cost = 5
        if self.gold < water_cost:
            return False, f"金幣不足！澆水加成需要 {water_cost} 金幣。"

        self.gold -= water_cost
        boost = crop.grow_time * 0.5
        crop.growth_timer += boost
        crop.update_growth(0.0)

        self._emit_event(
            EventType.CROP_WATERED,
            f"💧 澆水滋養！{crop.config['name']} 生長大幅加速！",
            {"x": x, "y": y}
        )
        return True, "澆水成功，生長大幅加速！"

    def use_flashlight_stun(self, target_x: float, target_y: float) -> Tuple[bool, str]:
        if self.phase == GamePhase.DAY:
            return False, "白天無法使用強光手電筒！"

        if self.flashlight_cooldown > 0:
            return False, f"強光手電筒充能中（剩餘 {self.flashlight_cooldown:.1f} 秒）！"

        stunned_enemy = None
        min_dist = 1.8

        for enemy in self.enemies:
            if enemy.state in (EnemyState.MOVING, EnemyState.ACTING):
                dist = math.hypot(enemy.x - target_x, enemy.y - target_y)
                if dist <= min_dist:
                    min_dist = dist
                    stunned_enemy = enemy

        if stunned_enemy:
            self.flashlight_cooldown = self.max_flashlight_cooldown
            stunned_enemy.state = EnemyState.STUNNED
            stunned_enemy.stun_timer = 2.5
            self._emit_event(
                EventType.ENEMY_STUNNED,
                f"🔦 強光直射！{stunned_enemy.config['name']} 陷入暈眩 2.5 秒！（進入 3s 冷卻）",
                {"x": stunned_enemy.x, "y": stunned_enemy.y, "enemy_id": stunned_enemy.id}
            )
            return True, f"成功照暈 {stunned_enemy.config['name']}！"

        return False, "強光照射範圍內沒有敵人！"

    def use_dog_whistle(self, target_x: float, target_y: float) -> Tuple[bool, str]:
        if not self.guard_dog:
            return False, "尚未領養看門柴犬！"

        self.guard_dog.target_pos = (target_x, target_y)
        self.guard_dog.state = DogState.COMMANDED
        self._emit_event(
            EventType.DOG_WHISTLE,
            f"🔔 吹響守衛哨！柴犬正奔向目標地點支援！",
            {"target_x": target_x, "target_y": target_y}
        )
        return True, "柴犬出擊！"

    def place_decoration(self, x: int, y: int, deco_type: DecorationType) -> Tuple[bool, str]:
        if self.phase == GamePhase.NIGHT:
            return False, "夜晚防守期間無法佈置景觀！"

        tile = self.get_tile(x, y)
        if not tile:
            return False, "座標無效！"

        if tile.zone != ZoneType.DECORATION_ZONE:
            return False, "景觀裝飾只能放置在中央農田「四周的莊園區」！"

        if not tile.is_empty:
            return False, "該位置已有物件！"

        cost = DECORATION_DATA[deco_type]["cost"]
        if self.gold < cost:
            return False, f"金幣不足！建造 {DECORATION_DATA[deco_type]['name']} 需要 {cost} 金幣。"

        self.gold -= cost
        tile.decoration = Decoration(decoration_type=deco_type)
        self.recalculate_prosperity()

        self._emit_event(
            EventType.DECORATION_PLACED,
            f"🏛️ 成功建造 {DECORATION_DATA[deco_type]['name']}，繁榮度 +{DECORATION_DATA[deco_type]['prosperity_score']}。",
            {"x": x, "y": y, "deco_type": deco_type.value, "cost": cost, "prosperity": self.prosperity_score}
        )
        return True, "放置成功！"

    def place_defense(self, x: int, y: int, defense_type: DefenseType) -> Tuple[bool, str]:
        if self.phase == GamePhase.NIGHT:
            return False, "夜晚防守期間無法建造防禦設施！"

        tile = self.get_tile(x, y)
        if not tile:
            return False, "座標無效！"

        if not tile.is_empty:
            return False, "該位置已有物件，無法放置防禦設施！"

        cost = DEFENSE_DATA[defense_type]["cost"]
        if self.gold < cost:
            return False, f"金幣不足！需要 {cost} 金幣。"

        self.gold -= cost
        tile.defense = DefenseStructure(defense_type=defense_type)

        self._emit_event(
            EventType.DEFENSE_PLACED,
            f"🛡️ 已建造 {DEFENSE_DATA[defense_type]['name']}，花費 {cost} 金幣。",
            {"x": x, "y": y, "defense_type": defense_type.value, "cost": cost}
        )
        return True, "放置成功！"

    def buy_guard_dog(self) -> Tuple[bool, str]:
        if self.has_dog and self.guard_dog is not None:
            return False, "您已經擁有看門柴犬了！"

        cost = DOG_CONFIG["cost"]
        if self.gold < cost:
            return False, f"金幣不足！購買看門柴犬需要 {cost} 金幣。"

        self.gold -= cost
        self.guard_dog = GuardDog()
        self.has_dog = True

        self._emit_event(
            EventType.PET_BOUGHT,
            f"🐕 成功領養看門柴犬！夜晚將在中央農田周邊守護撲咬敵人！",
            {"cost": cost, "gold": self.gold}
        )
        return True, "購買成功！"

    def buy_farm_cat(self) -> Tuple[bool, str]:
        if self.has_cat and self.farm_cat is not None:
            return False, "您已經擁有招財小貓了！"

        cost = CAT_CONFIG["cost"]
        if self.gold < cost:
            return False, f"金幣不足！購買招財小貓需要 {cost} 金幣。"

        self.gold -= cost
        self.farm_cat = FarmCat()
        self.has_cat = True

        self._emit_event(
            EventType.PET_BOUGHT,
            f"🐱 成功領養招財小貓！白天巡視農場時將定期為您帶來幸運金幣！",
            {"cost": cost, "gold": self.gold}
        )
        return True, "購買成功！"

    # =========================================================================
    # 日夜交替
    # =========================================================================

    def _start_night(self):
        self.phase = GamePhase.NIGHT
        self.time_in_phase = 0.0
        
        self.is_blood_moon = (self.day_count % 3 == 0)
        
        base_enemies = 3 + (self.day_count * 2)
        prosperity_bonus = self.prosperity_score // 25
        self.enemies_to_spawn = base_enemies + prosperity_bonus
        self.spawn_timer = 0.8
        self.enemies.clear()

        # 夜間作物月光滋養標記
        for row in self.grid:
            for tile in row:
                if tile.crop is not None:
                    tile.crop.is_moonlight_boosted = True

        if self.guard_dog:
            self.guard_dog.state = DogState.PATROL
            self.guard_dog.target_enemy_id = None
            self.guard_dog.target_pos = None

        if self.is_blood_moon:
            self._emit_event(
                EventType.BLOOD_MOON_WARNING,
                f"🩸 【血月警報】第 {self.day_count} 天血月降臨！巨型野豬首領即將襲擊莊園！",
                {"day": self.day_count}
            )
            boss = Enemy(
                id="boss_boar",
                enemy_type=EnemyType.BOSS_BOAR_KING,
                x=float(self.width // 2),
                y=0.0
            )
            self._assign_enemy_target_and_path(boss)
            self.enemies.append(boss)
        else:
            self._emit_event(
                EventType.NIGHT_STARTED,
                f"🌙 第 {self.day_count} 天夜晚降臨！{self.enemies_to_spawn} 名入侵者正逼近！",
                {"day": self.day_count, "total_enemies": self.enemies_to_spawn}
            )

    def _start_day(self):
        self.phase = GamePhase.DAY
        self.time_in_phase = 0.0
        self.day_count += 1
        self.is_blood_moon = False
        self.enemies.clear()

        if self.guard_dog:
            self.guard_dog.state = DogState.RETURNING
            self.guard_dog.x = float(DOG_CONFIG["home_pos"][0])
            self.guard_dog.y = float(DOG_CONFIG["home_pos"][1])
            self.guard_dog.target_pos = None

        # 每日領地地租/維護費（防止玩家空田掛機）
        tax = self.config["DAILY_TAX_BASE"] + (self.day_count * self.config["DAILY_TAX_PER_DAY"])
        self.gold -= tax

        self._emit_event(
            EventType.DAILY_TAX_PAID,
            f"🏛️ 支付第 {self.day_count} 天莊園地租與維護費 -{tax} G！",
            {"tax": tax, "gold": self.gold}
        )

        self._emit_event(
            EventType.DAY_STARTED,
            f"☀️ 第 {self.day_count} 天黎明破曉！殘餘敵人已散去，請把握白天耕作！",
            {"day": self.day_count, "gold": self.gold, "prosperity": self.prosperity_score}
        )
        
        self.check_game_over()

    # =========================================================================
    # 敵人生成與金庫掠奪尋路
    # =========================================================================

    def _spawn_enemy(self):
        weights = [45, 40, 15 if self.day_count >= 2 else 0]
        enemy_type = random.choices(
            [EnemyType.THIEF, EnemyType.WILD_BOAR, EnemyType.SHADOW_BAT],
            weights=weights
        )[0]
        
        border = random.choice(["TOP", "BOTTOM", "LEFT", "RIGHT"])
        if border == "TOP":
            spawn_x, spawn_y = random.randint(0, self.width - 1), 0
        elif border == "BOTTOM":
            spawn_x, spawn_y = random.randint(0, self.width - 1), self.height - 1
        elif border == "LEFT":
            spawn_x, spawn_y = 0, random.randint(0, self.height - 1)
        else:
            spawn_x, spawn_y = self.width - 1, random.randint(0, self.height - 1)

        enemy = Enemy(
            id=str(uuid.uuid4())[:8],
            enemy_type=enemy_type,
            x=float(spawn_x),
            y=float(spawn_y)
        )
        
        self._assign_enemy_target_and_path(enemy)
        self.enemies.append(enemy)

        self._emit_event(
            EventType.ENEMY_SPAWNED,
            f"⚠️ 警告！{enemy.config['name']} 自邊緣突襲莊園！",
            {"enemy_id": enemy.id, "type": enemy_type.value, "spawn_pos": (spawn_x, spawn_y)}
        )

    def _assign_enemy_target_and_path(self, enemy: Enemy):
        # 1. 優先搜尋農田區作物
        best_crop_val = -1
        best_crop_tile = None
        
        for row in self.grid:
            for tile in row:
                if tile.zone == ZoneType.FARM_ZONE and tile.crop is not None:
                    val = tile.crop.config["harvest_reward"]
                    if tile.crop.is_mature:
                        val += 1000
                    if val > best_crop_val:
                        best_crop_val = val
                        best_crop_tile = (tile.x, tile.y)
                        
        if best_crop_tile:
            target_pos = best_crop_tile
            enemy.is_targeting_vault = False
        else:
            # 2. 若農田無任何作物（玩家試圖空田防守）：直接突襲農莊金庫/糧倉！
            target_pos = self.config["VAULT_POS"]
            enemy.is_targeting_vault = True

        enemy.target_grid = target_pos
        enemy.state = EnemyState.MOVING

        start_grid = (int(round(enemy.x)), int(round(enemy.y)))
        walk_fn = (lambda x, y: True) if enemy.enemy_type == EnemyType.SHADOW_BAT else self.is_tile_walkable
        path = self.pathfinder.find_path(
            start=start_grid,
            goal=target_pos,
            is_walkable_fn=walk_fn
        )
        enemy.path = path

    # =========================================================================
    # 更新循環
    # =========================================================================

    def update(self, dt: float):
        if self.game_over:
            return

        self.total_game_time += dt
        self.time_in_phase += dt

        if self.flashlight_cooldown > 0:
            self.flashlight_cooldown = max(0.0, self.flashlight_cooldown - dt)

        self._update_crops_growth(dt)
        self._update_pets(dt)
        self._update_beehives(dt)

        if self.phase == GamePhase.DAY:
            if self.time_in_phase >= self.day_duration:
                self._start_night()
        else:
            self._update_night_spawning(dt)
            self._update_enemies(dt)
            self._update_guard_dog(dt)
            
            # 夜晚時間結束立即破曉切換至白天！
            if self.time_in_phase >= self.night_duration:
                self._start_day()

        self.check_game_over()

    def _update_crops_growth(self, dt: float):
        for row in self.grid:
            for tile in row:
                if tile.crop is not None:
                    new_stage = tile.crop.update_growth(dt)
                    if new_stage == CropStage.MATURE:
                        self._emit_event(
                            EventType.CROP_MATURED,
                            f"✨ ({tile.x}, {tile.y}) 的 {tile.crop.config['name']} 已經成熟！可於白天採收。",
                            {"x": tile.x, "y": tile.y, "crop_type": tile.crop.crop_type.value}
                        )

    def _update_pets(self, dt: float):
        if self.phase == GamePhase.DAY and self.farm_cat:
            self.farm_cat.timer += dt
            if self.farm_cat.timer >= CAT_CONFIG["bonus_interval"]:
                self.farm_cat.timer = 0.0
                bonus = CAT_CONFIG["bonus_gold"]
                self.gold += bonus
                self._emit_event(
                    EventType.CAT_BONUS,
                    f"🐱 招財小貓巡視莊園，為您帶來了 +{bonus} 金幣！",
                    {"bonus": bonus, "gold": self.gold}
                )

    def _update_beehives(self, dt: float):
        if self.phase != GamePhase.NIGHT:
            return

        for row in self.grid:
            for tile in row:
                if tile.defense and tile.defense.defense_type == DefenseType.BEEHIVE:
                    bh = tile.defense
                    if bh.cooldown_timer > 0:
                        bh.cooldown_timer -= dt
                    else:
                        r = bh.config["attack_range"]
                        closest_enemy = None
                        closest_dist = float('inf')
                        for enemy in self.enemies:
                            if enemy.state in (EnemyState.MOVING, EnemyState.ACTING, EnemyState.STUNNED):
                                d = math.hypot(enemy.x - tile.x, enemy.y - tile.y)
                                if d <= r and d < closest_dist:
                                    closest_dist = d
                                    closest_enemy = enemy

                        if closest_enemy:
                            bh.cooldown_timer = bh.config["attack_cooldown"]
                            dmg = bh.config["attack_power"]
                            killed = closest_enemy.take_damage(dmg)
                            self._emit_event(
                                EventType.BEE_ATTACK,
                                f"🐝 蜜蜂守衛巢發射蜂針！重擊 {closest_enemy.config['name']} 造成 {dmg} 傷害！",
                                {"from_x": tile.x, "from_y": tile.y, "to_x": closest_enemy.x, "to_y": closest_enemy.y, "damage": dmg}
                            )
                            if killed:
                                self._emit_event(
                                    EventType.ENEMY_DEFEATED,
                                    f"💀 {closest_enemy.config['name']} 被蜜蜂擊倒！",
                                    {"enemy_id": closest_enemy.id}
                                )

    def _update_night_spawning(self, dt: float):
        if self.enemies_to_spawn > 0:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                self._spawn_enemy()
                self.enemies_to_spawn -= 1
                self.spawn_timer = self.spawn_interval

    def _update_enemies(self, dt: float):
        dead_or_escaped = []

        scarecrows = [
            (tile.x, tile.y) for row in self.grid for tile in row
            if tile.defense and tile.defense.defense_type == DefenseType.SCARECROW
        ]

        for enemy in self.enemies:
            if enemy.state == EnemyState.DEAD:
                dead_or_escaped.append(enemy)
                continue

            if enemy.state == EnemyState.STUNNED:
                enemy.stun_timer -= dt
                if enemy.stun_timer <= 0:
                    enemy.state = EnemyState.MOVING
                continue

            grid_x, grid_y = int(round(enemy.x)), int(round(enemy.y))
            tile = self.get_tile(grid_x, grid_y)

            # 稻草人驚嚇
            if enemy.enemy_type == EnemyType.THIEF and enemy.state == EnemyState.MOVING:
                for sc_x, sc_y in scarecrows:
                    if math.hypot(sc_x - enemy.x, sc_y - enemy.y) <= DEFENSE_DATA[DefenseType.SCARECROW]["scare_radius"]:
                        self._emit_event(
                            EventType.SCARECROW_SCARE,
                            f"🌾 稻草人嚇退了小偷！",
                            {"enemy_id": enemy.id}
                        )
                        self._set_enemy_flee_path(enemy)
                        break

            # 捕獸夾
            if tile and tile.defense and tile.defense.defense_type == DefenseType.BEAR_TRAP and tile.defense.is_armed:
                damage = tile.defense.trigger_trap()
                self._emit_event(
                    EventType.TRAP_TRIGGERED,
                    f"💥 捕獸夾在 ({grid_x}, {grid_y}) 觸發！造成 {damage} 傷害！",
                    {"x": grid_x, "y": grid_y, "enemy_id": enemy.id, "damage": damage}
                )
                if enemy.take_damage(damage):
                    self._emit_event(
                        EventType.ENEMY_DEFEATED,
                        f"💀 {enemy.config['name']} 被捕獸夾消滅！",
                        {"enemy_id": enemy.id}
                    )
                    dead_or_escaped.append(enemy)
                    continue

            # 刺藤木柵尖刺反傷 (Thorn Damage to nearby enemies)
            has_thorn_nearby = False
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = grid_x + dx, grid_y + dy
                ntile = self.get_tile(nx, ny)
                if ntile and ntile.defense and ntile.defense.defense_type == DefenseType.WOODEN_FENCE:
                    has_thorn_nearby = True
                    break

            if has_thorn_nearby and enemy.state in (EnemyState.MOVING, EnemyState.ACTING):
                thorn_dmg = 12.0 * dt
                if enemy.take_damage(thorn_dmg):
                    self._emit_event(
                        EventType.ENEMY_DEFEATED,
                        f"💀 {enemy.config['name']} 撞上刺藤木柵被尖刺消滅！",
                        {"enemy_id": enemy.id}
                    )
                    dead_or_escaped.append(enemy)
                    continue

            # 逃跑
            if enemy.state == EnemyState.FLEEING:
                self._move_enemy_along_path(enemy, dt)
                if (int(round(enemy.x)) in (0, self.width - 1) or int(round(enemy.y)) in (0, self.height - 1)):
                    dead_or_escaped.append(enemy)
                continue

            # 掠奪動作
            if enemy.state == EnemyState.ACTING:
                enemy.action_timer += dt
                if enemy.action_timer >= enemy.config["action_duration"]:
                    self._execute_enemy_action(enemy)
                continue

            # 移動中
            if enemy.state == EnemyState.MOVING:
                if not self._is_target_still_valid(enemy):
                    self._assign_enemy_target_and_path(enemy)

                if enemy.path:
                    next_node = enemy.path[0]
                    dx = next_node[0] - enemy.x
                    dy = next_node[1] - enemy.y
                    dist = math.hypot(dx, dy)
                    step = enemy.speed * dt

                    if dist <= step:
                        enemy.x, enemy.y = float(next_node[0]), float(next_node[1])
                        enemy.path.pop(0)
                        if len(enemy.path) == 0:
                            enemy.state = EnemyState.ACTING
                            enemy.action_timer = 0.0
                    else:
                        enemy.x += (dx / dist) * step
                        enemy.y += (dy / dist) * step
                else:
                    self._assign_enemy_target_and_path(enemy)

        for e in dead_or_escaped:
            if e in self.enemies:
                self.enemies.remove(e)

    def _move_enemy_along_path(self, enemy: Enemy, dt: float):
        if enemy.path:
            next_node = enemy.path[0]
            dx = next_node[0] - enemy.x
            dy = next_node[1] - enemy.y
            dist = math.hypot(dx, dy)
            step = enemy.speed * dt * 1.4
            if dist <= step:
                enemy.x, enemy.y = float(next_node[0]), float(next_node[1])
                enemy.path.pop(0)
            else:
                enemy.x += (dx / dist) * step
                enemy.y += (dy / dist) * step

    def _is_target_still_valid(self, enemy: Enemy) -> bool:
        if enemy.is_targeting_vault:
            return True
        if not enemy.target_grid:
            return False
        tx, ty = enemy.target_grid
        tile = self.get_tile(tx, ty)
        if not tile:
            return False
        return tile.crop is not None

    def _execute_enemy_action(self, enemy: Enemy):
        # 情況 A：突襲農莊金庫 (若無作物)
        if enemy.is_targeting_vault:
            stolen_vault_gold = max(30, int(self.gold * 0.35))
            self.gold -= stolen_vault_gold
            self._emit_event(
                EventType.VAULT_RAIDED,
                f"🚨 金庫失守！{enemy.config['name']} 洗劫了中央農莊金庫，掠奪了 {stolen_vault_gold} 金幣！",
                {"gold_lost": stolen_vault_gold, "remaining_gold": self.gold}
            )
            self._set_enemy_flee_path(enemy)
            self.check_game_over()
            return

        # 情況 B：破壞作物
        if not enemy.target_grid:
            return
        tx, ty = enemy.target_grid
        tile = self.get_tile(tx, ty)

        if tile and tile.crop:
            crop_name = tile.crop.config["name"]
            gold_loss = tile.crop.config["theft_gold_loss"]
            tile.crop = None
            self.gold = max(0, self.gold - gold_loss)
            
            self._emit_event(
                EventType.CROP_STOLEN,
                f"😱 {enemy.config['name']} 破壞了 ({tx}, {ty}) 的 {crop_name}，並使您損失了 {gold_loss} 金幣！",
                {"x": tx, "y": ty, "gold_lost": gold_loss, "remaining_gold": self.gold}
            )
        self._set_enemy_flee_path(enemy)

    def _set_enemy_flee_path(self, enemy: Enemy):
        enemy.state = EnemyState.FLEEING
        curr_grid = (int(round(enemy.x)), int(round(enemy.y)))
        borders = [
            (curr_grid[0], 0), (curr_grid[0], self.height - 1),
            (0, curr_grid[1]), (self.width - 1, curr_grid[1])
        ]
        closest_border = min(borders, key=lambda p: math.hypot(p[0] - enemy.x, p[1] - enemy.y))
        path = self.pathfinder.find_path(
            start=curr_grid,
            goal=closest_border,
            is_walkable_fn=self.is_tile_walkable
        )
        enemy.path = path if path else [closest_border]

    def _update_guard_dog(self, dt: float):
        if not self.guard_dog:
            return
            
        dog = self.guard_dog
        if dog.attack_cooldown_timer > 0:
            dog.attack_cooldown_timer -= dt

        if dog.state == DogState.COMMANDED and dog.target_pos:
            tx, ty = dog.target_pos
            dx = tx - dog.x
            dy = ty - dog.y
            dist = math.hypot(dx, dy)
            if dist <= 0.6:
                dog.state = DogState.CHASING
                dog.target_pos = None
            else:
                step = dog.speed * 1.3 * dt
                dog.x += (dx / dist) * step
                dog.y += (dy / dist) * step
            return

        active_enemies = [e for e in self.enemies if e.state in (EnemyState.MOVING, EnemyState.ACTING, EnemyState.STUNNED, EnemyState.FLEEING)]
        closest_enemy = None
        closest_dist = float('inf')

        for enemy in active_enemies:
            dist = math.hypot(enemy.x - dog.x, enemy.y - dog.y)
            if dist <= dog.detection_radius and dist < closest_dist:
                closest_dist = dist
                closest_enemy = enemy

        if closest_enemy:
            if dog.state != DogState.CHASING:
                dog.state = DogState.CHASING
                self._emit_event(
                    EventType.DOG_BARK,
                    f"🐕 看門柴犬發現入侵者 {closest_enemy.config['name']}！展開追擊！",
                    {"enemy_id": closest_enemy.id}
                )

            dx = closest_enemy.x - dog.x
            dy = closest_enemy.y - dog.y
            dist = math.hypot(dx, dy)

            if dist <= DOG_CONFIG["attack_range"]:
                if dog.attack_cooldown_timer <= 0:
                    dog.attack_cooldown_timer = DOG_CONFIG["attack_cooldown"]
                    dmg = DOG_CONFIG["attack_power"]
                    killed = closest_enemy.take_damage(dmg)
                    
                    self._emit_event(
                        EventType.DOG_ATTACK,
                        f"🐕 柴犬撲咬 {closest_enemy.config['name']}（造成 {dmg} 傷害）！",
                        {"enemy_id": closest_enemy.id, "damage": dmg}
                    )
                    
                    if killed:
                        self._emit_event(
                            EventType.ENEMY_DEFEATED,
                            f"🏆 柴犬成功消滅了 {closest_enemy.config['name']}！",
                            {"enemy_id": closest_enemy.id}
                        )
                    else:
                        if closest_enemy.enemy_type != EnemyType.BOSS_BOAR_KING:
                            self._set_enemy_flee_path(closest_enemy)
            else:
                step = dog.speed * dt
                dog.x += (dx / dist) * step
                dog.y += (dy / dist) * step

        else:
            if dog.state != DogState.PATROL:
                dog.state = DogState.PATROL

            home_x, home_y = float(DOG_CONFIG["home_pos"][0]), float(DOG_CONFIG["home_pos"][1])
            dist_to_home = math.hypot(home_x - dog.x, home_y - dog.y)
            if dist_to_home > 0.5:
                step = (dog.speed * 0.7) * dt
                dog.x += ((home_x - dog.x) / dist_to_home) * step
                dog.y += ((home_y - dog.y) / dist_to_home) * step

    # =========================================================================
    # 結束條件判定
    # =========================================================================

    def check_game_over(self) -> bool:
        if self.game_over:
            return True

        min_seed_cost = min(c["seed_cost"] for c in CROP_DATA.values())
        has_enough_gold = (self.gold >= min_seed_cost)

        crops_count = sum(
            1 for row in self.grid for tile in row
            if tile.zone == ZoneType.FARM_ZONE and tile.crop is not None
        )

        if not has_enough_gold and crops_count == 0:
            self.game_over = True
            self.game_over_reason = f"莊園資金斷絕破產！持金不足購買任何種子（< {min_seed_cost} G），且農田已無作物！"
            self._emit_event(
                EventType.GAME_OVER,
                f"💀 【遊戲結束】{self.game_over_reason}",
                {"total_days_survived": self.day_count, "final_gold": self.gold}
            )
            return True

        return False
