"""思索系統 (Thought) -- decides what to show while F is held.

This is a different concern from src/tutorial.py:
  - tutorial.py tracks *progress*: "has the player ever demonstrated they
    understand mechanic X" (a one-way latch).
  - thought.py answers a question asked *right now*: "I'm looking at this,
    what does it mean?" It runs every time F is held, regardless of whether
    Tutorial is complete -- F keeps working forever. It just stops
    volunteering "here's how tilling works" once tilling is already
    understood, and leans on situational/ambient information instead.

Not an AI reasoning system. Every Thought is a plain, deterministic rule
(a condition function + a priority), evaluated by strict priority every
frame -- no randomness, no "what did I say last time" beyond the small
per-id cooldown described below. That keeps it clear and reliable rather
than trying to infer intent, per the project's own "don't over-complicate
this into a big AI reasoning system" guidance.

Because this game has no player-avatar position (camera panning, not
character movement), "nearby" / "the player is standing next to X" is
represented by which grid cell the mouse is hovering -- main.py computes
that cell each frame (world coords snapped to the same grid the click
handler and renderer's placement preview already use) and passes it in as
`hover_pos`. This module never touches pygame or the mouse directly.

Priority tiers (lower number wins; see _entry_matches_context / the
selection loop in get_contemplation_lines):
    0-9   danger -- an enemy is actively a threat right now
    10-19 actionable -- something the player can do this instant
    20-29 an important mechanic the player hasn't demonstrated yet
    30-39 description of something nearby (informative, not actionable)
    40-49 general ambient status (the always-available fallback)

Each Thought entry is a dict with:
    id               unique string
    text             str, or (state, ctx) -> str/list[str] for dynamic text
    priority         int, or (state, ctx) -> int -- used for entries whose
                     urgency should fade once the player clearly already
                     knows this (see _demote_once_learned)
    trigger          short free-text description only ("hover"/"state"/
                     "always") -- documentation; `condition` does the work
    condition        (state, ctx) -> bool: is this relevant right now?
    cooldown         int: how many subsequent get_contemplation_lines calls
                     (i.e. rendered frames while F is held) this id stays
                     suppressed for immediately after it stops being shown.
                     0 (default) = no cooldown; only worth setting on
                     entries that could flap against another equally-ranked
                     one as hover position changes rapidly.
    required_map     "farm" / "decor" / None (either)
    required_phase   "day" / "night" / None (either)
    required_item    a tool id, a list of tool ids, or None (any/no tool)
    required_tutorial  a src.tutorial TUTORIAL_STEPS id this entry relates
                     to. Purely informational/traceability by itself --
                     entries that should *disappear* once learned bake
                     `not is_unlocked(...)` into `condition`; entries that
                     should merely *lose urgency* once learned (so they can
                     still surface as a fallback, just not dominate) use
                     `_demote_once_learned` for `priority`. Both read the
                     same id this field names, kept in sync by convention.
    enabled          bool, default True -- a static kill switch independent
                     of `condition`, for quickly disabling an entry.

Extending this: add one entry to THOUGHT_ENTRIES. No other file needs to
change.
"""

import math

from src import tutorial as _tutorial


def _inventory_total(state):
    return sum(sum(g.values()) for g in state.get("inventory", {}).values())


def _learned(state, step_id):
    return _tutorial.is_unlocked(state, step_id)


def _demote_once_learned(base, demoted, step_id):
    """priority helper: `base` while the player hasn't demonstrated they
    understand `step_id` yet, `demoted` (a much higher number, i.e. much
    lower urgency) once they have. Keeps an actionable hint truthful and
    available forever without letting it keep dominating over more useful
    information once it's clearly no longer teaching the player anything
    new -- e.g. after tilling dozens of tiles, "you could till this" should
    stop outranking a nearby mature crop or an active threat."""
    def _priority(state, ctx):
        return demoted if _learned(state, step_id) else base
    return _priority


# ---------------------------------------------------------------------------
# Hover helpers. ctx["hover_pos"] is the (gx, gy) grid cell the mouse is
# over, in the same units as farmland/crops/fences/etc positions, or None.
# ---------------------------------------------------------------------------

def _hover_is_tillable(state, ctx):
    """Hovering plain ground in the farm zone: not farmland yet, not a
    tree/rock."""
    pos = ctx.get("hover_pos")
    if pos is None or ctx["active_zone"] != "farm":
        return False
    farm = state["farm"]
    if pos in farm.get("farmland", []):
        return False
    if pos in farm.get("trees", []) or pos in farm.get("rocks", []):
        return False
    return True


