import pygame
import time
from src.config import *
from src.assets import images
from src.capstone_contract import CROP_INFO
from src import ui_layout
from src import tutorial_quests as _quests

# -- Message notification queue (module-level, persists across frames) --
# Phase 4: replaced the single "_msg_text/_msg_time/_msg_color" slot with a
# bounded queue. Previously a second message arriving while the first was
# still fading out simply overwrote it -- a burst of feedback (e.g. buying
# several items back to back, or several combat events in a few seconds)
# silently lost everything but the last message. Now up to
# ui_layout.MAX_VISIBLE_TOASTS stack vertically above the hint strip, each
# fading out independently on its own timer.
_toast_queue = []          # list of {"text", "time", "color"} dicts, oldest first
_last_seen_state_msg = ""  # de-dupes state["last_msg"] into "one notify() per change"

def _get_msg_color(msg: str):
    for cat, keywords in MSG_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return MSG_COLORS[cat]
    return MSG_COLORS["info"]

def notify(msg: str):
    """Enqueue a new toast. Call this whenever last_msg changes."""
    global _toast_queue
    _toast_queue.append({"text": msg, "time": time.time(), "color": _get_msg_color(msg)})
    # Cap the queue itself (not just what's drawn) so it can't grow
    # unbounded if draw_hud somehow skips a frame or two.
    if len(_toast_queue) > ui_layout.MAX_VISIBLE_TOASTS:
        _toast_queue = _toast_queue[-ui_layout.MAX_VISIBLE_TOASTS:]


# ---------------------------------------------------------------------------
# Phase 5: draw_hud() used to be one function covering every HUD element
# (top panel + zone buttons, PRIMARY/SECONDARY/TERTIARY stat rows, money,
# day/night bar, shop button, toast queue, bottom hint strip + tool
# indicator, debug overlay). Split into one function per element, in the
# same order they used to render in -- a mechanical extraction (drawing
# logic unchanged), so draw_hud() itself now reads as the ordered list of
# what's on the HUD.
# ---------------------------------------------------------------------------

