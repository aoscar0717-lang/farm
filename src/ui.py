import pygame
import time
from src.config import *
from src.assets import images
from src.capstone_contract import CROP_INFO

# -- Message notification state (module-level, persists across frames) --
_msg_text = ""
_msg_time = 0.0   # time.time() when message was set
_msg_color = MSG_COLORS["info"]

def _get_msg_color(msg: str):
    for cat, keywords in MSG_KEYWORDS.items():
        if any(kw in msg for kw in keywords):
            return MSG_COLORS[cat]
    return MSG_COLORS["info"]

def notify(msg: str):
    """Call this whenever last_msg changes to start the fade timer."""
    global _msg_text, _msg_time, _msg_color
    _msg_text = msg
    _msg_time = time.time()
    _msg_color = _get_msg_color(msg)


def draw_hud(screen, state, current_tool, active_zone):
    now = time.time()

    # ── Top Panel ──────────────────────────────────────────────────────────
    panel_h = 90
    top_panel = pygame.Surface((WIDTH - 40, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(top_panel, (10, 8, 5, 210), top_panel.get_rect(), border_radius=14)
    pygame.draw.rect(top_panel, (80, 60, 30, 200), top_panel.get_rect(), 2, border_radius=14)
    
    # Active Zone Toggle
    toggle_rect = pygame.Rect(WIDTH // 2 - 110 - 20, 14, 220, 44) # -20 to offset from left padding
    pygame.draw.rect(top_panel, (120, 90, 50, 200), toggle_rect, border_radius=8)
    mode_text = "農田區" if active_zone == "farm" else "佈置區"
    mode_surf = font_small.render(f"切換區域: {mode_text}", True, WHITE)
    top_panel.blit(mode_surf, (toggle_rect.x + toggle_rect.width//2 - mode_surf.get_width()//2, toggle_rect.y + 10))
    
    screen.blit(top_panel, (20, 12))

    # Phase & time
    mins = state['time_left'] // 60
    secs = state['time_left'] % 60
    is_night = state['phase'] == "night"
    phase_str = "夜晚" if is_night else "白天"
    phase_text = f"第 {state['day_count']} 回合 - {phase_str} ({mins:02d}:{secs:02d})"
    text_surf = font_large.render(phase_text, True, (240, 220, 150) if not is_night else (160, 200, 255))
    screen.blit(text_surf, (40, 22))

    # Pet / farm stats
    pet_stats = f"狗: {len(state.get('dogs',[]))}/10   繁榮度: {state.get('prosperity_score',0)}   農場等級: Lv{state.get('farm_level',1)}"
    pet_surf = font_small.render(pet_stats, True, (180, 200, 255))
    screen.blit(pet_surf, (40, 66))

    # Money (top-right)
    rent = 20 + (state["day_count"] - 1) * 10
    money_color = (255, 215, 0) if state['money'] >= rent else (255, 90, 90)
    money_surf = font_small.render(f"資金: ${state['money']} (今晚租金: ${rent})", True, money_color)
    screen.blit(money_surf, (WIDTH - money_surf.get_width() - 40, 35))

    # ── Day/Night Progress Bar ─────────────────────────────────────────────
    total_time = 120
    ratio = max(0.0, min(1.0, (total_time - state['time_left']) / total_time))

    bar_w = WIDTH - 80
    bar_h = 8
    bar_x = 40
    bar_y = 108

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

    # ── Zone Toggle Button ─────────────────────────────────────────────────
    # ── Shop Button ────────────────────────────────────────────────────────
    shop_rect = pygame.Rect(WIDTH - 158, 14, 140, 44)
    pygame.draw.rect(screen, (55, 50, 85), shop_rect, border_radius=10)
    pygame.draw.rect(screen, (200, 200, 200), shop_rect, 2, border_radius=10)
    shop_surf = font_small.render("商店 (B)", True, WHITE)
    screen.blit(shop_surf, (shop_rect.centerx - shop_surf.get_width()//2,
                             shop_rect.centery - shop_surf.get_height()//2))

    # ── Animated Message Notification ─────────────────────────────────────
    global _msg_text, _msg_time, _msg_color
    state_msg = state.get("last_msg", "")
    if state_msg and state_msg != _msg_text:
        notify(state_msg)

    if _msg_text:
        elapsed_msg = now - _msg_time
        total_display = MSG_DURATION + MSG_FADE_DURATION
        if elapsed_msg < total_display:
            # Alpha: full -> fade
            if elapsed_msg > MSG_DURATION:
                fade_p = (elapsed_msg - MSG_DURATION) / MSG_FADE_DURATION
                alpha = int(255 * (1.0 - fade_p))
            else:
                alpha = 255

            # Float up as it appears
            float_off = int(8 * min(1.0, elapsed_msg / 0.25))

            msg_surf = font_large.render(_msg_text, True, _msg_color)
            msg_w = msg_surf.get_width() + 28
            msg_h = msg_surf.get_height() + 14

            msg_bg = pygame.Surface((msg_w, msg_h), pygame.SRCALPHA)
            r, g, b = _msg_color[:3]
            pygame.draw.rect(msg_bg, (r, g, b, int(60 * alpha / 255)), msg_bg.get_rect(), border_radius=10)
            pygame.draw.rect(msg_bg, (r, g, b, alpha), msg_bg.get_rect(), 2, border_radius=10)
            msg_surf.set_alpha(alpha)

            bx = WIDTH // 2 - msg_w // 2
            by = HEIGHT - 165 - float_off
            screen.blit(msg_bg, (bx, by))
            screen.blit(msg_surf, (bx + 14, by + 7))

    # ── Bottom info strip ──────────────────────────────────────────────────
    bottom_panel = pygame.Surface((WIDTH - 40, 48), pygame.SRCALPHA)
    pygame.draw.rect(bottom_panel, (0, 0, 0, 155), bottom_panel.get_rect(), border_radius=12)
    screen.blit(bottom_panel, (20, HEIGHT - 132))

    help_text = "[空白]: 進入夜晚  [TAB]: 切換區域  [B]: 商店  [WASD/右鍵]: 移動  [1-4]: 工具  [ESC]: 取消"
    help_surf = font_tiny.render(help_text, True, (165, 165, 185))
    screen.blit(help_surf, (WIDTH//2 - help_surf.get_width()//2, HEIGHT - 122))

    # Current tool indicator bottom-right
    tool_text = f"裝備中: {TOOL_NAMES.get(current_tool, current_tool)}" if current_tool else "一般模式 (右鍵/ESC取消裝備)"
    indicator = font_small.render(tool_text, True, (220, 220, 255))
    screen.blit(indicator, (WIDTH - indicator.get_width() - 40, HEIGHT - 86))

    # Debug scale overlay
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


def draw_shop(screen, state, shop_open, active_tab, mouse_pos):
    if not shop_open:
        return
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (0, 0))

    shop_w = 1180
    shop_h = 700
    shop_x = (WIDTH - shop_w) // 2
    shop_y = (HEIGHT - shop_h) // 2
    shop_rect = pygame.Rect(shop_x, shop_y, shop_w, shop_h)

    bg_img = images.get("shop_bg")
    if bg_img:
        screen.blit(pygame.transform.scale(bg_img, (shop_w, shop_h)), shop_rect.topleft)
    else:
        pygame.draw.rect(screen, (245, 245, 250), shop_rect, border_radius=15)

    is_sell = active_tab == "sell"

    left_page_x  = shop_x + 90
    left_page_w  = 400
    right_page_x = shop_x + 675
    right_page_w = 400

    tab_buy  = pygame.Rect(left_page_x,  shop_y + 110, left_page_w,  45)
    tab_sell = pygame.Rect(right_page_x, shop_y + 110, right_page_w, 45)

    patch_rect = pygame.Rect(left_page_x, shop_y + 80, left_page_w, 80)
    pygame.draw.rect(screen, (220, 185, 138), patch_rect)

    pygame.draw.rect(screen, BLUE if not is_sell else GRAY, tab_buy,  border_radius=10)
    pygame.draw.rect(screen, BLUE if is_sell  else GRAY, tab_sell, border_radius=10)

    tb_surf = font_small.render("購買道具", True, WHITE)
    ts_surf = font_small.render("出售作物", True, WHITE)
    screen.blit(tb_surf, (tab_buy.centerx  - tb_surf.get_width()//2, tab_buy.centery  - tb_surf.get_height()//2))
    screen.blit(ts_surf, (tab_sell.centerx - ts_surf.get_width()//2, tab_sell.centery - ts_surf.get_height()//2))

    if not is_sell:
        tabs = [
            {"id": "seed", "name": "種子"},
            {"id": "def",  "name": "防禦"},
            {"id": "pet",  "name": "景觀"},
        ]
        tab_w = (left_page_w - 10) // 3
        for i, tab in enumerate(tabs):
            tab_rect = pygame.Rect(left_page_x + i * (tab_w + 5), shop_y + 165, tab_w, 30)
            color = (100, 150, 255) if active_tab == tab["id"] else (200, 200, 200)
            pygame.draw.rect(screen, color, tab_rect, border_radius=5)
            txt = font_tiny.render(tab["name"], True, BLACK)
            screen.blit(txt, (tab_rect.centerx - txt.get_width()//2, tab_rect.centery - txt.get_height()//2))

        items = []
        if active_tab == "seed":
            items = [
                {"id": "radish",  "name": "白蘿蔔種子",  "price": 30,  "desc": "1天成熟，賣出 $50  (等級 1)"},
                {"id": "carrot",  "name": "胡蘿蔔種子",  "price": 100, "desc": "2天成熟，賣出 $250 (等級 2)"},
                {"id": "pumpkin", "name": "魔法南瓜種子", "price": 300, "desc": "3天成熟，賣出 $1000 (等級 3)"},
            ]
        elif active_tab == "def":
            items = [
                {"id": "fence", "name": "木圍欄", "price": "1 木材", "desc": "實體障礙，需木材"},
                {"id": "trap",  "name": "捕獸夾", "price": 50,       "desc": "對敵人造成傷害"},
                {"id": "dog",   "name": "看門狗", "price": "FREE" if state.get("free_dog") else 200, "desc": "主動攻擊附近的敵人"},
            ]
        elif active_tab == "pet":
            items = [
                {"id": "stone_path", "name": "石板路",   "price": 20,  "desc": "繁榮度 +5"},
                {"id": "flower",     "name": "鮮花盆栽", "price": 50,  "desc": "繁榮度 +15"},
                {"id": "bench",      "name": "木製長椅", "price": 100, "desc": "繁榮度 +35"},
                {"id": "fountain",   "name": "小型噴泉", "price": 300, "desc": "繁榮度 +120"},
            ]

        left_items  = items[:(len(items)+1)//2]
        right_items = items[(len(items)+1)//2:]

        for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 210), (right_items, right_page_x, shop_y + 170)]:
            y_offset = start_y
            for item in page_items:
                card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                hovered = card_rect.collidepoint(mouse_pos)

                card_surf = pygame.Surface((left_page_w, 65), pygame.SRCALPHA)
                bg_a = 160 if hovered else 100
                pygame.draw.rect(card_surf, (255, 255, 255, bg_a), card_surf.get_rect(), border_radius=10)
                screen.blit(card_surf, card_rect.topleft)

                img = images.get(item["id"])
                if img:
                    screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))
                else:
                    pygame.draw.rect(screen, (220, 220, 220), (card_rect.x + 10, card_rect.y + 12, 40, 40), border_radius=5)
                    fb = font_tiny.render(item["name"][:2], True, (100, 100, 100))
                    screen.blit(fb, (card_rect.x + 30 - fb.get_width()//2, card_rect.y + 32 - fb.get_height()//2))

                n_surf = font_small.render(item["name"], True, BLACK)
                screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))

                d_surf = font_tiny.render(item["desc"], True, (80, 80, 80))
                screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))

                p_str = f"${item['price']}" if isinstance(item['price'], int) else str(item['price'])
                p_col = YELLOW if item['price'] != "FREE" else (50, 220, 50)
                p_surf = font_small.render(p_str, True, p_col)
                screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))

                if hovered:
                    pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)

                y_offset += 75
    else:
        grades     = ["normal", "rare", "epic", "legendary"]
        grades_tw  = {"normal": "一般", "rare": "稀有", "epic": "史詩", "legendary": "傳奇"}
        multipliers = {"normal": 1, "rare": 2, "epic": 3, "legendary": 5}

        sellable = []
        for c_id, c_name in [("radish", "白蘿蔔"), ("carrot", "胡蘿蔔"), ("pumpkin", "魔法南瓜")]:
            base_price = CROP_INFO[c_id]["yield"] if c_id in CROP_INFO else 100
            for grade in grades:
                count = state["inventory"].get(c_id, {}).get(grade, 0)
                if count > 0:
                    sellable.append({
                        "id": c_id,
                        "name": f"{c_name} ({grades_tw[grade]})",
                        "count": count,
                        "price": base_price * multipliers[grade],
                        "grade": grade,
                    })

        left_items  = sellable[:6]
        right_items = sellable[6:12]

        for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 170), (right_items, right_page_x, shop_y + 170)]:
            y_offset = start_y
            for item in page_items:
                card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                hovered = card_rect.collidepoint(mouse_pos)

                card_surf = pygame.Surface((left_page_w, 65), pygame.SRCALPHA)
                pygame.draw.rect(card_surf, (255, 255, 255, 160 if hovered else 100), card_surf.get_rect(), border_radius=10)
                screen.blit(card_surf, card_rect.topleft)

                img = images.get(item["id"])
                if img:
                    screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))

                n_surf = font_small.render(f"{item['name']} x{item['count']}", True, BLACK)
                screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))

                d_surf = font_tiny.render("點擊賣出 1 個", True, (80, 80, 80))
                screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))

                p_surf = font_small.render(f"+${item['price']}", True, (50, 205, 50))
                screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))

                if hovered:
                    pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)

                y_offset += 75


