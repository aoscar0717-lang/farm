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
    DefenseType, BuildingType, EnemyType, EnemyState, DogState, EventType,
    MAP_CONFIG, FARM_LEVELS, CROP_DATA, DECORATION_DATA, DEFENSE_DATA,
    DOG_CONFIG, CAT_CONFIG, ENEMY_DATA,
    RESOURCE_KEYS, ORDER_CROP_ALIASES, ORDER_CONFIG, BUILDING_DATA,
    Crop, Decoration, DefenseStructure, Tile, GuardDog, FarmCat, Enemy, GameEvent, Order, Building,
    direction_from_delta
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

        # === 生產線 / 科技樹 終局系統 (Phase 1) ===
        # 原料/半成品背包：wood、charcoal、metal_ore、metal_ingot、bread、
        # battery，全部從 0 開始。目前還沒有任何地方會增加這些數量（要
        # 等下一階段的建築放置/加工邏輯），這裡先把欄位建好。
        self.inventory: Dict[str, int] = {key: 0 for key in RESOURCE_KEYS}
        # 已採收但還沒交訂單的作物庫存，key 是 ORDER_CROP_ALIASES 的簡短
        # 代稱（"wheat"/"tomato"/...）。過去 harvest_crop() 只會把作物
        # 直接換成金幣、作物本身就消失，訂單系統需要「交出 N 個某作物」
        # 這種可累積、可查詢的數量，所以額外加這個字典；金幣獎勵維持
        # 完全不變，這是在原有金幣收益之外「附加」記錄下來的採收數量，
        # 不會讓玩家變相損失原本的採收金幣。
        self.crop_inventory: Dict[str, int] = {alias: 0 for alias in ORDER_CROP_ALIASES}
        # 科技點數：終局進度貨幣，目前只有 fulfill_order() 這個管道可以
        # 取得，下一階段的科技樹系統會消耗它來解鎖 FURNACE/OVEN/
        # HAMSTER_WHEEL 等建築。
        self.tech_points: int = 0
        # 每日訂單：進入白天時 (_start_day / __init__ 的第 1 天) 呼叫
        # _generate_daily_orders() 產生 1~3 張新訂單，取代前一天沒交完
        # 的舊訂單（見該方法內註解說明為何選擇「不跨日累積」）。
        self.active_orders: List[Order] = []
        self._next_order_id: int = 1

        # 加工機台 (Phase 2)：跟防禦設施不同，這裡額外維護一個扁平陣列
        # 方便每幀直接遍歷做狀態更新 (_update_buildings)，不用像防禦
        # 設施那樣每幀重新掃一次整張地圖；tile.building 是反向參照，兩邊
        # 由 place_building()/demolish_tile() 統一同步增減，見 Building
        # 這個 dataclass 開頭的說明註解。
        self.buildings: List[Building] = []
        
        self.phase: GamePhase = GamePhase.DAY
        self.time_in_phase: float = 0.0
        self.total_game_time: float = 0.0
        self.day_duration: float = self.config.get("DAY_1_DURATION", 30.0) if self.day_count == 1 else self.config["DAY_DURATION"]
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

        # 第 1 天一開局也要有訂單可以交，不用等到隔天 _start_day() 才生成。
        self._generate_daily_orders()

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
    # 每日訂單系統 (Order System) —— Phase 1
    # =========================================================================

    def _get_item_count(self, item_key: str) -> int:
        """統一查詢某個訂單品項目前持有的數量。item_key 可能是
        ORDER_CROP_ALIASES 裡的作物代稱（查 crop_inventory），也可能是
        RESOURCE_KEYS 裡的原料/半成品名稱（查 inventory）——未來加工
        資源真的能被生產出來之後，訂單就能直接混合要求兩種來源，這裡
        不用再改。查不到的 key 一律當成 0，不會噴例外。"""
        if item_key in self.crop_inventory:
            return self.crop_inventory[item_key]
        if item_key in self.inventory:
            return self.inventory[item_key]
        return 0

    def _consume_item(self, item_key: str, qty: int) -> None:
        if item_key in self.crop_inventory:
            self.crop_inventory[item_key] = max(0, self.crop_inventory[item_key] - qty)
        elif item_key in self.inventory:
            self.inventory[item_key] = max(0, self.inventory[item_key] - qty)

    def _item_display_name(self, item_key: str) -> str:
        """把訂單/建築配方裡的物品 key 轉成給玩家看的中文名稱：作物代稱
        (ORDER_CROP_ALIASES 的 key) 轉成 CROP_DATA 裡的中文名稱；原料/
        半成品 (RESOURCE_KEYS) 目前沒有中文名稱表，先照英文代稱原樣
        顯示，以後要加中文名稱只要改這個函式，呼叫端不用動。"""
        if item_key in ORDER_CROP_ALIASES:
            return CROP_DATA[ORDER_CROP_ALIASES[item_key]]["name"]
        return item_key

    def _check_recipe_shortfall(self, requirements: Dict[str, int]) -> List[str]:
        """回傳每一項數量不足的物品描述（例如「小麥 還差 2 個」）的
        列表；全部足夠時回傳空列表。訂單交付 (fulfill_order)、建築開關
        (toggle_building) 跟自動投料 (_update_buildings) 共用同一份檢查
        邏輯，不用各寫一份。"""
        missing = []
        for item_key, need_qty in requirements.items():
            have_qty = self._get_item_count(item_key)
            if have_qty < need_qty:
                missing.append(f"{self._item_display_name(item_key)} 還差 {need_qty - have_qty} 個")
        return missing

    def _generate_daily_orders(self) -> None:
        """每天早上（進入 GamePhase.DAY 時）呼叫，隨機產生 1~3 張新訂單。

        設計決定：新的一天會直接「換掉」active_orders，而不是累加保留
        前一天沒交的舊訂單——理由是訂單需求的作物種類取決於當時已解鎖
        的作物（is_crop_unlocked），舊訂單若跨天保留，玩家會被要求交出
        「今天已經買不到種子」的過期作物組合；而且不清空的話 active_orders
        會隨天數無限增長。這個行為之後如果想改成「舊訂單保留、只是新
        增而非取代，並讓過期訂單顯示逾期」，只要把下面這行
        `self.active_orders = []` 改成有條件的淘汰邏輯即可，其餘生成
        程式碼不用動。
        """
        self.active_orders = []

        unlocked_aliases = [
            alias for alias, crop_type in ORDER_CROP_ALIASES.items()
            if self.is_crop_unlocked(crop_type)
        ]
        if not unlocked_aliases:
            return  # 理論上不會發生（Lv.1 就解鎖 2 種作物），保險起見不硬生成訂單

        order_count = random.randint(ORDER_CONFIG["MIN_ORDERS_PER_DAY"], ORDER_CONFIG["MAX_ORDERS_PER_DAY"])
        generated = []
        for _ in range(order_count):
            kind_count = min(
                len(unlocked_aliases),
                random.randint(ORDER_CONFIG["MIN_ITEM_KINDS"], ORDER_CONFIG["MAX_ITEM_KINDS"])
            )
            chosen_aliases = random.sample(unlocked_aliases, kind_count)

            requirements: Dict[str, int] = {}
            gold_value = 0
            for alias in chosen_aliases:
                qty = random.randint(ORDER_CONFIG["MIN_QTY_PER_ITEM"], ORDER_CONFIG["MAX_QTY_PER_ITEM"])
                requirements[alias] = qty
                crop_type = ORDER_CROP_ALIASES[alias]
                gold_value += qty * CROP_DATA[crop_type]["harvest_reward"]

            reward_gold = max(1, round(gold_value * ORDER_CONFIG["GOLD_REWARD_RATIO"]))
            reward_tech = (
                ORDER_CONFIG["TECH_REWARD_BASE"]
                + kind_count * ORDER_CONFIG["TECH_REWARD_PER_ITEM_KIND"]
                + random.randint(0, 3)
            )

            order = Order(
                order_id=self._next_order_id,
                requirements=requirements,
                reward_gold=reward_gold,
                reward_tech=reward_tech,
            )
            self._next_order_id += 1
            generated.append(order)

        self.active_orders = generated

        req_summary = "；".join(
            "、".join(f"{self._item_display_name(a)} x{q}" for a, q in o.requirements.items())
            for o in generated
        )
        self._emit_event(
            EventType.ORDERS_GENERATED,
            f"📋 今日新訂單共 {len(generated)} 張：{req_summary}",
            {"order_ids": [o.order_id for o in generated]}
        )

    def fulfill_order(self, order_id: int) -> Tuple[bool, str]:
        """檢查玩家背包(crop_inventory/inventory)是否滿足指定訂單的
        requirements；全部滿足才會真的扣除物品並發放 reward_gold/
        reward_tech，任何一項不足都不會扣任何東西（全有或全無，不會
        扣一半）。成功後該訂單會從 active_orders 移除（視為已交付）。"""
        order = next((o for o in self.active_orders if o.order_id == order_id), None)
        if order is None:
            return False, "找不到這張訂單（可能已經交付或過期）！"
        if order.is_fulfilled:
            return False, "這張訂單已經交付過了！"

        # 缺項檢查改呼叫共用的 _check_recipe_shortfall()（跟 Phase 2 新增
        # 的建築投料共用同一份邏輯）；順便把提示文字從 enum 原始值（例如
        # "WHEAT"）改成 _item_display_name() 查出來的中文名稱（"小麥"），
        # 跟遊戲其餘介面的在地化文字風格一致——這是本次順手修正的小
        # 瑕疵，不影響任何數值判定，只改錯誤訊息的顯示文字。
        missing = self._check_recipe_shortfall(order.requirements)

        if missing:
            return False, f"物資不足，無法交付訂單！（{'、'.join(missing)}）"

        for item_key, need_qty in order.requirements.items():
            self._consume_item(item_key, need_qty)

        order.is_fulfilled = True
        self.gold += order.reward_gold
        self.tech_points += order.reward_tech
        self.active_orders = [o for o in self.active_orders if o.order_id != order_id]

        self._emit_event(
            EventType.ORDER_FULFILLED,
            f"📦 訂單交付成功！獲得 {order.reward_gold} 金幣、{order.reward_tech} 科技點數。",
            {"order_id": order_id, "reward_gold": order.reward_gold, "reward_tech": order.reward_tech,
             "total_gold": self.gold, "total_tech": self.tech_points}
        )
        return True, f"訂單交付成功！獲得 {order.reward_gold} 金幣、{order.reward_tech} 科技點數。"

    # =========================================================================
    # 加工建築系統 (Building System) —— Phase 2
    # =========================================================================

    def place_building(self, x: int, y: int, building_type: BuildingType) -> Tuple[bool, str]:
        """建造一座加工機台。跟 place_defense() 走同一套檢查順序（夜晚
        禁建 -> 座標有效 -> 區域限制 -> 空地 -> 解鎖等級 -> 金幣），只是
        多一道「科技點數」門檻，而且區域限制刻意跟防禦設施相反：防禦
        設施 (place_defense) 只能蓋在中央「農田防衛區」(FARM_ZONE)，
        加工機台則只能蓋在四周的「莊園景觀區」(DECORATION_ZONE)——中央
        農田格子數量有限，要優先留給種作物跟防禦，機台更像是「莊園裡
        的一間工坊」，跟景觀裝飾放在同一個區域競爭空間更合理。"""
        if self.phase == GamePhase.NIGHT:
            return False, "夜晚防守期間無法建造加工機台！"

        tile = self.get_tile(x, y)
        if not tile:
            return False, "座標無效！"

        if tile.zone != ZoneType.DECORATION_ZONE:
            return False, "加工機台只能建造在「四周的莊園景觀區」！中央農田請保留給作物與防禦設施。"

        if not tile.is_empty:
            return False, "該位置已有物件，無法建造加工機台！"

        config = BUILDING_DATA[building_type]
        req_lvl = config["unlock_level"]
        if self.farm_level < req_lvl:
            return False, f"{config['name']} 需要莊園等級 Lv.{req_lvl} 才能建造！"

        cost_gold = config["build_cost_gold"]
        cost_tech = config["build_cost_tech"]
        if self.gold < cost_gold:
            return False, f"金幣不足！建造 {config['name']} 需要 {cost_gold} 金幣。"
        if self.tech_points < cost_tech:
            return False, f"科技點數不足！建造 {config['name']} 需要 {cost_tech} 科技點數（目前 {self.tech_points} 點）。"

        self.gold -= cost_gold
        self.tech_points -= cost_tech
        building = Building(building_type=building_type, x=x, y=y)
        tile.building = building
        self.buildings.append(building)

        self._emit_event(
            EventType.BUILDING_PLACED,
            f"🏭 已建造 {config['name']}，花費 {cost_gold} 金幣、{cost_tech} 科技點數。",
            {"x": x, "y": y, "building_type": building_type.value, "cost_gold": cost_gold, "cost_tech": cost_tech}
        )
        return True, f"{config['name']} 建造成功！"

    def toggle_building(self, x: int, y: int) -> Tuple[bool, str]:
        """Phase 3：玩家點擊機台改成單純「切換開關」，不再是投料/採收
        兩種手動操作。

        關閉 -> 開啟：呼叫 Building.toggle() 把 is_active 設成 True 之前，
        先用 _check_recipe_shortfall() 幫玩家「預檢查」一次原料夠不夠——
        嚴格照使用者的字面規格，這個預檢查其實可以省略（純粹
        `self.is_active = not self.is_active`，交給下一幀
        _update_buildings() 的自動投料邏輯去發現原料不足、自動關閉、
        emit BUILDING_STOPPED），但那樣玩家點下去的當下畫面會先顯示
        「開啟」一瞬間，下一幀又立刻被系統改回「關閉」，體驗上會有一
        次觀感閃爍，而且這中間如果原料本來就有但不夠一整輪，玩家會誤
        以為自己點擊沒生效。這裡選擇「開啟當下立刻檢查、不夠就直接
        拒絕這次切換」，讓失敗訊息即時、明確，且不會產生開啟-立刻被
        關閉的閃爍——這是唯一跟字面規格不同的地方，其餘（is_active 的
        切換本身、「這一輪跑完才停工」的行為）完全照規格實作。

        開啟 -> 關閉：純粹 `Building.toggle()`，不打斷正在跑的這一輪
        （tick() 只認 is_processing），也不退還已經投入的原料——這是
        使用者要求的「完成當前這輪再停工」優雅做法，不是「立刻中斷並
        退還原料」那個選項。"""
        tile = self.get_tile(x, y)
        if not tile or tile.building is None:
            return False, "此處沒有加工機台！"

        building = tile.building
        config = building.config

        if not building.is_active:
            # 準備開啟：閒置中才需要預檢查原料（如果這一輪其實還在跑，
            # 例如玩家先關閉又立刻反悔重新打開，直接放行，讓它自然接
            # 續 tick() 倒數，不用重新檢查/重新扣一次原料）。
            if not building.is_processing:
                missing = self._check_recipe_shortfall(config["recipe"])
                if missing:
                    return False, f"原料不足，無法啟動 {config['name']}！（{'、'.join(missing)}）"
            building.toggle()
            self._emit_event(
                EventType.BUILDING_TOGGLED,
                f"🟢 {config['name']} 已開啟自動運作！",
                {"x": x, "y": y, "building_type": building.building_type.value, "is_active": True}
            )
            return True, f"{config['name']} 已開啟！"
        else:
            building.toggle()
            if building.is_processing:
                self._emit_event(
                    EventType.BUILDING_TOGGLED,
                    f"🟡 {config['name']} 將在這一輪運作完成後停工。",
                    {"x": x, "y": y, "building_type": building.building_type.value, "is_active": False}
                )
                return True, f"{config['name']} 將在這一輪結束後停工。"
            else:
                self._emit_event(
                    EventType.BUILDING_TOGGLED,
                    f"🔴 {config['name']} 已關閉。",
                    {"x": x, "y": y, "building_type": building.building_type.value, "is_active": False}
                )
                return True, f"{config['name']} 已關閉。"

    def _update_buildings(self, dt: float) -> None:
        """Phase 3 自動化循環：每幀對每座機台做兩件事，順序不能反：

        1. 如果正在運作 (is_processing)，呼叫 Building.tick(dt) 扣減
           倒數計時；剛好倒數完成的那一幀，直接把產出物加進玩家背包
           （crop_inventory 或 inventory，用 key 是否存在於 crop_inventory
           判斷該寫哪邊——這兩個系統的物品命名空間互斥不重複，Phase 1
           就已經是這樣設計）並 emit BUILDING_COLLECTED，不用等玩家
           點擊採收。

        2. 接著（故意不用 elif）：如果 is_active 為 True 且現在沒有在
           運作中（可能是本來就閒置，也可能是上一步剛跑完一輪），嘗試
           自動投料開始下一輪——原料夠就扣除、開始計時；原料不夠就把
           is_active 強制設回 False 並 emit BUILDING_STOPPED 提示玩家。
           這個「不用 elif」是刻意的：同一幀「跑完一輪」後緊接著判斷
           能不能開始下一輪，玩家觀感上就是完全連續自動運作，不會因為
           一幀的時間差而看起來卡了一下，也不會漏判。
        """
        for building in self.buildings:
            config = building.config

            if building.is_processing:
                if building.tick(dt):
                    output_key = config["output_key"]
                    output_qty = config["output_qty"]
                    if output_key in self.crop_inventory:
                        self.crop_inventory[output_key] = self.crop_inventory.get(output_key, 0) + output_qty
                    else:
                        self.inventory[output_key] = self.inventory.get(output_key, 0) + output_qty
                    self._emit_event(
                        EventType.BUILDING_COLLECTED,
                        f"📦 {config['name']} 自動產出 {output_qty} 個 {self._item_display_name(output_key)}！",
                        {"x": building.x, "y": building.y, "building_type": building.building_type.value,
                         "output_key": output_key, "output_qty": output_qty}
                    )

            if building.is_active and not building.is_processing:
                recipe = config["recipe"]
                missing = self._check_recipe_shortfall(recipe)
                if missing:
                    building.is_active = False
                    self._emit_event(
                        EventType.BUILDING_STOPPED,
                        f"⏸️ {config['name']} 原料不足，已自動關閉！（{'、'.join(missing)}）",
                        {"x": building.x, "y": building.y, "building_type": building.building_type.value}
                    )
                else:
                    for item_key, need_qty in recipe.items():
                        self._consume_item(item_key, need_qty)
                    building.start_processing()
                    self._emit_event(
                        EventType.BUILDING_STARTED,
                        f"⚙️ {config['name']} 開始運作，預計 {config['process_time']:.0f} 秒後完成。",
                        {"x": building.x, "y": building.y, "building_type": building.building_type.value}
                    )

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

        # 訂單系統需要「已採收、還沒交出去」的作物數量可查詢/可扣除，
        # 過去這裡採收完作物就直接消失（只換成金幣），現在額外記一份
        # 到 crop_inventory；找不到對應代稱（理論上不會發生，
        # ORDER_CROP_ALIASES 涵蓋全部 10 種作物）就靜默略過，不影響
        # 既有的金幣採收流程。
        crop_alias = next((a for a, ct in ORDER_CROP_ALIASES.items() if ct == crop.crop_type), None)
        if crop_alias is not None:
            self.crop_inventory[crop_alias] = self.crop_inventory.get(crop_alias, 0) + 1

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

        # 1. 優先照暈游標附近的敵人（範圍縮減為原本 3.5 格的一半：1.75 格）
        stunned_enemies = []
        for enemy in self.enemies:
            if enemy.state in (EnemyState.MOVING, EnemyState.ACTING):
                dist = math.hypot(enemy.x - target_x, enemy.y - target_y)
                if dist <= 1.75:
                    stunned_enemies.append(enemy)

        # 2. 若游標周圍無敵人，自動輔助瞄準全場最近的入侵敵人
        if not stunned_enemies:
            active_enemies = [e for e in self.enemies if e.state in (EnemyState.MOVING, EnemyState.ACTING)]
            if active_enemies:
                active_enemies.sort(key=lambda e: math.hypot(e.x - target_x, e.y - target_y))
                if math.hypot(active_enemies[0].x - target_x, active_enemies[0].y - target_y) <= 3.0:  # 原本 6.0 格，縮減為一半
                    stunned_enemies.append(active_enemies[0])

        if stunned_enemies:
            self.flashlight_cooldown = self.max_flashlight_cooldown
            names = []
            for e in stunned_enemies:
                e.state = EnemyState.STUNNED
                e.stun_timer = 2.5
                names.append(e.config['name'])
                self._emit_event(
                    EventType.ENEMY_STUNNED,
                    f"🔦 強光直射！{e.config['name']} 陷入暈眩 2.5 秒！（進入 3s 冷卻）",
                    {"x": e.x, "y": e.y, "enemy_id": e.id}
                )
            return True, f"成功照暈 {'、'.join(names)}！"

        return False, "視野內暫無可照射的入侵敵人！"

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

        if tile.zone != ZoneType.FARM_ZONE:
            return False, "防禦設施（木柵、捕獸夾、稻草人、蜜蜂塔）只能建造在「中央農田防衛區」！四周請保留給景觀建築。"

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

    def demolish_tile(self, x: int, y: int) -> Tuple[bool, str, int]:
        """使用鏟子挖除作物或拆除設施（退還 80% 建造金幣）"""
        tile = self.get_tile(x, y)
        if not tile or tile.is_empty:
            return False, "此處為空地，無需剷除！", 0

        # 1. 剷除作物 (不退款)
        if tile.crop is not None:
            name = tile.crop.config["name"]
            tile.crop = None
            self._emit_event(
                EventType.TILE_CLEARED,
                f"🌾 已剷除 ({x}, {y}) 的 {name} 作物！",
                {"x": x, "y": y, "refund": 0}
            )
            return True, f"已剷除 {name} 作物！", 0

        # 2. 拆除防禦設施 (退還 80% 金幣)
        if tile.defense is not None:
            name = tile.defense.config["name"]
            cost = tile.defense.config["cost"]
            refund = int(cost * 0.8)
            self.gold += refund
            tile.defense = None
            self._emit_event(
                EventType.TILE_CLEARED,
                f"🔨 已拆除 ({x}, {y}) 的 {name}，退還 {refund} 金幣！",
                {"x": x, "y": y, "refund": refund, "gold": self.gold}
            )
            return True, f"已拆除 {name}，退還 {refund} 金幣！", refund

        # 3. 移除景觀設施 (退還 80% 金幣並扣回繁榮度)
        if tile.decoration is not None:
            name = tile.decoration.config["name"]
            cost = tile.decoration.config["cost"]
            refund = int(cost * 0.8)
            self.gold += refund
            tile.decoration = None
            self.recalculate_prosperity()
            self._emit_event(
                EventType.TILE_CLEARED,
                f"🌸 已移除 ({x}, {y}) 的 {name}，退還 {refund} 金幣！",
                {"x": x, "y": y, "refund": refund, "gold": self.gold}
            )
            return True, f"已移除 {name}，退還 {refund} 金幣！", refund

        # 4. 拆除加工機台 (退還 80% 建造金幣；已花費的科技點數不退還，
        # 跟金幣一樣是「建造成本」，但科技點數代表的是已經投入的研發
        # 進度，設計上不應該靠蓋了再拆來套利)。正在運作中被拆除的話，
        # 已經投入配方的原料一律視為損耗，不會退還——這跟其他遊戲裡
        # 「拆除生產中的建築會損失在製品」是一樣的取捨，避免玩家用
        # 「蓋機台consume原料 -> 立刻拆除retrieve金幣」的套利路徑繞過
        # 訂單系統原本要建立的資源消耗。
        if tile.building is not None:
            name = tile.building.config["name"]
            cost = tile.building.config["build_cost_gold"]
            refund = int(cost * 0.8)
            self.gold += refund
            self.buildings = [b for b in self.buildings if b is not tile.building]
            tile.building = None
            self._emit_event(
                EventType.TILE_CLEARED,
                f"🔨 已拆除 ({x}, {y}) 的 {name}，退還 {refund} 金幣！",
                {"x": x, "y": y, "refund": refund, "gold": self.gold}
            )
            return True, f"已拆除 {name}，退還 {refund} 金幣！", refund

        return False, "無法剷除此處物品！", 0

    # =========================================================================
    # 日夜交替
    # =========================================================================


    def _start_night(self):
        self.phase = GamePhase.NIGHT
        self.time_in_phase = 0.0
        
        self.is_blood_moon = (self.day_count % 3 == 0)
        
        if self.day_count == 1:
            self.enemies_to_spawn = 2   # 第 1 天夜晚僅出 2 隻小偷，友善新手教學
        else:
            base_enemies = 2 + (self.day_count * 2)
            prosperity_bonus = self.prosperity_score // 25
            self.enemies_to_spawn = base_enemies + prosperity_bonus
        self.spawn_timer = 1.2
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
        self.day_duration = self.config.get("DAY_1_DURATION", 30.0) if self.day_count == 1 else self.config["DAY_DURATION"]
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

        # 莊園分紅：依「目前擺著的」景觀總繁榮度發錢，讓景觀從一次性的
        # 升級門檻變成持續生錢的資產。prosperity_score 是
        # recalculate_prosperity() 每次從場上實際景觀重算出來的即時值
        # （demolish_tile 拆除景觀時也會呼叫），不是累加值，所以「買了
        # 領一次分紅、馬上鏟掉退錢」的套利在設計上就不成立。
        dividend = int(self.prosperity_score * self.config.get("PROSPERITY_DIVIDEND_RATE", 0.3))
        if dividend > 0:
            self.gold += dividend
            self._emit_event(
                EventType.PROSPERITY_DIVIDEND,
                f"🏡 莊園景觀帶來 {dividend} G 分紅收入！（繁榮度 {self.prosperity_score}）",
                {"dividend": dividend, "prosperity": self.prosperity_score, "gold": self.gold}
            )

        self._emit_event(
            EventType.DAY_STARTED,
            f"☀️ 第 {self.day_count} 天黎明破曉！殘餘敵人已散去，請把握白天耕作！",
            {"day": self.day_count, "gold": self.gold, "prosperity": self.prosperity_score}
        )

        self._generate_daily_orders()

        self.check_game_over()

    # =========================================================================
    # 敵人生成與金庫掠奪尋路
    # =========================================================================

    def _spawn_enemy(self):
        if self.day_count == 1:
            enemy_type = EnemyType.THIEF
        else:
            weights = [45, 40 if self.day_count >= 2 else 0, 15 if self.day_count >= 3 else 0]
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
        # 若正常無障礙路徑被圍籬完全封死，啟動強行突破尋路（無視木柵阻擋，朝最近圍籬推進破壞）
        if not path and enemy.enemy_type != EnemyType.SHADOW_BAT:
            path = self.pathfinder.find_path(
                start=start_grid,
                goal=target_pos,
                is_walkable_fn=lambda x, y: True
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
        self._update_buildings(dt)

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

            # 地刺陷阱 (BEAR_TRAP)：永久性設施，敵人只要站在陷阱格上，
            # 每一幀都會持續受到 DoT 傷害（乘上 dt，不受 FPS 影響），
            # 不會像舊版一樣觸發一次就失效／消失——這裡刻意不寫
            # `tile.defense = None`，陷阱會永久留在場上，直到玩家自己
            # 用鏟子拆除。視覺/音效脈動節流成每 dot_tick_interval 秒一次
            # （由 tile.defense.dot_tick_timer 倒數），避免 60 FPS 下
            # 每一幀都噴粒子跟浮動文字。
            if tile and tile.defense and tile.defense.defense_type == DefenseType.BEAR_TRAP:
                trap = tile.defense
                dot_damage = trap.tick_trap_damage(dt)
                if dot_damage > 0:
                    trap.dot_tick_timer -= dt
                    should_pulse = trap.dot_tick_timer <= 0
                    if should_pulse:
                        trap.dot_tick_timer = trap.config.get("dot_tick_interval", 0.4)

                    if enemy.take_damage(dot_damage):
                        self._emit_event(
                            EventType.ENEMY_DEFEATED,
                            f"💀 {enemy.config['name']} 被地刺陷阱的持續傷害消滅！",
                            {"enemy_id": enemy.id}
                        )
                        dead_or_escaped.append(enemy)
                        continue
                    elif should_pulse:
                        self._emit_event(
                            EventType.TRAP_TRIGGERED,
                            f"💥 地刺陷阱在 ({grid_x}, {grid_y}) 持續刺傷 {enemy.config['name']}！",
                            {"x": grid_x, "y": grid_y, "enemy_id": enemy.id, "damage": dot_damage}
                        )

            # 刺藤木柵尖刺反傷 (Thorn Damage to nearby enemies)
            has_thorn_nearby = False
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = grid_x + dx, grid_y + dy
                ntile = self.get_tile(nx, ny)
                if ntile and ntile.defense and ntile.defense.defense_type == DefenseType.WOODEN_FENCE:
                    has_thorn_nearby = True
                    break

            if has_thorn_nearby and enemy.state in (EnemyState.MOVING, EnemyState.ACTING):
                thorn_dmg = 8.0 * dt
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

            # 移動中與破壞圍籬
            if enemy.state == EnemyState.MOVING:
                if not self._is_target_still_valid(enemy):
                    self._assign_enemy_target_and_path(enemy)

                if enemy.path:
                    next_node = enemy.path[0]
                    next_tile = self.get_tile(next_node[0], next_node[1])

                    # 檢查前進格是否為阻擋中的刺藤木柵（且非飛行魔蝠）
                    if (next_tile and next_tile.defense and 
                        next_tile.defense.defense_type == DefenseType.WOODEN_FENCE and 
                        enemy.enemy_type != EnemyType.SHADOW_BAT):
                        
                        fence_dps = enemy.config.get("fence_dps", 25.0)
                        destroyed = next_tile.defense.take_damage(fence_dps * dt)
                        enemy.attacking_fence = (next_node[0], next_node[1])

                        if destroyed:
                            next_tile.defense = None
                            enemy.attacking_fence = None
                            self._emit_event(
                                EventType.FENCE_DESTROYED,
                                f"💥 {enemy.config['name']} 衝破了 ({next_node[0]}, {next_node[1]}) 的木柵欄！防線失守！",
                                {"x": next_node[0], "y": next_node[1], "enemy_id": enemy.id}
                            )
                            # 缺口破開，重新為所有敵人尋找突破路徑
                            for other in self.enemies:
                                self._assign_enemy_target_and_path(other)
                    else:
                        enemy.attacking_fence = None
                        dx = next_node[0] - enemy.x
                        dy = next_node[1] - enemy.y
                        dist = math.hypot(dx, dy)
                        step = enemy.speed * dt
                        enemy.facing_direction = direction_from_delta(dx, dy)

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

        self._apply_enemy_separation(dt)

    def _apply_enemy_separation(self, dt: float):
        """簡化版 Boids 分離 (Separation)：多隻敵人的尋路都指向同一個目標
        時，座標會完全重合、疊成一坨，畫面上看起來只有一隻。這裡在正常
        的尋路移動『之上』疊加一個很小的互斥推力，讓彼此靠太近時輕微
        擠開，形成散開的一群，而不影響原本朝目標前進的路徑邏輯。

        只處理 MOVING / FLEEING（正在移動的）敵人——ACTING（原地掠奪
        中）跟 STUNNED（暈眩）的敵人應該待在原地不動，不參與推擠，也
        不應該被推離它正在行動的目標格。

        距離用跟尋路一致的「格」為單位，不是像素：這個檔案（純邏輯層）
        不知道畫面上一格是幾像素，CELL_SIZE 是 advanced_nightwatch_farm
        -v3.py 渲染層的常數，邏輯層不應該反過來依賴渲染層的東西。
        0.8 格對應需求裡「CELL_SIZE * 0.8」的比例，換算成這個檔案原生
        使用的座標單位。

        效能：雙層迴圈是 O(n^2)，但夜晚同時存在的敵人數量通常是個位數
        到十幾隻，就算 20 隻同時在場也只是 190 次距離比較，這一幀內完全
        可忽略，不會造成卡頓。
        """
        movable = [e for e in self.enemies if e.state in (EnemyState.MOVING, EnemyState.FLEEING)]
        n = len(movable)
        if n < 2:
            return

        SEPARATION_DIST = 0.8   # 格：兩隻敵人的直線距離小於這個值就互推
        PUSH_STRENGTH = 1.6     # 格/秒：推力大小，乘上 dt 換算成這一幀的實際位移

        pushes = [[0.0, 0.0] for _ in range(n)]
        for i in range(n):
            ax, ay = movable[i].x, movable[i].y
            for j in range(i + 1, n):
                bx, by = movable[j].x, movable[j].y
                dx = ax - bx
                dy = ay - by
                dist = math.hypot(dx, dy)
                if dist >= SEPARATION_DIST:
                    continue
                if dist < 1e-6:
                    # 座標完全重合，方向不確定，給一個固定方向的小推力
                    # 錯開，避免除以 0。
                    nx, ny = 1.0, 0.0
                    overlap = 1.0
                else:
                    nx, ny = dx / dist, dy / dist
                    overlap = (SEPARATION_DIST - dist) / SEPARATION_DIST
                push_x = nx * overlap * PUSH_STRENGTH * dt
                push_y = ny * overlap * PUSH_STRENGTH * dt
                pushes[i][0] += push_x
                pushes[i][1] += push_y
                pushes[j][0] -= push_x
                pushes[j][1] -= push_y

        for enemy, (px, py) in zip(movable, pushes):
            if px == 0.0 and py == 0.0:
                continue
            enemy.x = max(0.0, min(float(self.width - 1), enemy.x + px))
            enemy.y = max(0.0, min(float(self.height - 1), enemy.y + py))

    def _move_enemy_along_path(self, enemy: Enemy, dt: float):
        if enemy.path:
            next_node = enemy.path[0]
            dx = next_node[0] - enemy.x
            dy = next_node[1] - enemy.y
            dist = math.hypot(dx, dy)
            step = enemy.speed * dt * 1.4
            enemy.facing_direction = direction_from_delta(dx, dy)
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
            # 夾住下限，不讓金幣變負數——這個下限同時也是「還有沒有東西
            # 可以打」的判斷依據 (見 _retreat_or_reengage)：金庫被搬空到
            # 0 金幣之後，敵人才會判定金庫已經沒有意義，考慮撤退。
            self.gold = max(0, self.gold - stolen_vault_gold)
            self._emit_event(
                EventType.VAULT_RAIDED,
                f"🚨 金庫失守！{enemy.config['name']} 洗劫了中央農莊金庫，掠奪了 {stolen_vault_gold} 金幣！",
                {"gold_lost": stolen_vault_gold, "remaining_gold": self.gold}
            )
            self.check_game_over()
            self._retreat_or_reengage(enemy)
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
        self._retreat_or_reengage(enemy)

    def _retreat_or_reengage(self, enemy: Enemy):
        """敵人破壞/偷竊完一個目標後的下一步決定：不再是原本『吃完就跑』
        的固定行為，改成預設繼續進攻——立刻重新尋路找下一個目標（下一塊
        作物，或者農田已經被搜刮一空時改盯上金庫）。

        允許撤退（進入 FLEEING）只有幾種情況：
          - 白天來臨：_update_enemies() 本來就只在夜晚 (GamePhase.NIGHT)
            被 update() 呼叫，天亮之後敵人根本不會再跑到這個函式，不用
            在這裡另外判斷一次。
          - 被手電筒擊暈 / 被看門狗或陷阱擊敗：這兩種情況分別會提前把
            敵人設成 STUNNED（在 _update_enemies 開頭就 continue，不會
            執行到掠奪動作）或直接消滅放進 dead_or_escaped（同樣走不到
            這裡），跟這個函式互不影響。
          - 地圖上已經完全沒有任何可攻擊目標：農田裡一株作物都不剩，
            且金庫也已經被搬空到 0 金幣，再攻擊金庫也搬不到東西，這時
            才真的撤退，不會呆站在空地圖中央發呆。
        """
        self._assign_enemy_target_and_path(enemy)
        if enemy.is_targeting_vault and self.gold <= 0:
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
                dog.facing_direction = direction_from_delta(dx, dy)
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
                dog.facing_direction = direction_from_delta(dx, dy)

        else:
            if dog.state != DogState.PATROL:
                dog.state = DogState.PATROL

            home_x, home_y = float(DOG_CONFIG["home_pos"][0]), float(DOG_CONFIG["home_pos"][1])
            dist_to_home = math.hypot(home_x - dog.x, home_y - dog.y)
            if dist_to_home > 0.5:
                step = (dog.speed * 0.7) * dt
                dx_home = (home_x - dog.x) / dist_to_home
                dy_home = (home_y - dog.y) / dist_to_home
                dog.x += dx_home * step
                dog.y += dy_home * step
                dog.facing_direction = direction_from_delta(dx_home, dy_home)

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
