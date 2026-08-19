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
from src import tutorial_quests as _quests
from src import ui_layout as _ui_layout
from src.capstone_contract import DECOR_INFO, CROP_INFO, CROP_NAMES, DECOR_NAMES


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


def _tiered_text(entry_id, step_id, tier1, tier2, tier3, tier3_after=6):
    """Text that gets more concise as the player demonstrates familiarity,
    instead of showing the exact same sentence every single time F is held
    (the "新手→詳細, 熟悉→簡短" requirement):
      - tier1: shown while `step_id` hasn't latched in tutorial.py yet --
        the full, detailed explanation.
      - tier2: `step_id` is learned, but this exact entry hasn't been shown
        `tier3_after` times yet -- a medium-length reminder.
      - tier3: learned AND shown `tier3_after`+ times -- the terse, veteran
        phrasing.
    `entry_id` must match the THOUGHT_ENTRIES entry this text function is
    attached to (so it can look up its own seen_counts -- see tutorial.py's
    note_seen/get_seen_count). Passed explicitly rather than auto-detected
    because the entry's own dict doesn't exist yet at the point this
    function is called to build its "text" value."""
    def _text(state, ctx):
        if not _learned(state, step_id):
            return tier1
        if _tutorial.get_seen_count(state, entry_id) < tier3_after:
            return tier2
        return tier3
    return _text


def _afford_text(get_price, base_text):
    """Wraps a static hint with a money-shortfall variant: while the player
    can't currently afford the thing this entry is about, override the text
    with an explicit "$X of $Y needed" line instead of pretending the
    action is freely available (section 十三's explicit money example).
    `get_price` is (state, ctx) -> int (or None to skip the check entirely,
    e.g. an item whose price varies by sub-type resolved elsewhere)."""
    def _text(state, ctx):
        price = get_price(state, ctx)
        if price is not None:
            money = state.get("money", 0)
            if money < price:
                return f"目前有 ${money}，但這項建造需要 ${price}。"
        return base_text
    return _text


def _decor_price(state, ctx):
    return DECOR_INFO.get(ctx.get("current_tool"), {}).get("price")


def _fence_price(state, ctx):
    return 20  # matches capstone_contract.py's build_fence_ hardcoded cost


def _trap_price(state, ctx):
    return 50  # matches capstone_contract.py's place_trap_ hardcoded cost


def _dog_price(state, ctx):
    return 0 if state.get("free_dog") else 200  # matches place_dog_'s free_dog logic


# ---------------------------------------------------------------------------
# Hover helpers. ctx["hover_pos"] is the (gx, gy) grid cell the mouse is
# over, in the same units as farmland/crops/fences/etc positions, or None.
#
# _get_hover_context() is the SINGLE authoritative read of "what is the
# mouse cell actually pointing at" -- every farmland/crop-shaped condition
# and text function below reads through it instead of independently
# re-deriving state["farm"]["farmland"] / state["farm"]["crop_data"]
# membership. This was the root cause of the "已種植農田/作物 hover 沒有
# Thought" gap: individual conditions used to be gated on `required_item`
# (a specific tool being equipped) rather than on what's actually under the
# cursor, so a planted-but-not-mature crop hovered with no tool (or the
# "wrong" tool) equipped fell through every entry and landed on the fully
# generic ambient fallback. Hover Context now comes first; tool is just one
# more fact a text function can consult, never a gate on whether the cell
# gets described at all.
# ---------------------------------------------------------------------------

def _get_hover_context(state, ctx):
    """Returns a dict describing the world cell ctx["hover_pos"] is over,
    in the active zone:
        kind            "crop" / "farmland_empty" / "tillable" / "decor" /
                        None (nothing recognized here, or hover_pos is None)
        crop_type       "radish"/"carrot"/"pumpkin" or None
        crop_stage      int or None
        crop_max_stage  int or None
        crop_mature     bool
        farmland        bool -- is this cell tilled farmland at all
        decor_type      decor sub-type string or None (decor zone only)

    Deliberately narrow (farm crops/farmland + decor-zone decorations) --
    fences/traps/dogs/enemies already have their own radius-based "nearby"
    helpers below (_hovering_entity / _hovering_entity's callers), which
    check proximity rather than "is this the exact cell", so folding them
    into this exact-cell context would change their matching behavior.
    Nothing outside this function should read
    state["farm"]["farmland"]/["crop_data"] or state["decor"]["decorations"]
    to answer "what is the player looking at" -- extend this function
    instead of adding another ad hoc reader."""
    empty = {
        "kind": None, "crop_type": None, "crop_stage": None,
        "crop_max_stage": None, "crop_mature": False, "farmland": False,
        "decor_type": None,
    }
    pos = ctx.get("hover_pos")
    if pos is None:
        return empty

    if ctx.get("active_zone") == "farm":
        farm = state["farm"]
        data = farm.get("crop_data", {}).get(pos)
        if data is not None:
            stage = data.get("stage", 0)
            max_stage = data.get("max_stage", 1)
            return {
                **empty,
                "kind": "crop",
                "crop_type": data.get("type"),
                "crop_stage": stage,
                "crop_max_stage": max_stage,
                "crop_mature": stage >= max_stage,
                "farmland": True,
            }
        if pos in farm.get("farmland", []):
            return {**empty, "kind": "farmland_empty", "farmland": True}
        if pos not in farm.get("trees", []) and pos not in farm.get("rocks", []):
            return {**empty, "kind": "tillable"}
        return empty

    if ctx.get("active_zone") == "decor":
        for d in state["decor"].get("decorations", []):
            dx, dy, dtype, _hp = d
            if (dx, dy) == pos:
                return {**empty, "kind": "decor", "decor_type": dtype}
        return empty

    return empty


