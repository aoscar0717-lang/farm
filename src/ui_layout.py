"""Centralized UI layout + theme constants.

Phase 1 of the UX Polish / Refactor pass (see the analysis report from this
session for the full plan). This module has two jobs:

1. Hold the palette/spacing constants for HUD-level chrome (panels, hotbar,
   thought panel) so they're not scattered as bare RGB tuples across
   ui.py/renderer.py. This intentionally does NOT touch world-rendering
   colors (crops/fences/trees/decor fallback shapes) -- those are Layer
   0-1 "world" concerns, not "UI" concerns, and were explicitly out of
   scope in the analysis.

2. Be the SINGLE SOURCE OF TRUTH for a handful of UI element geometries
   that used to be independently duplicated in both the rendering code
   (ui.py / renderer.py) and the click-hit-testing code (input_handler.py).
   Those two copies had already drifted apart in a few places (the
   zone-toggle button and the shop button hit-rects did not actually match
   what was drawn) -- routing both sides through the same functions here
   fixes that as a side effect of removing the duplication, without any
   other visual change.

Nothing in this module imports pygame.display or creates any state; it's
pure geometry/constants, safe to import from anywhere (rendering code,
input handling code, or tests) without side effects.
"""

import pygame
from src.config import WIDTH, HEIGHT

# ---------------------------------------------------------------------------
# Spacing
# ---------------------------------------------------------------------------
UI_MARGIN = 20   # outer margin used around the top/bottom HUD panels
UI_PADDING = 12  # inner padding used inside panels

# ---------------------------------------------------------------------------
# Palette (HUD chrome only -- see module docstring)
# ---------------------------------------------------------------------------
COLOR_TOP_PANEL_BG = (10, 8, 5, 210)
COLOR_TOP_PANEL_BORDER = (80, 60, 30, 200)

COLOR_TEXT_DAY = (240, 220, 150)
COLOR_TEXT_NIGHT = (160, 200, 255)
COLOR_TEXT_STAT = (180, 200, 255)
COLOR_MONEY = (255, 215, 0)

COLOR_ZONE_ACTIVE_FARM_BG = (80, 160, 60, 240)
COLOR_ZONE_ACTIVE_FARM_BORDER = (180, 255, 120)
COLOR_ZONE_ACTIVE_DECOR_BG = (60, 100, 180, 240)
COLOR_ZONE_ACTIVE_DECOR_BORDER = (120, 180, 255)
COLOR_ZONE_INACTIVE_BG = (40, 30, 20, 160)
COLOR_ZONE_INACTIVE_BORDER = (80, 70, 50, 180)
COLOR_ZONE_LABEL_ACTIVE = (255, 255, 200)
COLOR_ZONE_LABEL_INACTIVE = (160, 150, 130)
# Phase 3: a third state for the zone-toggle buttons, between "active" and
# "inactive" -- an inactive button the mouse is currently over. Previously
# these buttons only had two visual states, so there was no feedback that
# the *other* zone's button was actually clickable until you clicked it.
COLOR_ZONE_HOVER_BG = (70, 60, 40, 200)
COLOR_ZONE_HOVER_BORDER = (200, 180, 120, 220)
COLOR_ZONE_LABEL_HOVER = (230, 220, 190)

# Phase 3: PRIMARY/SECONDARY/TERTIARY visual-hierarchy tiers for the top
# panel's stat lines (the day/phase/timer line is already PRIMARY via
# font_large + COLOR_TEXT_DAY/COLOR_TEXT_NIGHT below). Previously every
# stat after the title -- dog count, prosperity, farm level, lifetime
# enemies defeated -- was crammed into one font_small line with identical
# visual weight, so a stat worth checking every night (how many dogs are
# guarding) looked exactly as important as a lifetime vanity counter.
COLOR_STAT_SECONDARY = (210, 225, 255)  # the one stat worth a glance during play: zone dog count
COLOR_STAT_TERTIARY = (150, 145, 130)   # low-emphasis background info: prosperity / farm level / lifetime totals

COLOR_SHOP_BTN_BG = (70, 70, 90)
COLOR_SHOP_BTN_BORDER = (200, 200, 200)

