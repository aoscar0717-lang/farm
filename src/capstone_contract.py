import random
import math
from copy import deepcopy
from typing import Any

GameState = dict[str, Any]

ITEM_SIZE = 10
GRID_W = 100
GRID_H = 100

CROP_INFO = {
    "tomato": {"price": 30, "growth_time": 1, "yield": 60},
    "carrot": {"price": 50, "growth_time": 2, "yield": 120},
    "corn": {"price": 100, "growth_time": 2, "yield": 250},
    "pumpkin": {"price": 200, "growth_time": 3, "yield": 600}
}

def new_game(seed: int = 0) -> GameState:
    random.seed(seed)
    
    state: GameState = {
        "phase": "day",                 
        "crops": [],      
        "crop_data": {}, 
        "fences": [], 
        "scarecrows": [], 
        "dogs": [],
        "cats": [],
        "geese": [],
        "owls": [],
        "money": 500,
        "time_left": 10,
        "day_count": 1,
        "thief_pos": (-100, -100),
        "thief_path": [],
        "target_crop": None, 
        "thief_hp": 0,
        "free_dog": False,
        "status": "playing",            
        "last_msg": "開放世界：按 [B] 打開商店選購道具！" 
    }
    
    return state

def _rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2):
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

def _is_occupied(state, x, y, size=ITEM_SIZE, include_crops=True):
    if x < 0 or x + size > GRID_W or y < 0 or y + size > GRID_H:
        return True
    
    all_entities = state["fences"] + state["dogs"] + state.get("cats",[]) + state.get("geese",[]) + state.get("owls",[])
    if include_crops:
        all_entities += state["crops"]
    for ex, ey in all_entities:
        if _rects_overlap(x, y, size, size, ex, ey, ITEM_SIZE, ITEM_SIZE):
            return True
            
    return False