def _hover_is_tillable(state, ctx):
    """Hovering plain ground in the farm zone: not farmland yet, not a
    tree/rock."""
    return _get_hover_context(state, ctx)["kind"] == "tillable"


def _hover_is_empty_farmland(state, ctx):
    """Hovering tilled soil with nothing planted on it yet."""
    return _get_hover_context(state, ctx)["kind"] == "farmland_empty"


def _hover_crop_stage(state, ctx):
    hc = _get_hover_context(state, ctx)
    if hc["kind"] != "crop":
        return None
    return hc["crop_stage"], hc["crop_max_stage"]


def _hover_is_growing_crop(state, ctx):
    hc = _get_hover_context(state, ctx)
    return hc["kind"] == "crop" and not hc["crop_mature"]


def _hover_is_mature_crop(state, ctx):
    hc = _get_hover_context(state, ctx)
    return hc["kind"] == "crop" and hc["crop_mature"]


def _hovering_entity(state, ctx, kind):
    """True when the hover cell is EXACTLY on an entity of `kind` ("fences"/"traps"/"dogs") in the active zone.
    Entities are stored as (x, y, ...) tuples -- only x/y are position."""
    pos = ctx.get("hover_pos")
    if pos is None:
        return False
    zone = state[ctx["active_zone"]]
    for entity in zone.get(kind, []):
        if pos[0] == entity[0] and pos[1] == entity[1]:
            return True
    return False


def _hover_is_unfertilized_crop(state, ctx):
    """Hovering a real, already-planted crop that hasn't been fertilized
    yet (matches use_fertilizer_'s own "not data.get('fertilized')" gate in
    capstone_contract.py, so this entry never claims fertilizing is possible
    somewhere it actually isn't)."""
    pos = ctx.get("hover_pos")
    if pos is None or ctx["active_zone"] != "farm":
        return False
    farm = state["farm"]
    if pos not in farm.get("crops", []):
        return False
    data = farm["crop_data"].get(pos)
    return bool(data) and not data.get("fertilized")


def _crop_display_name(crop_type):
    return CROP_NAMES.get(crop_type, "作物")


def _empty_farmland_text(state, ctx):
    """Hovering tilled-but-unplanted farmland -- fires regardless of which
    tool (if any) is equipped, unlike action_plant which only applies while
    a seed is actually held. This is the entry that closes the original
    bug report: "已開墾的農地 hover 卻沒有 Thought" whenever the player
    wasn't holding a seed at the time."""
    return "這塊土地已經整理好了，可以種下種子。"


def _growing_crop_text(state, ctx):
    """Crop-type-aware growing text (section 一): differs by which crop is
    planted (so radish/carrot/pumpkin never share one generic sentence),
    and switches to a "快要成熟" phrasing on the crop's last growth stage
    before maturity -- skipped for 1-stage crops (radish's growth_time is
    1, so stage 0 IS "one stage before mature" for it; treating that as
    "near maturity" would make radish permanently near-mature and never
    show the plain growing message, so the near-maturity phrasing only
    kicks in for crops with at least 2 growth stages)."""
    hc = _get_hover_context(state, ctx)
    name = _crop_display_name(hc["crop_type"])
    max_stage = hc["crop_max_stage"] or 1
    stage = hc["crop_stage"] or 0
    if max_stage >= 2 and stage == max_stage - 1:
        return f"{name}快要成熟了，再等一下就可以收割。"
    return f"這裡種著{name}。再等一段時間，成熟後就可以用鐮刀收割。"


def _harvest_ready_text(state, ctx):
    """Tool-aware mature-crop text (section 一's explicit "手持鐮刀" vs
    "手持其他工具" distinction). Tier1 (not yet learned "harvest") keeps
    the ORIGINAL static sentence byte-for-byte -- tests/test_thought.py's
    test_B_hovering_a_mature_crop pins that exact string against a fresh,
    not-yet-learned state, so only tier2/tier3 (already learned "harvest")
    gain the crop-name + tool-aware phrasing; a brand new player sees the
    same gentle "也許可以收割" nudge as before."""
    hc = _get_hover_context(state, ctx)
    name = _crop_display_name(hc["crop_type"])
    if not _learned(state, "harvest"):
        return "這株作物似乎已經成熟了，也許可以收割。"
    if ctx.get("current_tool") == "scythe":
        return f"這株{name}已經成熟了，現在可以使用鐮刀收割。"
    return f"這株{name}已經成熟了，可以換成鐮刀收割。"


def _mouse_over_ui_chrome(ctx):
    """True when ctx["mouse_pos"] lands on any known interactive HUD chrome
    rect (shop button/money/stats row/day-night bar/zone toggle/hotbar/
    tutorial sidebar). Used to make the World Hover Context authoritatively
    null the instant the mouse is actually over UI: hover_pos is computed
    by main.py from the raw mouse position regardless of what's drawn on
    top of that screen location, so without this check a world-grid cell
    that happens to sit "behind" the shop button (say, a mature crop) could
    outrank the UI hint the player is actually pointing at -- exactly the
    bug section 十三 describes. get_contemplation_lines calls this once and
    overrides ctx["hover_pos"] to None when true, which makes every
    hover_pos-gated world entry naturally inapplicable without having to
    touch each one's condition individually."""
    if ctx.get("shop_open") or ctx.get("mouse_pos") is None:
        return False
    mp = ctx["mouse_pos"]
    rects = (
        _ui_layout.shop_button_rect(),
        _ui_layout.money_readout_rect(),
        _ui_layout.top_panel_stats_row_rect(),
        _ui_layout.daynight_bar_rect(),
        _ui_layout.zone_toggle_button_rects()["farm"],
        _ui_layout.zone_toggle_button_rects()["decor"],
        _ui_layout.hotbar_layout()["panel_rect"],
        _ui_layout.tutorial_sidebar_rect(),
    )
    return any(r.collidepoint(mp) for r in rects)


