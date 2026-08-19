import random
import math
from copy import deepcopy
from typing import Any

GameState = dict[str, Any]

ITEM_SIZE = 10

# Farm and Decor are two independent maps, each with its own coordinate
# origin (0, 0) and its own GRID_W x GRID_H bounds. They do NOT share a
# coordinate line / world grid the way the previous "one map split by
# camera into two halves" version did.
GRID_W = 500
GRID_H = 500

CROP_INFO = {
    # growth_time = how many day->night transitions (see the "start_night"
    # handler below) a crop needs to reach max_stage. These now match what
    # the shop description has always promised ("1天/2天/3天成熟") instead
    # of all three secretly needing 5 nights regardless of type -- V1.1
    # balance pass, see DEBUG_LOG/AI_USE notes for the full before/after.
    "radish": {"price": 30, "growth_time": 1, "yield": 50, "level_req": 1},
    "carrot": {"price": 100, "growth_time": 2, "yield": 250, "level_req": 2},
    "pumpkin": {"price": 300, "growth_time": 3, "yield": 1000, "level_req": 3}
}

CROP_NAMES = {
    "radish": "白蘿蔔",
    "carrot": "胡蘿蔔",
    "pumpkin": "魔法南瓜"
}

DECOR_INFO = {
    "stone_path": {"price": 20, "prosperity": 5},
    "flower": {"price": 50, "prosperity": 15},
    "bench": {"price": 100, "prosperity": 35},
    "fountain": {"price": 300, "prosperity": 120},
    # Landscape expansion: 7 new decor items, all sourced from real,
    # visually-confirmed existing assets (see the analysis report). Price/
    # prosperity extend the existing small/mid/large curve above rather than
    # flattening everything to one number.
    "scarecrow": {"price": 30, "prosperity": 10},
    "crate": {"price": 25, "prosperity": 8},
    "bush": {"price": 20, "prosperity": 8},
    "rock": {"price": 60, "prosperity": 18},
    "sunflower": {"price": 80, "prosperity": 25},
    "pine_tree": {"price": 90, "prosperity": 28},
    "big_tree": {"price": 260, "prosperity": 95},
    # Landscape expansion round 2: 8 more decor items. Prices/prosperity
    # picked so the FULL merged curve (all 19 items sorted by price) stays
    # non-decreasing in prosperity -- see
    # tests/test_landscape_consistency.py::TestDecorInfoAndNames::test_price_curve_is_non_decreasing_with_prosperity.
    # A "leafy_tree" candidate was dropped during this round (see assets.py)
    # -- it would have reused the same sprite already drawn for the farm
    # zone's wild obstacle trees, making a paid decoration look identical
    # to unplaced world clutter.
    "stump": {"price": 12, "prosperity": 4},
    "mushroom": {"price": 16, "prosperity": 5},
    "picnic_basket": {"price": 22, "prosperity": 8},
    "woodpile": {"price": 28, "prosperity": 9},
    "picnic_blanket": {"price": 45, "prosperity": 13},
    "beehive": {"price": 70, "prosperity": 22},
    "garden_table": {"price": 105, "prosperity": 42},
    "fruit_tree": {"price": 150, "prosperity": 55},
}

DECOR_NAMES = {
    "stone_path": "石板路",
    "flower": "鮮花盆栽",
    "bench": "木製長椅",
    # Visual identity changed 小型噴泉 -> 風車 (windmill): the project has no
    # dedicated fountain/well art anywhere in its asset packs (checked
    # every pack), and the decoration's world sprite already reused the
    # windmill animation (spr_deco_windmill_strip9.png, see renderer.py's
    # _draw_decorations) -- renaming the label to match what's actually
    # drawn, per user decision, rather than pretending a windmill icon is
    # a fountain. price/prosperity in DECOR_INFO above are unchanged.
    "fountain": "風車",
    "scarecrow": "稻草人",
    "crate": "木箱",
    "bush": "灌木叢",
    "rock": "庭院石",
    "sunflower": "向日葵",
    "pine_tree": "松樹",
    "big_tree": "大樹",
    "stump": "樹墩",
    "mushroom": "蘑菇",
    "picnic_basket": "野餐籃",
    "woodpile": "柴堆",
    "picnic_blanket": "野餐墊",
    "beehive": "蜂箱",
    "garden_table": "庭院桌",
    "fruit_tree": "果樹",
}

# --- Fence combat tuning (goblin/thief vs. fence system) -------------------
# Fences are shared infrastructure between the farm and decor maps (same
# tuple shape, same build/removal code), so bumping FENCE_MAX_HP affects
# both zones' fences equally. The thief's attack behavior (below) was fixed
# first; the boar's matching fix (BOAR_FENCE_DAMAGE_PER_HIT /
# BOAR_FENCE_ATTACK_INTERVAL_TICKS, defined further down) came in the V1.1
# balance pass once the boar's fence-hit code turned out to have the exact
# same "no cooldown, damage every uncooled tick" bug the thief used to have
# -- see that block's comment for the before/after numbers.
FENCE_MAX_HP = 100
FENCE_DAMAGE_PER_HIT = 8
# main.py drives night_tick at roughly 30 calls/sec (33ms delay), so 30
# ticks between hits approximates the requested 1.0s attack interval.
# Ticks (not wall-clock seconds) are used to stay consistent with every
# other cooldown in this file (e.g. thief_iframes) and to keep apply_action
# fully deterministic for tests -- no real-time dependency in the contract
# layer.
FENCE_ATTACK_INTERVAL_TICKS = 30

# Bug fix: thief permanently frozen after squeezing through a single-tile
# gap in a fence wall (see thief_stuck_ticks' comment in _new_zone_state and
# _night_tick_thief's STATE_MOVING branch for the full mechanism). 5 ticks
# is a small fraction of FENCE_ATTACK_INTERVAL_TICKS (30) -- long enough
# that a normal one-tick graze while rounding a corner elsewhere resolves
# on its own well before this fires, short enough that a real geometric
# deadlock (which never resolves on its own) gets corrected almost
# immediately rather than leaving the thief visibly stuck for a while.
THIEF_STUCK_TICKS_THRESHOLD = 5