def draw_game_over(screen, state):
    if state.get('money', 0) < 0:
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        screen.blit(s, (0, 0))

        res_surf = font_large.render("GAME OVER", True, RED)
        res_rect = res_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
        screen.blit(res_surf, res_rect)

        info_surf = font_small.render(f"你總共生存了 {state['day_count'] - 1} 天", True, WHITE)
        info_rect = info_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        screen.blit(info_surf, info_rect)






    secs = state['time_left'] % 60
    phase_str = "白天" if state['phase'] == "day" else "夜晚"
    phase_text = f"第 {state['day_count']} 回合 - {phase_str} ({mins:02d}:{secs:02d})"
    text_surf = font_large.render(phase_text, True, WHITE)
    screen.blit(text_surf, (40, 30))
    
    pet_stats = f"狗: {len(state.get('dogs',[]))}/10   繁榮度: {state.get('prosperity_score',0)}   農場等級: Lv{state.get('farm_level',1)}"
    pet_surf = font_small.render(pet_stats, True, (200, 200, 255))
    screen.blit(pet_surf, (40, 65))
    
    rent = 20 + (state["day_count"] - 1) * 10
    money_surf = font_small.render(f"資金: ${state['money']} (今晚租金: ${rent})", True, YELLOW)
    screen.blit(money_surf, (WIDTH - money_surf.get_width() - 40, 35))
    
    # Bottom Panel
    bottom_panel = pygame.Surface((WIDTH - 40, 50), pygame.SRCALPHA)
    pygame.draw.rect(bottom_panel, (0, 0, 0, 180), bottom_panel.get_rect(), border_radius=15)
    screen.blit(bottom_panel, (20, HEIGHT - 140))
    
    # Map Toggle Button
    toggle_rect = pygame.Rect(WIDTH // 2 - 100, 10, 200, 40)
    pygame.draw.rect(screen, (70, 70, 90), toggle_rect, border_radius=10)
    pygame.draw.rect(screen, (200, 200, 200), toggle_rect, 2, border_radius=10)
    zone_text = "前往佈置區 ➡️" if active_zone == "farm" else "⬅️ 返回農場區"
    zone_surf = font_small.render(zone_text, True, WHITE)
    screen.blit(zone_surf, (toggle_rect.centerx - zone_surf.get_width()//2, toggle_rect.centery - zone_surf.get_height()//2))
    
    msg = state.get("last_msg", "")
    if msg:
        msg_surf = font_large.render(msg, True, (255, 200, 200))
        screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, HEIGHT - 135))
        
    help_text = "[空白]: 進入夜晚  [B]: 打開商店  [WASD/右鍵]: 移動視角"
    help_surf = font_tiny.render(help_text, True, (200, 200, 200))
    screen.blit(help_surf, (WIDTH//2 - help_surf.get_width()//2, HEIGHT - 20))
    
    if state.get("debug_scale_mode"):
        from src.config import SPRITE_SCALES
        keys_list = list(SPRITE_SCALES.keys())
        idx = state.get("debug_scale_idx", 0)
        if idx < len(keys_list):
            k = keys_list[idx]
            w, h = SPRITE_SCALES[k]
            debug_txt = font_small.render(f"[F9] Debug - {k} (W: {w:.1f}, H: {h:.1f}). [TAB] Next | [-/=] Width | [[/]] Height | [F10] Print", True, (0, 255, 0))
            pygame.draw.rect(screen, (0, 0, 0, 180), (8, 8, debug_txt.get_width()+4, debug_txt.get_height()+4))
            screen.blit(debug_txt, (10, 10))
        
    # Shop Button
    shop_rect = pygame.Rect(WIDTH - 150, 10, 130, 40)
    pygame.draw.rect(screen, (70, 70, 90), shop_rect, border_radius=10)
    pygame.draw.rect(screen, (200, 200, 200), shop_rect, 2, border_radius=10)
    shop_surf = font_small.render("🛒 商店 (B)", True, WHITE)
    screen.blit(shop_surf, (shop_rect.centerx - shop_surf.get_width()//2, shop_rect.centery - shop_surf.get_height()//2))
    

    tool_text = f"裝備中: {TOOL_NAMES.get(current_tool, current_tool)}" if current_tool else "一般模式 (點擊右鍵/ESC取消裝備)"
    indicator = font_small.render(tool_text, True, WHITE)
    screen.blit(indicator, (WIDTH - indicator.get_width() - 40, HEIGHT - 85))
    

def draw_shop(screen, state, shop_open, active_tab, mouse_pos):
    if not shop_open:
        return
    shop_surf = pygame.Surface((WIDTH, HEIGHT))
    shop_surf.set_alpha(150)
    shop_surf.fill(BLACK)
    screen.blit(shop_surf, (0, 0))
    
    shop_w = 1180
    shop_h = 700
    shop_x = (WIDTH - shop_w) // 2
    shop_y = (HEIGHT - shop_h) // 2
    shop_rect = pygame.Rect(shop_x, shop_y, shop_w, shop_h)
    
    bg_img = images.get("shop_bg")
    if bg_img:
        screen.blit(pygame.transform.scale(bg_img, (shop_w, shop_h)), shop_rect.topleft)
    else:
        pygame.draw.rect(screen, (245, 245, 250), shop_rect, border_radius=15)
        
    is_sell = active_tab == "sell"
    
    left_page_x = shop_x + 90
    left_page_w = 400
    right_page_x = shop_x + 675
    right_page_w = 400
    
    tab_buy = pygame.Rect(left_page_x, shop_y + 110, left_page_w, 45)
    tab_sell = pygame.Rect(right_page_x, shop_y + 110, right_page_w, 45)
    
    # Patch out the "SETTINGS" word from the background image
    patch_rect = pygame.Rect(left_page_x, shop_y + 80, left_page_w, 80)
    pygame.draw.rect(screen, (220, 185, 138), patch_rect)
    
    pygame.draw.rect(screen, BLUE if not is_sell else GRAY, tab_buy, border_radius=10)
    pygame.draw.rect(screen, BLUE if is_sell else GRAY, tab_sell, border_radius=10)
    
    tb_surf = font_small.render("購買道具", True, WHITE)
    ts_surf = font_small.render("出售作物", True, WHITE)
    screen.blit(tb_surf, (tab_buy.centerx - tb_surf.get_width()//2, tab_buy.centery - tb_surf.get_height()//2))
    screen.blit(ts_surf, (tab_sell.centerx - ts_surf.get_width()//2, tab_sell.centery - ts_surf.get_height()//2))
    
    if not is_sell:
        sub_w = (left_page_w - 30) // 4
        tab_seed = pygame.Rect(left_page_x, shop_y + 165, sub_w, 30)
        tab_def = pygame.Rect(left_page_x + sub_w + 10, shop_y + 165, sub_w, 30)
        tab_pet = pygame.Rect(left_page_x + (sub_w + 10)*2, shop_y + 165, sub_w, 30)
        tab_tool = pygame.Rect(left_page_x + (sub_w + 10)*3, shop_y + 165, sub_w, 30)
        
        pygame.draw.rect(screen, (100, 150, 255) if active_tab == "seed" else (200,200,200), tab_seed, border_radius=5)
        pygame.draw.rect(screen, (100, 150, 255) if active_tab == "def" else (200,200,200), tab_def, border_radius=5)
        pygame.draw.rect(screen, (100, 150, 255) if active_tab == "pet" else (200,200,200), tab_pet, border_radius=5)
        pygame.draw.rect(screen, (100, 150, 255) if active_tab == "tool" else (200,200,200), tab_tool, border_radius=5)
        
        sub1 = font_tiny.render("種子", True, BLACK)
        tabs = [
            {"id": "seed", "name": "種子"},
            {"id": "def", "name": "防禦"},
            {"id": "pet", "name": "景觀"}
        ]
        tab_w = (left_page_w - 10) // 3
        for i, tab in enumerate(tabs):
            tab_rect = pygame.Rect(left_page_x + i * (tab_w + 5), shop_y + 165, tab_w, 30)
            color = (100, 150, 255) if active_tab == tab["id"] else (200, 200, 200)
            pygame.draw.rect(screen, color, tab_rect, border_radius=5)
            txt = font_tiny.render(tab["name"], True, BLACK)
            screen.blit(txt, (tab_rect.centerx - txt.get_width()//2, tab_rect.centery - txt.get_height()//2))
        
        items = []
        if active_tab == "seed":
            items = [
                {"id": "radish", "name": "白蘿蔔種子", "price": 30, "desc": f"1天成熟，賣出 $50 (需要等級 1)"},
                {"id": "carrot", "name": "胡蘿蔔種子", "price": 100, "desc": f"2天成熟，賣出 $250 (需要等級 2)"},
                {"id": "pumpkin", "name": "魔法南瓜種子", "price": 300, "desc": f"3天成熟，賣出 $1000 (需要等級 3)"}
            ]
        elif active_tab == "def":
            items = [
                {"id": "fence", "name": "木圍欄", "price": "1 木材", "desc": "實體障礙，需木材"},
                {"id": "trap", "name": "捕獸夾", "price": 50, "desc": "對敵人造成傷害"},
                {"id": "dog", "name": "看門狗", "price": "FREE" if state.get("free_dog") else 200, "desc": "主動攻擊附近的敵人"}
            ]
        elif active_tab == "pet":
            items = [
                {"id": "stone_path", "name": "石板路", "price": 20, "desc": "繁榮度 +5"},
                {"id": "flower", "name": "鮮花盆栽", "price": 50, "desc": "繁榮度 +15"},
                {"id": "bench", "name": "木製長椅", "price": 100, "desc": "繁榮度 +35"},
                {"id": "fountain", "name": "小型噴泉", "price": 300, "desc": "繁榮度 +120"}
            ]
            
        left_items = items[:(len(items)+1)//2]
        right_items = items[(len(items)+1)//2:]
        
        for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 210), (right_items, right_page_x, shop_y + 170)]:
            y_offset = start_y
            for item in page_items:
                card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                card_surf = pygame.Surface((left_page_w, 65), pygame.SRCALPHA)
                pygame.draw.rect(card_surf, (255, 255, 255, 100), card_surf.get_rect(), border_radius=10)
                screen.blit(card_surf, card_rect.topleft)
                
                img = images.get(item["id"])
                if img:
                    screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))
                else:
                    pygame.draw.rect(screen, (220, 220, 220), (card_rect.x + 10, card_rect.y + 12, 40, 40), border_radius=5)
                    fb_text = font_tiny.render(item["name"][:2], True, (100, 100, 100))
                    screen.blit(fb_text, (card_rect.x + 30 - fb_text.get_width()//2, card_rect.y + 32 - fb_text.get_height()//2))
                    
                n_surf = font_small.render(item["name"], True, BLACK)
                screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))
                
                d_surf = font_tiny.render(item["desc"], True, (80, 80, 80))
                screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))
                
                p_str = f"${item['price']}" if isinstance(item['price'], int) else str(item['price'])
                p_surf = font_small.render(p_str, True, YELLOW if item['price'] != "FREE" else RED)
                screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))
                
                if card_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)
                
                y_offset += 75
    else:
        grades = ["normal", "rare", "epic", "legendary"]
        grades_tw = {"normal": "一般", "rare": "稀有", "epic": "史詩", "legendary": "傳奇"}
        multipliers = {"normal": 1, "rare": 2, "epic": 3, "legendary": 5}
        
        sellable = []
        for c_id, c_name in [("radish", "白蘿蔔"), ("carrot", "胡蘿蔔"), ("pumpkin", "魔法南瓜")]:
            base_price = CROP_INFO[c_id]["yield"] if c_id in CROP_INFO else 100
            for grade in grades:
                count = state["inventory"].get(c_id, {}).get(grade, 0)
                if count > 0:
                    sellable.append({"id": c_id, "name": f"{c_name} ({grades_tw[grade]})", "count": count, "price": base_price * multipliers[grade], "grade": grade})
                    
        left_items = sellable[:6]
        right_items = sellable[6:12]
        
        for page_items, page_x, start_y in [(left_items, left_page_x, shop_y + 170), (right_items, right_page_x, shop_y + 170)]:
            y_offset = start_y
            for item in page_items:
                card_rect = pygame.Rect(page_x, y_offset, left_page_w, 65)
                card_surf = pygame.Surface((left_page_w, 65), pygame.SRCALPHA)
                pygame.draw.rect(card_surf, (255, 255, 255, 100), card_surf.get_rect(), border_radius=10)
                screen.blit(card_surf, card_rect.topleft)
                
                img = images.get(item["id"])
                if img:
                    screen.blit(pygame.transform.scale(img, (40, 40)), (card_rect.x + 10, card_rect.y + 12))
                
                n_surf = font_small.render(f"{item['name']} x{item['count']}", True, BLACK)
                screen.blit(n_surf, (card_rect.x + 60, card_rect.y + 10))
                
                d_surf = font_tiny.render("點擊賣出 1 個", True, (80, 80, 80))
                screen.blit(d_surf, (card_rect.x + 60, card_rect.y + 35))
                
                p_surf = font_small.render(f"+${item['price']}", True, (50, 205, 50))
                screen.blit(p_surf, (card_rect.right - 80, card_rect.centery - p_surf.get_height()//2))
                
                if card_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, BLUE, card_rect, 2, border_radius=10)
                
                y_offset += 75
        

def draw_game_over(screen, state):
    if state.get('money') < 0:
        s = pygame.Surface((WIDTH, HEIGHT))
        s.set_alpha(200)
        s.fill(BLACK)
        screen.blit(s, (0, 0))
        
        res_surf = font_large.render("GAME OVER", True, RED)
        res_rect = res_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
        screen.blit(res_surf, res_rect)
        
        info_surf = font_small.render(f"你總共生存了 {state['day_count'] - 1} 天", True, WHITE)
        info_rect = info_surf.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        screen.blit(info_surf, info_rect)