def _hovered_sidebar_task(state, ctx):
    """Which TutorialTask (if any) in the Sidebar's currently-shown chapter
    the mouse is over, using the exact same row rects
    draw_tutorial_sidebar() renders from (ui_layout.tutorial_sidebar_task_rects
    -- single source of truth for draw + hover, section 九)."""
    if ctx.get("shop_open") or ctx.get("mouse_pos") is None:
        return None
    for task, rect in _ui_layout.tutorial_sidebar_task_rects(state):
        if rect.collidepoint(ctx["mouse_pos"]):
            return task
    return None


def _sidebar_task_text(state, ctx):
    task = _hovered_sidebar_task(state, ctx)
    if task is None:
        return "這裡會顯示目前的新手任務進度，完成的項目會打勾。"
    progress = _quests.get_quest_progress(state)
    current_task = progress["current_task"]
    if task.is_done(state):
        return f"✓ 已完成：{task.title}。"
    if current_task is not None and task.id == current_task.id:
        return f"你現在的目標：{task.title}。{task.hint}"
    return f"{task.title}。{task.hint}（還沒輪到，需要先完成前面的任務。）"


# ---------------------------------------------------------------------------
# Shop hover helpers (section 五) -- resolve exactly which shop widget the
# mouse is over while the shop is open, mirroring input_handler.py's own
# _handle_shop_click slicing (same id lists, same left/right column split)
# so "what the player is hovering" and "what a click there would do" can
# never disagree.
# ---------------------------------------------------------------------------