def apply_action(state: GameState, action: str) -> GameState:
    if state["status"] != "playing":
        return state
        
    _working_copy = deepcopy(state)
    
    if action == "tick":
        if _working_copy["phase"] == "day":
            _working_copy["time_left"] -= 1
            if _working_copy["time_left"] <= 0:
                return apply_action(_working_copy, "start_night")
            # Cat random money event
            cats_count = len(_working_copy.get("cats", []))
            if cats_count > 0:
                if random.random() < (cats_count * 0.05): 
                    _working_copy["money"] += 5
                    _working_copy["last_msg"] = "招財貓在田裡撿到了 $5！"
        return _working_copy
        
    elif action == "night_tick":
        if _working_copy["phase"] == "night":
            tx, ty = _working_copy["thief_pos"]
            
            if _working_copy.get("thief_iframes", 0) > 0:
                _working_copy["thief_iframes"] -= 1
            
            # Dog AI
            new_dogs = []
            thief_bitten = False
            for dx, dy in _working_copy["dogs"]:
                if tx >= 0 and _working_copy["thief_hp"] > 0:
                    if _rects_overlap(dx, dy, ITEM_SIZE, ITEM_SIZE, tx, ty, ITEM_SIZE, ITEM_SIZE):
                        if _working_copy.get("thief_iframes", 0) <= 0:
                            thief_bitten = True
                        new_dogs.append((dx, dy))
                    else:
                        step = 1.0
                        dist_x = tx - dx
                        dist_y = ty - dy
                        length = math.hypot(dist_x, dist_y)
                        if length > 0:
                            dx += (dist_x / length) * step
                            dy += (dist_y / length) * step
                        new_dogs.append((dx, dy))
                else:
                    new_dogs.append((dx, dy))
            _working_copy["dogs"] = new_dogs
            
            if thief_bitten:
                _working_copy["thief_hp"] -= 1
                _working_copy["thief_iframes"] = 30
                if _working_copy["thief_hp"] <= 0:
                    _working_copy["last_msg"] = "看門狗成功擊退小偷！獲得獎勵 $200"
                    _working_copy["money"] += 200
                    _working_copy["phase"] = "day"
                    _working_copy["day_count"] += 1
                    _working_copy["time_left"] = 10
                    _working_copy["thief_pos"] = (-100, -100)
                    _working_copy["thief_path"] = []
                    _working_copy["target_crop"] = None
                    return _working_copy
                else:
                    _working_copy["last_msg"] = f"看門狗咬了小偷！小偷剩餘血量: {_working_copy['thief_hp']}"

            # Thief Movement
            if _working_copy.get("thief_path"):
                target = _working_copy["thief_path"][0]
                dist_x = target[0] - tx
                dist_y = target[1] - ty
                length = math.hypot(dist_x, dist_y)
                
                # Goose slow down effect
                geese_count = len(_working_copy.get("geese", []))
                speed = max(0.3, 0.8 - geese_count * 0.1)
                
                if length <= speed:
                    _working_copy["thief_pos"] = _working_copy["thief_path"].pop(0)
                else:
                    tx += (dist_x / length) * speed
                    ty += (dist_y / length) * speed
                    _working_copy["thief_pos"] = (tx, ty)
            else:
                if _working_copy.get("target_crop"):
                    target = _working_copy["target_crop"]
                    if target in _working_copy.get("scarecrows", []):
                        _working_copy["scarecrows"].remove(target)
                        _working_copy["last_msg"] = "小偷摧毀了稻草人並逃跑了！"
                    elif target in _working_copy["crops"]:
                        _working_copy["crops"].remove(target)
                        if target in _working_copy["crop_data"]:
                            del _working_copy["crop_data"][target]
                        _working_copy["last_msg"] = "糟糕！昨晚有一塊農田被小偷毀了！"
                else:
                    _working_copy["last_msg"] = "小偷找不到目標，無聊地離開了。"
                    
                _working_copy["phase"] = "day"
                _working_copy["day_count"] += 1
                _working_copy["time_left"] = 10
                _working_copy["thief_pos"] = (-100, -100)
                _working_copy["thief_path"] = []
                _working_copy["target_crop"] = None
                
        return _working_copy
        
    elif action.startswith("plant_crop_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: 
            crop_type = parts[2]
            pos = (int(parts[3]), int(parts[4]))
        except: return _working_copy
        
        if crop_type not in CROP_INFO: return _working_copy
        price = CROP_INFO[crop_type]["price"]
        
        if _working_copy["money"] < price: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["crops"].append(pos)
            _working_copy["crop_data"][pos] = {"type": crop_type, "stage": 0, "max_stage": CROP_INFO[crop_type]["growth_time"]}
            _working_copy["money"] -= price
            _working_copy["last_msg"] = f"種植了 {crop_type}！"

    elif action.startswith("build_fence_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 100: return _working_copy
        # Must be on empty land
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["fences"].append(pos)
            _working_copy["money"] -= 100
            _working_copy["last_msg"] = "建造了木圍欄！"
            
    elif action.startswith("build_scarecrow_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 150: return _working_copy
        # Must place ON a crop
        if pos in _working_copy["crops"] and pos not in _working_copy.get("scarecrows", []):
            _working_copy["scarecrows"].append(pos)
            _working_copy["money"] -= 150
            _working_copy["last_msg"] = "放置了稻草人誘餌！"

    elif action.startswith("use_fertilizer_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 80: return _working_copy
        if pos in _working_copy["crops"]:
            data = _working_copy["crop_data"][pos]
            if data["stage"] < data["max_stage"]:
                data["stage"] = data["max_stage"]
                _working_copy["money"] -= 80
                _working_copy["last_msg"] = "使用了魔法肥料，作物瞬間成熟！"
                
    elif action.startswith("use_shovel_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if pos in _working_copy["crops"]:
            _working_copy["crops"].remove(pos)
            if pos in _working_copy["crop_data"]: del _working_copy["crop_data"][pos]
            if pos in _working_copy.get("scarecrows", []): _working_copy["scarecrows"].remove(pos)
            _working_copy["last_msg"] = "移除了農田！"
        elif pos in _working_copy["fences"]:
            _working_copy["fences"].remove(pos)
            _working_copy["last_msg"] = "移除了木圍欄！"

    elif action.startswith("place_dog_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("dogs", [])) >= 10:
            _working_copy["last_msg"] = "已達看門狗數量上限 (10隻)！"
            return _working_copy
        price = 0 if _working_copy.get("free_dog") else 200
        if _working_copy["money"] < price: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["dogs"].append(pos)
            _working_copy["money"] -= price
            _working_copy["free_dog"] = False
            _working_copy["last_msg"] = "看門狗放置成功！"

    elif action.startswith("place_cat_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("cats", [])) >= 10:
            _working_copy["last_msg"] = "已達貓咪數量上限 (10隻)！"
            return _working_copy
        if _working_copy["money"] < 150: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["cats"].append(pos)
            _working_copy["money"] -= 150
            _working_copy["last_msg"] = f"貓咪放置成功！白天有機率撿錢！"

    elif action.startswith("place_goose_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("geese", [])) >= 5:
            _working_copy["last_msg"] = "已達戰鬥大鵝數量上限 (5隻)！"
            return _working_copy
        if _working_copy["money"] < 300: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["geese"].append(pos)
            _working_copy["money"] -= 300
            _working_copy["last_msg"] = f"戰鬥大鵝放置成功！夜晚緩速小偷！"

    elif action.startswith("place_owl_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("owls", [])) >= 5:
            _working_copy["last_msg"] = "已達守夜貓頭鷹數量上限 (5隻)！"
            return _working_copy
        if _working_copy["money"] < 250: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["owls"].append(pos)
            _working_copy["money"] -= 250
            _working_copy["last_msg"] = f"守夜貓頭鷹放置成功！"

    elif action.startswith("click_"):
        if _working_copy["phase"] == "night" and _working_copy["thief_path"]:
            _working_copy["thief_hp"] -= 1
            if _working_copy["thief_hp"] <= 0:
                _working_copy["last_msg"] = "成功趕走小偷！獲得獎勵 $200"
                _working_copy["money"] += 200
                _working_copy["phase"] = "day"
                if _working_copy["day_count"] == 1:
                    _working_copy["free_dog"] = True
                    _working_copy["last_msg"] += " 鄰居送來禮物：免費看門狗！"
                _working_copy["day_count"] += 1
                _working_copy["time_left"] = 10
                _working_copy["thief_pos"] = (-100, -100)
                _working_copy["thief_path"] = []
                _working_copy["target_crop"] = None
            else:
                _working_copy["last_msg"] = f"擊中小偷！小偷還剩 {_working_copy['thief_hp']} 滴血！"

    elif action == "start_night":
        if _working_copy["phase"] == "day":
            if len(_working_copy["crops"]) == 0:
                _working_copy["last_msg"] = "沒有農田，小偷不感興趣。平安度過一天！"
                _working_copy["day_count"] += 1
                _working_copy["time_left"] = 10
            else:
                crop_income = 0
                for c_pos in _working_copy["crops"]:
                    data = _working_copy["crop_data"].get(c_pos)
                    if data:
                        if data["stage"] >= data["max_stage"]:
                            crop_income += CROP_INFO[data["type"]]["yield"]
                        else:
                            data["stage"] += 1
                            
                total_income = crop_income
                
                income_msg = ""
                if total_income > 0:
                    _working_copy["money"] += total_income
                    income_msg = f" (成熟農產收益 ${crop_income})"
                    
                owl_chance = len(_working_copy["owls"]) * 0.25
                if random.random() < owl_chance:
                    _working_copy["last_msg"] = f"貓頭鷹威嚇了小偷！小偷不敢靠近。獲得防禦獎勵 $200{income_msg}"
                    _working_copy["money"] += 200
                    _working_copy["day_count"] += 1
                    _working_copy["time_left"] = 10
                    return _working_copy

                _working_copy["phase"] = "night"
                _working_copy["thief_pos"] = _spawn_thief()
                _working_copy["thief_hp"] = 3
                _working_copy["last_msg"] = f"夜晚降臨！小偷出現了！{income_msg}"
                
                _working_copy["thief_path"], _working_copy["target_crop"] = _simulate_night_path(_working_copy)
                
    return _working_copy

def _spawn_thief():
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top": return (random.randint(0, GRID_W//ITEM_SIZE - 1)*ITEM_SIZE, 0)
    elif side == "bottom": return (random.randint(0, GRID_W//ITEM_SIZE - 1)*ITEM_SIZE, GRID_H - ITEM_SIZE)
    elif side == "left": return (0, random.randint(0, GRID_H//ITEM_SIZE - 1)*ITEM_SIZE)
    else: return (GRID_W - ITEM_SIZE, random.randint(0, GRID_H//ITEM_SIZE - 1)*ITEM_SIZE)

def _simulate_night_path(state):
    tx, ty = state["thief_pos"]
    gx, gy = tx // ITEM_SIZE, ty // ITEM_SIZE
    
    targets = state.get("scarecrows", [])
    if not targets:
        targets = state["crops"]
        
    if not targets:
        return [], None
        
    obstacles = set()
    for fx, fy in state["fences"]:
        obstacles.add((fx // ITEM_SIZE, fy // ITEM_SIZE))
        
    best_path = None
    best_target = None
    
    for t_pos in targets:
        tcx, tcy = t_pos[0] // ITEM_SIZE, t_pos[1] // ITEM_SIZE
        
        queue = [(gx, gy)]
        came_from = {(gx, gy): None}
        
        found = False
        while queue:
            current = queue.pop(0)
            if current == (tcx, tcy):
                found = True
                break
                
            for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                nx, ny = current[0] + dx, current[1] + dy
                
                if nx < 0 or nx >= GRID_W // ITEM_SIZE or ny < 0 or ny >= GRID_H // ITEM_SIZE:
                    continue
                    
                if (nx, ny) in obstacles and (nx, ny) != (tcx, tcy):
                    continue
                    
                if (nx, ny) not in came_from:
                    queue.append((nx, ny))
                    came_from[(nx, ny)] = current
                    
        if found:
            path = []
            curr = (tcx, tcy)
            while curr != (gx, gy):
                path.append((curr[0] * ITEM_SIZE, curr[1] * ITEM_SIZE))
                curr = came_from[curr]
            path.reverse()
            
            if best_path is None or len(path) < len(best_path):
                best_path = path
                best_target = t_pos
                
    if best_path is None:
        return [], None
        
    return best_path, best_target

def is_terminal(state: GameState) -> bool:
    if state.get("status") == "game_over":
        return True
    # 如果沒有農田且錢不夠買最便宜的番茄種子 (30)，就 Game Over
    if len(state.get("crops", [])) == 0 and state.get("money", 0) < 30:
        return True
    return False