# --- V1.1 balance-fix additions -------------------------------------------
# The boar's fence-attack used to have no cooldown at all (see the original
# comment above this block, now out of date): it landed 1 dmg on *every*
# uncooled night_tick it spent blocked by a fence, i.e. ~30 dmg/sec at this
# file's ~30 ticks/sec cadence -- almost 4x the thief's post-rework 8 dmg/
# sec, and enough to grind down a full 100 HP fence in ~3.3 seconds instead
# of the intended ~12.5. That's a plain mechanism bug (missing cooldown),
# not a "boar is too strong" balance call -- the per-hit damage itself
# (1) is left exactly as it was; only the missing interval is being added,
# mirroring FENCE_ATTACK_INTERVAL_TICKS above.
BOAR_FENCE_DAMAGE_PER_HIT = 1
BOAR_FENCE_ATTACK_INTERVAL_TICKS = 30

# Decorations were always created with hp=3 (see _new_zone_state's comment
# on the "decorations" list shape), but nothing ever read that field: the
# boar's decor-destroy code removed a decoration outright the instant it
# arrived, regardless of hp. DECOR_MAX_HP documents that pre-existing (but
# previously-ignored) value; DECOR_DAMAGE_PER_HIT/DECOR_ATTACK_INTERVAL_TICKS
# give the boar the same cooldown-gated "gradual damage" attack against
# decorations that it (and the thief) now have against fences, instead of a
# one-hit kill the moment it arrives.
DECOR_MAX_HP = 3
DECOR_DAMAGE_PER_HIT = 1
DECOR_ATTACK_INTERVAL_TICKS = 30


def _new_zone_state() -> dict:
    """Shared shape for both maps. Farm actions only ever populate the
    crop/farmland fields and thief_*; decor actions only ever populate the
    decorations field and boar_*. Keeping both zones the same shape lets the
    obstacle/occupancy helpers below work on either zone without branching."""
    return {
        "crops": [],
        "crop_data": {},
        "farmland": [],
        "decorations": [],  # list of (x, y, type, hp)
        "fences": [],
        "traps": [],
        "dogs": [],
        "trees": [],
        "rocks": [],
        "building_tasks": [],

        # Farm-only: thief threat
        "thief_pos": None,
        "thief_path": [],
        "target_crop": None,
        "thief_hp": 0,
        "thief_iframes": 0,
        "thief_spawn_cooldown": 0,
        "thieves_spawned": 0,
        "max_thieves": 1,
        # Farm-only: thief-vs-fence AI state (see _night_tick_thief).
        # "moving": following thief_path toward its target as before.
        # "attacking_fence": stopped, landing cooldown-gated hits on
        # thief_attack_target_fence instead of moving.
        "thief_ai_state": "moving",
        "thief_attack_cooldown": 0,
        "thief_attack_target_fence": None,
        # Consecutive night_ticks the thief has been in "moving" state,
        # detected a fence blocking its tentative next step, but NOT
        # actually moved (see the fence_hit branch in _night_tick_thief).
        # Normally zero -- a real detour resolves within a tick or two as
        # the thief walks clear. It only climbs when the thief is wedged in
        # a gap exactly as wide as its own hitbox (destroyed-fence gap
        # between two still-standing posts on the same 10-unit grid the
        # fence hitboxes use) -- BFS pathfinding (point-sampled, see
        # _is_obstacle) reports the route as reachable, but the finer-
        # grained box collision the continuous movement below uses can
        # never actually complete that squeeze, so the same "found a
        # detour" verdict repeats every tick with zero progress. Past
        # THIEF_STUCK_TICKS_THRESHOLD, _night_tick_thief stops trusting the
        # detour verdict and attacks whatever fence is actually touching
        # it instead, guaranteeing forward progress (a destroyed fence
        # always eventually widens the gap) without touching pathfinding,
        # collision sizing, or fence HP.
        "thief_stuck_ticks": 0,
        # Ticks remaining to render a hit-shake/flash on the fence just
        # struck -- renderer-only concern, decremented in night_tick.
        "thief_hit_flash": 0,

        # Shared (farm + decor): fences that reached 0 HP but are still
        # playing their collapse animation before actually being removed
        # from `fences`. List of (x, y, ticks_remaining). Both the thief
        # (farm) and the boar (decor, since the V1.1 balance fix) populate
        # this; the renderer handles whatever ends up in here regardless of
        # which zone/enemy caused it.
        "collapsing_fences": [],

        # Decor-only: boar threat
        "boar_pos": None,
        "boar_path": [],
        "target_decor": None,
        "boar_hp": 0,
        "boar_iframes": 0,
        "boar_spawn_cooldown": 0,
        "boars_spawned": 0,
        "max_boars": 0,
        # V1.1: cooldown-gated attacks against whatever the boar is
        # currently stopped in front of (a blocking fence, or the
        # decoration it has arrived at) -- one shared timer, since a boar
        # is only ever doing one of those two things at a time. Mirrors
        # thief_attack_cooldown's role for the farm zone.
        "boar_attack_cooldown": 0,
        # Ticks remaining to render a hit-shake/flash -- renderer-only,
        # decremented in night_tick. target_decor doubles as "what's being
        # hit" for this purpose (it's only ever set while the boar is
        # traveling to or attacking that decoration).
        "boar_hit_flash": 0,
        # Decorations that hit 0 HP but are still playing their collapse
        # animation before being removed from `decorations` -- mirrors
        # collapsing_fences. List of (x, y, decor_type, ticks_remaining).
        "collapsing_decorations": [],
    }


def _generate_rocks(zone: dict) -> None:
    for _ in range(random.randint(5, 8)):
        rx = random.randint(2, GRID_W - 2)
        ry = random.randint(2, GRID_H - 2)
        if (rx, ry) not in zone["trees"] and (rx, ry) not in zone["rocks"]:
            zone["rocks"].append((rx, ry))


def new_game(seed: int = 0) -> GameState:
    random.seed(seed)

    state: GameState = {
        "phase": "day",
        "money": 500,
        "prosperity_score": 0,
        "farm_level": 1,

        "time_left": 120,
        "day_count": 1,

        "free_dog": False,
        "status": "playing",
        "last_msg": "歡迎來到農場！按 [B] 打開商店，用鋤頭[1]開墾農田，種植作物賺錢！",

        # Uncapped lifetime progression stat -- never resets, never caps.
        # There is no rent/Game Over anymore, so this (plus day_count itself)
        # is the long-run "how far have I gotten" number for endless play.
        "enemies_defeated": 0,

        "inventory": {
            "radish": {"normal": 0, "rare": 0, "epic": 0, "legendary": 0},
            "carrot": {"normal": 0, "rare": 0, "epic": 0, "legendary": 0},
            "pumpkin": {"normal": 0, "rare": 0, "epic": 0, "legendary": 0}
        },

        # Two fully independent maps.
        "farm": _new_zone_state(),
        "decor": _new_zone_state(),
    }

    # Auto-generation of trees has been disabled

    _generate_rocks(state["farm"])
    _generate_rocks(state["decor"])

    return state


