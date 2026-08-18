"""Tutorial progress tracking -- "has the player ever demonstrated they
understand mechanic X".

This is deliberately narrow and deliberately does NOT decide what to show
on screen. That job belongs to src/thought.py (思索系統), which is a
different concern: Tutorial answers "has this been learned" (a one-way
latch, checked once per concept, never un-learned even if the underlying
game state that triggered it changes later -- e.g. all crops get harvested
again); Thought answers "what's relevant to say right now" and keeps
working forever, including long after every Tutorial step here is done.
thought.py reads from this module (via `is_unlocked`) to decide how urgently
to bring something up; this module never imports or knows about thought.py
-- the dependency only goes one direction.

Nothing here is wired into capstone_contract.py. The contract layer (rules,
balance, tests) is untouched; this module only *observes* GameState from
the outside and keeps its own bookkeeping under state["tutorial"], so a
fresh state without that key still works.

Extending this: to track a new topic, add one entry to TUTORIAL_STEPS (just
an id + an unlock_check). No other file needs to know the step exists
unless something in thought.py wants to react to it.
"""

def _inventory_total(state):
    return sum(sum(grades.values()) for grades in state.get("inventory", {}).values())


def _tutorial_state(state):
    """Returns state["tutorial"], creating it (and its sub-dicts) if this is
    a state that predates the tutorial system, or a fresh new_game() state."""
    t = state.setdefault("tutorial", {})
    t.setdefault("unlocked", {})
    t.setdefault("flags", {})
    return t


def note_event(state, flag_name):
    """Record a one-off breadcrumb for things that happen outside
    apply_action and therefore leave no lasting trace in GameState itself
    (e.g. the shop being opened, the player switching zones). Called from
    input_handler.py / main.py at the exact moment the event happens."""
    _tutorial_state(state)["flags"][flag_name] = True
    return state


def is_unlocked(state, step_id):
    """Public read: has the player ever demonstrated they understand
    `step_id`? This is the one thing other modules (thought.py) need from
    Tutorial."""
    return _tutorial_state(state)["unlocked"].get(step_id, False)


# ---------------------------------------------------------------------------
# Step table. Each step is just:
#   id            unique string, also the key stored in tutorial.unlocked
#   unlock_check  (state) -> bool: has the player already demonstrated they
#                 understand this? Latches permanently once True (see
#                 update_unlocks) -- it's fine for unlock_check to reference
#                 a transient condition (e.g. "a thief is currently on
#                 screen"), the latch is what makes that stick.
# There is no display text, priority, or "is this relevant right now"
# condition here on purpose -- that's thought.py's job, not Tutorial's.
# ---------------------------------------------------------------------------

TUTORIAL_STEPS = [
    # ---- Day 1 fundamentals ----
    {
        "id": "move",
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("camera_moved", False),
    },
    {
        "id": "hoe",
        "unlock_check": lambda state: len(state["farm"]["farmland"]) > 0,
    },
    {
        "id": "plant",
        "unlock_check": lambda state: len(state["farm"]["crops"]) > 0 or len(state["farm"]["crop_data"]) > 0,
    },
    {
        "id": "harvest",
        "unlock_check": lambda state: _inventory_total(state) > 0,
    },
    {
        "id": "shop_sell",
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("shop_opened", False),
    },
    {
        "id": "shop_buy_defense",
        "unlock_check": lambda state: (
            len(state["farm"]["fences"]) + len(state["farm"]["traps"]) + len(state["farm"]["dogs"]) > 0
        ),
    },
    {
        "id": "night_start",
        # A night having fully completed at least once (day_count only
        # advances at _end_night) is a solid, directly-derivable signal --
        # no need to force-latch this at display time anymore now that
        # Tutorial itself never displays anything.
        "unlock_check": lambda state: state.get("day_count", 1) >= 2,
    },
    {
        "id": "thief_seen",
        # Transient (thief_pos resets to None once it despawns), but the
        # latch in update_unlocks makes "was this ever true" stick even
        # though the raw condition itself isn't persistent.
        "unlock_check": lambda state: state["farm"].get("thief_pos") is not None,
    },
    {
        "id": "combat",
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("landed_hit", False),
    },
    {
        "id": "night_end",
        "unlock_check": lambda state: state.get("day_count", 1) >= 3,
    },

    # ---- Day 2+: deeper systems, no fixed order required ----
    {
        "id": "zone_switch",
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("zone_switched", False),
    },
    {
        "id": "decor_place",
        "unlock_check": lambda state: len(state["decor"]["decorations"]) > 0,
    },
    {
        "id": "prosperity",
        "unlock_check": lambda state: state.get("prosperity_score", 0) > 0,
    },
    {
        "id": "farm_level",
        "unlock_check": lambda state: state.get("farm_level", 1) >= 2,
    },
    {
        "id": "carrot",
        "unlock_check": lambda state: any(
            d.get("type") == "carrot" for d in state["farm"]["crop_data"].values()
        ),
    },
    {
        "id": "pumpkin",
        "unlock_check": lambda state: any(
            d.get("type") == "pumpkin" for d in state["farm"]["crop_data"].values()
        ),
    },
    {
        "id": "fence",
        "unlock_check": lambda state: len(state["farm"]["fences"]) + len(state["decor"]["fences"]) > 0,
    },
    {
        "id": "trap",
        "unlock_check": lambda state: len(state["farm"]["traps"]) + len(state["decor"]["traps"]) > 0,
    },
    {
        "id": "dog",
        "unlock_check": lambda state: len(state["farm"]["dogs"]) + len(state["decor"]["dogs"]) > 0,
    },
    {
        "id": "advanced_defense",
        "unlock_check": lambda state: (
            len(state["farm"]["fences"]) > 0 and len(state["farm"]["traps"]) > 0 and len(state["farm"]["dogs"]) > 0
        ),
    },
    # NOTE: a previous version of this table had a "minimap" step. Checked
    # renderer.py while doing this refactor -- the game doesn't actually
    # have a minimap, so that step (and its hint text) was describing a
    # feature that doesn't exist. Dropped rather than carried forward.
]


def update_unlocks(state):
    """Call once per frame while F is held (cheap: just dict lookups + list
    lengths). Any step whose unlock_check now passes gets latched
    permanently. thought.py calls this before evaluating what to show."""
    t = _tutorial_state(state)
    unlocked = t["unlocked"]

    # landed_hit is a genuinely *later*, distinct event from "an enemy is
    # present" -- the player has to actually click and connect first -- so
    # it's safe to derive here rather than needing display-time latching.
    flags = t["flags"]
    last_msg = state.get("last_msg", "")
    if "擊中" in last_msg:
        flags["landed_hit"] = True

    for step in TUTORIAL_STEPS:
        sid = step["id"]
        if unlocked.get(sid):
            continue
        if step["unlock_check"](state):
            unlocked[sid] = True

    return state