def _hovered_shop_buy_item(state, ctx):
    if ctx.get("active_tab") == "sell":
        return None
    geo = _ui_layout.shop_page_geometry()
    mp = ctx.get("mouse_pos")
    if mp is None or not geo["shop_rect"].collidepoint(mp):
        return None
    active_tab = ctx.get("active_tab") or "seed"
    ids = _ui_layout.SHOP_ITEM_IDS.get(active_tab, [])
    left_ids = ids[:(len(ids) + 1) // 2]
    right_ids = ids[(len(ids) + 1) // 2:]
    for col_ids, column in [(left_ids, "left"), (right_ids, "right")]:
        rects = _ui_layout.shop_column_rects(len(col_ids), is_sell=False, column=column)
        for item_id, card_rect in zip(col_ids, rects):
            if card_rect.collidepoint(mp):
                return item_id
    return None


def _hovered_shop_sell_item(state, ctx):
    if ctx.get("active_tab") != "sell":
        return None
    mp = ctx.get("mouse_pos")
    if mp is None:
        return None
    sellable = _ui_layout.build_sellable_list(state, CROP_INFO)
    left_items, right_items = sellable[:6], sellable[6:12]
    for col_items, column in [(left_items, "left"), (right_items, "right")]:
        rects = _ui_layout.shop_column_rects(len(col_items), is_sell=True, column=column)
        for item, card_rect in zip(col_items, rects):
            if card_rect.collidepoint(mp):
                return item
    return None


def _shop_buy_item_text(state, ctx):
    item_id = _hovered_shop_buy_item(state, ctx)
    if item_id is None:
        return "選擇這個項目可以裝備對應的工具。"
    if item_id in CROP_INFO:
        name = f"{CROP_NAMES.get(item_id, item_id)}種子"
        price = CROP_INFO[item_id]["price"]
        base = f"{name}。選擇後可以在已開墾的農田種植。"
    elif item_id == "fence":
        price = 20
        base = "木圍欄。可以擋住敵人的行動路線，替作物或造景爭取時間。"
    elif item_id == "trap":
        price = 50
        base = "地刺陷阱。敵人踩到會受到傷害，是一次性的。"
    elif item_id == "dog":
        price = 0 if state.get("free_dog") else 200
        base = "看門狗。會主動攻擊靠近的敵人，且不會陣亡。"
    elif item_id in DECOR_INFO:
        name = DECOR_NAMES.get(item_id, item_id)
        price = DECOR_INFO[item_id]["price"]
        base = f"{name}。放置後可以提升農場的繁榮度。"
    else:
        return "選擇這個項目可以裝備對應的工具。"

    money = state.get("money", 0)
    if price and money < price:
        return f"{base}目前資金不足，需要 ${price}。"
    if price:
        return f"{base}目前資金足夠，可以使用這個項目。"
    return base


def _shop_sell_item_text(state, ctx):
    item = _hovered_shop_sell_item(state, ctx)
    if item is None:
        return "把收穫的作物出售，換取農場資金。"
    return f"{item['name']}。點擊可以出售，獲得 ${item['price']}。"


def _prosperity_text(state, ctx):
    """Section 六: hovering the top-panel stats row must report the REAL
    prosperity value / farm level / progress toward the next level, not
    just a static description of what prosperity is -- and switch to
    near-upgrade-specific phrasing once the player is close, mirroring the
    real _update_prosperity_and_level thresholds (100 for level 2, 300 for
    level 3, level 3 is the cap) instead of inventing separate numbers."""
    score = state.get("prosperity_score", 0)
    level = state.get("farm_level", 1)
    if level >= 3:
        return f"目前繁榮度 {score}，農場已經是最高的等級 {level}。"
    next_threshold = 100 if level == 1 else 300
    remaining = max(0, next_threshold - score)
    if remaining <= 20:
        return f"目前繁榮度 {score}，農場等級 {level}。再增加 {remaining} 點繁榮度就能升到等級 {level + 1} 了！"
    return f"目前繁榮度 {score}，農場等級 {level}。累積到 {next_threshold} 點繁榮度就能升到下一級。"


def _hovering_rect(ctx, rect):
    """True when ctx["mouse_pos"] (raw screen pixel coords, distinct from
    hover_pos's world-grid coords) falls inside `rect`. Backs the UI-chrome
    Thought entries (shop button/money/stats/day-night bar/zone toggle/
    hotbar/sidebar) -- those live in fixed screen space, not the scrolling
    world, so they can't reuse hover_pos."""
    pos = ctx.get("mouse_pos")
    return pos is not None and rect.collidepoint(pos)


def _hovering_decor(state, ctx, decor_type):
    """Like _hovering_entity, but for one specific decoration sub-type.
    Unlike fences/traps/dogs (each its own list), every placed decoration --
    regardless of sub-type -- lives together in zone["decorations"] as
    (x, y, decor_type, hp) tuples (see renderer.py _draw_decorations), so
    this filters by decor_type instead of picking a different list."""
    pos = ctx.get("hover_pos")
    if pos is None:
        return False
    zone = state[ctx["active_zone"]]
    for d in zone.get("decorations", []):
        dx, dy, dtype, _hp = d
        if dtype == decor_type and pos[0] == dx and pos[1] == dy:
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
    {
        "id": "danger_hovered_fence_attack",
        # More specific (and more urgent, priority -1) than the generic
        # danger_fence_under_attack above: fires only while the mouse is
        # actually over the exact fence currently being attacked, using the
        # thief's own real AI state (thief_ai_state == "attacking_fence" +
        # thief_attack_target_fence), not a last_msg keyword match. No boar
        # equivalent -- the boar's fence-hit code (see
        # capstone_contract.py's _night_tick_boar) never tracks a specific
        # target fence position the way the thief does, so a hover-specific
        # boar version would be describing a mechanic that doesn't exist.
        "text": "小偷正在攻擊這座柵欄！如果柵欄被破壞，可以考慮增加防禦或使用陷阱。",
        "priority": -1,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("hover_pos") is not None
            and state["farm"].get("thief_ai_state") == "attacking_fence"
            and state["farm"].get("thief_attack_target_fence") is not None
            and ctx["hover_pos"][0] == state["farm"]["thief_attack_target_fence"][0]
            and ctx["hover_pos"][1] == state["farm"]["thief_attack_target_fence"][1]
        ),
        "required_map": "farm",
        "required_phase": "night",
    },

    # -----------------------------------------------------------------
    # Tier 1 -- actionable right now. Hover-aware where the action is
    # spatial. Demoted (not hidden) once the underlying Tutorial step is
    # learned, so it can still surface as a lesser fallback.
    # -----------------------------------------------------------------
    {
        "id": "action_till",
        "text": _tiered_text(
            "action_till", "hoe",
            tier1="這裡似乎可以開墾成農田。",
            tier2="使用鋤頭可以開墾這塊土地。",
            tier3="這裡可以開墾。",
        ),
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
        "text": _tiered_text(
            "action_plant", "plant",
            tier1="這塊土地應該可以種下種子。",
            tier2="選擇一種種子，然後種在這裡。",
            tier3="可以種植。",
        ),
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
        "text": _harvest_ready_text,
        "priority": _demote_once_learned(11, 32, "harvest"),
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_mature_crop(state, ctx),
        "required_map": "farm",
        "required_tutorial": "harvest",
    },
    {
        "id": "action_fence_place",
        "text": _afford_text(_fence_price, "圍欄可以擋住敵人的路線，也許適合放在這裡。"),
        "priority": _demote_once_learned(13, 33, "fence"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "fence",
        "required_phase": "day",
        "required_tutorial": "fence",
    },
    {
        "id": "action_trap_place",
        "text": _afford_text(_trap_price, "陷阱會對踩到的敵人造成傷害，適合放在必經之路上。"),
        "priority": _demote_once_learned(13, 33, "trap"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "trap",
        "required_phase": "day",
        "required_tutorial": "trap",
    },
    {
        "id": "action_dog_place",
        "text": _afford_text(_dog_price, "狗會主動攻擊靠近的敵人，適合放在容易被入侵的地方。"),
        "priority": _demote_once_learned(13, 33, "dog"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "dog",
        "required_phase": "day",
        "required_tutorial": "dog",
    },

    {
        "id": "action_cat_place",
        "text": "招財小貓跑速極快，爪擊能減速敵人 50%，白天還能定期為農場摸出金幣！",
        "priority": 13,
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "cat",
        "required_phase": "day",
    },
    {
        "id": "action_goose_place",
        "text": "警戒鵝領域意識極強，憤怒衝撞能將入侵的敵人強力向後擊退！",
        "priority": 13,
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "goose",
        "required_phase": "day",
    },
    {
        "id": "action_sheep_place",
        "text": "棉花守護羊擁有 10 點厚實羊毛護盾，能主動吸引周圍敵人仇恨以保護作物。",
        "priority": 13,
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "sheep",
        "required_phase": "day",
    },
    {
        "id": "action_bull_place",
        "text": "鐵壁戰鬥牛威嚴強大，巨角挑擊能造成雙倍重擊傷害（2點傷害）！",
        "priority": 13,
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "bull",
        "required_phase": "day",
    },
    {
        "id": "action_owl_place",
        "text": "夜行守護鳥飛行極快，遠程空中俯衝啄擊，有機會直接將敵人嚇得原地僵直！",
        "priority": 13,
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "owl",
        "required_phase": "day",
    },
    {
        "id": "action_shovel_use",
        "text": "鐵鏟可以移除這裡的農田、圍欄、景觀、陷阱或守護動物。",

        "priority": 14,
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "shovel",
    },
    {
        "id": "action_fertilizer_use",
        "text": "對這株作物施肥，可以加快它的生長速度。",
        "priority": 14,
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_unfertilized_crop(state, ctx),
        "required_map": "farm",
        "required_item": "fertilizer",
    },
    {
        "id": "info_fertilizer_no_crop",
        "text": "這裡沒有作物可以施肥。",
        "priority": 36,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("hover_pos") is not None and not _hover_is_unfertilized_crop(state, ctx)
        ),
        "required_map": "farm",
        "required_item": "fertilizer",
    },
    {
        "id": "info_no_harvestable_crop",
        "text": "目前沒有成熟作物可以收割。",
        "priority": 36,
        "trigger": "state",
        "condition": lambda state, ctx: not any(
            d.get("stage", 0) >= d.get("max_stage", 1) for d in state["farm"]["crop_data"].values()
        ),
        "required_map": "farm",
        "required_item": "scythe",
    },
    # Landscape/decor placement hints -- same shape as action_fence_place /
    # action_trap_place / action_dog_place above (hover-aware, gated on the
    # matching tool being equipped), but there's no per-sub-type Tutorial
    # step for decor (only the shared "decor_place" -- see tutorial.py), so
    # all four demote against that one shared step instead of inventing four
    # new Tutorial entries just for this.
    {
        "id": "action_stone_path_place",
        "text": _afford_text(_decor_price, "在這裡鋪一段石板路，也許能讓農場的動線更清楚一點。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "stone_path",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_flower_place",
        "text": _afford_text(_decor_price, "擺一盆花在這裡，能替農場添點生氣，也對繁榮度有幫助。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "flower",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_bench_place",
        "text": _afford_text(_decor_price, "放一張長椅在這裡，讓農場多一個可以停下來坐坐的角落。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "bench",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_fountain_place",
        "text": _afford_text(_decor_price, "立一座風車在這裡，能替農場添點鄉村風景，也對繁榮度有幫助。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "fountain",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    # Landscape expansion pass -- 7 more decor sub-types, same shape as the
    # four above (still all demoting against the one shared "decor_place"
    # Tutorial step).
    {
        "id": "action_scarecrow_place",
        "text": _afford_text(_decor_price, "立一個稻草人在這裡，能替農場添點田園氣氛，雖然它不會真的嚇跑什麼。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "scarecrow",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_crate_place",
        "text": _afford_text(_decor_price, "放一個木箱在這裡，讓農場看起來更有生活感。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "crate",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_bush_place",
        "text": _afford_text(_decor_price, "種一叢灌木在這裡，讓農場的綠意更豐富一些。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "bush",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_rock_place",
        "text": _afford_text(_decor_price, "放一塊石頭在這裡，替農場增添一點自然的庭院感。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "rock",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_sunflower_place",
        "text": _afford_text(_decor_price, "種一株向日葵在這裡，鮮豔的花朵能讓農場更有生氣。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "sunflower",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_pine_tree_place",
        "text": _afford_text(_decor_price, "在這裡種一棵松樹，能讓農場多一點綠蔭與層次感。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "pine_tree",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_big_tree_place",
        "text": _afford_text(_decor_price, "在這裡種一棵大樹，會是農場裡相當顯眼的核心景觀。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "big_tree",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    # Landscape expansion round 2 -- 8 more decor sub-types, same shape.
    {
        "id": "action_stump_place",
        "text": _afford_text(_decor_price, "在這裡留一段樹墩，能替農場添點原始自然的味道。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "stump",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_mushroom_place",
        "text": _afford_text(_decor_price, "在這裡種一朵蘑菇，替農場角落添點野趣。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "mushroom",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_picnic_basket_place",
        "text": _afford_text(_decor_price, "放一個野餐籃在這裡，讓農場多一點悠閒的生活氣息。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "picnic_basket",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_woodpile_place",
        "text": _afford_text(_decor_price, "在這裡堆一疊柴薪，讓農場更有生活感。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "woodpile",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_picnic_blanket_place",
        "text": _afford_text(_decor_price, "鋪一張野餐墊在這裡，適合當作農場裡休息放鬆的角落。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "picnic_blanket",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_beehive_place",
        "text": _afford_text(_decor_price, "在這裡放一個蜂箱，能替農場增添一點養蜂的田園氣息。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "beehive",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_garden_table_place",
        "text": _afford_text(_decor_price, "放一張庭院桌在這裡，能跟長椅搭配成休息的角落。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "garden_table",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
    },
    {
        "id": "action_fruit_tree_place",
        "text": _afford_text(_decor_price, "在這裡種一棵果樹，能替農場增添真正的農家風景。"),
        "priority": _demote_once_learned(13, 33, "decor_place"),
        "trigger": "hover",
        "condition": lambda state, ctx: ctx.get("hover_pos") is not None,
        "required_item": "fruit_tree",
        "required_map": "decor",
        "required_phase": "day",
        "required_tutorial": "decor_place",
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
        "text": _growing_crop_text,
        "priority": 30,
        "trigger": "hover",
        "condition": lambda state, ctx: _hover_is_growing_crop(state, ctx),
        "required_map": "farm",
    },
    {
        "id": "info_empty_farmland",
        # Fires regardless of which tool (if any) is equipped -- unlike
        # action_plant, which only applies while a seed is actually held.
        # This is the entry that closes the original bug report: hovering
        # already-tilled, unplanted farmland used to fall straight through
        # to the generic ambient fallback whenever the player wasn't
        # holding a seed at that exact moment.
        "text": _empty_farmland_text,
        "priority": 30,
        "trigger": "hover",
        # Deliberately excludes the case a seed is actually equipped --
        # action_plant (above) already owns that combination at a lower
        # (more urgent) priority band and stays authoritative for it at
        # every tutorial tier, learned or not; this entry only needs to
        # cover every OTHER tool (or no tool), which action_plant's own
        # required_item never did.
        "condition": lambda state, ctx: (
            _hover_is_empty_farmland(state, ctx)
            and ctx.get("current_tool") not in ("radish", "carrot", "pumpkin")
        ),
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
        "text": "地刺陷阱會對踩到的敵人造成傷害。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_entity(state, ctx, "traps"),
    },
    {
        "id": "info_dog_nearby",
        "text": "這隻狗會主動攻擊靠近的敵人。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_entity(state, ctx, "dogs"),
    },
    {
        "id": "info_stone_path_nearby",
        "text": "這條石板路讓農場走起來更有規劃感。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "stone_path"),
        "required_map": "decor",
    },
    {
        "id": "info_flower_nearby",
        "text": "這盆花替周圍添了點生氣，也貢獻了一些繁榮度。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "flower"),
        "required_map": "decor",
    },
    {
        "id": "info_bench_nearby",
        "text": "這張長椅讓農場多了一處可以喘口氣的角落。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "bench"),
        "required_map": "decor",
    },
    {
        "id": "info_fountain_nearby",
        "text": "這座風車讓農場多了一點悠閒的鄉村氣息。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "fountain"),
        "required_map": "decor",
    },
    {
        "id": "info_scarecrow_nearby",
        "text": "這個稻草人靜靜站在田邊，替農場增添了一點田園味。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "scarecrow"),
        "required_map": "decor",
    },
    {
        "id": "info_crate_nearby",
        "text": "這個木箱堆在角落，替農場添了點生活痕跡。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "crate"),
        "required_map": "decor",
    },
    {
        "id": "info_bush_nearby",
        "text": "這叢灌木讓周圍多了一點自然的綠意。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "bush"),
        "required_map": "decor",
    },
    {
        "id": "info_rock_nearby",
        "text": "這塊石頭安靜地待在這裡，替庭院增添了一點自然感。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "rock"),
        "required_map": "decor",
    },
    {
        "id": "info_sunflower_nearby",
        "text": "這株向日葵迎著陽光綻放，讓農場看起來更有生氣。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "sunflower"),
        "required_map": "decor",
    },
    {
        "id": "info_pine_tree_nearby",
        "text": "這棵松樹替農場添了一片綠蔭，也讓景觀更有層次。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "pine_tree"),
        "required_map": "decor",
    },
    {
        "id": "info_big_tree_nearby",
        "text": "這棵大樹枝葉茂密，是農場裡相當醒目的核心景觀。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "big_tree"),
        "required_map": "decor",
    },
    {
        "id": "info_stump_nearby",
        "text": "這段樹墩透出一點原始自然的味道，也是農場裡小小的休憩點。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "stump"),
        "required_map": "decor",
    },
    {
        "id": "info_mushroom_nearby",
        "text": "這朵蘑菇靜靜長在角落，替農場增添了一點野趣。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "mushroom"),
        "required_map": "decor",
    },
    {
        "id": "info_picnic_basket_nearby",
        "text": "這個野餐籃擺在這裡，讓農場多了一點悠閒的生活氣息。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "picnic_basket"),
        "required_map": "decor",
    },
    {
        "id": "info_woodpile_nearby",
        "text": "這疊柴薪堆在這裡，替農場添了點樸實的生活感。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "woodpile"),
        "required_map": "decor",
    },
    {
        "id": "info_picnic_blanket_nearby",
        "text": "這張野餐墊鋪在這裡，是農場裡一個適合休息放鬆的角落。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "picnic_blanket"),
        "required_map": "decor",
    },
    {
        "id": "info_beehive_nearby",
        "text": "這個蜂箱安靜地放在這裡，替農場增添了一點養蜂的田園氣息。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "beehive"),
        "required_map": "decor",
    },
    {
        "id": "info_garden_table_nearby",
        "text": "這張庭院桌擺在這裡，是農場裡一個適合坐下來的角落。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "garden_table"),
        "required_map": "decor",
    },
    {
        "id": "info_fruit_tree_nearby",
        "text": "這棵果樹結實纍纍，是農場裡最有農家氣息的風景之一。",
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: _hovering_decor(state, ctx, "fruit_tree"),
        "required_map": "decor",
    },

    # -----------------------------------------------------------------
    # Tier 3b -- UI chrome hover coverage (section 十二). These key off
    # ctx["mouse_pos"] (raw screen pixels), not hover_pos (world grid), so
    # they only ever fire when a caller actually supplies mouse_pos --
    # existing tests that omit it simply never reach these. All gated on
    # `not ctx["shop_open"]` even though main.py already only calls this
    # while the shop is closed, so the entries stay honest if ever called
    # otherwise (e.g. from a future test).
    # -----------------------------------------------------------------
    {
        "id": "ui_shop_button",
        "text": "商店可以購買種子、防禦道具與景觀，也能在裡面把收成換成資金。",
        "priority": 34,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovering_rect(ctx, _ui_layout.shop_button_rect())
        ),
    },
    {
        "id": "ui_money",
        "text": lambda state, ctx: f"這是目前可以用來種植與建造的資金，現在有 ${state.get('money', 0)}。",
        "priority": 34,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovering_rect(ctx, _ui_layout.money_readout_rect())
        ),
    },
    {
        "id": "ui_stats_row",
        "text": _prosperity_text,
        "priority": 34,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovering_rect(ctx, _ui_layout.top_panel_stats_row_rect())
        ),
    },
    {
        "id": "ui_daynight_bar",
        "text": "夜晚會出現更多威脅，白天則適合整理與建設。",
        "priority": 34,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovering_rect(ctx, _ui_layout.daynight_bar_rect())
        ),
    },
    {
        "id": "ui_zone_toggle",
        "text": "按這裡（或按 TAB）可以切換農田區與佈置區。",
        "priority": 34,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"]
            and (
                _hovering_rect(ctx, _ui_layout.zone_toggle_button_rects()["farm"])
                or _hovering_rect(ctx, _ui_layout.zone_toggle_button_rects()["decor"])
            )
        ),
    },
    {
        "id": "ui_hotbar",
        "text": "這是快捷工具列，按數字鍵 1-4 也能快速切換。",
        "priority": 35,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovering_rect(ctx, _ui_layout.hotbar_layout()["panel_rect"])
        ),
    },
    {
        "id": "ui_tutorial_sidebar",
        "text": "這裡會顯示目前的新手任務進度，完成的項目會打勾。",
        "priority": 35,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovering_rect(ctx, _ui_layout.tutorial_sidebar_rect())
            and _hovered_sidebar_task(state, ctx) is None
        ),
    },
    {
        "id": "ui_tutorial_sidebar_task",
        # More specific than ui_tutorial_sidebar above (priority 33 < 35):
        # fires when the mouse is over one particular task ROW, not just
        # the sidebar panel in general (section 九 -- "Sidebar 也要能被 F
        # 思考", including "hover the current task" vs "hover a completed
        # task" giving different text).
        "text": _sidebar_task_text,
        "priority": 33,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            not ctx["shop_open"] and _hovered_sidebar_task(state, ctx) is not None
        ),
        "detail_key": lambda state, ctx: getattr(_hovered_sidebar_task(state, ctx), "id", None),
    },

    # -----------------------------------------------------------------
    # Tier 3d -- Shop hover coverage (section 五). Only reachable while the
    # shop is actually open (ctx["shop_open"] is True) -- everything above
    # this point that depends on hover_pos is already naturally silenced by
    # main.py setting hover_pos to None whenever the shop covers the
    # screen, but these entries need their own explicit shop_open check
    # since they key off mouse_pos, which stays valid the whole time.
    # -----------------------------------------------------------------
    {
        "id": "shop_buy_tab",
        "text": "這裡可以選擇要種植或建造的項目。",
        "priority": 32,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("shop_open")
            and _hovering_rect(ctx, _ui_layout.shop_page_geometry()["tab_buy"])
        ),
    },
    {
        "id": "shop_sell_tab",
        "text": "把收穫的作物出售，換取農場資金。",
        "priority": 32,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("shop_open")
            and _hovering_rect(ctx, _ui_layout.shop_page_geometry()["tab_sell"])
        ),
    },
    {
        "id": "shop_subtab",
        "text": lambda state, ctx: {
            "seed": "這裡可以選擇要種植的種子。",
            "def": "這裡可以選擇防禦設施：圍欄、陷阱、看門狗。",
            "pet": "這裡可以選擇農場的景觀裝飾。",
        }.get(ctx.get("active_tab"), "這裡可以選擇要購買的項目分類。"),
        "priority": 32,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("shop_open") and ctx.get("active_tab") != "sell"
            and any(
                _hovering_rect(ctx, r) for r in _ui_layout.shop_subtab_rects().values()
            )
        ),
    },
    {
        "id": "shop_item_card_buy",
        "text": _shop_buy_item_text,
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("shop_open") and _hovered_shop_buy_item(state, ctx) is not None
        ),
        "detail_key": lambda state, ctx: _hovered_shop_buy_item(state, ctx),
    },
    {
        "id": "shop_item_card_sell",
        "text": _shop_sell_item_text,
        "priority": 31,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("shop_open") and _hovered_shop_sell_item(state, ctx) is not None
        ),
        "detail_key": lambda state, ctx: (_hovered_shop_sell_item(state, ctx) or {}).get("id"),
    },
    {
        "id": "shop_close_hint",
        # There's no dedicated close button widget in this game -- clicking
        # anywhere outside the shop panel closes it (see input_handler.py's
        # _handle_shop_click: `if not shop_rect.collidepoint(...): shop_open
        # = False`). This entry describes that real mechanic instead of
        # inventing a close button that doesn't exist.
        "text": "點擊商店外的區域可以關閉商店。",
        "priority": 38,
        "trigger": "hover",
        "condition": lambda state, ctx: (
            ctx.get("shop_open")
            and ctx.get("mouse_pos") is not None
            and not _ui_layout.shop_page_geometry()["shop_rect"].collidepoint(ctx["mouse_pos"])
        ),
    },

    # -----------------------------------------------------------------
    # Tier 3c -- Sidebar <-> F guidance link (section 十一). A weak
    # fallback: only wins when nothing more specific (danger/actionable/
    # unlearned-mechanic/nearby-info/UI-hover above) applies, but still
    # beats the fully generic ambient status line below it. Reads the exact
    # same tutorial_quests.get_quest_progress() the Sidebar renders from, so
    # the two can never disagree about what "the current task" is -- this
    # is deliberately NOT a duplicate of the Sidebar's own text (that would
    # just be Sidebar repeated twice); it exists for the moment the player
    # is looking at something with no dedicated Thought of its own and asks
    # "okay, so what should I even be doing".
    # -----------------------------------------------------------------
    {
        "id": "quest_guidance",
        "text": lambda state, ctx: _quests.get_quest_progress(state)["current_task"].hint,
        "priority": 39,
        "trigger": "state",
        "condition": lambda state, ctx: _quests.get_quest_progress(state)["current_task"] is not None,
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
    # _last_shown_key backs the seen_counts increment below: it's the
    # (entry_id, detail) pair that was on screen last time
    # get_contemplation_lines was called *this F-hold session*
    # (reset_hold_session clears it back to None the moment F is released
    # -- see main.py). `detail` disambiguates entries whose CONTENT can
    # change without their id changing (e.g. info_growing_crop shows
    # different text for a carrot vs a pumpkin) -- comparing the full pair
    # is what makes note_seen fire once per genuinely new "look" (moving
    # from one crop to a different one counts as fresh, section 十四's
    # "胡蘿蔔 → 南瓜 → 商店，每次都是新的 context"), while holding F still
    # over the exact same cell/widget never fires more than once.
    t.setdefault("_last_shown_key", None)
    return t


def reset_hold_session(state):
    """Call once, the moment F transitions from held to released (main.py).
    Clears the "what was last shown" bookkeeping so the next time F is
    pressed, whatever entry comes up first is counted as a fresh look (and
    therefore increments its seen_count) even if it's the exact same entry
    that was showing at the end of the previous hold."""
    _thought_state(state)["_last_shown_key"] = None
    return state


def get_contemplation_lines(
    state, active_zone, current_tool, shop_open, hover_pos=None, mouse_pos=None, active_tab=None,
):
    """The single entry point main.py needs: figure out what to show while
    F is held. Also nudges Tutorial's bookkeeping forward (update_unlocks)
    since several entries here need current unlock status.

    hover_pos is the (gx, gy) grid cell the mouse is currently over (same
    units/snap as farmland/crops/fences/etc), or None -- main.py computes
    this every frame from the mouse position + camera offset. mouse_pos is
    the raw (screen-pixel) mouse position, used by the UI-chrome hover
    entries (shop button/money/stats row/day-night bar/zone toggle/hotbar/
    sidebar -- see ui_layout.py) and, while the shop is open, by the shop's
    own internal hover entries (tabs/item cards). active_tab is the shop's
    current buy/sell sub-tab ("seed"/"def"/"pet"/"sell"), only consulted
    while shop_open -- needed to resolve which item card is under the
    mouse. Callers that don't care about any of these can omit them."""
    _tutorial.update_unlocks(state)
    ctx = {
        "active_zone": active_zone,
        "current_tool": current_tool,
        "shop_open": shop_open,
        "hover_pos": hover_pos,
        "mouse_pos": mouse_pos,
        "active_tab": active_tab,
    }

    # Hit-test UI chrome FIRST (section 八's "Mouse Position -> Hit Test ->
    # Hover Context -> Thought Resolver" flow): if the mouse is actually
    # over a known HUD element, the World Hover Context is authoritatively
    # nulled out so nothing sitting "behind" that UI element in world-grid
    # coordinates can outrank the UI hint the player is actually pointing
    # at (section 十三).
    if _mouse_over_ui_chrome(ctx):
        ctx["hover_pos"] = None

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

    # Seen-count bookkeeping (section 九/十四): only increment when this
    # entry -- or, for entries whose text varies by sub-target, this exact
    # sub-target -- is newly the one being shown. World-hover entries key
    # naturally off hover_pos (moving to a different cell is always a fresh
    # look); UI-ish entries that share one id across several possible
    # widgets (shop item cards, sidebar task rows) declare their own
    # "detail_key" function to disambiguate. Anything else falls back to
    # just the entry id, so holding F over the exact same spot/widget for
    # several seconds still counts as exactly one look, never once a frame.
    if ctx.get("hover_pos") is not None:
        detail = ctx["hover_pos"]
    elif "detail_key" in best:
        detail = _resolve(best["detail_key"], state, ctx)
    else:
        detail = None
    shown_key = (best["id"], detail)
    if shown_key != ts.get("_last_shown_key"):
        _tutorial.note_seen(state, best["id"])
        ts["_last_shown_key"] = shown_key

    text = _resolve(best["text"], state, ctx)
    return text if isinstance(text, list) else [text]