def _rects_overlap(x1, y1, w1, h1, x2, y2, w2, h2):
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)


def _is_obstacle(zone, x, y):
    px, py = x * ITEM_SIZE, y * ITEM_SIZE
    for tx, ty in zone.get("trees", []):
        if _rects_overlap(px, py, ITEM_SIZE, ITEM_SIZE, tx, ty, ITEM_SIZE, ITEM_SIZE): return True
    for rx, ry in zone.get("rocks", []):
        if _rects_overlap(px, py, ITEM_SIZE, ITEM_SIZE, rx, ry, ITEM_SIZE, ITEM_SIZE): return True
    # Fences: every caller of _is_obstacle already passes x/y in the same
    # world-scale units fences are stored in (unlike trees/rocks above,
    # which get rescaled by ITEM_SIZE first) -- so this compares directly
    # against x, y, not px, py. It used to be an exact (x == f[0] and y ==
    # f[1]) equality check, which only ever flagged the *one* grid point a
    # fence sits on. Since pathfinding samples points 5 world-units apart
    # while a fence's real footprint is ITEM_SIZE=10 wide, that left a
    # sampling gap exactly 5 units to one side of every fence -- BFS could
    # always "see" a way through what should have been a solid wall made of
    # adjacently-built fences, which defeated the entire point of building
    # one. This is a point-in-rect test (is this exact sample point inside
    # the fence's real footprint), not a box-overlap test -- overlap would
    # treat every sample as if it were itself a 10-wide box, which inflates
    # a single fence into blocking its entire 3x3 neighborhood of sample
    # points instead of just the ~2x2 it actually occupies.
    for f in zone.get("fences", []):
        if f[0] <= x < f[0] + ITEM_SIZE and f[1] <= y < f[1] + ITEM_SIZE:
            return True
    return False


def _can_build_fence(zone, pos):
    # Only checks if it completely blocks crops (same rule the single-map
    # version used; decorations were never protected by this check either).
    temp_zone = deepcopy(zone)
    temp_zone["fences"].append((pos[0], pos[1], 3))

    targets = temp_zone.get("crops", [])
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
            if 0 <= nx <= GRID_W // 5 and 0 <= ny <= GRID_H // 5:
                if (nx, ny) not in visited:
                    px, py = nx * 5, ny * 5
                    if not _is_obstacle(temp_zone, px, py):
                        visited.add((nx, ny))
                        queue.append((nx, ny))

    return len(reached_crops) == len(targets)


def _is_occupied(zone, x, y, size=ITEM_SIZE, include_crops=True):
    if _is_obstacle(zone, x, y): return True

    all_entities = [(f[0], f[1]) for f in zone["fences"]] + zone["dogs"] + zone.get("traps", [])
    all_entities += [(d[0], d[1]) for d in zone.get("decorations", [])]
    for task in zone["building_tasks"]:
        if task["type"] != "fence":
            all_entities.append(task["pos"])

    if include_crops:
        all_entities += zone["crops"]

    for ex, ey in all_entities:
        if ex == x and ey == y:  # exact grid cell match
            return True

    return False


def _update_prosperity_and_level(state):
    score = 0
    for d in state["decor"]["decorations"]:
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
    # No rent, no bankruptcy check, no Game Over: a night always just ends
    # and rolls into the next day. Whatever losses happened overnight (crops
    # stolen, decor smashed, traps consumed) stay lost, but they never end
    # the run -- the player always gets tomorrow to rebuild.
    farm = state["farm"]
    decor = state["decor"]

    if state.get("last_msg", "").startswith("所有敵人"):
        state["last_msg"] = f"{state['last_msg']} 迎接新的一天。"
    else:
        state["last_msg"] = "夜晚結束！新的一天開始了。"

    state["phase"] = "day"
    state["day_count"] += 1
    state["time_left"] = 120

    farm["thief_pos"] = None
    farm["thief_path"] = []
    farm["target_crop"] = None
    decor["boar_pos"] = None
    decor["boar_path"] = []
    decor["target_decor"] = None
    return state


def _tick_zone_building(zone, on_decor_complete=None):
    new_tasks = []
    for task in zone["building_tasks"]:
        task["progress"] += 1
        if task["progress"] >= task["max_progress"]:
            t_type = task["type"]
            pos = task["pos"]
            if t_type == "crop":
                crop_type = task["crop_type"]
                zone["crops"].append(pos)
                zone["crop_data"][pos] = {
                    "type": crop_type,
                    "stage": 0,
                    "max_stage": CROP_INFO[crop_type]["growth_time"],
                    "fertilized": False,
                    "growth_timer": 0
                }
            elif t_type == "fence": zone["fences"].append((pos[0], pos[1], FENCE_MAX_HP))
            elif t_type == "farmland": zone["farmland"].append(pos)
            elif t_type == "dog": zone["dogs"].append(pos)
            elif t_type == "trap": zone["traps"].append(pos)
            elif t_type == "decor":
                decor_type = task["decor_type"]
                zone["decorations"].append((pos[0], pos[1], decor_type, 3))
                if on_decor_complete: on_decor_complete()
        else:
            new_tasks.append(task)
    zone["building_tasks"] = new_tasks