def _hover_is_empty_farmland(state, ctx):
    """Hovering tilled soil with nothing planted on it yet."""
    pos = ctx.get("hover_pos")
    if pos is None or ctx["active_zone"] != "farm":
        return False
    farm = state["farm"]
    return pos in farm.get("farmland", []) and pos not in farm.get("crops", [])


def _hover_crop_stage(state, ctx):
    pos = ctx.get("hover_pos")
    if pos is None or ctx["active_zone"] != "farm":
        return None
    data = state["farm"]["crop_data"].get(pos)
    if not data:
        return None
    return data.get("stage", 0), data.get("max_stage", 1)


def _hover_is_growing_crop(state, ctx):
    info = _hover_crop_stage(state, ctx)
    return info is not None and info[0] < info[1]


def _hover_is_mature_crop(state, ctx):
    info = _hover_crop_stage(state, ctx)
    return info is not None and info[0] >= info[1]


def _hovering_entity(state, ctx, kind, radius=25):
    """True when the hover cell is within `radius` world units of any
    existing entity of `kind` ("fences"/"traps"/"dogs") in the active zone.
    Entities are stored as (x, y, ...) tuples -- only x/y are position."""
    pos = ctx.get("hover_pos")
    if pos is None:
        return False
    zone = state[ctx["active_zone"]]
    for entity in zone.get(kind, []):
        ex, ey = entity[0], entity[1]
        if math.hypot(pos[0] - ex, pos[1] - ey) <= radius:
            return True
    return False


def _status_text(state, ctx):
    """The ultimate fallback: day/zone/money, plus enemy-HP-or-not at
    night, or a running prosperity/kill-count summary by day."""
    zone_name = "農田區" if ctx["active_zone"] == "farm" else "佈置區"
    lines = [f"第 {state.get('day_count', 1)} 天・{zone_name}・資金 ${state.get('money', 0)}"]
    if state.get("phase") == "night":
        if ctx["active_zone"] == "farm" and state["farm"].get("thief_pos") is not None:
            lines.append(f"小偷 HP 約 {state['farm'].get('thief_hp')}")
        elif ctx["active_zone"] == "decor" and state["decor"].get("boar_pos") is not None:
            lines.append(f"野豬 HP 約 {state['decor'].get('boar_hp')}")
        else:
            lines.append("目前沒有敵人靠近。")
    else:
        lines.append(f"繁榮度 {state.get('prosperity_score', 0)}・累積擊退敵人 {state.get('enemies_defeated', 0)}")
    return lines


# ---------------------------------------------------------------------------
# Tier 0 -- danger. Always wins over everything else.
# ---------------------------------------------------------------------------

