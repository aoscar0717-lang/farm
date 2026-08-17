import random
import math
from copy import deepcopy
from typing import Any

GameState = dict[str, Any]

ITEM_SIZE = 10
GRID_W = 100
GRID_H = 100

CROP_INFO = {
    "tomato": {"price": 30, "growth_time": 1, "yield": 90},
    "carrot": {"price": 50, "growth_time": 2, "yield": 180},
    "corn": {"price": 100, "growth_time": 2, "yield": 375},
    "pumpkin": {"price": 200, "growth_time": 3, "yield": 900}
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
        "building_tasks": [],
        "money": 500,
        "time_left": 120,
        "day_count": 1,
        "thief_pos": (-100, -100),
        "thief_path": [],
        "target_crop": None, 
        "thief_hp": 0,
        "thief_iframes": 0,
        "thief_spawn_cooldown": 0,
        "thieves_spawned": 0,
        "max_thieves": 2,
        "free_dog": False,
        "status": "playing",            
        "last_msg": "開放世界：按 [B] 打開商店選購道具！白天時間 120 秒。" 
    }
    
    return state

def _rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2):
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

def _is_occupied(state, x, y, size=ITEM_SIZE, include_crops=True):
    if x < 0 or x + size > GRID_W or y < 0 or y + size > GRID_H:
        return True
    
    all_entities = [(f[0], f[1]) for f in state["fences"]] + state["dogs"] + state.get("cats",[]) + state.get("geese",[]) + state.get("owls",[])
    for task in state["building_tasks"]:
        if task["type"] != "fence":
            all_entities.append(task["pos"])
            
    if include_crops:
        all_entities += state["crops"]
        
    for ex, ey in all_entities:
        if _rects_overlap(x, y, size, size, ex, ey, ITEM_SIZE, ITEM_SIZE):
            return True
            
    return False