def apply_action(state: GameState, action: str, zone: str = "farm") -> GameState:
    if state["status"] != "playing":
        return state

    _working_copy = deepcopy(state)
    zstate = _working_copy.get(zone, _working_copy["farm"])

    if action == "tick":
        _tick_zone_building(_working_copy["farm"])
        _tick_zone_building(_working_copy["decor"], on_decor_complete=lambda: _update_prosperity_and_level(_working_copy))

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
            farm_active = _night_tick_thief(_working_copy)
            decor_active = _night_tick_boar(_working_copy)

            if not farm_active and not decor_active:
                farm = _working_copy["farm"]
                decor = _working_copy["decor"]
                if farm.get("thieves_spawned", 0) >= farm.get("max_thieves", 1) and \
                   decor.get("boars_spawned", 0) >= decor.get("max_boars", 0):
                    _working_copy["last_msg"] = "所有敵人已被消滅，提早迎接清晨！"
                    return _end_night(_working_copy)

        return _working_copy

    elif action == "start_night":
        if _working_copy["phase"] == "day":
            farm = _working_copy["farm"]
            decor = _working_copy["decor"]
            crop_income = 0
            for c_pos in farm["crops"]:
                data = farm["crop_data"].get(c_pos)
                if data:
                    if data["stage"] >= data["max_stage"]:
                        crop_income += CROP_INFO[data["type"]]["yield"]
                    else:
                        growth_amount = 2 if data.get("fertilized") else 1
                        data["stage"] = min(data["stage"] + growth_amount, data["max_stage"])

            if crop_income > 0:
                _working_copy["money"] += crop_income
                income_msg = f" (成熟收益 ${crop_income})"
            else:
                income_msg = ""

            _working_copy["phase"] = "night"
            _working_copy["time_left"] = 60

            farm["thief_pos"] = None
            farm["thief_spawn_cooldown"] = 30
            farm["thieves_spawned"] = 0
            farm["max_thieves"] = 1 + _working_copy["day_count"] // 2

            decor["boar_pos"] = None
            decor["boar_spawn_cooldown"] = 60
            decor["boars_spawned"] = 0
            # Boars appear after day 2 or if prosperity is high
            if _working_copy["day_count"] >= 2 or _working_copy["prosperity_score"] > 0:
                decor["max_boars"] = 1 + _working_copy["day_count"] // 3
            else:
                decor["max_boars"] = 0

            _working_copy["last_msg"] = f"夜晚降臨！今晚有 {farm['max_thieves']} 小偷, {decor['max_boars']} 野豬！{income_msg}"

    elif action.startswith("use_hoe_"):
        if zone != "farm": return _working_copy
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if not _is_occupied(zstate, pos[0], pos[1]) and pos not in zstate["farmland"]:
            zstate["building_tasks"].append({"type": "farmland", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["last_msg"] = "開始開墾農田..."

    elif action.startswith("use_scythe_"):
        if zone != "farm": return _working_copy
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy

        if pos in zstate["crops"]:
            data = zstate["crop_data"].get(pos)
            if data and data["stage"] >= data["max_stage"]:
                zstate["crops"].remove(pos)
                del zstate["crop_data"][pos]
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
        if zone != "farm": return _working_copy
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try:
            crop_type = "_".join(parts[2:-2])
            pos = (int(parts[-2]), int(parts[-1]))
        except: return _working_copy
        if crop_type not in CROP_INFO: return _working_copy

        req_level = CROP_INFO[crop_type].get("level_req", 1)
        if _working_copy["farm_level"] < req_level:
            _working_copy["last_msg"] = f"農場等級不足！需要等級 {req_level} 才能種植 {CROP_NAMES.get(crop_type, crop_type)}。"
            return _working_copy

        price = CROP_INFO[crop_type]["price"]
        if _working_copy["money"] < price: return _working_copy
        if pos in zstate["farmland"] and pos not in zstate["crops"]:
            if not any(t["type"] == "crop" and t["pos"] == pos for t in zstate["building_tasks"]):
                zstate["building_tasks"].append({"type": "crop", "crop_type": crop_type, "pos": pos, "progress": 0, "max_progress": 3})
                _working_copy["money"] -= price
                _working_copy["last_msg"] = f"開始種植 {CROP_NAMES.get(crop_type, crop_type)}..."

    elif action.startswith("build_decor_"):
        if zone != "decor": return _working_copy
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try:
            decor_type = "_".join(parts[2:-2])
            pos = (int(parts[-2]), int(parts[-1]))
        except: return _working_copy
        if decor_type not in DECOR_INFO: return _working_copy
        price = DECOR_INFO[decor_type]["price"]
        if _working_copy["money"] < price: return _working_copy

        if not _is_occupied(zstate, pos[0], pos[1]):
            zstate["building_tasks"].append({"type": "decor", "decor_type": decor_type, "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= price
            _working_copy["last_msg"] = f"開始佈置 {DECOR_NAMES.get(decor_type, decor_type)}..."

    elif action.startswith("build_fence_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 20: return _working_copy

        if pos in zstate.get("farmland", []):
            _working_copy["last_msg"] = "無法建造！木圍欄不能蓋在農田上！"
            return _working_copy

        if not _is_occupied(zstate, pos[0], pos[1]):
            if not _can_build_fence(zstate, pos):
                _working_copy["last_msg"] = "無法建造！不能將農田完全封死！"
                return _working_copy
            if not any(t["type"] == "fence" and t["pos"] == pos for t in zstate["building_tasks"]):
                zstate["building_tasks"].append({"type": "fence", "pos": pos, "progress": 0, "max_progress": 2})
                _working_copy["money"] -= 20
                _working_copy["last_msg"] = "消耗 $20，開始加裝木圍欄..."

    elif action.startswith("place_trap_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if _working_copy["money"] < 50: return _working_copy
        if not _is_occupied(zstate, pos[0], pos[1], include_crops=False):
            zstate["building_tasks"].append({"type": "trap", "pos": pos, "progress": 0, "max_progress": 1})
            _working_copy["money"] -= 50
            _working_copy["last_msg"] = "設置了地刺陷阱！"

    elif action.startswith("place_dog_"):
        if _working_copy.get("phase") != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if len(zstate.get("dogs", [])) >= 10: return _working_copy
        price = 0 if _working_copy.get("free_dog") else 200
        if _working_copy["money"] < price: return _working_copy
        if not _is_occupied(zstate, pos[0], pos[1]):
            zstate["building_tasks"].append({"type": "dog", "pos": pos, "progress": 0, "max_progress": 2})
            _working_copy["money"] -= price
            _working_copy["free_dog"] = False
            _working_copy["last_msg"] = "呼叫看門狗..."

    elif action.startswith("click_"):
        parts = action.split("_")
        try: pos = (float(parts[1]), float(parts[2]))
        except: return _working_copy

        if _working_copy["phase"] == "night":
            if zone == "farm" and zstate.get("thief_pos"):
                tx, ty = zstate["thief_pos"]
                if math.hypot(tx - pos[0], ty - pos[1]) < ITEM_SIZE:
                    if zstate.get("thief_iframes", 0) <= 0:
                        zstate["thief_hp"] -= 1
                        zstate["thief_iframes"] = 15
                        _working_copy["last_msg"] = "擊中小偷！"
            if zone == "decor" and zstate.get("boar_pos"):
                bx, by = zstate["boar_pos"]
                if math.hypot(bx - pos[0], by - pos[1]) < ITEM_SIZE:
                    if zstate.get("boar_iframes", 0) <= 0:
                        zstate["boar_hp"] -= 1
                        zstate["boar_iframes"] = 15
                        _working_copy["last_msg"] = "擊中野豬！"

    elif action.startswith("use_fertilizer_"):
        if zone != "farm": return _working_copy
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy

        if pos in zstate["crops"]:
            data = zstate["crop_data"].get(pos)
            if data and not data.get("fertilized"):
                data["fertilized"] = True
                _working_copy["last_msg"] = "施肥成功！作物生長速度加快。"
        else:
            _working_copy["last_msg"] = "這裡沒有作物可以施肥。"

    elif action.startswith("use_shovel_"):
        if _working_copy["phase"] != "day": return _working_copy
        parts = action.split("_")
        try: pos = (int(parts[2]), int(parts[3]))
        except: return _working_copy
        if pos in zstate["crops"]:
            zstate["crops"].remove(pos)
            if pos in zstate["crop_data"]: del zstate["crop_data"][pos]
            _working_copy["last_msg"] = "移除了農田！"
        elif any(f[0] == pos[0] and f[1] == pos[1] for f in zstate.get("fences", [])):
            fence = next(f for f in zstate["fences"] if f[0] == pos[0] and f[1] == pos[1])
            zstate["fences"].remove(fence)
            _working_copy["last_msg"] = "移除了木圍欄！"
        elif any(d[0] == pos[0] and d[1] == pos[1] for d in zstate.get("decorations", [])):
            decor_item = next(d for d in zstate["decorations"] if d[0] == pos[0] and d[1] == pos[1])
            zstate["decorations"].remove(decor_item)
            _update_prosperity_and_level(_working_copy)
            _working_copy["last_msg"] = "移除了景觀物！"
        elif pos in zstate.get("traps", []):
            zstate["traps"].remove(pos)
            _working_copy["last_msg"] = "回收了地刺陷阱！"
        elif pos in zstate.get("dogs", []):
            zstate["dogs"].remove(pos)
            _working_copy["last_msg"] = "收回了看門狗！"
        elif pos in zstate.get("trees", []):
            _working_copy["last_msg"] = "樹木是景觀，無法用鐵鏟移除！"
        elif pos in zstate.get("rocks", []):
            _working_copy["last_msg"] = "石頭是景觀，無法用鐵鏟移除！"
        else:
            tasks = [t for t in zstate["building_tasks"] if t["pos"] == pos]
            if tasks:
                zstate["building_tasks"].remove(tasks[0])
                _working_copy["last_msg"] = "取消了建造！"

    return _working_copy


def _spawn_thief(farm):
    ty = random.randint(0, GRID_H - ITEM_SIZE)
    tx = 0  # thieves creep in from the farm map's left edge
    return (tx, ty)


def _spawn_boar(decor):
    ty = random.randint(0, GRID_H - ITEM_SIZE)
    tx = GRID_W - ITEM_SIZE  # boars charge in from the decor map's right edge
    return (tx, ty)


def _simulate_night_path(zone, start_pos, targets, return_reachable=False):
    """Shared BFS pathfinder used by both the thief (farm zone) and the
    boar (decor zone) — each only ever sees obstacles/targets in its own
    zone's map, so they can never path into the other zone.

    return_reachable is opt-in and defaults to False so every existing
    caller (boar, and the thief's own spawn-time call) is completely
    unaffected and keeps unpacking a plain (path, target) 2-tuple. Passing
    True additionally returns whether a real route was found via BFS vs.
    the straight-line-through-obstacles fallback below -- used by the
    thief's fence-detour check to tell "found an actual way around" apart
    from "gave up and is just facing the obstacle directly"."""
    if not targets:
        return ([], None, False) if return_reachable else ([], None)

    ex, ey = start_pos
    best_target = None
    min_dist = float('inf')
    for t_pos in targets:
        dist = math.hypot(t_pos[0] - ex, t_pos[1] - ey)
        if dist < min_dist:
            min_dist = dist
            best_target = t_pos

    if best_target is None:
        return ([], None, False) if return_reachable else ([], None)

    start_grid = (int(ex // 5), int(ey // 5))
    target_grid = (int(best_target[0] // 5), int(best_target[1] // 5))

    queue = [start_grid]
    came_from = {start_grid: None}

    while queue:
        curr = queue.pop(0)
        if curr == target_grid: break

        for dx, dy in [(0, 1), (1, 0), (0, -1), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
            nx, ny = curr[0] + dx, curr[1] + dy
            if 0 <= nx <= GRID_W // 5 and 0 <= ny <= GRID_H // 5:
                if (nx, ny) not in came_from:
                    px, py = nx * 5, ny * 5
                    if (nx, ny) == target_grid or not _is_obstacle(zone, px, py):
                        came_from[(nx, ny)] = curr
                        queue.append((nx, ny))

    reachable = target_grid in came_from
    if not reachable:
        path = []
        curr_x, curr_y = ex, ey
        tx, ty = best_target[0], best_target[1]
        steps = int(math.hypot(tx - curr_x, ty - curr_y) / 5)
        if steps == 0: steps = 1
        for i in range(1, steps + 1):
            path.append((curr_x + (tx - curr_x) * i / steps, curr_y + (ty - curr_y) * i / steps))
        return (path, best_target, False) if return_reachable else (path, best_target)

    path = []
    curr = target_grid
    while curr != start_grid and curr is not None:
        if curr == target_grid: path.append((best_target[0], best_target[1]))
        else: path.append((curr[0] * 5, curr[1] * 5))
        curr = came_from[curr]

    path.reverse()
    return (path, best_target, True) if return_reachable else (path, best_target)


def _thief_pick_targets(farm):
    """Which crops the thief is trying to reach: mature ones first, falling
    back to any crop at all if none are ready yet. Extracted so both the
    initial spawn decision and a later fence-detour repath use exactly the
    same target-selection rule -- the target is decided once, never
    re-picked mid-chase just because a fence got in the way (requirement:
    the fence system must not change *what* the thief is going for)."""
    targets = [
        c for c in farm.get("crops", [])
        if farm["crop_data"].get(c, {}).get("stage", 0) >= farm["crop_data"].get(c, {}).get("max_stage", 1)
    ]
    if not targets:
        targets = farm.get("crops", [])
    return targets


def _tick_collapsing_fences(zone):
    """Advance the collapse-animation countdown for fences that already hit
    0 HP, actually removing them once their animation timer runs out. Kept
    as a separate list from `fences` so the main fences list never holds a
    dead entry and the renderer can draw "mid-collapse" fences differently."""
    still_collapsing = []
    for cx, cy, ticks_left in zone.get("collapsing_fences", []):
        ticks_left -= 1
        if ticks_left > 0:
            still_collapsing.append((cx, cy, ticks_left))
    zone["collapsing_fences"] = still_collapsing


def _tick_collapsing_decorations(zone):
    """Same idea as _tick_collapsing_fences, for decorations the boar has
    just finished destroying (V1.1 balance fix -- decorations used to be
    removed outright the instant HP hit 0)."""
    still_collapsing = []
    for cx, cy, dtype, ticks_left in zone.get("collapsing_decorations", []):
        ticks_left -= 1
        if ticks_left > 0:
            still_collapsing.append((cx, cy, dtype, ticks_left))
    zone["collapsing_decorations"] = still_collapsing


def _night_tick_thief(state):
    """Advances the thief threat within the farm map only, using and
    updating only state['farm']. Returns True while a thief is active or
    still queued to spawn this night."""
    farm = state["farm"]
    day_count = state["day_count"]
    enemies_active = False

    _tick_collapsing_fences(farm)
    if farm.get("thief_hit_flash", 0) > 0:
        farm["thief_hit_flash"] -= 1

    if farm["thief_pos"] is None:
        if farm.get("thieves_spawned", 0) < farm.get("max_thieves", 1):
            if farm.get("thief_spawn_cooldown", 0) > 0:
                farm["thief_spawn_cooldown"] -= 1
                enemies_active = True
            else:
                farm["thief_pos"] = _spawn_thief(farm)
                farm["thieves_spawned"] = farm.get("thieves_spawned", 0) + 1
                farm["thief_hp"] = 3 + (day_count // 3)
                farm["thief_iframes"] = 0
                farm["thief_ai_state"] = "moving"
                farm["thief_attack_cooldown"] = 0
                farm["thief_attack_target_fence"] = None
                farm["thief_stuck_ticks"] = 0
                targets = _thief_pick_targets(farm)
                farm["thief_path"], farm["target_crop"] = _simulate_night_path(farm, farm["thief_pos"], targets)
                enemies_active = True
    else:
        enemies_active = True
        if farm.get("thief_iframes", 0) > 0:
            farm["thief_iframes"] -= 1

        trapped = None
        for trx, try_ in farm["traps"]:
            if _rects_overlap(trx, try_, ITEM_SIZE, ITEM_SIZE, farm["thief_pos"][0], farm["thief_pos"][1], ITEM_SIZE, ITEM_SIZE):
                trapped = (trx, try_)
                break
        if trapped:
            farm["traps"].remove(trapped)
            farm["thief_hp"] = 0
            state["last_msg"] = "小偷踩到了地刺陷阱！陷阱損壞，小偷被擊敗！"

        if farm["thief_hp"] <= 0:
            if "小偷踩到" not in state.get("last_msg", ""):
                state["last_msg"] = "小偷被擊退！"
            state["enemies_defeated"] = state.get("enemies_defeated", 0) + 1
            farm["thief_pos"] = None
            farm["thief_path"] = []
            farm["target_crop"] = None
            farm["thief_ai_state"] = "moving"
            farm["thief_attack_cooldown"] = 0
            farm["thief_attack_target_fence"] = None
            farm["thief_stuck_ticks"] = 0
            farm["thief_spawn_cooldown"] = 30 + random.randint(0, 30)
        elif farm.get("thief_iframes", 0) <= 0:

            if farm.get("thief_ai_state") == "attacking_fence":
                # STATE_ATTACKING_FENCE: stopped, landing cooldown-gated
                # hits instead of moving.
                target_pos = farm.get("thief_attack_target_fence")
                fence = next(
                    (f for f in farm["fences"] if f[0] == target_pos[0] and f[1] == target_pos[1]),
                    None,
                ) if target_pos else None

                if fence is None:
                    # Gone (we finished it off, or the player removed it) --
                    # the obstacle cleared, resume moving toward the same
                    # target as before.
                    farm["thief_ai_state"] = "moving"
                    farm["thief_attack_target_fence"] = None
                    farm["thief_attack_cooldown"] = 0
                    targets = [farm["target_crop"]] if farm.get("target_crop") else _thief_pick_targets(farm)
                    farm["thief_path"], farm["target_crop"] = _simulate_night_path(farm, farm["thief_pos"], targets)
                else:
                    cooldown = farm.get("thief_attack_cooldown", 0)
                    if cooldown > 0:
                        farm["thief_attack_cooldown"] = cooldown - 1
                    else:
                        # attack_interval = FENCE_ATTACK_INTERVAL_TICKS;
                        # each attack: fence hp -= FENCE_DAMAGE_PER_HIT.
                        new_hp = fence[2] - FENCE_DAMAGE_PER_HIT
                        farm["fences"].remove(fence)
                        farm["thief_hit_flash"] = 5  # a few ticks of shake/flash for the renderer
                        # SFX hook: a hit just landed on a fence -- this
                        # project has no audio system yet, wire a sound
                        # call here if/when one gets added.
                        if new_hp > 0:
                            farm["fences"].append((fence[0], fence[1], new_hp))
                            state["last_msg"] = f"小偷正在破壞木圍欄！圍欄剩餘耐久 {new_hp}/{FENCE_MAX_HP}"
                        else:
                            # Hand off to the collapse animation instead of
                            # vanishing on the spot -- actually removed once
                            # that finishes (_tick_collapsing_fences above).
                            farm["collapsing_fences"].append((fence[0], fence[1], 12))
                            state["last_msg"] = "小偷摧毀了木圍欄！"
                        farm["thief_attack_cooldown"] = FENCE_ATTACK_INTERVAL_TICKS
            else:
                # STATE_MOVING: follow thief_path as before.
                tx, ty = farm["thief_pos"]
                if farm.get("thief_path"):
                    target = farm["thief_path"][0]
                    dist_x = target[0] - tx
                    dist_y = target[1] - ty
                    length = math.hypot(dist_x, dist_y)
                    speed = 0.5

                    next_x = tx + (dist_x / length) * speed if length > 0 else tx
                    next_y = ty + (dist_y / length) * speed if length > 0 else ty

                    fence_hit = None
                    for f in farm.get("fences", []):
                        if _rects_overlap(next_x, next_y, ITEM_SIZE, ITEM_SIZE, f[0], f[1], ITEM_SIZE, ITEM_SIZE):
                            fence_hit = f
                            break

                    if fence_hit:
                        # STATE_REPATHING (conceptually): don't attack yet --
                        # try to find a way around this specific fence first,
                        # toward the same target we already committed to.
                        # `reachable` (return_reachable=True) tells us
                        # whether BFS found an actual route vs. fell back to
                        # a straight line through whatever's in the way --
                        # trusting that flag instead of re-deriving "is the
                        # first step blocked" avoids false negatives right
                        # at the moment of contact, when the thief is
                        # already touching the fence and almost *any*
                        # nearby waypoint would still graze its hitbox.
                        #
                        # Neither branch below moves the thief this tick --
                        # that's fine normally (a fresh detour resolves on
                        # its own within a tick or two as the thief steps
                        # clear), but if the thief is wedged in a gap
                        # exactly as wide as its own hitbox (see
                        # thief_stuck_ticks' definition in _new_zone_state),
                        # BFS keeps reporting the same "reachable" verdict
                        # forever while the finer-grained box collision
                        # never lets the actual step complete -- zero
                        # progress, every tick, indefinitely. Bug fix:
                        # count consecutive fence_hit ticks with no
                        # movement, and once that streak is suspiciously
                        # long, stop trusting the detour verdict and attack
                        # whatever's actually touching the thief instead --
                        # destroying it is guaranteed to eventually widen
                        # the gap, unlike re-asking the same question.
                        farm["thief_stuck_ticks"] = farm.get("thief_stuck_ticks", 0) + 1
                        detour_targets = [farm["target_crop"]] if farm.get("target_crop") else _thief_pick_targets(farm)
                        alt_path, alt_target, reachable = _simulate_night_path(
                            farm, farm["thief_pos"], detour_targets, return_reachable=True
                        )
                        stuck = farm["thief_stuck_ticks"] >= THIEF_STUCK_TICKS_THRESHOLD
                        if reachable and alt_path and not stuck:
                            # Found a clear alternate route -- take it
                            # instead of fighting through the fence.
                            farm["thief_path"], farm["target_crop"] = alt_path, alt_target
                        else:
                            # No viable detour right now (a real wall, every
                            # alternate route is also blocked, or we've been
                            # "finding" the same non-progressing detour for
                            # THIEF_STUCK_TICKS_THRESHOLD ticks straight) --
                            # stop and start wearing this fence down.
                            # Cooldown starts at 0 so the *next* night_tick
                            # (now in STATE_ATTACKING_FENCE) lands the first
                            # hit almost immediately, then every
                            # FENCE_ATTACK_INTERVAL_TICKS after that.
                            farm["thief_ai_state"] = "attacking_fence"
                            farm["thief_attack_target_fence"] = (fence_hit[0], fence_hit[1])
                            farm["thief_attack_cooldown"] = 0
                            farm["thief_stuck_ticks"] = 0
                    else:
                        farm["thief_stuck_ticks"] = 0
                        if length <= speed:
                            farm["thief_pos"] = farm["thief_path"].pop(0)
                        else:
                            farm["thief_pos"] = (next_x, next_y)
                else:
                    if farm.get("target_crop"):
                        target = farm["target_crop"]
                        if target in farm["crops"]:
                            farm["crops"].remove(target)
                            if target in farm["crop_data"]:
                                del farm["crop_data"][target]
                            state["last_msg"] = "糟糕！有一塊農作被小偷偷走了！"
                    farm["thief_pos"] = None
                    farm["thief_path"] = []
                    farm["target_crop"] = None
                    farm["thief_ai_state"] = "moving"
                    farm["thief_attack_cooldown"] = 0
                    farm["thief_attack_target_fence"] = None
                    farm["thief_stuck_ticks"] = 0
                    farm["thief_spawn_cooldown"] = 30 + random.randint(0, 30)

    _process_zone_dogs(farm, "thief")
    return enemies_active


def _night_tick_boar(state):
    """Advances the boar threat within the decor map only, using and
    updating only state['decor']. Returns True while a boar is active or
    still queued to spawn this night."""
    decor = state["decor"]
    day_count = state["day_count"]
    enemies_active = False

    _tick_collapsing_decorations(decor)
    if decor.get("boar_hit_flash", 0) > 0:
        decor["boar_hit_flash"] -= 1

    if decor["boar_pos"] is None:
        if decor.get("boars_spawned", 0) < decor.get("max_boars", 0):
            if decor.get("boar_spawn_cooldown", 0) > 0:
                decor["boar_spawn_cooldown"] -= 1
                enemies_active = True
            else:
                decor["boar_pos"] = _spawn_boar(decor)
                decor["boars_spawned"] = decor.get("boars_spawned", 0) + 1
                decor["boar_hp"] = 5 + (day_count // 2)
                decor["boar_iframes"] = 0
                decor["boar_attack_cooldown"] = 0
                decors = decor.get("decorations", [])
                if decors:
                    max_pros = max(DECOR_INFO.get(d[2], {}).get("prosperity", 0) for d in decors)
                    targets = [(d[0], d[1]) for d in decors if DECOR_INFO.get(d[2], {}).get("prosperity", 0) == max_pros]
                else:
                    targets = []
                decor["boar_path"], decor["target_decor"] = _simulate_night_path(decor, decor["boar_pos"], targets)
                enemies_active = True
    else:
        enemies_active = True
        if decor.get("boar_iframes", 0) > 0:
            decor["boar_iframes"] -= 1

        trapped = None
        for trx, try_ in decor["traps"]:
            if _rects_overlap(trx, try_, ITEM_SIZE, ITEM_SIZE, decor["boar_pos"][0], decor["boar_pos"][1], ITEM_SIZE, ITEM_SIZE):
                trapped = (trx, try_)
                break
        if trapped:
            decor["traps"].remove(trapped)
            decor["boar_hp"] -= 5  # Boar is tough, trap does 5 dmg
            state["last_msg"] = "野豬踩到了地刺陷阱！陷阱損壞，野豬受到重創！"

        if decor["boar_hp"] <= 0:
            if "踩到" not in state.get("last_msg", ""):
                state["last_msg"] = "野豬被擊退！"
            state["enemies_defeated"] = state.get("enemies_defeated", 0) + 1
            decor["boar_pos"] = None
            decor["boar_path"] = []
            decor["target_decor"] = None
            decor["boar_attack_cooldown"] = 0
            decor["boar_spawn_cooldown"] = 45 + random.randint(0, 30)
        elif decor.get("boar_iframes", 0) <= 0:
            bx, by = decor["boar_pos"]
            if decor.get("boar_path"):
                target = decor["boar_path"][0]
                dist_x = target[0] - bx
                dist_y = target[1] - by
                length = math.hypot(dist_x, dist_y)
                speed = 0.6  # Boars run faster

                fence_hit = None
                for f in decor.get("fences", []):
                    if _rects_overlap(bx + (dist_x/length)*speed if length > 0 else 0, by + (dist_y/length)*speed if length > 0 else 0, ITEM_SIZE, ITEM_SIZE, f[0], f[1], ITEM_SIZE, ITEM_SIZE):
                        fence_hit = f
                        break

                if fence_hit:
                    # V1.1 fix: this used to deal BOAR_FENCE_DAMAGE_PER_HIT
                    # on *every* uncooled tick it stayed blocked here (see
                    # the tuning comment near BOAR_FENCE_DAMAGE_PER_HIT) --
                    # now gated behind the same kind of cooldown the thief
                    # already has. The boar still doesn't try to detour
                    # (that behavior was scoped to the thief/fence rework
                    # only); it just stands here and pounds on the fence
                    # once every BOAR_FENCE_ATTACK_INTERVAL_TICKS instead of
                    # every single tick.
                    cooldown = decor.get("boar_attack_cooldown", 0)
                    if cooldown > 0:
                        decor["boar_attack_cooldown"] = cooldown - 1
                    else:
                        new_hp = fence_hit[2] - BOAR_FENCE_DAMAGE_PER_HIT
                        decor["fences"].remove(fence_hit)
                        decor["boar_hit_flash"] = 5
                        if new_hp > 0:
                            decor["fences"].append((fence_hit[0], fence_hit[1], new_hp))
                            state["last_msg"] = f"野豬衝撞了木圍欄！圍欄剩餘耐久: {new_hp}"
                        else:
                            decor["collapsing_fences"].append((fence_hit[0], fence_hit[1], 12))
                            state["last_msg"] = "野豬衝破了木圍欄！"
                        decor["boar_attack_cooldown"] = BOAR_FENCE_ATTACK_INTERVAL_TICKS
                else:
                    if length <= speed:
                        decor["boar_pos"] = decor["boar_path"].pop(0)
                    else:
                        decor["boar_pos"] = (bx + (dist_x / length) * speed, by + (dist_y / length) * speed)
            else:
                target = decor.get("target_decor")
                decor_match = None
                if target:
                    decor_match = next(
                        (d for d in decor["decorations"] if d[0] == target[0] and d[1] == target[1]), None
                    )

                if decor_match is None:
                    # Nothing left to attack (already destroyed by some
                    # other means, or there was never a target) -- leave.
                    decor["boar_pos"] = None
                    decor["boar_path"] = []
                    decor["target_decor"] = None
                    decor["boar_attack_cooldown"] = 0
                    decor["boar_spawn_cooldown"] = 45 + random.randint(0, 30)
                else:
                    # V1.1 fix: decorations were always created with
                    # hp=DECOR_MAX_HP (see _new_zone_state's comment) but
                    # nothing ever read it -- the boar destroyed whatever it
                    # arrived at in one hit, on the spot. Now it lands the
                    # same kind of cooldown-gated, gradually-damaging hits
                    # the thief lands on fences, using that already-present
                    # hp field for real.
                    cooldown = decor.get("boar_attack_cooldown", 0)
                    if cooldown > 0:
                        decor["boar_attack_cooldown"] = cooldown - 1
                    else:
                        dx, dy, dtype, dhp = decor_match
                        new_hp = dhp - DECOR_DAMAGE_PER_HIT
                        decor["decorations"].remove(decor_match)
                        decor["boar_hit_flash"] = 5
                        # SFX hook: a hit just landed on a decoration -- no
                        # audio system in this project yet, wire a sound
                        # call here if/when one gets added (same as the
                        # thief's fence-hit hook).
                        if new_hp > 0:
                            decor["decorations"].append((dx, dy, dtype, new_hp))
                            state["last_msg"] = f"野豬正在衝撞 {DECOR_NAMES.get(dtype, '景觀物')}！"
                            decor["boar_attack_cooldown"] = DECOR_ATTACK_INTERVAL_TICKS
                        else:
                            decor["collapsing_decorations"].append((dx, dy, dtype, 12))
                            _update_prosperity_and_level(state)
                            state["last_msg"] = f"糟糕！野豬摧毀了 {DECOR_NAMES.get(dtype, '景觀物')}！繁榮度下降！"
                            decor["boar_pos"] = None
                            decor["boar_path"] = []
                            decor["target_decor"] = None
                            decor["boar_attack_cooldown"] = 0
                            decor["boar_spawn_cooldown"] = 45 + random.randint(0, 30)

    _process_zone_dogs(decor, "boar")
    return enemies_active


def _process_zone_dogs(zone, enemy_key):
    """enemy_key is 'thief' for the farm map, 'boar' for the decor map —
    dogs only ever fight the threat that exists in their own zone."""
    pos_key = f"{enemy_key}_pos"
    hp_key = f"{enemy_key}_hp"
    iframes_key = f"{enemy_key}_iframes"

    new_dogs = []
    for dx, dy in zone["dogs"]:
        enemy_pos = zone.get(pos_key)
        if enemy_pos is not None and zone.get(hp_key, 0) > 0:
            tx, ty = enemy_pos
            if _rects_overlap(dx, dy, ITEM_SIZE, ITEM_SIZE, tx, ty, ITEM_SIZE, ITEM_SIZE):
                if zone.get(iframes_key, 0) <= 0:
                    zone[hp_key] -= 1
                    zone[iframes_key] = 20
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
    zone["dogs"] = new_dogs


def is_terminal(state: GameState) -> bool:
    return state.get("status") == "game_over"


def fence_damage_state(hp: int, max_hp: int = FENCE_MAX_HP) -> str:
    """Which of the three visual damage tiers a fence's current HP falls
    into. Pure/pygame-free on purpose so it's directly unit-testable and so
    renderer.py has one shared source of truth for the thresholds instead
    of re-deriving them from raw HP wherever a fence gets drawn.
    100-60% "intact", 59-30% "damaged", 29-1% "critical"."""
    if max_hp <= 0:
        return "intact"
    ratio = hp / max_hp
    if ratio >= 0.6:
        return "intact"
    if ratio >= 0.3:
        return "damaged"
    return "critical"