THOUGHT_ENTRIES = [
    {
        "id": "danger_fence_under_attack",
        "text": "有圍欄正在被攻擊，可能需要支援！",
        "priority": 0,
        "trigger": "state",
        "condition": lambda state, ctx: any(
            k in state.get("last_msg", "") for k in ("破壞木圍欄", "衝撞了木圍欄")
        ),
        "required_phase": "night",
    },
    {
        "id": "danger_thief_present",
        "text": "有小偷正在靠近農田，直接點擊他可以攻擊。",
        "priority": 2,
        "trigger": "state",
        "condition": lambda state, ctx: state["farm"].get("thief_pos") is not None,
        "required_map": "farm",
        "required_phase": "night",
    },
    {
        "id": "danger_boar_present",
        "text": "有野豬正在靠近造景，直接點擊牠可以攻擊。",
        "priority": 2,
        "trigger": "state",
        "condition": lambda state, ctx: state["decor"].get("boar_pos") is not None,
        "required_map": "decor",
        "required_phase": "night",
    },

    # -----------------------------------------------------------------
    # Tier 1 -- actionable right now. Hover-aware where the action is
    # spatial. Demoted (not hidden) once the underlying Tutorial step is
    # learned, so it can still surface as a lesser fallback.
    # -----------------------------------------------------------------
    {
        "id": "action_till",
        "text": "這裡似乎可以開墾成農田。",
        "priority": _demote_once_learned(10, 32, "hoe"),
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_tillable(state, ctx),
        "required_map": "farm",
        "required_phase": "day",
        "required_item": "hoe",
        "required_tutorial": "hoe",
    },
    {
        "id": "action_plant",
        "text": "這塊土地應該可以種下種子。",
        "priority": _demote_once_learned(10, 32, "plant"),
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_empty_farmland(state, ctx),
        "required_map": "farm",
        "required_phase": "day",
        "required_item": ["radish", "carrot", "pumpkin"],
        "required_tutorial": "plant",
    },
    {
        "id": "action_harvest",
        "text": "這株作物似乎已經成熟了，也許可以收割。",
        "priority": _demote_once_learned(11, 32, "harvest"),
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_mature_crop(state, ctx),
        "required_map": "farm",
        "required_tutorial": "harvest",
    },
    {
        "id": "action_fence_place",
        "text": "圍欄可以擋住敵人的路線，也許適合放在這裡。",
        "priority": _demote_once_learned(13, 33, "fence"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "fence",
        "required_phase": "day",
        "required_tutorial": "fence",
    },
    {
        "id": "action_trap_place",
        "text": "陷阱會對踩到的敵人造成傷害，適合放在必經之路上。",
        "priority": _demote_once_learned(13, 33, "trap"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "trap",
        "required_phase": "day",
        "required_tutorial": "trap",
    },
    {
        "id": "action_dog_place",
        "text": "狗會主動攻擊靠近的敵人，適合放在容易被入侵的地方。",
        "priority": _demote_once_learned(13, 33, "dog"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "dog",
        "required_phase": "day",
        "required_tutorial": "dog",
    },
    {
        "id": "action_sell_crops",
        "text": "背包裡有收成了，按 B 打開商店可以賣掉換錢。",
        "priority": _demote_once_learned(15, 34, "shop_sell"),
        "trigger": "state",
        "condition": lambda state, ctx: _inventory_total(state) > 0 and not ctx["shop_open"],
        "required_tutorial": "shop_sell",
    },
    {
        "id": "action_buy_defense",
        "text": "有點資金了，商店裡的圍欄、陷阱、狗都能拿來準備防守。",
        "priority": _demote_once_learned(16, 34, "shop_buy_defense"),
        "trigger": "state",
        "condition": lambda state, ctx: state.get("money", 0) >= 20 and not ctx["shop_open"],
        "required_phase": "day",
        "required_tutorial": "shop_buy_defense",
    },

    # -----------------------------------------------------------------
    # Tier 2 -- important mechanics not yet learned. Disappears entirely
    # (via `not _learned(...)` in condition) once the Tutorial step
    # latches, rather than fading -- these are one-time introductions,
    # not standing facts about the world.
    # -----------------------------------------------------------------
    {
        "id": "learn_move",
        "text": "按住滑鼠右鍵拖曳，或用 WASD/方向鍵，可以看看農場其他地方。",
        "priority": 20,
        "trigger": "always",
        "condition": lambda state, ctx: not _learned(state, "move"),
        "required_tutorial": "move",
    },
    {
        "id": "learn_shop_intro",
        "text": "也許商店裡能找到種植或防守需要的東西。",
        "priority": 20,
        "trigger": "always",
        "condition": lambda state, ctx: not _learned(state, "shop_sell") and not ctx["shop_open"],
        "required_tutorial": "shop_sell",
    },
    {
        "id": "learn_night_start",
        "text": "夜晚降臨了，注意周圍的動靜。",
        "priority": 21,
        "trigger": "state",
        "condition": lambda state, ctx: not _learned(state, "night_start"),
        "required_phase": "night",
        "required_tutorial": "night_start",
    },
    {
        "id": "learn_night_end",
        "text": "撐過了一個晚上，新的一天開始了。",
        "priority": 21,
        "trigger": "state",
        "condition": lambda state, ctx: not _learned(state, "night_end") and state.get("day_count", 1) >= 2,
        "required_phase": "day",
        "required_tutorial": "night_end",
    },
    {
        "id": "learn_zone_switch",
        "text": "按 TAB 或畫面上方的按鈕，可以切換到佈置區看看。",
        "priority": 22,
        "trigger": "always",
        "condition": lambda state, ctx: not _learned(state, "zone_switch"),
        "required_tutorial": "zone_switch",
    },
    {
        "id": "learn_decor_place",
        "text": "佈置區可以擺放造景物，替農場增添一些繁榮度。",
        "priority": 23,
        "trigger": "state",
        "condition": lambda state, ctx: not _learned(state, "decor_place"),
        "required_map": "decor",
        "required_tutorial": "decor_place",
    },
    {
        "id": "learn_prosperity",
        "text": "繁榮度提升了，這會影響農場等級。",
        "priority": 24,
        "trigger": "state",
        "condition": lambda state, ctx: not _learned(state, "prosperity") and state.get("prosperity_score", 0) > 0,
        "required_tutorial": "prosperity",
    },
    {
        "id": "learn_farm_level",
        "text": "農場升級了，解鎖了新的作物。",
        "priority": 24,
        "trigger": "state",
        "condition": lambda state, ctx: not _learned(state, "farm_level") and state.get("farm_level", 1) >= 2,
        "required_tutorial": "farm_level",
    },
    {
        "id": "learn_carrot",
        "text": "胡蘿蔔已經解鎖，成熟後價值比白蘿蔔高。",
        "priority": 25,
        "trigger": "state",
        "condition": lambda state, ctx: (
            not _learned(state, "carrot") and state.get("farm_level", 1) >= 2 and ctx["shop_open"]
        ),
        "required_tutorial": "carrot",
    },
    {
        "id": "learn_pumpkin",
        "text": "魔法南瓜已經解鎖，是目前最值錢的作物。",
        "priority": 25,
        "trigger": "state",
        "condition": lambda state, ctx: (
            not _learned(state, "pumpkin") and state.get("farm_level", 1) >= 3 and ctx["shop_open"]
        ),
        "required_tutorial": "pumpkin",
    },
    {
        "id": "learn_advanced_defense",
        "text": "圍欄、陷阱、狗一起搭配，防守會更穩固。",
        "priority": 26,
        "trigger": "state",
        "condition": lambda state, ctx: not _learned(state, "advanced_defense") and state.get("day_count", 1) >= 5,
        "required_phase": "day",
        "required_tutorial": "advanced_defense",
    },

    # -----------------------------------------------------------------
    # Tier 3 -- descriptions of something nearby. Purely informative, not
    # actionable, never gated on Tutorial (this is ongoing situational
    # info, not a one-time lesson -- stays useful for a veteran player too).
    # -----------------------------------------------------------------
    {
        "id": "info_growing_crop",
        "text": "作物正在生長，可能還需要一點時間才會成熟。",
        "priority": 30,
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_growing_crop(state, ctx),
        "required_map": "farm",
    },
    {
        "id": "info_fence_nearby",
        "text": "圍欄可以擋住敵人的行動路線，替作物或造景爭取時間。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_entity(state, ctx, "fences"),
    },
    {
        "id": "info_trap_nearby",
        "text": "捕獸夾會對踩到的敵人造成傷害。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_entity(state, ctx, "traps"),
    },
    {
        "id": "info_dog_nearby",
        "text": "這隻狗會主動攻擊靠近的敵人。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_entity(state, ctx, "dogs", radius=15),
    },

    # -----------------------------------------------------------------
    # Tier 4 -- general ambient status. Always true -> guarantees the
    # candidate list is never empty.
    # -----------------------------------------------------------------
    {
        "id": "status_summary",
        "text": _status_text,
        "priority": 49,
        "trigger": "always",
        "condition": lambda state, ctx: True,
    },
]


def _resolve(value, state, ctx):
    return value(state, ctx) if callable(value) else value


def _entry_matches_context(entry, state, ctx):
    if not entry.get("enabled", True):
        return False
    required_map = entry.get("required_map")
    if required_map is not None and ctx["active_zone"] != required_map:
        return False
    required_phase = entry.get("required_phase")
    if required_phase is not None and state.get("phase") != required_phase:
        return False
    required_item = entry.get("required_item")
    if required_item is not None:
        items = required_item if isinstance(required_item, (list, tuple, set)) else [required_item]
        if ctx["current_tool"] not in items:
            return False
    condition = entry.get("condition")
    if condition is not None and not condition(state, ctx):
        return False
    return True


def _thought_state(state):
    t = state.setdefault("thought", {})
    t.setdefault("cooldowns", {})
    return t


def get_contemplation_lines(state, active_zone, current_tool, shop_open, hover_pos=None):
    """The single entry point main.py needs: figure out what to show while
    F is held. Also nudges Tutorial's bookkeeping forward (update_unlocks)
    since several entries here need current unlock status.

    hover_pos is the (gx, gy) grid cell the mouse is currently over (same
    units/snap as farmland/crops/fences/etc), or None -- main.py computes
    this every frame from the mouse position + camera offset. Callers that
    don't care about spatial hints (e.g. tests) can omit it."""
    _tutorial.update_unlocks(state)
    ctx = {
        "active_zone": active_zone,
        "current_tool": current_tool,
        "shop_open": shop_open,
        "hover_pos": hover_pos,
    }

    ts = _thought_state(state)
    cooldowns = ts["cooldowns"]
    for eid in list(cooldowns.keys()):
        cooldowns[eid] -= 1
        if cooldowns[eid] <= 0:
            del cooldowns[eid]

    candidates = [
        e for e in THOUGHT_ENTRIES
        if e["id"] not in cooldowns and _entry_matches_context(e, state, ctx)
    ]
    if not candidates:
        # status_summary's condition is unconditionally True, so this
        # shouldn't happen in practice -- stay defensive anyway.
        return _status_text(state, ctx)

    best = min(candidates, key=lambda e: _resolve(e["priority"], state, ctx))
    if best.get("cooldown"):
        cooldowns[best["id"]] = best["cooldown"]

    text = _resolve(best["text"], state, ctx)
    return text if isinstance(text, list) else [text]
