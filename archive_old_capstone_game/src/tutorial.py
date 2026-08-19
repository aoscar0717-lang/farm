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
    # seen_counts is written by thought.py (how many times each Thought
    # entry has actually been shown while F was held -- see thought.py's
    # module docstring), but lives under this same state["tutorial"] dict
    # per the "one shared progress store" rule, so it's initialized here
    # too rather than thought.py inventing its own separate state pocket.
    t.setdefault("seen_counts", {})
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


def note_seen(state, thought_entry_id):
    """Record that a src.thought THOUGHT_ENTRIES entry was actually
    selected and shown to the player (not just eligible) -- called from
    thought.py's get_contemplation_lines the moment an entry newly becomes
    the one on screen, not every frame it continues to be the one on
    screen (see thought.py's reset_hold_session / _last_shown_id for how
    that's de-duped). Backs the seen-count tiered-text mechanism (thought.py
    _tiered_text) and the a handful of *_aware Tutorial steps above that
    check "has this hint been shown at all yet" as an alternative to "has
    the underlying thing actually been built"."""
    sc = _tutorial_state(state)["seen_counts"]
    sc[thought_entry_id] = sc.get(thought_entry_id, 0) + 1
    return state


def get_seen_count(state, thought_entry_id):
    """How many times a given Thought entry has actually been shown (see
    note_seen). Used by thought.py's tiered-text helper to decide how
    concise a hint should be, and readable by anything else (tests, other
    UI) that wants the same number."""
    return _tutorial_state(state)["seen_counts"].get(thought_entry_id, 0)


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

    # ---- Added for the Tutorial Quest / Sidebar system (tutorial_quests.py) ----
    # These follow the exact same "one-way latch over real state" rule as
    # every step above -- no new mechanism, just more topics. See
    # tutorial_quests.py's module docstring for which quest task each one
    # backs, and why "click a button" was deliberately NOT used as a
    # completion signal anywhere in this table.
    {
        "id": "f_thought_used",
        # Set once the F-hold fade-in actually completes (main.py), i.e.
        # the player genuinely saw a 思索 line, not just tapped the key.
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("f_thought_used", False),
    },
    {
        "id": "seed_selected",
        # The shop's buy-tab click only *equips* a tool -- money isn't
        # spent until plant_crop_ actually happens (see capstone_contract.py).
        # There is genuinely no separate "purchased a seed" moment in this
        # game to detect, so this tracks "picked a seed tool from the shop
        # at least once" instead of inventing a purchase event that doesn't
        # exist. input_handler.py sets this flag at the exact click that
        # equips radish/carrot/pumpkin.
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("seed_selected", False),
    },
    {
        "id": "crop_matured",
        "unlock_check": lambda state: any(
            d.get("stage", 0) >= d.get("max_stage", 1) for d in state["farm"]["crop_data"].values()
        ),
    },
    {
        "id": "crop_sold",
        # Distinct from "shop_sell" above (which only means the shop was
        # opened) -- this is the real sell click in the shop's sell tab.
        # input_handler.py sets this flag at the exact point money is
        # actually credited for a sold item.
        "unlock_check": lambda state: _tutorial_state(state)["flags"].get("crop_sold", False),
    },
    {
        "id": "enemy_defeated",
        # Broader than the existing "combat" step (which only latches when
        # the *player's own click* lands a hit) -- this is "an enemy was
        # actually defeated" by any means (player, dog, or trap), matching
        # the shared enemies_defeated counter every defeat path already
        # increments.
        "unlock_check": lambda state: state.get("enemies_defeated", 0) > 0,
    },
    {
        "id": "decor_place_2",
        "unlock_check": lambda state: len(state["decor"]["decorations"]) >= 2,
    },
    {
        "id": "fountain_aware",
        # "Aware of" (not necessarily placed) -- true once the player has
        # either placed a fountain/風車, or has had its Thought line shown
        # at least once (thought.py increments seen_counts; see its module
        # docstring). Reads thought.py's bookkeeping without importing
        # thought.py itself (the dependency direction stays one-way, per
        # this module's own docstring) -- it's just another key under the
        # same state["tutorial"] dict this module already owns.
        "unlock_check": lambda state: (
            any(d[2] == "fountain" for d in state["decor"]["decorations"])
            or _tutorial_state(state).get("seen_counts", {}).get("action_fountain_place", 0) > 0
            or _tutorial_state(state).get("seen_counts", {}).get("info_fountain_nearby", 0) > 0
        ),
    },
    {
        "id": "trap_aware",
        "unlock_check": lambda state: (
            len(state["farm"]["traps"]) + len(state["decor"]["traps"]) > 0
            or _tutorial_state(state).get("seen_counts", {}).get("action_trap_place", 0) > 0
        ),
    },
    {
        "id": "dog_aware",
        "unlock_check": lambda state: (
            len(state["farm"]["dogs"]) + len(state["decor"]["dogs"]) > 0
            or _tutorial_state(state).get("seen_counts", {}).get("action_dog_place", 0) > 0
        ),
    },
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