COLOR_HOTBAR_BG = (20, 14, 8, 210)
COLOR_HOTBAR_BORDER = (110, 80, 45, 200)
COLOR_SLOT_NORMAL = (55, 38, 18)
COLOR_SLOT_SELECTED = (180, 140, 40)
COLOR_SLOT_GLOW = (255, 240, 80, 255)
COLOR_SLOT_KEY_NORMAL = (220, 220, 200)
COLOR_SLOT_KEY_SELECTED = (255, 255, 120)

COLOR_THOUGHT_BG = (15, 12, 20)
COLOR_THOUGHT_BORDER = (140, 170, 210)
COLOR_THOUGHT_TITLE = (180, 220, 255)
COLOR_THOUGHT_KEY = (255, 230, 120)
COLOR_THOUGHT_TEXT = (235, 230, 210)

# ---------------------------------------------------------------------------
# Shared geometry: HUD top bar
# ---------------------------------------------------------------------------

def top_panel_rect():
    """The dark rounded panel behind the day/phase text and zone buttons.

    Phase 3: grew from 90 to 130px tall to fit the new PRIMARY/SECONDARY/
    TERTIARY stat-row hierarchy (title, then a dog-count row, then a
    lifetime-stats row) without any row spilling past the panel's own
    background. The row heights are estimated generously (this project has
    no headless-pygame test environment with the real "microsoftjhenghei"
    font metrics available, so TOP_PANEL_* below err on the side of extra
    padding rather than risk a tight fit); daynight_bar_rect() derives its
    y from this rect's bottom edge, so this is the only place that height
    lives -- if it ever looks too tall/short in practice, adjust it here
    and everything below it reflows automatically."""
    return pygame.Rect(UI_MARGIN, 12, WIDTH - 2 * UI_MARGIN, 130)


# Left inset + row anchors for the PRIMARY/SECONDARY/TERTIARY text lines
# inside the top panel. These are plain (x, y) coordinates rather than
# Rects since each is a single line of variable-width text, not a box.
TOP_PANEL_TEXT_X = 40
TOP_PANEL_PRIMARY_Y = 22    # day/phase/timer (font_large)
TOP_PANEL_SECONDARY_Y = 72  # zone dog count (font_small)
TOP_PANEL_TERTIARY_Y = 106  # prosperity / farm level / lifetime totals (font_tiny)


def daynight_bar_rect():
    """The day/night progress bar, directly below the top panel.

    Previously hardcoded at a fixed y=108 that only happened to sit below
    the panel because the panel's old height (90) put its bottom edge at
    exactly 102. Deriving this from top_panel_rect().bottom means growing
    the panel (as Phase 3 just did) can't silently make the bar overlap
    the panel's own background again."""
    panel = top_panel_rect()
    gap = 10
    bar_h = 8
    return pygame.Rect(UI_MARGIN * 2, panel.bottom + gap, WIDTH - UI_MARGIN * 4, bar_h)


