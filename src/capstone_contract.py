import random
import math
from copy import deepcopy
from typing import Any

GameState = dict[str, Any]

ITEM_SIZE = 10
GRID_W = 100
GRID_H = 100

CROP_INFO = {
    "radish": {"price": 30, "growth_time": 1, "yield": 50, "level_req": 1},
    "corn": {"price": 100, "growth_time": 2, "yield": 250, "level_req": 2},
    "pumpkin": {"price": 300, "growth_time": 3, "yield": 1000, "level_req": 3}
}

CROP_NAMES = {
    "radish": "白蘿蔔",
    "corn": "甜玉米",
    "pumpkin": "魔法南瓜"
}

DECOR_INFO = {
    "stone_path": {"price": 20, "prosperity": 5},
    "flower": {"price": 50, "prosperity": 15},
    "bench": {"price": 100, "prosperity": 35},
    "fountain": {"price": 300, "prosperity": 120}
}

DECOR_NAMES = {
    "stone_path": "石板路",
    "flower": "鮮花盆栽",
    "bench": "木製長椅",
    "fountain": "小型噴泉"
}

def new_game(seed: int = 0) -> GameState:
    random.seed(seed)
    
    state: GameState = {
        "phase": "day",                 
        "crops": [],      
        "crop_data": {}, 
        "fences": [], 
        "scarecrows": [], 
        "traps": [],
        "dogs": [],
        "decorations": [], # list of (x, y, type, hp)
        "building_tasks": [],
        
        "money": 500,
        "prosperity_score": 0,
        "farm_level": 1,
        
        "time_left": 120,
        "day_count": 1,
        
        "thief_pos": None,
        "thief_path": [],
        "target_crop": None, 
        "thief_hp": 0,
        "thief_iframes": 0,
        "thief_spawn_cooldown": 0,
        "thieves_spawned": 0,
        "max_thieves": 1,
        
        "boar_pos": None,
        "boar_path": [],
        "target_decor": None,
        "boar_hp": 0,
        "boar_iframes": 0,
        "boar_spawn_cooldown": 0,
        "boars_spawned": 0,
        "max_boars": 0,
        
        "free_dog": False,
        "status": "playing",            
        "last_msg": "開放世界：按 [B] 打開商店選購道具！左側為農田區，右側為佈置區。",
        "wood": 0,
        "stone": 0,
        "inventory": {
            "radish": {"normal": 0, "rare": 0, "epic": 0, "legendary": 0},
            "corn": {"normal": 0, "rare": 0, "epic": 0, "legendary": 0},
            "pumpkin": {"normal": 0, "rare": 0, "epic": 0, "legendary": 0}
        },
        "farmland": [],
        "water": [],
        "trees": [],
        "rocks": []
    }
    
    # Generate 3-5 trees
    for _ in range(random.randint(3, 5)):
        tx = random.randint(0, GRID_W // ITEM_SIZE - 1) * ITEM_SIZE
        ty = random.randint(0, GRID_H // ITEM_SIZE - 1) * ITEM_SIZE
        
        if (tx, ty) not in state["trees"]:
            state["trees"].append((tx, ty))
            
    # Generate 5-8 rocks
    for _ in range(random.randint(5, 8)):
        rx = random.randint(0, GRID_W // ITEM_SIZE - 1) * ITEM_SIZE
        ry = random.randint(0, GRID_H // ITEM_SIZE - 1) * ITEM_SIZE
        
        if (rx, ry) not in state["trees"] and (rx, ry) not in state["rocks"]:
            state["rocks"].append((rx, ry))
    
    return state

def _rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2):
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

def _is_obstacle(state, x, y):
    for tx, ty in state.get("trees", []):
        if _rects_overlap(x, y, ITEM_SIZE, ITEM_SIZE, tx, ty, ITEM_SIZE, ITEM_SIZE): return True
    for rx, ry in state.get("rocks", []):
        if _rects_overlap(x, y, ITEM_SIZE, ITEM_SIZE, rx, ry, ITEM_SIZE, ITEM_SIZE): return True
    for f in state.get("fences", []):
        if _rects_overlap(x, y, ITEM_SIZE, ITEM_SIZE, f[0], f[1], ITEM_SIZE, ITEM_SIZE): return True
    return False

def _can_build_fence(state, pos):
    # Only checks if it completely blocks crops
    temp_state = deepcopy(state)
    temp_state["fences"].append((pos[0], pos[1], 3))
    
    targets = temp_state.get("crops", [])
    if not targets: return True
    
    start_grid = (0, 0)
    queue = [start_grid]
    visited = {start_grid}
    reached_crops = set()
    
    while queue:
        cx, cy = queue.pop(0)
        
        for t_pos in targets:
            if t_pos not in reached_crops:
                if t_pos[0]//5 == cx and t_pos[1]//5 == cy:
                    reached_crops.add(t_pos)
        
        if len(reached_crops) == len(targets):
            return True
            
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx <= 20 and 0 <= ny <= 20:
                if (nx, ny) not in visited:
                    px, py = nx * 5, ny * 5
                    if not _is_obstacle(temp_state, px, py):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                        
    return len(reached_crops) == len(targets)

def _is_occupied(state, x, y, size=ITEM_SIZE, include_crops=True):
    if _is_obstacle(state, x, y): return True
    
    all_entities = [(f[0], f[1]) for f in state["fences"]] + state["dogs"] + state.get("traps", [])
    all_entities += [(d[0], d[1]) for d in state.get("decorations", [])]
    for task in state["building_tasks"]:
        if task["type"] != "fence":
            all_entities.append(task["pos"])
            
    if include_crops:
        all_entities += state["crops"]
        
    for ex, ey in all_entities:
        if _rects_overlap(x, y, size, size, ex, ey, ITEM_SIZE, ITEM_SIZE):
            return True
            
    return False

def _update_prosperity_and_level(state):
    score = 0
    for d in state["decorations"]:
        dtype = d[2]
        score += DECOR_INFO.get(dtype, {}).get("prosperity", 0)
    state["prosperity_score"] = score
    
    old_level = state["farm_level"]
    if score >= 300:
        state["farm_level"] = 3
    elif score >= 100:
        state["farm_level"] = 2
    else:
        state["farm_level"] = 1
        
    if state["farm_level"] > old_level:
        state["last_msg"] = f"農場升級了！目前等級 {state['farm_level']}，解鎖新種子！"
    elif state["farm_level"] < old_level:
        state["last_msg"] = f"農場繁榮度下降，降級至 {state['farm_level']}..."

def _end_night(state):
    rent = 20 + (state["day_count"] - 1) * 10
    state["money"] -= rent
    
    building_crops = len([t for t in state.get("building_tasks", []) if t["type"] == "crop"])
    building_decors = len([t for t in state.get("building_tasks", []) if t["type"] == "decor"])
    
    if (len(state["crops"]) + building_crops + len(state["decorations"]) + building_decors) == 0 and state["money"] < 0:
        state["status"] = "game_over"
        state["last_msg"] = f"結算失敗！支付租金 ${rent} 後破產且無任何農田與景觀。Game Over！"
    else:
        if state.get("last_msg", "").startswith("所有敵人"):
            state["last_msg"] = f"{state['last_msg']} 支付每日租金 ${rent}。"
        else:
            state["last_msg"] = f"夜晚結束！支付每日租金 ${rent}。"
        
        state["phase"] = "day"
        state["day_count"] += 1
        state["time_left"] = 120
        
    state["thief_pos"] = None
    state["thief_path"] = []
    state["target_crop"] = None
    state["boar_pos"] = None
    state["boar_path"] = []
    state["target_decor"] = None
    return state

def apply_action(state: GameState, action: str) -> GameState:
    if state["status"] != "playing":
        return state
        
    _working_copy = deepcopy(state)
    
    if action == "tick":
        new_tasks = []
        for task in _working_copy["building_tasks"]:
            task["progress"] += 1
            if task["progress"] >= task["max_progress"]:
                t_type = task["type"]
                pos = task["pos"]
                if t_type == "crop":
                    crop_type = task["crop_type"]
                    _working_copy["crops"].append(pos)
                    _working_copy["crop_data"][pos] = {
                        "type": crop_type, 
                        "stage": 0, 
                        "max_stage": CROP_INFO[crop_type]["growth_time"],
                        "fertilized": False,
                        "growth_timer": 0
                    }
                elif t_type == "fence": _working_copy["fences"].append((pos[0], pos[1], 3))
                elif t_type == "farmland": _working_copy["farmland"].append(pos)
                elif t_type == "dog": _working_copy["dogs"].append(pos)
                elif t_type == "trap": _working_copy["traps"].append(pos)
                elif t_type == "decor":
                    decor_type = task["decor_type"]
                    _working_copy["decorations"].append((pos[0], pos[1], decor_type, 3))
                    _update_prosperity_and_level(_working_copy)
            else:
                new_tasks.append(task)
        _working_copy["building_tasks"] = new_tasks

        if _working_copy["phase"] == "day":
            _working_copy["time_left"] -= 1
            if _working_copy["time_left"] <= 0:
                return apply_action(_working_copy, "start_night")
        elif _working_copy["phase"] == "night":
            _working_copy["time_left"] -= 1
            if _working_copy["time_left"] <= 0:
                return _end_night(_working_copy)
        return _working_copy
        
    elif action == "night_tick":
        if _working_copy["phase"] == "night":
            enemies_active = False
            
            # --- THIEF LOGIC ---
            if _working_copy["thief_pos"] is None:
                if _working_copy.get("thieves_spawned", 0) < _working_copy.get("max_thieves", 1):
                    if _working_copy.get("thief_spawn_cooldown", 0) > 0:
                        _working_copy["thief_spawn_cooldown"] -= 1
                        enemies_active = True
                    else:
                        _working_copy["thief_pos"] = _spawn_thief(_working_copy)
                        _working_copy["thieves_spawned"] = _working_copy.get("thieves_spawned", 0) + 1
                        _working_copy["thief_hp"] = 3 + (_working_copy["day_count"] // 3)
                        _working_copy["thief_iframes"] = 0
                        _working_copy["thief_path"], _working_copy["target_crop"] = _simulate_night_path(_working_copy, "thief")
                        enemies_active = True
            else:
                enemies_active = True
                if _working_copy.get("thief_iframes", 0) > 0:
                    _working_copy["thief_iframes"] -= 1
                    
                # Trap logic
                trapped = None
                for trx, try_ in _working_copy["traps"]:
                    if _rects_overlap(trx, try_, ITEM_SIZE, ITEM_SIZE, _working_copy["thief_pos"][0], _working_copy["thief_pos"][1], ITEM_SIZE, ITEM_SIZE):
                        trapped = (trx, try_)
                        break
                if trapped:
                    _working_copy["traps"].remove(trapped)
                    _working_copy["thief_hp"] = 0
                    _working_copy["last_msg"] = "小偷踩到了捕獸夾！陷阱損壞，小偷被擊敗！"
                    
                if _working_copy["thief_hp"] <= 0:
                    if "小偷踩到" not in _working_copy.get("last_msg", ""):
                        _working_copy["last_msg"] = "小偷被擊退！"
                    _working_copy["thief_pos"] = None
                    _working_copy["thief_path"] = []
                    _working_copy["target_crop"] = None
                    _working_copy["thief_spawn_cooldown"] = 30 + random.randint(0, 30)
                elif _working_copy.get("thief_iframes", 0) <= 0:
                    tx, ty = _working_copy["thief_pos"]
                    if _working_copy.get("thief_path"):
                        target = _working_copy["thief_path"][0]
                        dist_x = target[0] - tx
                        dist_y = target[1] - ty
                        length = math.hypot(dist_x, dist_y)
                        speed = 0.5
                        
                        if length <= speed:
                            _working_copy["thief_pos"] = _working_copy["thief_path"].pop(0)
                        else:
                            _working_copy["thief_pos"] = (tx + (dist_x / length) * speed, ty + (dist_y / length) * speed)
                    else:
                        if _working_copy.get("target_crop"):
                            target = _working_copy["target_crop"]
                            fence = next((f for f in _working_copy.get("fences", []) if f[0] == target[0] and f[1] == target[1]), None)
                            if fence:
                                _working_copy["fences"].remove(fence)
                                if len(fence) > 2 and fence[2] > 1:
                                    _working_copy["fences"].append((fence[0], fence[1], fence[2] - 1))
                                    _working_copy["last_msg"] = f"小偷破壞了木圍欄！圍欄剩餘耐久: {fence[2] - 1}"
                                else:
                                    _working_copy["last_msg"] = "小偷摧毀了木圍欄！"
                            elif target in _working_copy["crops"]:
                                _working_copy["crops"].remove(target)
                                if target in _working_copy["crop_data"]:
                                    del _working_copy["crop_data"][target]
                                _working_copy["last_msg"] = "糟糕！有一塊農作被小偷偷走了！"
                        _working_copy["thief_pos"] = None
                        _working_copy["thief_path"] = []
                        _working_copy["target_crop"] = None
                        _working_copy["thief_spawn_cooldown"] = 30 + random.randint(0, 30)

            # --- BOAR LOGIC ---
            if _working_copy["boar_pos"] is None:
                if _working_copy.get("boars_spawned", 0) < _working_copy.get("max_boars", 0):
                    if _working_copy.get("boar_spawn_cooldown", 0) > 0:
                        _working_copy["boar_spawn_cooldown"] -= 1
                        enemies_active = True
                    else:
                        _working_copy["boar_pos"] = _spawn_boar(_working_copy)
                        _working_copy["boars_spawned"] = _working_copy.get("boars_spawned", 0) + 1
                        _working_copy["boar_hp"] = 5 + (_working_copy["day_count"] // 2)
                        _working_copy["boar_iframes"] = 0
                        _working_copy["boar_path"], _working_copy["target_decor"] = _simulate_night_path(_working_copy, "boar")
                        enemies_active = True
            else:
                enemies_active = True
                if _working_copy.get("boar_iframes", 0) > 0:
                    _working_copy["boar_iframes"] -= 1
                    
                # Trap logic
                trapped = None
                for trx, try_ in _working_copy["traps"]:
                    if _rects_overlap(trx, try_, ITEM_SIZE, ITEM_SIZE, _working_copy["boar_pos"][0], _working_copy["boar_pos"][1], ITEM_SIZE, ITEM_SIZE):
                        trapped = (trx, try_)
                        break
                if trapped:
                    _working_copy["traps"].remove(trapped)
                    _working_copy["boar_hp"] -= 5 # Boar is tough, trap does 5 dmg
                    _working_copy["last_msg"] = "野豬踩到了捕獸夾！陷阱損壞，野豬受到重創！"
                    
                if _working_copy["boar_hp"] <= 0:
                    if "踩到" not in _working_copy.get("last_msg", ""):
                        _working_copy["last_msg"] = "野豬被擊退！"
                    _working_copy["boar_pos"] = None
                    _working_copy["boar_path"] = []
                    _working_copy["target_decor"] = None
                    _working_copy["boar_spawn_cooldown"] = 45 + random.randint(0, 30)
                elif _working_copy.get("boar_iframes", 0) <= 0:
                    bx, by = _working_copy["boar_pos"]
                    if _working_copy.get("boar_path"):
                        target = _working_copy["boar_path"][0]
                        dist_x = target[0] - bx
                        dist_y = target[1] - by
                        length = math.hypot(dist_x, dist_y)
                        speed = 0.6 # Boars run faster
                        
                        if length <= speed:
                            _working_copy["boar_pos"] = _working_copy["boar_path"].pop(0)
                        else:
                            _working_copy["boar_pos"] = (bx + (dist_x / length) * speed, by + (dist_y / length) * speed)
                    else:
                        if _working_copy.get("target_decor"):
                            target = _working_copy["target_decor"]
                            decor_match = next((d for d in _working_copy["decorations"] if d[0] == target[0] and d[1] == target[1]), None)
                            if decor_match:
                                _working_copy["decorations"].remove(decor_match)
                                _update_prosperity_and_level(_working_copy)
                                _working_copy["last_msg"] = f"糟糕！野豬衝撞並摧毀了 {DECOR_NAMES.get(decor_match[2], '景觀物')}！繁榮度下降！"
                        _working_copy["boar_pos"] = None
                        _working_copy["boar_path"] = []
                        _working_copy["target_decor"] = None
                        _working_copy["boar_spawn_cooldown"] = 45 + random.randint(0, 30)

            # DOG LOGIC
            new_dogs = []
            for dx, dy in _working_copy["dogs"]:
                target_enemy = None
                tx, ty = -1, -1
                enemy_type = ""
                
                # Prioritize closer enemy
                dist_thief = float('inf')
                dist_boar = float('inf')
                
                if _working_copy["thief_pos"] is not None and _working_copy["thief_hp"] > 0:
                    dist_thief = math.hypot(_working_copy["thief_pos"][0] - dx, _working_copy["thief_pos"][1] - dy)
                if _working_copy["boar_pos"] is not None and _working_copy["boar_hp"] > 0:
                    dist_boar = math.hypot(_working_copy["boar_pos"][0] - dx, _working_copy["boar_pos"][1] - dy)
                    
                if dist_thief < dist_boar and dist_thief != float('inf'):
                    target_enemy = _working_copy["thief_pos"]
                    enemy_type = "thief"
                elif dist_boar != float('inf'):
                    target_enemy = _working_copy["boar_pos"]
                    enemy_type = "boar"

                if target_enemy:
                    tx, ty = target_enemy
                    if _rects_overlap(dx, dy, ITEM_SIZE, ITEM_SIZE, tx, ty, ITEM_SIZE, ITEM_SIZE):
                        if enemy_type == "thief" and _working_copy.get("thief_iframes", 0) <= 0:
                            _working_copy["thief_hp"] -= 1
                            _working_copy["thief_iframes"] = 20
                        elif enemy_type == "boar" and _working_copy.get("boar_iframes", 0) <= 0:
                            _working_copy["boar_hp"] -= 1
                            _working_copy["boar_iframes"] = 20
                        new_dogs.append((dx, dy))
                    else:
                        step = 1.0
                        dist_x = tx - dx
                        dist_y = ty - dy
                        length = math.hypot(dist_x, dist_y)
                        if length > 0:
                            new_dogs.append((dx + (dist_x / length) * step, dy + (dist_y / length) * step))
                        else:
                            new_dogs.append((dx, dy))
                else:
                    new_dogs.append((dx, dy))
            _working_copy["dogs"] = new_dogs

            # Skip early if all dead
            if not enemies_active:
                if _working_copy.get("thieves_spawned", 0) >= _working_copy.get("max_thieves", 1) and \
                   _working_copy.get("boars_spawned", 0) >= _working_copy.get("max_boars", 0):
                    _working_copy["last_msg"] = "所有敵人已被消滅，提早迎接清晨！"
                    return _end_night(_working_copy)
                    
        return _working_copy

    elif action == "start_night":
        if _working_copy["phase"] == "day":
            crop_income = 0
            for c_pos in _working_copy["crops"]:
                data = _working_copy["crop_data"].get(c_pos)
                if data:
                    if data["stage"] >= data["max_stage"]:
                        crop_income += CROP_INFO[data["type"]]["yield"]
                    else:
                        data["stage"] += 1
                        
            if crop_income > 0:
                _working_copy["money"] += crop_income
                income_msg = f" (成熟收益 ${crop_income})"
            else:
                income_msg = ""
                
            _working_copy["phase"] = "night"
            _working_copy["time_left"] = 60
            
            _working_copy["thief_pos"] = None
            _working_copy["thief_spawn_cooldown"] = 30
            _working_copy["thieves_spawned"] = 0
            _working_copy["max_thieves"] = 1 + _working_copy["day_count"] // 2
            
            _working_copy["boar_pos"] = None
            _working_copy["boar_spawn_cooldown"] = 60
            _working_copy["boars_spawned"] = 0
            # Boars appear after day 2 or if prosperity is high
            if _working_copy["day_count"] >= 2 or _working_copy["prosperity_score"] > 0:
                _working_copy["max_boars"] = 1 + _working_copy["day_count"] // 3
            else:
                _working_copy["max_boars"] = 0
                
            _working_copy["last_msg"] = f"夜晚降臨！今晚有 {_working_copy['max_thieves']} 小偷, {_working_copy['max_boars']} 野豬！{income_msg}"
            
    elif action.startswith("use_hoe_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if pos[0] >= 50:
            _working_copy["last_msg"] = "農田只能開墾在左側農田區！"
            return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]) and pos not in _working_copy["farmland"]:
            _working_copy["building_tasks"].append({"type": "farmland", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["last_msg"] = "開始開墾農田..."
            
    elif action.startswith("use_scythe_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        
        if pos in _working_copy["crops"]:
            data = _working_copy["crop_data"].get(pos)
            if data and data["stage"] >= data["max_stage"]:
                _working_copy["crops"].remove(pos)
                del _working_copy["crop_data"][pos]
                crop_type = data["type"]
                
                r = random.random()
                if r < 0.05: grade = "legendary"
                elif r < 0.15: grade = "epic"
                elif r < 0.40: grade = "rare"
                else: grade = "normal"
                
                _working_copy["inventory"][crop_type][grade] += 1
                
                grades_tw = {"normal": "一般", "rare": "稀有", "epic": "史詩", "legendary": "傳奇"}
                _working_copy["last_msg"] = f"收割成功！獲得 {grades_tw[grade]}品質 的 {CROP_NAMES.get(crop_type, crop_type)}。"
            else:
                _working_copy["last_msg"] = "作物還沒成熟，無法收割。"
        else:
            _working_copy["last_msg"] = "這裡沒有作物。"
            
    elif action.startswith("plant_crop_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: 
            crop_type = parts[2]
            pos = (int(parts[3]), int(parts[4]))
        except: return _working_copy
        if pos[0] >= 50:
            _working_copy["last_msg"] = "作物只能種植在左側農田區！"
            return _working_copy
        if crop_type not in CROP_INFO: return _working_copy
        
        req_level = CROP_INFO[crop_type].get("level_req", 1)
        if _working_copy["farm_level"] < req_level:
            _working_copy["last_msg"] = f"農場等級不足！需要等級 {req_level} 才能種植 {CROP_NAMES.get(crop_type, crop_type)}。"
            return _working_copy
            
        price = CROP_INFO[crop_type]["price"]
        if _working_copy["money"] < price: return _working_copy
        if pos in _working_copy["farmland"] and pos not in _working_copy["crops"]:
            if not any(t["type"] == "crop" and t["pos"] == pos for t in _working_copy["building_tasks"]):
                _working_copy["building_tasks"].append({"type": "crop", "crop_type": crop_type, "pos": pos, "progress": 0, "max_progress": 3})
                _working_copy["money"] -= price
                _working_copy["last_msg"] = f"開始種植 {CROP_NAMES.get(crop_type, crop_type)}..."

    elif action.startswith("build_decor_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try:
            decor_type = parts[2]
            pos = (int(parts[3]), int(parts[4]))
        except: return _working_copy
        
        if pos[0] < 50:
            _working_copy["last_msg"] = "景觀物只能佈置在右側佈置區！"
            return _working_copy
            
        if decor_type not in DECOR_INFO: return _working_copy
        price = DECOR_INFO[decor_type]["price"]
        if _working_copy["money"] < price: return _working_copy
        
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["building_tasks"].append({"type": "decor", "decor_type": decor_type, "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= price
            _working_copy["last_msg"] = f"開始佈置 {DECOR_NAMES.get(decor_type, decor_type)}..."

    elif action.startswith("build_fence_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if pos[0] >= 50:
            _working_copy["last_msg"] = "圍欄只能蓋在左側農田區！"
            return _working_copy
        if _working_copy.get("wood", 0) < 1: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            if not _can_build_fence(_working_copy, pos):
                _working_copy["last_msg"] = "無法建造！不能將農田完全封死！"
                return _working_copy
            if not any(t["type"] == "fence" and t["pos"] == pos for t in _working_copy["building_tasks"]):
                _working_copy["building_tasks"].append({"type": "fence", "pos": pos, "progress": 0, "max_progress": 2})
                _working_copy["wood"] -= 1
                _working_copy["last_msg"] = "消耗 1 木材，開始加裝木圍欄..."
                
    elif action.startswith("place_trap_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 50: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1], include_crops=False):
            _working_copy["building_tasks"].append({"type": "trap", "pos": pos, "progress": 0, "max_progress": 1})
            _working_copy["money"] -= 50
            _working_copy["last_msg"] = "設置了捕獸夾！"
            
    elif action.startswith("place_dog_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("dogs", [])) >= 10: return _working_copy
        price = 0 if _working_copy.get("free_dog") else 200
        if _working_copy["money"] < price: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["building_tasks"].append({"type": "dog", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= price
            _working_copy["free_dog"] = False
            _working_copy["last_msg"] = "呼叫看門狗..."
            
    elif action.startswith("use_axe_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        
        hit_tree = None
        for tx, ty in _working_copy.get("trees", []):
            if _rects_overlap(pos[0], pos[1], ITEM_SIZE, ITEM_SIZE, tx, ty, ITEM_SIZE, ITEM_SIZE):
                hit_tree = (tx, ty)
                break
                
        if hit_tree:
            _working_copy["trees"].remove(hit_tree)
            _working_copy["wood"] = _working_copy.get("wood", 0) + 1
            _working_copy["last_msg"] = "伐木成功！獲得 1 單位的木材。"
        else:
            _working_copy["last_msg"] = "這裡沒有樹木可以砍伐。"
            
    elif action.startswith("use_shovel_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if pos in _working_copy["crops"]:
            _working_copy["crops"].remove(pos)
            if pos in _working_copy["crop_data"]: del _working_copy["crop_data"][pos]
            _working_copy["last_msg"] = "移除了農田！"
        elif any(f[0] == pos[0] and f[1] == pos[1] for f in _working_copy["fences"]):
            fence = next(f for f in _working_copy["fences"] if f[0] == pos[0] and f[1] == pos[1])
            _working_copy["fences"].remove(fence)
            _working_copy["last_msg"] = "移除了木圍欄！"
        elif any(d[0] == pos[0] and d[1] == pos[1] for d in _working_copy["decorations"]):
            decor = next(d for d in _working_copy["decorations"] if d[0] == pos[0] and d[1] == pos[1])
            _working_copy["decorations"].remove(decor)
            _update_prosperity_and_level(_working_copy)
            _working_copy["last_msg"] = "移除了景觀物！"
        elif pos in _working_copy.get("trees", []):
            _working_copy["trees"].remove(pos)
            _working_copy["wood"] = _working_copy.get("wood", 0) + 1
            _working_copy["last_msg"] = "砍伐樹木，獲得 1 木材！"
        else:
            tasks = [t for t in _working_copy["building_tasks"] if t["pos"] == pos]
            if tasks:
                _working_copy["building_tasks"].remove(tasks[0])
                _working_copy["last_msg"] = "取消了建造！"

    return _working_copy

def _spawn_thief(state):
    import math
    cx, cy = 25, 50 # Target left zone (0-50)
    if state["crops"]:
        cx = sum(c[0] for c in state["crops"]) // len(state["crops"])
        cy = sum(c[1] for c in state["crops"]) // len(state["crops"])
    # Spawn from left edge
    ty = random.randint(0, GRID_H - ITEM_SIZE)
    tx = 0
    return (tx, ty)

def _spawn_boar(state):
    import math
    # Spawn from right edge
    ty = random.randint(0, GRID_H - ITEM_SIZE)
    tx = GRID_W - ITEM_SIZE
    return (tx, ty)

def _simulate_night_path(state, enemy_type):
    if enemy_type == "thief":
        ex, ey = state["thief_pos"]
        targets = [c for c in state.get("crops", []) if state["crop_data"].get(c, {}).get("stage", 0) >= state["crop_data"].get(c, {}).get("max_stage", 1)]
        if not targets:
            targets = state.get("crops", [])
    elif enemy_type == "boar":
        ex, ey = state["boar_pos"]
        # Targets are decors, prioritize highest prosperity
        decors = state.get("decorations", [])
        if decors:
            max_pros = max(DECOR_INFO.get(d[2], {}).get("prosperity", 0) for d in decors)
            targets = [(d[0], d[1]) for d in decors if DECOR_INFO.get(d[2], {}).get("prosperity", 0) == max_pros]
        else:
            targets = []

    if not targets: return [], None
        
    best_target = None
    min_dist = float('inf')
    for t_pos in targets:
        tcx, tcy = t_pos[0], t_pos[1]
        dist = math.hypot(tcx - ex, tcy - ey)
        if dist < min_dist:
            min_dist = dist
            best_target = t_pos
            
    if best_target is None: return [], None
    
    start_grid = (int(ex // 5), int(ey // 5))
    target_grid = (int(best_target[0] // 5), int(best_target[1] // 5))
    
    queue = [start_grid]
    came_from = {start_grid: None}
    
    while queue:
        curr = queue.pop(0)
        if curr == target_grid: break
            
        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
            nx, ny = curr[0] + dx, curr[1] + dy
            if 0 <= nx <= 20 and 0 <= ny <= 20:
                if (nx, ny) not in came_from:
                    px, py = nx * 5, ny * 5
                    # Target itself might be an obstacle, so allow stepping on target
                    if (nx, ny) == target_grid or not _is_obstacle(state, px, py):
                        came_from[(nx, ny)] = curr
                        queue.append((nx, ny))
                        
    if target_grid not in came_from:
        return [(best_target[0], best_target[1])], best_target
        
    path = []
    curr = target_grid
    while curr != start_grid and curr is not None:
        if curr == target_grid: path.append((best_target[0], best_target[1]))
        else: path.append((curr[0] * 5, curr[1] * 5))
        curr = came_from[curr]
        
    path.reverse()
    return path, best_target

def is_terminal(state: GameState) -> bool:
    return state.get("status") == "game_over"
