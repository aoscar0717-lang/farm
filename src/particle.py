"""Floating Text Particle Manager (Juiciness / 視覺回饋).

Pure drawing-layer module -- reads the plain, presentation-agnostic
events that capstone_contract.py's apply_action appends to
state["events"] (see _emit_event there) and turns them into upward-
drifting, fading text particles. capstone_contract.py itself never
imports this module and never decides colors/text/animation -- all of
that lives here, in KIND_STYLES, exactly per the "keep drawing logic out
of apply_action" constraint.

Lifecycle (mirrors ui.py's existing _toast_queue pattern):
  - main.py/renderer.py call ingest_events(state) once per frame to pull
    any new events out of state["events"] and turn them into particles.
  - renderer.py calls update_and_draw(screen, camera_x, camera_y) once
    per frame to age, drift, fade, and draw (and drop expired) particles.
  - main.py is responsible for clearing state["events"] = [] once per
    frame after ingest_events has consumed them (same "producer appends,
    consumer drains" contract as the events list's docstring says).
"""
import pygame

CELL_SIZE = 10  # duplicated from config.py (see renderer.py's own
                 # _screen_coords) to avoid a circular import back into
                 # config/capstone_contract from this pure drawing module.

PARTICLE_LIFETIME_TICKS = 40  # frames; ~0.67s at 60fps
RISE_PX_PER_TICK = 0.6

# All presentation decisions for a given event "kind" live here, and only
# here -- color, the text template, nothing else touches this mapping.
KIND_STYLES = {
    "money_gain": {"color": (80, 220, 90), "template": lambda amt: f"+${amt}"},
    "money_loss": {"color": (220, 70, 70), "template": lambda amt: f"-${amt}"},
    "damage": {"color": (230, 200, 60), "template": lambda amt: f"-{amt}" if amt else "擊中！"},
    "death": {"color": (230, 200, 60), "template": lambda amt: "擊敗！"},
}

_particles = []  # each: {"x","y","kind","amount","age"} in world-grid coords


def reset():
    """Clears all in-flight particles -- call on new_game()/scene reset
    so stale particles from a previous game don't linger on screen."""
    _particles.clear()


def ingest_events(state):
    """Pulls any new events out of state["events"] and spawns matching
    particles. Does NOT clear state["events"] itself -- main.py owns
    that, since other consumers (future ones) might also want a look at
    the same list before it's drained for the frame."""
    for ev in state.get("events", []):
        kind = ev.get("kind")
        if kind not in KIND_STYLES:
            continue
        pos = ev.get("pos")
        if pos is None:
            continue
        _particles.append({
            "x": pos[0], "y": pos[1],
            "kind": kind, "amount": ev.get("amount", 0),
            "age": 0,
        })


def update_and_draw(screen, camera_x, camera_y, font=None):
    """Ages/drifts/fades every live particle, draws it, and drops it once
    it exceeds PARTICLE_LIFETIME_TICKS. `font` lets renderer.py pass in an
    already-loaded pygame.font.Font; a small default is created lazily
    (and cached) if omitted."""
    if not _particles:
        return
    if font is None:
        font = _get_default_font()

    alive = []
    for p in _particles:
        p["age"] += 1
        if p["age"] > PARTICLE_LIFETIME_TICKS:
            continue

        style = KIND_STYLES[p["kind"]]
        text = style["template"](p["amount"])
        ratio = p["age"] / PARTICLE_LIFETIME_TICKS
        alpha = max(0, int(255 * (1.0 - ratio)))

        sx = p["x"] * CELL_SIZE - camera_x
        sy = p["y"] * CELL_SIZE - camera_y - p["age"] * RISE_PX_PER_TICK

        surf = font.render(text, True, style["color"])
        surf.set_alpha(alpha)
        screen.blit(surf, (sx, sy))

        alive.append(p)

    _particles[:] = alive


_default_font = None


def _get_default_font():
    global _default_font
    if _default_font is None:
        _default_font = pygame.font.SysFont(None, 20)
    return _default_font