def _draw_top_panel_and_zone_buttons(screen, active_zone, mouse_pos):
    # Geometry comes from ui_layout so input_handler.py's click detection
    # can never drift out of sync with what's actually drawn here (it used
    # to: the old hand-copied hit-rect for these two buttons did not line
    # up with where they're really rendered).
    panel_rect = ui_layout.top_panel_rect()
    top_panel = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(top_panel, ui_layout.COLOR_TOP_PANEL_BG, top_panel.get_rect(), border_radius=14)
    pygame.draw.rect(top_panel, ui_layout.COLOR_TOP_PANEL_BORDER, top_panel.get_rect(), 2, border_radius=14)

    # Active Zone Toggle — two clear tab-style buttons, with a third
    # (hover) visual state so the non-active button gives feedback before
    # it's clicked, not just after.
    zone_rects = ui_layout.zone_toggle_button_rects()
    for zone_id, label in [("farm", "農田區"), ("decor", "佈置區")]:
        abs_rect = zone_rects[zone_id]
        bx, by = abs_rect.x - panel_rect.x, abs_rect.y - panel_rect.y  # panel-local
        active = (active_zone == zone_id)
        hovered = (not active) and abs_rect.collidepoint(mouse_pos)
        if active and zone_id == "farm":
            bg_col, border_col, label_col = ui_layout.COLOR_ZONE_ACTIVE_FARM_BG, ui_layout.COLOR_ZONE_ACTIVE_FARM_BORDER, ui_layout.COLOR_ZONE_LABEL_ACTIVE
        elif active and zone_id == "decor":
            bg_col, border_col, label_col = ui_layout.COLOR_ZONE_ACTIVE_DECOR_BG, ui_layout.COLOR_ZONE_ACTIVE_DECOR_BORDER, ui_layout.COLOR_ZONE_LABEL_ACTIVE
        elif hovered:
            bg_col, border_col, label_col = ui_layout.COLOR_ZONE_HOVER_BG, ui_layout.COLOR_ZONE_HOVER_BORDER, ui_layout.COLOR_ZONE_LABEL_HOVER
        else:
            bg_col, border_col, label_col = ui_layout.COLOR_ZONE_INACTIVE_BG, ui_layout.COLOR_ZONE_INACTIVE_BORDER, ui_layout.COLOR_ZONE_LABEL_INACTIVE
        btn_surf = pygame.Surface((abs_rect.w, abs_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg_col, btn_surf.get_rect(), border_radius=10)
        pygame.draw.rect(btn_surf, border_col, btn_surf.get_rect(), 2, border_radius=10)
        top_panel.blit(btn_surf, (bx, by))
        label_surf = font_small.render(label, True, label_col)
        top_panel.blit(label_surf, (bx + (abs_rect.w - label_surf.get_width()) // 2, by + (abs_rect.h - label_surf.get_height()) // 2))

    screen.blit(top_panel, panel_rect.topleft)


def _draw_top_panel_stats(screen, state, active_zone):
    is_night = state['phase'] == "night"

    # ── PRIMARY: day/phase/timer ─────────────────────────────────────────
    mins = state['time_left'] // 60
    secs = state['time_left'] % 60
    phase_str = "夜晚" if is_night else "白天"
    phase_text = f"第 {state['day_count']} 回合 - {phase_str} ({mins:02d}:{secs:02d})"
    text_color = ui_layout.COLOR_TEXT_NIGHT if is_night else ui_layout.COLOR_TEXT_DAY
    text_surf = font_large.render(phase_text, True, text_color)
    screen.blit(text_surf, (ui_layout.TOP_PANEL_TEXT_X, ui_layout.TOP_PANEL_PRIMARY_Y))

    # ── SECONDARY: zone dog count ─────────────────────────────────────────
    # The one stat actually worth checking during play (how well-guarded
    # is the zone I'm looking at), so it keeps its own line and a brighter
    # color instead of being buried mid-string among lifetime totals.
    zone_dogs = len(state.get(active_zone, {}).get('dogs', []))
    dog_stats = f"狗 ({'農田區' if active_zone == 'farm' else '佈置區'}): {zone_dogs}/10"
    dog_surf = font_small.render(dog_stats, True, ui_layout.COLOR_STAT_SECONDARY)
    screen.blit(dog_surf, (ui_layout.TOP_PANEL_TEXT_X, ui_layout.TOP_PANEL_SECONDARY_Y))

    # ── TERTIARY: prosperity / farm level / lifetime totals ────────────────
    # Low-emphasis background info -- there's no rent/Game Over anymore, so
    # "累積擊退敵人數" is one of the long-run numbers that keeps climbing
    # across an endless run instead of resetting; it doesn't need PRIMARY
    # or SECONDARY visual weight to be useful.
    lifetime_stats = f"繁榮度: {state.get('prosperity_score',0)}   農場等級: Lv{state.get('farm_level',1)}   累積擊退敵人: {state.get('enemies_defeated',0)}"
    lifetime_surf = font_tiny.render(lifetime_stats, True, ui_layout.COLOR_STAT_TERTIARY)
    screen.blit(lifetime_surf, (ui_layout.TOP_PANEL_TEXT_X, ui_layout.TOP_PANEL_TERTIARY_Y))

    # Money (top-right) -- no more rent, so this is just the current balance.
    # Anchored below the shop button (ui_layout.money_label_pos) instead of
    # an independent fixed coordinate that used to overlap it.
    money_surf = font_small.render(f"資金: ${state['money']}", True, ui_layout.COLOR_MONEY)
    screen.blit(money_surf, ui_layout.money_label_pos(money_surf.get_width()))


def _draw_daynight_bar(screen, state, now):
    # Geometry derived from the top panel's own bottom edge (ui_layout)
    # instead of a fixed y that only used to line up because the panel
    # happened to be exactly the right height.
    is_night = state['phase'] == "night"
    total_time = 120
    ratio = max(0.0, min(1.0, (total_time - state['time_left']) / total_time))

    bar_rect = ui_layout.daynight_bar_rect()
    bar_x, bar_y, bar_w, bar_h = bar_rect.x, bar_rect.y, bar_rect.w, bar_rect.h

    pygame.draw.rect(screen, (30, 25, 15), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
    fill_color = (255, 160, 30) if not is_night else (70, 90, 200)
    fill_w = max(4, int(bar_w * ratio))
    pygame.draw.rect(screen, fill_color, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

    # End-of-time warning: pulse the bar red if < 20s left
    if state['time_left'] < 20 and state['phase'] == 'day':
        pulse = abs((now * 4) % 2 - 1)
        warn_surf = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
        warn_surf.fill((255, 60, 60, int(180 * pulse)))
        screen.blit(warn_surf, (bar_x, bar_y))


def _draw_shop_button(screen):
    shop_rect = ui_layout.shop_button_rect()
    pygame.draw.rect(screen, ui_layout.COLOR_SHOP_BTN_BG, shop_rect, border_radius=10)
    pygame.draw.rect(screen, ui_layout.COLOR_SHOP_BTN_BORDER, shop_rect, 2, border_radius=10)
    shop_surf = font_small.render("商店 (B)", True, WHITE)
    screen.blit(shop_surf, (shop_rect.centerx - shop_surf.get_width()//2, shop_rect.centery - shop_surf.get_height()//2))


def _draw_toast_queue(screen, state, now):
    # Phase 4: up to ui_layout.MAX_VISIBLE_TOASTS messages stack upward
    # from just above the hint strip, newest closest to the hint strip,
    # each fading/floating in on its own independent timer.
    global _last_seen_state_msg, _toast_queue
    state_msg = state.get("last_msg", "")
    if state_msg and state_msg != _last_seen_state_msg:
        notify(state_msg)
        _last_seen_state_msg = state_msg

    total_display = MSG_DURATION + MSG_FADE_DURATION
    _toast_queue = [t for t in _toast_queue if now - t["time"] < total_display]
    active_toasts = _toast_queue[-ui_layout.MAX_VISIBLE_TOASTS:]

    # Render newest-first (bottom-most slot first) so stack_upward can hand
    # back each one's top-y without any toast needing to know about the
    # others' geometry -- just "how tall am I".
    rendered = []
    for toast in reversed(active_toasts):
        elapsed_msg = now - toast["time"]
        if elapsed_msg > MSG_DURATION:
            fade_p = (elapsed_msg - MSG_DURATION) / MSG_FADE_DURATION
            alpha = int(255 * (1.0 - fade_p))
        else:
            alpha = 255
        float_off = int(8 * min(1.0, elapsed_msg / 0.25))  # float up as it appears

        msg_surf = font_large.render(toast["text"], True, toast["color"])
        msg_w = msg_surf.get_width() + 28
        msg_h = msg_surf.get_height() + 14

        msg_bg = pygame.Surface((msg_w, msg_h), pygame.SRCALPHA)
        r, g, b = toast["color"][:3]
        pygame.draw.rect(msg_bg, (r, g, b, int(60 * alpha / 255)), msg_bg.get_rect(), border_radius=10)
        pygame.draw.rect(msg_bg, (r, g, b, alpha), msg_bg.get_rect(), 2, border_radius=10)
        msg_surf.set_alpha(alpha)

        rendered.append({"bg": msg_bg, "surf": msg_surf, "w": msg_w, "h": msg_h, "float_off": float_off})

    tops = ui_layout.stack_upward(ui_layout.bottom_toast_bottom_y(), [r["h"] for r in rendered])
    for r, top in zip(rendered, tops):
        bx = WIDTH // 2 - r["w"] // 2
        by = top - r["float_off"]
        screen.blit(r["bg"], (bx, by))
        screen.blit(r["surf"], (bx + 14, by + 7))


def _draw_bottom_hint_and_tool_indicator(screen, current_tool):
    # ── Bottom hint strip (BOTTOM_HINT_AREA) ────────────────────────────────
    hint_area = ui_layout.bottom_hint_area()
    hint_panel = pygame.Surface((hint_area.w, hint_area.h), pygame.SRCALPHA)
    pygame.draw.rect(hint_panel, (0, 0, 0, 155), hint_panel.get_rect(), border_radius=10)
    screen.blit(hint_panel, hint_area.topleft)

    help_text = "[空白]: 進入夜晚  [TAB]: 切換區域  [B]: 商店  [WASD/右鍵]: 移動  [1-4]: 工具  [ESC]: 取消"
    help_surf = font_tiny.render(help_text, True, (165, 165, 185))
    screen.blit(help_surf, (hint_area.centerx - help_surf.get_width() // 2,
                             hint_area.centery - help_surf.get_height() // 2))

    # Current tool indicator -- attached to the toolbar (BOTTOM_TOOLBAR_AREA)
    # it actually describes, instead of the hint strip it used to spill
    # out below (its old fixed y placed it partly outside the hint panel's
    # own background).
    tool_text = f"裝備中: {TOOL_NAMES.get(current_tool, current_tool)}" if current_tool else "一般模式 (右鍵/ESC取消裝備)"
    indicator = font_small.render(tool_text, True, (220, 220, 255))
    screen.blit(indicator, ui_layout.toolbar_side_label_pos(indicator.get_width(), indicator.get_height()))


def _draw_debug_overlay(screen, state):
    if state.get("debug_scale_mode"):
        from src.config import SPRITE_SCALES
        keys_list = list(SPRITE_SCALES.keys())
        idx = state.get("debug_scale_idx", 0)
        if idx < len(keys_list):
            k = keys_list[idx]
            w, h = SPRITE_SCALES[k]
            debug_txt = font_small.render(
                f"[F9] Debug - {k} (W:{w:.1f}, H:{h:.1f}). [TAB] Next | [-/=] W | [[/]] H | [F10] Print",
                True, (0, 255, 0))
            pygame.draw.rect(screen, (0, 0, 0, 180), (8, 8, debug_txt.get_width()+4, debug_txt.get_height()+4))
            screen.blit(debug_txt, (10, 10))


def draw_hud(screen, state, current_tool, active_zone, mouse_pos=(-1, -1)):
    now = time.time()
    _draw_top_panel_and_zone_buttons(screen, active_zone, mouse_pos)
    _draw_top_panel_stats(screen, state, active_zone)
    _draw_daynight_bar(screen, state, now)
    _draw_shop_button(screen)
    _draw_toast_queue(screen, state, now)
    _draw_bottom_hint_and_tool_indicator(screen, current_tool)
    _draw_debug_overlay(screen, state)


# Item *details* (display name / price / description) for the buy tabs.
# Keyed by id and iterated in ui_layout.SHOP_ITEM_IDS[tab] order so a
# card's index (and therefore its shared shop_column_rects position) always
# lines up with the same item the click handler resolves from that same
# canonical id list -- see ui_layout.py's module docstring.
SHOP_ITEM_DETAILS = {
    # V1.1 balance pass: growth_time now genuinely matches these numbers
    # (see CROP_INFO in capstone_contract.py) instead of every crop
    # secretly needing 5 nights regardless of what this text claimed.
    "radish":  {"name": "白蘿蔔種子",  "price": 30,  "desc": "1天成熟，鐮刀收割 $50"},
    "carrot":  {"name": "胡蘿蔔種子",  "price": 100, "desc": "2天成熟，鐮刀收割 $250"},
    "pumpkin": {"name": "魔法南瓜種子", "price": 300, "desc": "3天成熟，鐮刀收割 $1000"},
    # V1.1 balance pass: the fence card used to show a literal "1 木材"
    # price -- there is no wood/material system anywhere in this project
    # (only a couple of unused leftover sprite/string references), and
    # build_fence_ actually charges $20 cash, same as every other item
    # here. Descriptions rewritten to match each item's real behavior
    # instead of a generic placeholder.
    "fence": {"name": "木圍欄", "price": 20, "desc": "HP100，阻擋敵人，受損後被突破"},
    "trap":  {"name": "地刺陷阱", "price": 50, "desc": "敵人踩到觸發，一次性"},
    "dog":   {"name": "看門狗", "price": 200, "desc": "自動攻擊靠近敵人，不會陣亡"},  # price overridden below when free_dog
    "stone_path": {"name": "石板路",   "price": 20,  "desc": "繁榮度 +5"},
    "flower":     {"name": "鮮花盆栽", "price": 50,  "desc": "繁榮度 +15"},
    "bench":      {"name": "木製長椅", "price": 100, "desc": "繁榮度 +35"},
    "fountain":   {"name": "風車", "price": 300, "desc": "繁榮度 +120"},
    # Landscape expansion (7 new decor items) -- price/prosperity chosen to
    # extend the existing curve (small $20-30/+8-10, mid $60-90/+18-28,
    # large $260/+95) rather than flattening everything to one number; see
    # the analysis report for the per-item reasoning.
    "scarecrow":  {"name": "稻草人",   "price": 30,  "desc": "繁榮度 +10"},
    "crate":      {"name": "木箱",     "price": 25,  "desc": "繁榮度 +8"},
    "bush":       {"name": "灌木叢",   "price": 20,  "desc": "繁榮度 +8"},
    "rock":       {"name": "庭院石",   "price": 60,  "desc": "繁榮度 +18"},
    "sunflower":  {"name": "向日葵",   "price": 80,  "desc": "繁榮度 +25"},
    "pine_tree":  {"name": "松樹",     "price": 90,  "desc": "繁榮度 +28"},
    "big_tree":   {"name": "大樹",     "price": 260, "desc": "繁榮度 +95"},
    # Landscape expansion round 2 -- 8 more items, prices/prosperity chosen
    # so the FULL merged curve (all 19 decor items sorted by price) stays
    # non-decreasing in prosperity -- verified by
    # test_price_curve_is_non_decreasing_with_prosperity in
    # tests/test_landscape_consistency.py.
    "stump":          {"name": "樹墩",   "price": 12,  "desc": "繁榮度 +4"},
    "mushroom":       {"name": "蘑菇",   "price": 16,  "desc": "繁榮度 +5"},
    "picnic_basket":  {"name": "野餐籃", "price": 22,  "desc": "繁榮度 +8"},
    "woodpile":       {"name": "柴堆",   "price": 28,  "desc": "繁榮度 +9"},
    "picnic_blanket": {"name": "野餐墊", "price": 45,  "desc": "繁榮度 +13"},
    "beehive":        {"name": "蜂箱",   "price": 70,  "desc": "繁榮度 +22"},
    "garden_table":   {"name": "庭院桌", "price": 105, "desc": "繁榮度 +42"},
    "fruit_tree":     {"name": "果樹",   "price": 150, "desc": "繁榮度 +55"},
}


# ---------------------------------------------------------------------------
# Phase 5: draw_shop() split the same way -- frame/tabs, the buy-tab grid,
# and the sell-tab grid are independent concerns that used to live in one
# function; _draw_shop_card was already a nested closure (from Phase 1),
# promoted to a top-level function here since it no longer needs to close
# over anything draw_shop-local.
# ---------------------------------------------------------------------------

def _draw_shop_card(screen, card_rect, img_id, name, desc, price_display, price_color, hovered):
    card_surf = pygame.Surface((card_rect.w, card_rect.h), pygame.SRCALPHA)
    bg_a = 160 if hovered else 100
    pygame.draw.rect(card_surf, (255, 255, 255, bg_a), card_surf.get_rect(), border_radius=10)
    screen.blit(card_surf, card_rect.topleft)

    img = images.get(img_id)
    if img:
        screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))
    else:
        pygame.draw.rect(screen, (220, 220, 220), (card_rect.x + 10, card_rect.y + 12, 40, 40), border_radius=5)
        fb = font_tiny.render(name[:2], True, (100, 100, 100))
        screen.blit(fb, (card_rect.x + 30 - fb.get_width()//2, card_rect.y + 32 - fb.get_height()//2))

    n_surf = font_small.render(name, True, BLACK)
    screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))

    d_surf = font_tiny.render(desc, True, (80, 80, 80))
    screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))

    p_surf = font_small.render(price_display, True, price_color)
    screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))

    if hovered:
        pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)


def _draw_shop_frame(screen, geo, active_tab):
    shop_rect = geo["shop_rect"]
    shop_x, shop_y = shop_rect.x, shop_rect.y
    left_page_x, page_w = geo["left_page_x"], geo["page_w"]
    tab_buy, tab_sell = geo["tab_buy"], geo["tab_sell"]

    bg_img = images.get("shop_bg")
    if bg_img:
        screen.blit(pygame.transform.scale(bg_img, (shop_rect.w, shop_rect.h)), shop_rect.topleft)
    else:
        pygame.draw.rect(screen, (245, 245, 250), shop_rect, border_radius=15)

    is_sell = active_tab == "sell"

    patch_rect = pygame.Rect(left_page_x, shop_y + 80, page_w, 80)
    pygame.draw.rect(screen, (220, 185, 138), patch_rect)

    pygame.draw.rect(screen, BLUE if not is_sell else GRAY, tab_buy,  border_radius=10)
    pygame.draw.rect(screen, BLUE if is_sell  else GRAY, tab_sell, border_radius=10)

    tb_surf = font_small.render("購買道具", True, WHITE)
    ts_surf = font_small.render("出售作物", True, WHITE)
    screen.blit(tb_surf, (tab_buy.centerx  - tb_surf.get_width()//2, tab_buy.centery  - tb_surf.get_height()//2))
    screen.blit(ts_surf, (tab_sell.centerx - ts_surf.get_width()//2, tab_sell.centery - ts_surf.get_height()//2))


def _draw_shop_buy_tab(screen, state, active_tab, mouse_pos, geo):
    subtab_rects = ui_layout.shop_subtab_rects()
    for tab_id in ui_layout.SHOP_TABS:
        tab_rect = subtab_rects[tab_id]
        color = (100, 150, 255) if active_tab == tab_id else (200, 200, 200)
        pygame.draw.rect(screen, color, tab_rect, border_radius=5)
        txt = font_tiny.render(ui_layout.SHOP_TAB_LABELS[tab_id], True, BLACK)
        screen.blit(txt, (tab_rect.centerx - txt.get_width()//2, tab_rect.centery - txt.get_height()//2))

    ids = ui_layout.SHOP_ITEM_IDS.get(active_tab, [])
    left_ids  = ids[:(len(ids)+1)//2]
    right_ids = ids[(len(ids)+1)//2:]

    for column, col_ids in [("left", left_ids), ("right", right_ids)]:
        rects = ui_layout.shop_column_rects(len(col_ids), is_sell=False, column=column)
        for item_id, card_rect in zip(col_ids, rects):
            details = SHOP_ITEM_DETAILS[item_id]
            price = "FREE" if (item_id == "dog" and state.get("free_dog")) else details["price"]
            price_display = f"${price}" if isinstance(price, int) else str(price)
            price_color = YELLOW if price != "FREE" else (50, 220, 50)
            hovered = card_rect.collidepoint(mouse_pos)
            _draw_shop_card(screen, card_rect, item_id, details["name"], details["desc"], price_display, price_color, hovered)


def _draw_shop_sell_tab(screen, state, mouse_pos, geo):
    left_page_x, page_w = geo["left_page_x"], geo["page_w"]
    shop_y = geo["shop_rect"].y
    sellable = ui_layout.build_sellable_list(state, CROP_INFO)

    if not sellable:
        empty_surf = font_small.render("背包空空如也，快去收割吧！", True, (160, 120, 80))
        screen.blit(empty_surf, (left_page_x + page_w // 2 - empty_surf.get_width() // 2, shop_y + 300))
        return

    # Sell page is a fixed 6-per-column, 12-item cap (no scrolling) --
    # this slicing (not a 50/50 split like the buy page) matches what
    # shop_column_rects' "sell" column-start heights are laid out for.
    left_items, right_items = sellable[:6], sellable[6:12]

    for column, col_items in [("left", left_items), ("right", right_items)]:
        rects = ui_layout.shop_column_rects(len(col_items), is_sell=True, column=column)
        for item, card_rect in zip(col_items, rects):
            hovered = card_rect.collidepoint(mouse_pos)
            if hovered:
                card_rect = card_rect.move(0, -3)  # slight hover lift, same as before
            _draw_shop_card(
                screen, card_rect, item["id"], f"{item['name']} x{item['count']}", "點擊賣出 1 個",
                f"+${item['price']}", (50, 205, 50), hovered,
            )


def draw_shop(screen, state, shop_open, active_tab, mouse_pos):
    if not shop_open:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    geo = ui_layout.shop_page_geometry()
    _draw_shop_frame(screen, geo, active_tab)

    if active_tab == "sell":
        _draw_shop_sell_tab(screen, state, mouse_pos, geo)
    else:
        _draw_shop_buy_tab(screen, state, active_tab, mouse_pos, geo)


def _wrap_line_to_width(text, max_width):
    """Break `text` into sub-lines that each fit within max_width, measured
    with font_small. Character-by-character (not word-by-word) since
    Chinese text has no spaces to break on; still works fine for the
    occasional English token (TAB, WASD, [F], ...) mixed in."""
    if font_small.size(text)[0] <= max_width:
        return [text]
    wrapped = []
    current = ""
    for ch in text:
        trial = current + ch
        if current and font_small.size(trial)[0] > max_width:
            wrapped.append(current)
            current = ch
        else:
            current = trial
    if current:
        wrapped.append(current)
    return wrapped


def draw_contemplation(screen, lines, fade_ratio):
    """思索模式 panel: shown while F is held. Small, pixel-styled, sits
    above the hotbar so it never covers the main play area. `lines` is a
    list of 1-3 short strings from src/thought.py -- this function only
    handles layout/fade/wrapping, it has no opinion on what the text says.
    Long lines are wrapped rather than left to overflow the panel."""
    alpha = int(255 * fade_ratio)
    if alpha <= 0:
        return

    pad_x, pad_y = 18, 12
    line_gap = 4
    max_content_w = min(560, WIDTH - 160)

    wrapped_lines = []
    for line in lines:
        wrapped_lines.extend(_wrap_line_to_width(line, max_content_w))

    line_surfs = [font_small.render(line, True, (235, 230, 210)) for line in wrapped_lines]
    content_w = min(max((s.get_width() for s in line_surfs), default=0), max_content_w)
    content_h = sum(s.get_height() for s in line_surfs) + line_gap * max(0, len(line_surfs) - 1)

    title_surf = font_tiny.render("思索", True, (180, 220, 255))
    key_surf = font_tiny.render("[F]", True, (255, 230, 120))

    panel_w = max(content_w, title_surf.get_width() + key_surf.get_width() + 20) + pad_x * 2
    panel_h = pad_y * 2 + title_surf.get_height() + 6 + content_h

    panel_x = WIDTH // 2 - panel_w // 2
    # Anchored above the toast message's reserved slot (ui_layout), not a
    # fixed offset from the hotbar -- this is what keeps the Thought panel
    # from landing on top of the toast message or the hint strip whenever
    # either happens to be visible in the same frame.
    panel_y = ui_layout.bottom_thought_bottom_y() - panel_h

    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (15, 12, 20, int(215 * fade_ratio)), panel.get_rect(), border_radius=10)
    pygame.draw.rect(panel, (140, 170, 210, alpha), panel.get_rect(), 2, border_radius=10)

    title_surf.set_alpha(alpha)
    key_surf.set_alpha(alpha)
    panel.blit(title_surf, (pad_x, pad_y))
    panel.blit(key_surf, (panel_w - pad_x - key_surf.get_width(), pad_y))

    y = pad_y + title_surf.get_height() + 6
    for surf in line_surfs:
        surf.set_alpha(alpha)
        panel.blit(surf, (pad_x, y))
        y += surf.get_height() + line_gap

    screen.blit(panel, (panel_x, panel_y))


def _wrap_text_to_width(text, max_width, font):
    """Same character-by-character wrap as _wrap_line_to_width, but for an
    arbitrary font -- the sidebar draws at font_tiny inside a narrower
    (300px) panel than draw_contemplation's font_small wrapping was tuned
    for, so it needs its own width budget."""
    if font.size(text)[0] <= max_width:
        return [text]
    wrapped = []
    current = ""
    for ch in text:
        trial = current + ch
        if current and font.size(trial)[0] > max_width:
            wrapped.append(current)
            current = ch
        else:
            current = trial
    if current:
        wrapped.append(current)
    return wrapped


def draw_tutorial_sidebar(screen, state):
    """新手任務側欄 (section 一 of the Tutorial/Sidebar/Thought upgrade):
    right-edge panel showing the player's current quest chapter/task list,
    reading from tutorial_quests.get_quest_progress() -- the exact same
    function src/thought.py's quest_guidance entry reads, so the Sidebar and
    F 思索 can never disagree about what "the current task" is (section 八).

    Purely a read + draw -- no state mutation here, and no click handling
    (input_handler.py's own click-passthrough guard is what stops clicks
    on this panel from reaching the world underneath; this function only
    owns pixels).
    """
    panel_rect = ui_layout.tutorial_sidebar_rect()
    pad_x, pad_y = 14, 12

    panel = pygame.Surface((panel_rect.w, panel_rect.h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (12, 10, 8, 190), panel.get_rect(), border_radius=10)
    pygame.draw.rect(panel, (110, 85, 45, 210), panel.get_rect(), 2, border_radius=10)

    progress = _quests.get_quest_progress(state)
    current_chapter = progress["current_chapter"]
    current_task = progress["current_task"]
    total_done, total_count = progress["total_progress"]
    chap_done, chap_total = progress["chapter_progress"]

    # Once every chapter is complete, this stops being "new player
    # onboarding" and becomes a standing reference panel -- the title (and
    # the content below it) reflects that instead of forever claiming to be
    # "新手教學" for a player who's clearly not new anymore (section 一's
    # explicit requirement).
    all_done = current_task is None
    title_text = "農場指南" if all_done else "新手教學"

    y = pad_y
    title_surf = font_small.render(title_text, True, (240, 220, 150))
    panel.blit(title_surf, (pad_x, y))
    total_surf = font_tiny.render(f"{total_done}/{total_count}", True, (170, 160, 140))
    panel.blit(total_surf, (panel_rect.w - pad_x - total_surf.get_width(), y + 4))
    y += title_surf.get_height() + 6

    pygame.draw.line(panel, (110, 85, 45, 200), (pad_x, y), (panel_rect.w - pad_x, y), 1)
    y += 8

    if current_chapter is not None:
        chapter_line = f"{current_chapter.title} {chap_done}/{chap_total}"
        chap_surf = font_tiny.render(chapter_line, True, (200, 220, 255))
        panel.blit(chap_surf, (pad_x, y))
        y += chap_surf.get_height() + 4
        if current_chapter.subtitle:
            sub_surf = font_tiny.render(current_chapter.subtitle, True, (150, 145, 130))
            panel.blit(sub_surf, (pad_x, y))
            y += sub_surf.get_height() + 8
        else:
            y += 4

        # Recompute from the shared geometry function rather than trusting
        # the hand-drawn arithmetic above to stay in sync forever -- this
        # is what ui_layout.tutorial_sidebar_task_rects() uses to place the
        # first task row, so overriding y here guarantees draw and hover
        # hit-test can never drift apart even if one of the two is edited
        # later without the other.
        y = pad_y + ui_layout.tutorial_sidebar_header_height(current_chapter)

        max_w = panel_rect.w - pad_x * 2 - 24
        # Row positions come from ui_layout.tutorial_sidebar_task_rects --
        # the same function thought.py's Sidebar-hover resolution uses to
        # figure out which task row the mouse is over (section 九), so the
        # two can never disagree about where a given task's row actually
        # is on screen.
        for task, abs_row_rect in ui_layout.tutorial_sidebar_task_rects(state):
            row_y = abs_row_rect.y - panel_rect.y  # panel-local
            done = task.is_done(state)
            is_current = current_task is not None and task.id == current_task.id
            mark = "✓" if done else "○"  # checkmark / open circle
            mark_color = (140, 220, 140) if done else (150, 145, 130)
            title_color = (150, 145, 130) if done else ((255, 240, 150) if is_current else (225, 220, 205))

            if is_current:
                pygame.draw.rect(
                    panel, (70, 55, 25, 180),
                    pygame.Rect(pad_x - 4, row_y - 2, panel_rect.w - (pad_x - 4) * 2, abs_row_rect.h),
                    border_radius=5,
                )

            row_y_cursor = row_y
            mark_surf = font_tiny.render(mark, True, mark_color)
            panel.blit(mark_surf, (pad_x, row_y_cursor))
            title_lines = _wrap_text_to_width(task.title, max_w, font_tiny)
            title_surf2 = font_tiny.render(title_lines[0], True, title_color)
            panel.blit(title_surf2, (pad_x + 22, row_y_cursor))
            row_y_cursor += font_tiny.get_height() + 4

            if is_current and task.hint:
                for hint_line in _wrap_text_to_width(task.hint, max_w, font_tiny):
                    hint_surf = font_tiny.render(hint_line, True, (190, 210, 235))
                    panel.blit(hint_surf, (pad_x + 22, row_y_cursor))
                    row_y_cursor += hint_surf.get_height() + 2

            y = row_y + abs_row_rect.h + ui_layout.TUTORIAL_SIDEBAR_ROW_GAP

    else:
        empty_surf = font_tiny.render("目前沒有進行中的任務。", True, (170, 160, 140))
        panel.blit(empty_surf, (pad_x, y))
        y += empty_surf.get_height() + 6

    if all_done:
        done_lines = _wrap_text_to_width(
            "所有新手任務都完成了！農場接下來就是你自己的風格了。",
            panel_rect.w - pad_x * 2, font_tiny,
        )
        for line in done_lines:
            if y > panel_rect.h - pad_y - 20:
                break
            done_surf = font_tiny.render(line, True, (180, 220, 180))
            panel.blit(done_surf, (pad_x, y))
            y += done_surf.get_height() + 2

    screen.blit(panel, panel_rect.topleft)


def draw_game_over(screen, state):
    """Game Over has been removed from the design: no rent, no bankruptcy,
    no failure ending -- the farm is meant to be played indefinitely
    (Day 1, 2, 3, ... forever). Kept as a no-op so renderer.py doesn't need
    to change its call site."""
    return
