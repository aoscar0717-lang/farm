import pygame
from src.config import *
from src.capstone_contract import apply_action, apply_batch_action, new_game, is_terminal, CROP_INFO
from src.tutorial import note_event
from src import ui_layout


def _shop_page(state, active_tab):
    """Reads the current (already-clamped) page for `active_tab` out of
    state["shop_page"] -- a plain dict field on state, same convention as
    state["debug_show_grid"]/state["debug_scale_idx"] (a UI cursor that
    doesn't need capstone_contract.py's new_game()/apply_action() to know
    about it, just like current_tool/shop_open/active_tab already don't
    live in state at all). Not itself a geometry decision -- ui_layout.py
    still owns SHOP_ITEMS_PER_PAGE/shop_clamp_page/shop_page_key."""
    return state.get("shop_page", {}).get(ui_layout.shop_page_key(active_tab), 0)


def _set_shop_page(state, active_tab, page, item_count):
    pages = state.setdefault("shop_page", {})
    pages[ui_layout.shop_page_key(active_tab)] = ui_layout.shop_clamp_page(page, item_count)


def _handle_shop_pagination_click(state, mx, my, active_tab, item_count):
    """True if (mx, my) hit the Prev/Next bar -- and if so, already
    advanced/retreated state["shop_page"] for the current tab."""
    rects = ui_layout.shop_pagination_rects()
    page = _shop_page(state, active_tab)
    total_pages = ui_layout.shop_page_count(item_count)
    if rects["prev"].collidepoint(mx, my) and page > 0:
        _set_shop_page(state, active_tab, page - 1, item_count)
        return True
    if rects["next"].collidepoint(mx, my) and page < total_pages - 1:
        _set_shop_page(state, active_tab, page + 1, item_count)
        return True
    # Still swallow clicks anywhere on the pagination bar even when the
    # button is disabled (first/last page) -- a click on a greyed-out
    # "上一頁" shouldn't fall through and buy whatever card happens to
    # occupy that same screen real estate on some other tab's layout.
    return rects["prev"].collidepoint(mx, my) or rects["next"].collidepoint(mx, my)


def _handle_shop_wheel(state, button, active_tab):
    """Mouse wheel while the shop is open pages the currently visible
    tab/sell list -- button 4 = scroll up = previous page, button 5 =
    scroll down = next page (pygame's classic wheel-as-button convention;
    main.py already forwards every MOUSEBUTTONDOWN, wheel included, to
    handle_mouse_click without filtering by button number)."""
    if active_tab == "sell":
        item_count = len(ui_layout.build_sellable_list(state, CROP_INFO))
    else:
        item_count = len(ui_layout.SHOP_ITEM_IDS.get(active_tab, []))
    delta = -1 if button == 4 else 1
    _set_shop_page(state, active_tab, _shop_page(state, active_tab) + delta, item_count)
    return state