def zone_toggle_button_rects():
    """Absolute screen-space rects for the 農田區/佈置區 buttons, in the
    exact position draw_hud renders them (inside top_panel_rect(), which is
    itself offset from the screen origin -- callers that need to draw onto
    that panel's local surface should subtract top_panel_rect().topleft).

    This used to be duplicated in input_handler.py as a single guessed
    Rect(WIDTH//2-130, 14, 220, 44) that did not actually line up with
    these two buttons -- that mismatch is gone now that both drawing and
    click-hit-testing call this same function."""
    panel = top_panel_rect()
    btn_w, btn_h, btn_gap = 130, 44, 6
    total_btn_w = btn_w * 2 + btn_gap
    # Original formula computed this panel-local (relative to top_panel's
    # own (0,0)); the absolute screen x is just panel.x + that.
    base_x = panel.x + (WIDTH // 2 - total_btn_w // 2 - 20)
    y = panel.y + 14
    return {
        "farm": pygame.Rect(base_x, y, btn_w, btn_h),
        "decor": pygame.Rect(base_x + btn_w + btn_gap, y, btn_w, btn_h),
    }


def top_panel_stats_row_rect():
    """Hoverable region covering the SECONDARY (zone dog count) + TERTIARY
    (prosperity / farm level / lifetime kills) stat rows inside the top
    panel -- used by thought.py's UI-hover coverage (section 十二 of the
    Tutorial/Thought upgrade). These are drawn as plain text surfaces with
    no per-stat sub-rect, so this is deliberately approximate (the whole
    row, not each individual number) -- good enough for "is the mouse
    roughly over the stats", which is all a hover hint needs."""
    panel = top_panel_rect()
    y = panel.y + TOP_PANEL_SECONDARY_Y - 4
    h = (TOP_PANEL_TERTIARY_Y + 20) - TOP_PANEL_SECONDARY_Y
    return pygame.Rect(panel.x + TOP_PANEL_TEXT_X, y, panel.w - TOP_PANEL_TEXT_X - 20, h)


def money_readout_rect():
    """Approximate hoverable region for the money readout (top-right,
    below the shop button). Fixed generous size since the label's actual
    rendered width depends on the current value and isn't available outside
    the draw call itself."""
    x, y = money_label_pos(140)
    return pygame.Rect(x - 10, y - 4, 160, 30)


def shop_button_rect():
    """Absolute rect for the top-right 商店 (B) button.

    This used to be duplicated in input_handler.py as
    Rect(WIDTH-158, 14, 140, 44), which did not match what was actually
    drawn here (WIDTH-150, 10, 130, 40) -- both sides now share this."""
    return pygame.Rect(WIDTH - 150, 10, 130, 40)


# ---------------------------------------------------------------------------
# Shared geometry: time-scale control (pause / 1x / 2x / 4x)
# ---------------------------------------------------------------------------

TIME_SCALE_STEPS = [0.0, 1.0, 2.0, 4.0]


def time_scale_step_index(time_scale):
    """Which index of TIME_SCALE_STEPS `time_scale` currently is (used by
    input_handler.py's [ / ] step-up/step-down handlers). Falls back to
    the closest known step if state ever holds something off-list (should
    not happen -- apply_action's set_time_scale_* rejects anything not in
    TIME_SCALE_STEPS -- but this keeps a stray value from crashing the
    step logic)."""
    try:
        return TIME_SCALE_STEPS.index(float(time_scale))
    except ValueError:
        return min(range(len(TIME_SCALE_STEPS)), key=lambda i: abs(TIME_SCALE_STEPS[i] - time_scale))


def time_scale_badge_rect():
    """Small pill showing the current time-scale / PAUSED state. Placed in
    the top panel's top-right column, directly below the money readout
    (itself anchored below the shop button) -- same "derive from the
    element above it" pattern money_label_pos already uses, so this can
    never end up hardcoded to a coordinate that only happens to not
    collide with its neighbors today."""
    money_rect = money_readout_rect()
    w, h = 110, 26
    x = money_rect.right - w
    y = money_rect.bottom + 6
    return pygame.Rect(x, y, w, h)


def paused_banner_center():
    """Center point for the large, unmissable "已暫停" banner shown while
    time_scale == 0 -- directly below the day/night bar (itself derived
    from the top panel's bottom edge), so it reads as a global-state
    overlay sitting just under the HUD rather than competing with any
    single HUD element for space."""
    bar = daynight_bar_rect()
    return (WIDTH // 2, bar.bottom + 40)


# ---------------------------------------------------------------------------
# Shared geometry: hotbar
# ---------------------------------------------------------------------------

HOTBAR_ITEMS = [
    {"id": "hoe", "key": "1"},
    {"id": "scythe", "key": "2"},
    {"id": "shovel", "key": "3"},
    {"id": "fertilizer", "key": "4"},
]


def hotbar_layout():
    """Returns a dict describing the hotbar panel + each slot's rect, used
    identically by renderer.py (drawing) and input_handler.py (click
    detection) -- previously two independently hand-copied formulas."""
    slot_size, slot_gap = 58, 8
    bar_w = len(HOTBAR_ITEMS) * slot_size + (len(HOTBAR_ITEMS) + 1) * slot_gap
    bar_h = slot_size + 2 * slot_gap
    bar_x = (WIDTH - bar_w) // 2
    bar_y = HEIGHT - 82

    slots = []
    for i, item in enumerate(HOTBAR_ITEMS):
        sx = bar_x + slot_gap + i * (slot_size + slot_gap)
        sy = bar_y + slot_gap
        slots.append({"item": item, "rect": pygame.Rect(sx, sy, slot_size, slot_size)})

    return {
        "panel_rect": pygame.Rect(bar_x, bar_y, bar_w, bar_h),
        "slot_size": slot_size,
        "slot_gap": slot_gap,
        "slots": slots,
    }


# ---------------------------------------------------------------------------
# Shared geometry: shop
# ---------------------------------------------------------------------------

SHOP_TABS = ["seed", "def", "pet"]
SHOP_TAB_LABELS = {"seed": "種子", "def": "防禦", "pet": "景觀"}

# Canonical id lists per buy-tab, in display order. Item *details* (name,
# price, description) still live in ui.py next to the rendering code that
# needs them -- but both ui.py and input_handler.py iterate these same id
# lists, so a card's index (and therefore its rect from
# shop_item_card_rects) can never drift out of alignment with which item it
# actually represents.
SHOP_ITEM_IDS = {
    "seed": ["radish", "carrot", "pumpkin"],
    "def": ["fence", "trap", "dog"],
    # Landscape expansion round 1: 4 original + 7 (scarecrow/crate/bush/
    # rock/sunflower/pine_tree/big_tree). shop_column_rects has no hard cap
    # on count, so growing this list lays out automatically -- no geometry
    # changes needed. Note: at 75px per card row, the taller column may run
    # close to or past the shop panel's original height on some screens;
    # not fixed here since tuning shop panel size is a UI Layout change
    # outside this pass's scope (flagged in the report, not silently
    # patched).
    #
    # Landscape expansion round 2: 8 more (stump/mushroom/picnic_basket/
    # woodpile/picnic_blanket/beehive/garden_table/fruit_tree), bringing
    # "pet" to 19 items (10/9 split). The shop-panel-height risk flagged
    # above is now materially worse at this count -- still not fixed here
    # (same reasoning: UI Layout change, out of this pass's scope), but
    # re-flagged more strongly in this round's report since 19 items is a
    # lot more likely to actually overflow than 11 was.
    "pet": ["stone_path", "flower", "bench", "fountain",
            "scarecrow", "crate", "bush", "rock", "sunflower", "pine_tree", "big_tree",
            "stump", "mushroom", "picnic_basket", "woodpile",
            "picnic_blanket", "beehive", "garden_table", "fruit_tree"],
}


def shop_panel_rect():
    shop_w, shop_h = 1180, 700
    shop_x = (WIDTH - shop_w) // 2
    shop_y = (HEIGHT - shop_h) // 2
    return pygame.Rect(shop_x, shop_y, shop_w, shop_h)


def shop_page_geometry():
    """The two "page" columns (left = buy, right = sell) inside the shop
    panel, plus the buy/sell top tab rects. Shared by draw_shop and the
    click handler."""
    shop = shop_panel_rect()
    left_page_x = shop.x + 90
    right_page_x = shop.x + 675
    page_w = 400
    tab_buy = pygame.Rect(left_page_x, shop.y + 110, page_w, 45)
    tab_sell = pygame.Rect(right_page_x, shop.y + 110, page_w, 45)
    return {
        "shop_rect": shop,
        "left_page_x": left_page_x,
        "right_page_x": right_page_x,
        "page_w": page_w,
        "tab_buy": tab_buy,
        "tab_sell": tab_sell,
    }


def shop_subtab_rects():
    """The 種子/防禦/景觀 sub-tab buttons (only shown on the buy page)."""
    geo = shop_page_geometry()
    shop = geo["shop_rect"]
    left_page_x = geo["left_page_x"]
    page_w = geo["page_w"]
    sub_w = (page_w - 10) // 3
    rects = {}
    for i, tab_id in enumerate(SHOP_TABS):
        rects[tab_id] = pygame.Rect(left_page_x + i * (sub_w + 5), shop.y + 165, sub_w, 30)
    return rects


def shop_column_start(is_sell, column):
    """Where a card column's first row starts. column is "left" or "right".
    The buy page's left column starts lower than the right one (room for
    the seed/def/pet sub-tabs above it); the sell page doesn't have those
    sub-tabs so both columns start at the same height."""
    geo = shop_page_geometry()
    page_x = geo["left_page_x"] if column == "left" else geo["right_page_x"]
    shop_y = geo["shop_rect"].y
    if column == "left":
        start_y = shop_y + (170 if is_sell else 210)
    else:
        start_y = shop_y + 170
    return page_x, start_y


def shop_column_rects(count, is_sell, column):
    """Rects for `count` stacked item cards in one column (see
    shop_column_start). Both draw_shop and the click handler slice their
    item list into left/right columns themselves (buy: roughly half-half;
    sell: fixed 6 per column, 12 total, exactly as before) and call this
    once per column with that column's slice length -- so this stays a
    pure geometry helper with no opinion on how items get split."""
    page_x, start_y = shop_column_start(is_sell, column)
    page_w = shop_page_geometry()["page_w"]
    row_h = 75
    return [pygame.Rect(page_x, start_y + i * row_h, page_w, 65) for i in range(count)]


# ---------------------------------------------------------------------------
# Shared geometry: shop pagination
# ---------------------------------------------------------------------------
# Bug this fixes: a card column has no built-in limit, so a tab with enough
# items (originally: 佈置/pet's 19 items, or a sell page with more than 12
# sellable grades) lays out MORE rows than shop_column_start's fixed
# start_y + row_h*count can fit above the shop panel's bottom edge -- the
# extra cards still get real Rects and still draw, they just draw past the
# panel background, "hanging" over whatever is behind the shop. Pagination
# caps how many items shop_column_rects is ever asked to lay out at once,
# so that structurally can't happen again regardless of how many items a
# future tab/sell-grade list grows to.
#
# SHOP_ITEMS_PER_PAGE=10 (5 rows per column at row_h=75) is deliberately
# under the ~6-row ceiling the panel's height (700px) allows for the
# tightest case (buy page's left column, which starts lower than the
# others at shop_y+210 to leave room for the seed/def/pet sub-tabs) --
# that slack is what the Prev/Next bar below is drawn into, instead of
# competing with the last row of cards for the same pixels.
SHOP_ITEMS_PER_PAGE = 10


def shop_page_key(active_tab):
    """Which slot of state["shop_page"] a given active_tab's page cursor
    lives under. Each buy sub-tab (seed/def/pet) and the sell tab remember
    their own page independently, so switching tabs and switching back
    doesn't lose your place -- a plain naming decision, not geometry, but
    kept here (not duplicated in ui.py/input_handler.py/thought.py) so all
    four can never disagree about which key means what."""
    return active_tab if active_tab == "sell" else f"buy_{active_tab}"


def shop_page_count(item_count):
    """How many pages `item_count` items need at SHOP_ITEMS_PER_PAGE per
    page. Always >= 1 -- an empty list is still "page 1 of 1", not "page 1
    of 0", so callers (the Prev/Next bar, the "第 X / Y 頁" label) never
    have to special-case zero items."""
    return max(1, -(-item_count // SHOP_ITEMS_PER_PAGE))  # ceil division


def shop_clamp_page(page, item_count):
    """Clamps a possibly-stale page index (e.g. the player paged to page 3
    of a tab, then a sale emptied their inventory back down to 1 page)
    into [0, shop_page_count(item_count) - 1]."""
    return max(0, min(page, shop_page_count(item_count) - 1))


def shop_page_slice(items, page):
    """The (<= SHOP_ITEMS_PER_PAGE) items visible on `page` (0-indexed,
    already clamped). Single source of truth for "what's on this page" --
    drawing, click hit-testing, and F-Hover hit-testing all slice through
    this instead of each re-deriving their own start/stop math, so they
    can never disagree about which item a given card position represents."""
    page = shop_clamp_page(page, len(items))
    start = page * SHOP_ITEMS_PER_PAGE
    return items[start:start + SHOP_ITEMS_PER_PAGE]


def shop_pagination_rects():
    """Prev/Next button Rects plus the center point for a "第 X / Y 頁"
    label, spanning the full card-column width (both the left and right
    page columns together -- buy and sell each lay their cards out as ONE
    2-column grid across that combined width, not two independently-paged
    halves), anchored to the shop panel's own bottom edge so it can never
    need updating if shop_panel_rect's size changes."""
    geo = shop_page_geometry()
    shop = geo["shop_rect"]
    left_page_x = geo["left_page_x"]
    right_page_x = geo["right_page_x"]
    page_w = geo["page_w"]
    content_left = left_page_x
    content_right = right_page_x + page_w
    btn_w, btn_h = 90, 34
    y = shop.bottom - btn_h - 14
    return {
        "prev": pygame.Rect(content_left, y, btn_w, btn_h),
        "next": pygame.Rect(content_right - btn_w, y, btn_w, btn_h),
        "label_center": ((content_left + content_right) // 2, y + btn_h // 2),
    }


# ---------------------------------------------------------------------------
# Shared geometry: top-right money readout
# ---------------------------------------------------------------------------

def money_label_pos(label_width):
    """Right-aligned position for the money readout.

    Previously this was an independent fixed coordinate (WIDTH-money_w-40,
    35) that geometrically overlapped the shop button (WIDTH-150..WIDTH-20,
    10..50) -- same corner of the screen, same rows, two unrelated pieces
    of chrome drawn on top of each other. Deriving this from
    shop_button_rect() instead (sit directly below it, right-aligned to
    its right edge) makes "don't collide with the shop button" a structural
    fact instead of two magic numbers that happened to clash."""
    btn = shop_button_rect()
    x = btn.right - label_width
    y = btn.bottom + 10
    return x, y


# ---------------------------------------------------------------------------
# Shared geometry: bottom area (toolbar / hint / notification stack)
# ---------------------------------------------------------------------------
# Phase 2 restructuring. The bottom of the screen is owned bottom-to-top by
# three regions:
#   BOTTOM_TOOLBAR_AREA      -- the hotbar (bottom_toolbar_area())
#   BOTTOM_HINT_AREA         -- the one-line keybind hint strip
#                                (bottom_hint_area())
#   BOTTOM_NOTIFICATION_AREA -- transient stuff: the toast message queue
#                                (Phase 4: up to MAX_VISIBLE_TOASTS stacked
#                                via stack_upward()) and the Thought panel,
#                                anchored via bottom_toast_bottom_y() /
#                                bottom_thought_bottom_y()
#
# Each region is derived from the one below it (toolbar -> hint -> toast ->
# thought), so they can never overlap by construction -- moving or resizing
# the hotbar reflows everything above it automatically. This replaces four
# independently-hardcoded y-coordinates (hint strip, toast message, Thought
# panel, tool indicator) that had drifted into overlapping each other:
# the toast message and the Thought panel occupied the same vertical band
# whenever both were visible in the same frame, and the Thought panel's
# reserved gap above the hotbar actually landed inside the hint strip's own
# panel background.

BOTTOM_AREA_GAP = 8  # vertical gap between stacked bottom-area regions

# Phase 4: the toast slot can now hold multiple stacked messages at once
# (see ui.py's toast queue) instead of just one. MAX_VISIBLE_TOASTS caps
# how many are drawn simultaneously ("a reasonable max count", not an
# unbounded pile); TOAST_SLOT_HEIGHT is a generous per-toast height
# (message text + padding + inter-toast gap).
#
# TOAST_RESERVED_HEIGHT is the *worst case* total height of that stack.
# draw_hud (the toasts) and draw_contemplation (the Thought panel) are two
# independent calls with no shared per-frame state, so the Thought panel
# can't ask "how many toasts are actually showing right now" -- instead it
# always reserves room for the full MAX_VISIBLE_TOASTS stack above the
# toast area's own anchor, so it can never collide with the toast stack
# no matter how many toasts happen to be visible this frame.
MAX_VISIBLE_TOASTS = 4
TOAST_SLOT_HEIGHT = 62
TOAST_RESERVED_HEIGHT = MAX_VISIBLE_TOASTS * TOAST_SLOT_HEIGHT


def bottom_toolbar_area():
    """The hotbar's own rect -- the anchor the rest of the bottom-area
    layout is built from."""
    return hotbar_layout()["panel_rect"]


def bottom_hint_area():
    """Reserved strip for the keybind hint text, directly above the
    toolbar area."""
    toolbar = bottom_toolbar_area()
    h = 32
    y = toolbar.top - BOTTOM_AREA_GAP - h
    return pygame.Rect(UI_MARGIN, y, WIDTH - 2 * UI_MARGIN, h)


def bottom_toast_bottom_y():
    """The y-coordinate the toast message's bottom edge should sit at --
    directly above the hint area, regardless of the toast's own height
    (callers subtract their own rendered height from this to get their
    top-left)."""
    return bottom_hint_area().top - BOTTOM_AREA_GAP


def stack_upward(bottom_y, heights, gap=BOTTOM_AREA_GAP):
    """Given a y to start from and a list of element heights (bottom-most
    element first), returns a matching list of top-y coordinates so the
    elements stack upward without ever overlapping each other. Used by the
    toast queue (Phase 4) to place N messages -- each toast only needs to
    know its own rendered height, not the position of the others."""
    tops = []
    cursor = bottom_y
    for h in heights:
        top = cursor - h
        tops.append(top)
        cursor = top - gap
    return tops


def bottom_thought_bottom_y():
    """The y-coordinate the Thought panel's bottom edge should sit at --
    always above the toast's reserved slot (see TOAST_RESERVED_HEIGHT), so
    the two can never collide no matter which one(s) are visible this
    frame."""
    return bottom_toast_bottom_y() - TOAST_RESERVED_HEIGHT - BOTTOM_AREA_GAP


# ---------------------------------------------------------------------------
# Shared geometry: tutorial sidebar
# ---------------------------------------------------------------------------
# The right-edge panel added for the Tutorial Quest system (see
# tutorial_quests.py / ui.py::draw_tutorial_sidebar). Single source of truth
# for both the draw call and input_handler.py's click-passthrough guard, same
# "one function, two callers" pattern every other shared rect in this module
# already follows.

TUTORIAL_SIDEBAR_WIDTH = 300


def tutorial_sidebar_rect():
    """Right edge of the screen, directly below the top HUD panel, stopping
    above the bottom hint/toolbar/toast/thought stack. Derived from
    top_panel_rect() and bottom_hint_area() (not fixed coordinates), so it
    can never overlap either one regardless of screen resolution -- same
    reasoning daynight_bar_rect()/bottom_thought_bottom_y() already use for
    their own neighbors. Deliberately does not reach as far down as
    bottom_thought_bottom_y() -- the sidebar and the Thought panel are both
    allowed to be visible at the same time (they're different screen
    regions: right edge vs bottom-center), so there's no need to reserve
    room for one inside the other."""
    # Anchored below daynight_bar_rect() rather than top_panel_rect() --
    # the day/night bar spans nearly the same near-full width as the top
    # panel (UI_MARGIN*2 .. WIDTH-UI_MARGIN*4) and sits just below it, so
    # deriving from the bar's own bottom edge (not the panel's) is what
    # actually guarantees no overlap with either one.
    top = daynight_bar_rect().bottom + BOTTOM_AREA_GAP * 2
    bottom = bottom_hint_area().top - BOTTOM_AREA_GAP * 2
    x = WIDTH - TUTORIAL_SIDEBAR_WIDTH - UI_MARGIN
    h = max(160, bottom - top)
    return pygame.Rect(x, top, TUTORIAL_SIDEBAR_WIDTH, h)


# Per-task row geometry inside the sidebar -- fixed row heights (not a
# pixel-exact reproduction of the wrapped-hint text height) so this stays a
# pure, state-cheap geometry function usable both by draw_tutorial_sidebar
# (which positions each row here instead of hand-tracking a running y) and
# by thought.py's Sidebar-hover resolution (section 九: "Hover 目前任務 ->
# F 有對應思索"). A little vertical slack in TUTORIAL_SIDEBAR_CURRENT_ROW_H
# for the current task's wrapped hint is good enough for "is the mouse
# roughly over this task's row", which is all a hover target needs. The
# HEADER height, unlike the rows, is NOT a guess -- see
# tutorial_sidebar_header_height() below, which derives it from the real
# font metrics so it can't silently drift out of sync with what
# draw_tutorial_sidebar's title/chapter/subtitle block actually renders.
TUTORIAL_SIDEBAR_ROW_H = 24
TUTORIAL_SIDEBAR_CURRENT_ROW_H = 76
TUTORIAL_SIDEBAR_ROW_GAP = 4


def tutorial_sidebar_header_height(chapter):
    """Height (in px) of the Sidebar's title + separator + chapter-name +
    subtitle block, above where the first task row starts. Computed from
    the real font metrics (not a hand-picked constant) so
    draw_tutorial_sidebar (which draws this block) and
    tutorial_sidebar_task_rects (which needs to know where it ends) can
    never drift apart -- both call this same function."""
    from src.config import font_small, font_tiny

    pad_y = 12
    y = pad_y
    y += font_small.get_height() + 6   # title row
    y += 8                              # separator line's own gap
    if chapter is not None:
        y += font_tiny.get_height() + 4   # chapter name + progress row
        y += font_tiny.get_height() + (8 if chapter.subtitle else 4)  # subtitle row
    return y - pad_y


def tutorial_sidebar_task_rects(state):
    """[(TutorialTask, Rect), ...] for every task in the Sidebar's
    currently-shown chapter, in on-screen (absolute) coordinates -- single
    source of truth for both draw_tutorial_sidebar's row positions and
    thought.py's "which task is the mouse over" hit test, so the two can
    never drift out of sync. Returns [] if there's no current chapter
    (shouldn't happen with a non-empty TUTORIAL_CHAPTERS, but stay
    defensive)."""
    from src import tutorial_quests as _quests

    panel = tutorial_sidebar_rect()
    progress = _quests.get_quest_progress(state)
    chapter = progress["current_chapter"]
    current_task = progress["current_task"]
    if chapter is None:
        return []

    pad_x, pad_y = 14, 12
    y = panel.y + pad_y + tutorial_sidebar_header_height(chapter)
    rects = []
    for task in chapter.tasks:
        is_current = current_task is not None and task.id == current_task.id
        h = TUTORIAL_SIDEBAR_CURRENT_ROW_H if is_current else TUTORIAL_SIDEBAR_ROW_H
        rect = pygame.Rect(panel.x + pad_x - 4, y, panel.w - (pad_x - 4) * 2, h)
        rects.append((task, rect))
        y += h + TUTORIAL_SIDEBAR_ROW_GAP
        if y > panel.bottom - 20:
            break
    return rects


def toolbar_side_label_pos(label_width, label_height):
    """Where to draw a label attached to the right side of the hotbar
    (the 'currently equipped tool' indicator). Previously this indicator
    floated inside the hint strip's own panel at a fixed y that placed it
    partly below the hint panel's background (content overflowing its own
    container) -- attaching it to the toolbar area it actually describes
    fixes both the overflow and the semantic mismatch."""
    toolbar = bottom_toolbar_area()
    x = toolbar.right + 16
    y = toolbar.centery - label_height // 2
    return x, y


def build_sellable_list(state, crop_info):
    """The player's sellable inventory as a flat list of
    {id, name, grade, count, price} dicts, in a fixed (crop, grade) order.
    This was independently re-derived with the same loop in both
    ui.py::draw_shop and input_handler.py::handle_mouse_click; centralizing
    it means a sell-page card and the click handler's notion of "the Nth
    sellable item" can never disagree about what that item actually is."""
    grades = ["normal", "rare", "epic", "legendary"]
    grades_tw = {"normal": "一般", "rare": "稀有", "epic": "史詩", "legendary": "傳奇"}
    multipliers = {"normal": 1, "rare": 2, "epic": 3, "legendary": 5}
    crop_names = [("radish", "白蘿蔔"), ("carrot", "胡蘿蔔"), ("pumpkin", "魔法南瓜")]

    sellable = []
    for c_id, c_name in crop_names:
        base_price = crop_info.get(c_id, {}).get("yield", 100)
        for grade in grades:
            count = state.get("inventory", {}).get(c_id, {}).get(grade, 0)
            if count > 0:
                sellable.append({
                    "id": c_id,
                    "name": f"{c_name} ({grades_tw[grade]})",
                    "grade": grade,
                    "count": count,
                    "price": base_price * multipliers[grade],
                })
    return sellable
