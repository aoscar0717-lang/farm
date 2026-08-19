import pygame
from src.config import *
from src.capstone_contract import apply_action, new_game, is_terminal, CROP_INFO
from src.tutorial import note_event
from src import ui_layout


def _handle_shop_click(state, mx, my, shop_open, active_tab, current_tool):
    """Everything that can happen from a left-click while the shop is open:
    closing it, switching buy/sell or seed/def/pet tabs, buying an item, or
    selling one. Returns the (possibly) updated (state, current_tool,
    shop_open, active_tab)."""
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
            left_ids = ids[:(len(ids)+1)//2]
            right_ids = ids[(len(ids)+1)//2:]

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
        left_items = sellable[:6]
        right_items = sellable[6:12]

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
        elif current_tool in ["dog", "cat", "goose", "sheep", "bull", "owl"]:
            state = apply_action(state, f"place_{current_tool}_{gx}_{gy}", active_zone)
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

    if event.button != 1:
        return state, current_tool, shop_open, active_tab, active_zone

    mx, my = event.pos

    if shop_open:
        state, current_tool, shop_open, active_tab = _handle_shop_click(state, mx, my, shop_open, active_tab, current_tool)
        return state, current_tool, shop_open, active_tab, active_zone

    current_tool, hotbar_handled = _handle_hotbar_click(mx, my, current_tool)
    if hotbar_handled:
        return state, current_tool, shop_open, active_tab, active_zone

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
    elif event.key == pygame.K_1: current_tool = "hoe"
    elif event.key == pygame.K_2: current_tool = "scythe"
    elif event.key == pygame.K_3: current_tool = "shovel"
    elif event.key == pygame.K_4: current_tool = "fertilizer"

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