def _end_night(state):
    rent = 20 + (state["day_count"] - 1) * 10
    state["money"] -= rent
    
    building_crops = len([t for t in state.get("building_tasks", []) if t["type"] == "crop"])
    if len(state["crops"]) + building_crops == 0 or state["money"] < 0:
        state["status"] = "game_over"
        state["last_msg"] = f"結算失敗！支付租金 ${rent} 後破產或無農田。Game Over！"
    else:
        # 如果前面有設定過 last_msg (例如提早結束的訊息)，就保留並附加租金訊息
        if state.get("last_msg", "").startswith("所有小偷"):
            state["last_msg"] = f"{state['last_msg']} 支付每日租金 ${rent}。"
        else:
            state["last_msg"] = f"夜晚結束！支付每日租金 ${rent}。"
        
        state["phase"] = "day"
        state["day_count"] += 1
        state["time_left"] = 120
        
    state["thief_pos"] = (-100, -100)
    state["thief_path"] = []
    state["target_crop"] = None
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
                    _working_copy["crops"].append(pos)
                    _working_copy["crop_data"][pos] = {"type": task["crop_type"], "stage": 0, "max_stage": CROP_INFO[task["crop_type"]]["growth_time"]}
                elif t_type == "fence": _working_copy["fences"].append((pos[0], pos[1], 3))
                elif t_type == "scarecrow": _working_copy["scarecrows"].append(pos)
                elif t_type == "dog": _working_copy["dogs"].append(pos)
                elif t_type == "cat": _working_copy["cats"].append(pos)
                elif t_type == "goose": _working_copy["geese"].append(pos)
                elif t_type == "owl": _working_copy["owls"].append(pos)
            else:
                new_tasks.append(task)
        _working_copy["building_tasks"] = new_tasks

        if _working_copy["phase"] == "day":
            _working_copy["time_left"] -= 1
            if _working_copy["time_left"] <= 0:
                return apply_action(_working_copy, "start_night")
                
            cats_count = len(_working_copy.get("cats", []))
            if cats_count > 0:
                if random.random() < (cats_count * 0.05): 
                    _working_copy["money"] += 5
                    
        elif _working_copy["phase"] == "night":
            _working_copy["time_left"] -= 1
            if _working_copy["time_left"] <= 0:
                return _end_night(_working_copy)
                
        return _working_copy
        
    elif action == "night_tick":
        if _working_copy["phase"] == "night":
            tx, ty = _working_copy["thief_pos"]
            
            if tx < 0:
                if _working_copy.get("thieves_spawned", 0) >= _working_copy.get("max_thieves", 2):
                    # 今晚的小偷已經出完了，且場上已無小偷，直接跳到白天
                    _working_copy["last_msg"] = "所有小偷已被消滅，提早迎接清晨！"
                    return _end_night(_working_copy)
                    
                if _working_copy.get("thief_spawn_cooldown", 0) > 0:
                    _working_copy["thief_spawn_cooldown"] -= 1
                    return _working_copy
                
                _working_copy["thief_pos"] = _spawn_thief()
                _working_copy["thieves_spawned"] = _working_copy.get("thieves_spawned", 0) + 1
                _working_copy["thief_hp"] = 3 + (_working_copy["day_count"] // 3) # 血量隨天數微幅增加
                _working_copy["thief_iframes"] = 0
                _working_copy["thief_path"], _working_copy["target_crop"] = _simulate_night_path(_working_copy)
                tx, ty = _working_copy["thief_pos"]
                if tx < 0:
                    return _working_copy

            if _working_copy.get("thief_iframes", 0) > 0:
                _working_copy["thief_iframes"] -= 1
            
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
                    _working_copy["last_msg"] = "看門狗擊敗了小偷！獲得獎勵 $100。下一隻小偷準備中..."
                    _working_copy["money"] += 100
                    _working_copy["thief_pos"] = (-100, -100)
                    _working_copy["thief_path"] = []
                    _working_copy["target_crop"] = None
                    # 計算下一個小偷的冷卻時間 (基礎 3 秒 + 隨機，隨天數縮短)
                    base_cooldown = max(30, 150 - _working_copy["day_count"] * 10)
                    _working_copy["thief_spawn_cooldown"] = base_cooldown + random.randint(0, 30)
                    
                    if _working_copy["day_count"] == 1 and not _working_copy.get("first_blood"):
                        _working_copy["free_dog"] = True
                        _working_copy["first_blood"] = True
                        _working_copy["last_msg"] += " 鄰居送來禮物：免費看門狗！"
                    return _working_copy

            if tx >= 0:
                if _working_copy.get("thief_path"):
                    target = _working_copy["thief_path"][0]
                    dist_x = target[0] - tx
                    dist_y = target[1] - ty
                    length = math.hypot(dist_x, dist_y)
                    
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
                        fence = next((f for f in _working_copy.get("fences", []) if f[0] == target[0] and f[1] == target[1]), None)
                        
                        if fence:
                            _working_copy["fences"].remove(fence)
                            if len(fence) > 2 and fence[2] > 1:
                                _working_copy["fences"].append((fence[0], fence[1], fence[2] - 1))
                                _working_copy["last_msg"] = f"小偷撞上了木圍欄！小偷逃跑了，圍欄剩餘耐久: {fence[2] - 1}"
                            else:
                                _working_copy["last_msg"] = "小偷破壞了木圍欄並被困住逃跑了！圍欄已損毀！"
                        else:
                            if target in _working_copy.get("scarecrows", []):
                                _working_copy["scarecrows"].remove(target)
                                _working_copy["last_msg"] = "小偷摧毀了稻草人並逃跑了！"
                            elif target in _working_copy["crops"]:
                                _working_copy["crops"].remove(target)
                                if target in _working_copy["crop_data"]:
                                    del _working_copy["crop_data"][target]
                                _working_copy["last_msg"] = "糟糕！有一塊農田被小偷毀了！"
                    
                    _working_copy["thief_pos"] = (-100, -100)
                    _working_copy["thief_path"] = []
                    _working_copy["target_crop"] = None
                    base_cooldown = max(30, 150 - _working_copy["day_count"] * 10)
                    _working_copy["thief_spawn_cooldown"] = base_cooldown + random.randint(0, 30)
                    
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
            _working_copy["building_tasks"].append({"type": "crop", "crop_type": crop_type, "pos": pos, "progress": 0, "max_progress": 3})
            _working_copy["money"] -= price
            _working_copy["last_msg"] = f"開始種植 {crop_type}..."

    elif action.startswith("build_fence_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 100: return _working_copy
        if pos in _working_copy["crops"]:
            if not any(f[0] == pos[0] and f[1] == pos[1] for f in _working_copy.get("fences", [])):
                if not any(t["type"] == "fence" and t["pos"] == pos for t in _working_copy["building_tasks"]):
                    _working_copy["building_tasks"].append({"type": "fence", "pos": pos, "progress": 0, "max_progress": 2})
                    _working_copy["money"] -= 100
                    _working_copy["last_msg"] = "開始加裝木圍欄..."
            
    elif action.startswith("build_scarecrow_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 150: return _working_copy
        if pos in _working_copy["crops"] and pos not in _working_copy.get("scarecrows", []):
            if not any(t["type"] == "scarecrow" and t["pos"] == pos for t in _working_copy["building_tasks"]):
                _working_copy["building_tasks"].append({"type": "scarecrow", "pos": pos, "progress": 0, "max_progress": 2})
                _working_copy["money"] -= 150
                _working_copy["last_msg"] = "開始架設稻草人..."

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
        elif any(f[0] == pos[0] and f[1] == pos[1] for f in _working_copy["fences"]):
            fence = next(f for f in _working_copy["fences"] if f[0] == pos[0] and f[1] == pos[1])
            _working_copy["fences"].remove(fence)
            _working_copy["last_msg"] = "移除了木圍欄！"
        else:
            tasks = [t for t in _working_copy["building_tasks"] if t["pos"] == pos]
            if tasks:
                _working_copy["building_tasks"].remove(tasks[0])
                _working_copy["last_msg"] = "取消了建造！"

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

    elif action.startswith("place_cat_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("cats", [])) >= 10: return _working_copy
        if _working_copy["money"] < 150: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["building_tasks"].append({"type": "cat", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= 150
            _working_copy["last_msg"] = "呼叫貓咪..."

    elif action.startswith("place_goose_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("geese", [])) >= 5: return _working_copy
        if _working_copy["money"] < 300: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["building_tasks"].append({"type": "goose", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= 300
            _working_copy["last_msg"] = "呼叫戰鬥大鵝..."

    elif action.startswith("place_owl_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(_working_copy.get("owls", [])) >= 5: return _working_copy
        if _working_copy["money"] < 250: return _working_copy
        if not _is_occupied(_working_copy, pos[0], pos[1]):
            _working_copy["building_tasks"].append({"type": "owl", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= 250
            _working_copy["last_msg"] = "呼叫守夜貓頭鷹..."

    elif action.startswith("click_"):
        if _working_copy["phase"] == "night" and _working_copy["thief_path"]:
            _working_copy["thief_hp"] -= 1
            if _working_copy["thief_hp"] <= 0:
                _working_copy["last_msg"] = "成功趕走小偷！獲得獎勵 $200"
                _working_copy["money"] += 200
                _working_copy["thief_pos"] = (-100, -100)
                _working_copy["thief_path"] = []
                _working_copy["target_crop"] = None
                base_cooldown = max(30, 150 - _working_copy["day_count"] * 10)
                _working_copy["thief_spawn_cooldown"] = base_cooldown + random.randint(0, 30)
            else:
                _working_copy["last_msg"] = f"滑鼠擊中小偷！小偷還剩 {_working_copy['thief_hp']} 滴血！"

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
                
            owl_chance = len(_working_copy["owls"]) * 0.25
            if random.random() < owl_chance:
                _working_copy["last_msg"] = f"貓頭鷹威嚇了小偷群！今晚小偷不敢靠近。獲得防禦獎勵 $200{income_msg}"
                _working_copy["money"] += 200
                return _end_night(_working_copy)

            _working_copy["phase"] = "night"
            _working_copy["time_left"] = 60
            _working_copy["thief_pos"] = (-100, -100)
            _working_copy["thief_spawn_cooldown"] = 30 # 第一隻小偷 1 秒後才出現
            _working_copy["thieves_spawned"] = 0
            _working_copy["max_thieves"] = 1 + _working_copy["day_count"]
            _working_copy["last_msg"] = f"夜晚降臨！今晚預計有 {_working_copy['max_thieves']} 隻小偷，準備防禦！{income_msg}"
                
    return _working_copy

def _spawn_thief():
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top": return (random.randint(0, GRID_W//ITEM_SIZE - 1)*ITEM_SIZE, 0)
    elif side == "bottom": return (random.randint(0, GRID_W//ITEM_SIZE - 1)*ITEM_SIZE, GRID_H - ITEM_SIZE)
    elif side == "left": return (0, random.randint(0, GRID_H//ITEM_SIZE - 1)*ITEM_SIZE)
    else: return (GRID_W - ITEM_SIZE, random.randint(0, GRID_H//ITEM_SIZE - 1)*ITEM_SIZE)

def _simulate_night_path(state):
    tx, ty = state["thief_pos"]
    targets = state.get("scarecrows", [])
    if not targets:
        targets = state["crops"]
    if not targets: return [], None
        
    best_target = None
    min_dist = float('inf')
    for t_pos in targets:
        tcx, tcy = t_pos[0], t_pos[1]
        dist = math.hypot(tcx - tx, tcy - ty)
        if dist < min_dist:
            min_dist = dist
            best_target = t_pos
            
    if best_target is None: return [], None
    return [(best_target[0], best_target[1])], best_target

def is_terminal(state: GameState) -> bool:
    return state.get("status") == "game_over"