def _handle_shop_click(state, mx, my, shop_open, active_tab, current_tool):
    """Everything that can happen from a left-click while the shop is open:
    closing it, switching buy/sell or seed/def/pet tabs, paging, buying an
    item, or selling one. Returns the (possibly) updated (state,
    current_tool, shop_open, active_tab)."""
    geo = ui_layout.shop_page_geometry()
    shop_rect = geo["shop_rect"]
    left_page_x = geo["left_page_x"]
    right_page_x = geo["right_page_x"]
    page_w = geo["page_w"]

    if not shop_rect.collidepoint(mx, my):
        shop_open = False
        return state, current_tool, shop_open, active_tab

    is_sell = active_tab == "sell"

    if geo["tab_buy"].collidepoint(mx, my):
        active_tab = "seed"
    elif geo["tab_sell"].collidepoint(mx, my):
        active_tab = "sell"
    elif not is_sell:
        subtabs = ui_layout.shop_subtab_rects()
        if subtabs["seed"].collidepoint(mx, my): active_tab = "seed"
        elif subtabs["def"].collidepoint(mx, my): active_tab = "def"
        elif subtabs["pet"].collidepoint(mx, my): active_tab = "pet"
        else:
            ids = ui_layout.SHOP_ITEM_IDS.get(active_tab, [])
            if _handle_shop_pagination_click(state, mx, my, active_tab, len(ids)):
                return state, current_tool, shop_open, active_tab

            # Only the current PAGE's ids get hit-tested -- this is what
            # actually fixes the original overflow bug's other half: cards
            # that would have drawn past the panel background used to
            # still be clickable (they had real, if off-panel, Rects), and
            # now they simply aren't laid out at all until the player pages
            # to them.
            page_ids = ui_layout.shop_page_slice(ids, _shop_page(state, active_tab))
            left_ids = page_ids[:(len(page_ids)+1)//2]
            right_ids = page_ids[(len(page_ids)+1)//2:]

            clicked = False
            for col_ids, column in [(left_ids, "left"), (right_ids, "right")]:
                rects = ui_layout.shop_column_rects(len(col_ids), is_sell=False, column=column)
                for item_id, card_rect in zip(col_ids, rects):
                    if card_rect.collidepoint(mx, my):
                        current_tool = item_id
                        shop_open = False
                        clicked = True
                        if item_id in ("radish", "carrot", "pumpkin"):
                            # There's no separate "buy seed" moment in this
                            # game -- money is only spent later, when the
                            # seed is actually planted (plant_crop_ in
                            # capstone_contract.py). This flag exists so the
                            # Tutorial "選擇一種種子" task has a real signal
                            # to latch onto instead of a fabricated purchase
                            # event.
                            note_event(state, "seed_selected")
                        break
                if clicked: break
    else:
        sellable = ui_layout.build_sellable_list(state, CROP_INFO)
        if _handle_shop_pagination_click(state, mx, my, "sell", len(sellable)):
            return state, current_tool, shop_open, active_tab

        page_items = ui_layout.shop_page_slice(sellable, _shop_page(state, "sell"))
        left_items = page_items[:(len(page_items)+1)//2]
        right_items = page_items[(len(page_items)+1)//2:]

        clicked = False
        for col_items, column in [(left_items, "left"), (right_items, "right")]:
            rects = ui_layout.shop_column_rects(len(col_items), is_sell=True, column=column)
            for item, card_rect in zip(col_items, rects):
                if card_rect.collidepoint(mx, my):
                    state["inventory"][item["id"]][item["grade"]] -= 1
                    state["money"] += item["price"]
                    state["last_msg"] = f"成功出售 1 個 {item['name'][:4]}，獲得 ${item['price']}！"
                    # Real sell event -- distinct from just opening the shop
                    # (see tutorial.py's "crop_sold" vs "shop_sell" steps).
                    note_event(state, "crop_sold")
                    clicked = True
                    break
            if clicked: break

    return state, current_tool, shop_open, active_tab


def _handle_hotbar_click(mx, my, current_tool):
    """A click anywhere inside the hotbar panel selects that slot's tool
    (or does nothing if it lands in the panel's own padding) and always
    counts as "handled" -- same as before the split, clicking inside the
    hotbar panel never falls through to the zone-toggle/shop-button/world
    click handling below it."""
    hb = ui_layout.hotbar_layout()
    panel = hb["panel_rect"]
    slot_size, slot_gap = hb["slot_size"], hb["slot_gap"]
    if panel.y <= my <= panel.bottom and panel.x <= mx <= panel.right:
        idx = (mx - panel.x - slot_gap) // (slot_size + slot_gap)
        if 0 <= idx < len(hb["slots"]):
            current_tool = hb["slots"][idx]["item"]["id"]
        return current_tool, True
    return current_tool, False


def _handle_zone_and_shop_button_click(state, mx, my, shop_open, active_zone):
    """The two top-panel chrome buttons: zone toggle and shop open."""
    toggle_rects = ui_layout.zone_toggle_button_rects()
    shop_btn_rect = ui_layout.shop_button_rect()

    if toggle_rects["farm"].collidepoint(mx, my) or toggle_rects["decor"].collidepoint(mx, my):
        active_zone = "decor" if active_zone == "farm" else "farm"
        return shop_open, active_zone, True
    elif shop_btn_rect.collidepoint(mx, my):
        shop_open = True
        note_event(state, "shop_opened")
        return shop_open, active_zone, True
    return shop_open, active_zone, False


def _handle_world_click(state, mx, my, current_tool, camera_x, camera_y, active_zone):
    """A click on the game world itself: using the equipped tool at the
    clicked grid cell, or (no tool equipped) a plain inspect/interact
    click. Only called once shop/hotbar/chrome clicks have all been ruled
    out."""
    if not (my > MARGIN_TOP and my < HEIGHT - MARGIN_BOTTOM):
        return state

    # Farm and decor are independent maps now: whichever zone the
    # camera is currently showing is exactly the zone the click
    # belongs to, so there's no "wrong side of the world" check
    # needed anymore (there's no shared coordinate line to cross).
    world_x = mx + camera_x
    world_y = my + camera_y

    if current_tool:
        # Snap to ITEM_PX grid to prevent overlapping
        ITEM_PX = CELL_SIZE * 10
        gx = int(world_x // ITEM_PX) * 10
        gy = int(world_y // ITEM_PX) * 10

        if current_tool == "hoe":
            state = apply_action(state, f"use_hoe_{gx}_{gy}", active_zone)
        elif current_tool == "scythe":
            state = apply_action(state, f"use_scythe_{gx}_{gy}", active_zone)
        elif current_tool == "shovel":
            state = apply_action(state, f"use_shovel_{gx}_{gy}", active_zone)
        elif current_tool == "fertilizer":
            state = apply_action(state, f"use_fertilizer_{gx}_{gy}", active_zone)
        elif current_tool in ["radish", "carrot", "pumpkin"]:
            state = apply_action(state, f"plant_crop_{current_tool}_{gx}_{gy}", active_zone)
        elif current_tool in [
            "stone_path", "flower", "bench", "fountain",
            "scarecrow", "crate", "bush", "rock", "sunflower", "pine_tree", "big_tree",
            "stump", "mushroom", "picnic_basket", "woodpile",
            "picnic_blanket", "beehive", "garden_table", "fruit_tree",
        ]:
            state = apply_action(state, f"build_decor_{current_tool}_{gx}_{gy}", active_zone)
        elif current_tool == "fence":
            state = apply_action(state, f"build_fence_{gx}_{gy}", active_zone)
        elif current_tool == "trap":
            state = apply_action(state, f"place_trap_{gx}_{gy}", active_zone)
        elif current_tool == "dog":
            state = apply_action(state, f"place_dog_{gx}_{gy}", active_zone)
    else:
        gx, gy = world_x, world_y
        state = apply_action(state, f"click_{gx}_{gy}", active_zone)

    return state


def handle_mouse_click(state, event, current_tool, shop_open, active_tab, camera_x, camera_y, active_zone):
    """Phase 5: this used to be one function containing all of shop-click,
    hotbar-click, zone/shop-button-click, and world-click handling inline.
    Split into one helper per concern (see above); this is now just the
    dispatch order between them -- mechanical extraction, same behavior."""
    if is_terminal(state):
        return state, current_tool, shop_open, active_tab, active_zone

    # Mouse wheel (pygame's classic wheel-as-button convention: button 4 =
    # up, 5 = down) pages the shop's current tab/sell list -- checked
    # before the generic "button != 1 -> ignore" fallthrough below, which
    # would otherwise swallow it the same way it already swallows every
    # other non-left/right button.
    if shop_open and event.button in (4, 5):
        state = _handle_shop_wheel(state, event.button, active_tab)
        return state, current_tool, shop_open, active_tab, active_zone

    if event.button == 3:  # Right click to cancel tool
        return state, None, shop_open, active_tab, active_zone

    if event.button != 1:
        return state, current_tool, shop_open, active_tab, active_zone

    mx, my = event.pos

    if shop_open:
        state, current_tool, shop_open, active_tab = _handle_shop_click(state, mx, my, shop_open, active_tab, current_tool)
        return state, current_tool, shop_open, active_tab, active_zone

    current_tool, hotbar_handled = _handle_hotbar_click(mx, my, current_tool)
    if hotbar_handled:
        return state, current_tool, shop_open, active_tab, active_zone

    # The Tutorial Sidebar (src/ui.py::draw_tutorial_sidebar) sits on top of
    # the right edge of the world -- without this check, a click meant to
    # land on the sidebar panel would fall through to _handle_world_click
    # and use whatever tool is equipped on the world tile underneath it
    # (section 一's explicit "側欄區域不可讓滑鼠點擊穿透到世界" requirement).
    # The sidebar itself has no interactive elements yet, so "handled" here
    # just means "swallowed, do nothing" -- same shape as hotbar padding
    # clicks above.
    if ui_layout.tutorial_sidebar_rect().collidepoint(mx, my):
        return state, current_tool, shop_open, active_tab, active_zone

    shop_open, active_zone, chrome_handled = _handle_zone_and_shop_button_click(state, mx, my, shop_open, active_zone)
    if chrome_handled:
        return state, current_tool, shop_open, active_tab, active_zone

    state = _handle_world_click(state, mx, my, current_tool, camera_x, camera_y, active_zone)
    return state, current_tool, shop_open, active_tab, active_zone


def handle_keyboard_events(state, event, current_tool, shop_open, active_zone):
    if event.key == pygame.K_ESCAPE:
        return state, None, False, active_zone
    elif event.key == pygame.K_TAB:
        active_zone = "decor" if active_zone == "farm" else "farm"
    elif event.key == pygame.K_b:
        shop_open = not shop_open
        if shop_open:
            note_event(state, "shop_opened")
    elif event.key == pygame.K_SPACE:
        if not is_terminal(state):
            state = apply_action(state, "start_night")
    elif event.key == pygame.K_r:
        state = new_game()
        from src import particle
        particle.reset()  # drop any in-flight floating-text particles from the old run
    elif event.key == pygame.K_1: current_tool = "hoe"
    elif event.key == pygame.K_2: current_tool = "scythe"
    elif event.key == pygame.K_3: current_tool = "shovel"
    elif event.key == pygame.K_4: current_tool = "fertilizer"
    elif event.key == pygame.K_p:
        # Toggle pause / resume-last-speed. Space and 1/2/3 were already
        # taken (跳到夜晚 / 工具切換) so time-scale control uses its own
        # keys -- P to pause/resume, [ and ] to step through 0x/1x/2x/4x.
        if state.get("time_scale", 1.0) > 0:
            state = apply_action(state, "set_time_scale_0")
        else:
            resume = state.get("time_scale_before_pause", 1.0)
            state = apply_action(state, f"set_time_scale_{int(resume)}")
    elif event.key == pygame.K_LEFTBRACKET:
        idx = ui_layout.time_scale_step_index(state.get("time_scale", 1.0))
        idx = max(0, idx - 1)
        state = apply_action(state, f"set_time_scale_{int(ui_layout.TIME_SCALE_STEPS[idx])}")
    elif event.key == pygame.K_RIGHTBRACKET:
        idx = ui_layout.time_scale_step_index(state.get("time_scale", 1.0))
        idx = min(len(ui_layout.TIME_SCALE_STEPS) - 1, idx + 1)
        state = apply_action(state, f"set_time_scale_{int(ui_layout.TIME_SCALE_STEPS[idx])}")

    return state, current_tool, shop_open, active_zone

def update_camera(camera_x, camera_y, mouse_pressed, mouse_rel, keys, WORLD_W, WORLD_H, WIDTH, HEIGHT, active_zone):
    cam_speed = 15
    if keys.get(pygame.K_w, False) or keys.get(pygame.K_UP, False): camera_y -= cam_speed
    if keys.get(pygame.K_s, False) or keys.get(pygame.K_DOWN, False): camera_y += cam_speed
    if keys.get(pygame.K_a, False) or keys.get(pygame.K_LEFT, False): camera_x -= cam_speed
    if keys.get(pygame.K_d, False) or keys.get(pygame.K_RIGHT, False): camera_x += cam_speed

    if mouse_pressed:
        mx, my = mouse_rel
        camera_x -= mx
        camera_y -= my

    # Farm and decor are independent maps, each with its own (0,0) origin.
    # Both zones use the same WORLD_W/WORLD_H (they're the same size), so the
    # clamp formula is identical for either -- but crucially there is no
    # shared halfway line between them anymore; active_zone is kept in the
    # signature only in case the two maps ever need different sizes later.
    camera_x = max(0, min(camera_x, max(0, WORLD_W - WIDTH)))
    camera_y = max(0, min(camera_y, max(0, WORLD_H - HEIGHT)))

    return camera_x, camera_y


# ---------------------------------------------------------------------------
# DRAFT -- drag-select batch actions (拖拉框選). NOT YET WIRED IN:
#   - main.py's event loop does not forward MOUSEMOTION or MOUSEBUTTONUP to
#     input_handler.py at all today (only MOUSEBUTTONDOWN and KEYDOWN/
#     TICK_EVENT/QUIT); these three functions expect to be called from new
#     handlers for those two additional event types.
#   - handle_mouse_click's own MOUSEBUTTONDOWN dispatch does not yet call
#     start_drag_select below -- it still always fires _handle_world_click
#     immediately for every tool, including the ones this is meant to
#     apply to (hoe/scythe/seeds). Wiring that in is the next step, held
#     back pending review since it changes real click behavior (a fast
#     single click needs to still work exactly as before -- see
#     commit_drag_select's docstring for how that's meant to be preserved).
#   - No visual feedback yet (ui_layout.py/renderer.py) -- state["drag_select"]
#     below is written every motion frame specifically so a later renderer
#     step has eversomething to read without touching input_handler.py again.
#
# Design notes:
#   - Drag state lives in state["drag_select"], following this project's
#     existing convention for UI/session cursors that live on state for
#     convenience without capstone_contract.py's new_game()/apply_action()
#     needing to know about them (see state["shop_page"]/
#     state["debug_show_grid"] elsewhere in this codebase).
#   - Only tools where "select several cells, apply the same action to each"
#     is a meaningful player intent are batchable -- placing 9 fences from
#     one drag doesn't make sense the way tilling/planting/harvesting a 3x3
#     block does, so this is deliberately scoped to hoe/seeds/scythe, not
#     every tool.
#   - Per-tool max footprint (not one shared constant) so a future tool-
#     upgrade system has real room to grant a bigger drag footprint to some
#     tools/tiers later without this needing to change shape.
# ---------------------------------------------------------------------------

DRAG_BATCHABLE_ACTION_PREFIXES = {
    "hoe": "use_hoe",
    "scythe": "use_scythe",
    "radish": "plant_crop_radish",
    "carrot": "plant_crop_carrot",
    "pumpkin": "plant_crop_pumpkin",
}

# (max_cols, max_rows) -- see capstone_contract.BATCH_MAX_CELLS for the
# server-side cap this must stay within (3*3 = 9 = BATCH_MAX_CELLS).
DRAG_MAX_SIZE = {
    "hoe": (3, 3), "scythe": (3, 3),
    "radish": (3, 3), "carrot": (3, 3), "pumpkin": (3, 3),
}
DRAG_DEFAULT_MAX_SIZE = (3, 3)
_DRAG_GRID_STEP = 10  # world-grid cell size in the same units hover_pos/click positions already use


def _grid_pos_from_mouse(mx, my, camera_x, camera_y):
    """Same world-grid snap main.py's own per-frame hover_pos computation
    uses (CELL_SIZE*10-sized cells) -- duplicated here (not imported from
    main.py, which isn't a module other code imports from) so drag
    start/current can be computed identically to how hover_pos already is."""
    wx, wy = mx + camera_x, my + camera_y
    grid_px = CELL_SIZE * 10
    return (int(wx // grid_px) * 10, int(wy // grid_px) * 10)


def _drag_selected_cells(start, current, tool):
    """The rectangle of grid cells between `start` and `current`
    (inclusive), capped to DRAG_MAX_SIZE[tool] and anchored at `start` --
    dragging further than the cap just stops growing the selection instead
    of jumping/re-centering it, which would be disorienting mid-drag."""
    max_w, max_h = DRAG_MAX_SIZE.get(tool, DRAG_DEFAULT_MAX_SIZE)
    sx, sy = start
    cx, cy = current
    dir_x = 1 if cx >= sx else -1
    dir_y = 1 if cy >= sy else -1
    w = min(max_w, abs(cx - sx) // _DRAG_GRID_STEP + 1)
    h = min(max_h, abs(cy - sy) // _DRAG_GRID_STEP + 1)
    return [
        (sx + dir_x * i * _DRAG_GRID_STEP, sy + dir_y * j * _DRAG_GRID_STEP)
        for i in range(w) for j in range(h)
    ]


def start_drag_select(state, mx, my, current_tool, active_zone, camera_x, camera_y):
    """Call in place of an immediate _handle_world_click when: shop is
    closed, the click wasn't swallowed by any UI chrome (hotbar/sidebar/
    zone-shop buttons -- the exact same checks handle_mouse_click already
    runs before it would otherwise call _handle_world_click), and
    current_tool is in DRAG_BATCHABLE_ACTION_PREFIXES. Only remembers the
    start cell -- the batch doesn't actually apply until commit_drag_select
    on mouse-up, so a plain click-and-release-without-moving still ends up
    calling apply_batch_action with exactly one cell (identical net effect
    to today's single-cell click, see commit_drag_select)."""
    pos = _grid_pos_from_mouse(mx, my, camera_x, camera_y)
    state["drag_select"] = {
        "active": True, "tool": current_tool, "zone": active_zone,
        "start": pos, "current": pos,
    }
    return state


def update_drag_select(state, mx, my, camera_x, camera_y):
    """Call on every MOUSEMOTION event (unconditionally -- no-ops instantly
    if state.get("drag_select") isn't active). Updates only "current"; the
    selected-cells rectangle is derived from start/current on demand (by
    commit_drag_select, and later by a renderer preview) rather than
    recomputed and stored here every motion event."""
    drag = state.get("drag_select")
    if not drag or not drag.get("active"):
        return state
    drag["current"] = _grid_pos_from_mouse(mx, my, camera_x, camera_y)
    return state


def commit_drag_select(state):
    """Call on MOUSEBUTTONUP. If a drag is active, applies the batch action
    over every selected cell (via apply_batch_action -- see
    capstone_contract.py for why no per-cell resource-check logic needs to
    live here) and clears drag_select. No-ops (returns state unchanged) if
    no drag was in progress, e.g. the mouse-up came from a UI click that
    never went through start_drag_select in the first place."""
    drag = state.get("drag_select")
    if not drag or not drag.get("active"):
        return state
    cells = _drag_selected_cells(drag["start"], drag["current"], drag["tool"])
    action_prefix = DRAG_BATCHABLE_ACTION_PREFIXES.get(drag["tool"])
    if action_prefix:
        state = apply_batch_action(state, action_prefix, cells, zone=drag["zone"])
    state["drag_select"] = None
    return state
