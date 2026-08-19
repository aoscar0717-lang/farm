import sys
import os
import pygame
import time
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize pygame before loading modules
pygame.init()

from src.config import WIDTH, HEIGHT, MARGIN_TOP, MARGIN_BOTTOM, WORLD_W, WORLD_H, CELL_SIZE
from src.capstone_contract import new_game, apply_action, is_terminal
from src.assets import screen, get_bg_surfs, night_filter
from src.renderer import draw_board
from src.input_handler import handle_mouse_click, handle_keyboard_events
from src.tutorial import note_event, update_unlocks
from src.thought import get_contemplation_lines, reset_hold_session
from src.ui import draw_contemplation, draw_tutorial_sidebar

def log_action(msg):
    with open("log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

TICK_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(TICK_EVENT, 1000)

def play():
    state = new_game()
    clock = pygame.time.Clock()
    current_tool = "hoe"
    shop_open = False
    active_tab = "seed"
    active_zone = "farm"
    
    camera_x = (WORLD_W - WIDTH) // 2
    camera_y = (WORLD_H - HEIGHT) // 2
    _initial_camera = (camera_x, camera_y)

    pygame.mouse.get_rel()

    last_night_tick = 0
    night_tick_delay = 33
    night_start_time = None   # time.time() when night phase began
    NIGHT_FADE_DURATION = 2.0  # seconds for night to fully darken

    # -- 思索模式 (contemplation mode) -----------------------------------
    # Holding F pauses the simulation (crops/enemies/day timer) and dims
    # the screen while a short, situational hint is shown. See
    # src/tutorial.py for what gets shown and why -- nothing here decides
    # tutorial *content*, this just wires the F key to it.
    f_held = False
    f_held_since = None
    CONTEMPLATION_FADE_DURATION = 0.25
    contemplation_filter = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    contemplation_filter.fill((5, 5, 15))

    import time

    # Trigger background load
    get_bg_surfs()

    running = True
    while running:
        old_zone = active_zone
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break
                
            if event.type == TICK_EVENT:
                # Holding F pauses the simulation -- see the f_held block below.
                if not is_terminal(state) and not f_held:
                    state = apply_action(state, "tick")

            if event.type == pygame.MOUSEBUTTONDOWN and not f_held:
                log_action(f"Click at {mouse_pos}, tool={current_tool}, zone={active_zone}, cam=({camera_x},{camera_y})")
                state, current_tool, shop_open, active_tab, active_zone = handle_mouse_click(
                    state, event, current_tool, shop_open, active_tab, camera_x, camera_y, active_zone
                )
                log_action(f"After click: tool={current_tool}, msg={state.get('last_msg')}")
                                
            elif event.type == pygame.KEYDOWN:
                log_action(f"Key pressed: {pygame.key.name(event.key)}")
                if event.key == pygame.K_0:
                    state["debug_show_grid"] = not state.get("debug_show_grid", False)
                elif state.get("debug_scale_mode"):
                    from src.config import SPRITE_SCALES
                    k = list(SPRITE_SCALES.keys())[state.get("debug_scale_idx", 0)]
                    w, h = SPRITE_SCALES[k]
                    if event.key == pygame.K_TAB:
                        idx = state.get("debug_scale_idx", 0)
                        keys_list = list(SPRITE_SCALES.keys())
                        state["debug_scale_idx"] = (idx + 1) % len(keys_list)
                    elif event.key == pygame.K_MINUS: SPRITE_SCALES[k] = (round(w-0.1, 1), h)
                    elif event.key == pygame.K_EQUALS: SPRITE_SCALES[k] = (round(w+0.1, 1), h)
                    elif event.key == pygame.K_LEFTBRACKET: SPRITE_SCALES[k] = (w, round(h-0.1, 1))
                    elif event.key == pygame.K_RIGHTBRACKET: SPRITE_SCALES[k] = (w, round(h+0.1, 1))
                    elif event.key == pygame.K_F10:
                        print("Current SPRITE_SCALES:")
                        for key, val in SPRITE_SCALES.items():
                            print(f'    "{key}": {val},')
                else:
                    state, current_tool, shop_open, active_zone = handle_keyboard_events(
                        state, event, current_tool, shop_open, active_zone
                    )

        keys_pressed = pygame.key.get_pressed()

        # F is a hold-to-enter / release-to-exit toggle, not a single
        # keypress -- continuous polling (like WASD below) is the correct
        # way to detect "held", KEYDOWN/KEYUP would double-fire on repeat.
        f_held = keys_pressed[pygame.K_f]
        if f_held and f_held_since is None:
            f_held_since = time.time()
        elif not f_held:
            if f_held_since is not None:
                # F was just released -- clear "what was last shown" so the
                # next press always counts as a fresh look (see thought.py's
                # reset_hold_session docstring for why this matters for the
                # seen_count tiered-text mechanism).
                reset_hold_session(state)
            f_held_since = None

        keys_dict = {
            pygame.K_w: keys_pressed[pygame.K_w],
            pygame.K_UP: keys_pressed[pygame.K_UP],
            pygame.K_s: keys_pressed[pygame.K_s],
            pygame.K_DOWN: keys_pressed[pygame.K_DOWN],
            pygame.K_a: keys_pressed[pygame.K_a],
            pygame.K_LEFT: keys_pressed[pygame.K_LEFT],
            pygame.K_d: keys_pressed[pygame.K_d],
            pygame.K_RIGHT: keys_pressed[pygame.K_RIGHT],
        }
        
        mouse_buttons = pygame.mouse.get_pressed()
        mouse_rel = pygame.mouse.get_rel() if mouse_buttons[2] else (0, 0)
        if not mouse_buttons[2]:
            pygame.mouse.get_rel() # clear relative movement
        if old_zone != active_zone:
            # Farm and decor are separate maps now, each with its own (0,0)
            # origin -- switching zones re-centers the camera on the newly
            # entered map instead of jumping to an offset within one shared
            # coordinate line.
            camera_x = (WORLD_W - WIDTH) // 2
            camera_y = (WORLD_H - HEIGHT) // 2
            note_event(state, "zone_switched")

        from src.input_handler import update_camera
        camera_x, camera_y = update_camera(
            camera_x, camera_y,
            mouse_buttons[2], mouse_rel, keys_dict,
            WORLD_W, WORLD_H, WIDTH, HEIGHT, active_zone
        )
        if (camera_x, camera_y) != _initial_camera:
            note_event(state, "camera_moved")

        # Grid cell the mouse is hovering, in the same units/snap the click
        # handler and renderer's placement preview already use -- this is
        # what lets 思索模式 hints react to *where* the cursor is, not just
        # which tool/zone is active. None while the shop covers the world.
        if mouse_pos and not shop_open:
            hover_world_x = mouse_pos[0] + camera_x
            hover_world_y = mouse_pos[1] + camera_y
            _hover_grid_px = CELL_SIZE * 10
            hover_pos = (
                int(hover_world_x // _hover_grid_px) * 10,
                int(hover_world_y // _hover_grid_px) * 10,
            )
        else:
            hover_pos = None

        # Tutorial progress must update every frame, not just while F is
        # held -- otherwise the Sidebar (which is meant to show live ✓
        # marks the instant a task is really done) would only refresh when
        # the player happens to hold F, which defeats "任務完成要即時更新".
        # update_unlocks() is documented as cheap (dict lookups + list
        # lengths), so doing it unconditionally every frame is fine.
        # thought.py's own internal call inside get_contemplation_lines is
        # left in place too -- update_unlocks is idempotent (an already-
        # latched step just gets skipped), so calling it from both places
        # has no duplicate side effect, just redundant safety.
        update_unlocks(state)

        # Holding F pauses enemy/night ticking too, same reasoning as the
        # TICK_EVENT gate above.
        if state["phase"] == "night" and not is_terminal(state) and not f_held:
            current_time = pygame.time.get_ticks()
            if current_time - last_night_tick > night_tick_delay:
                state = apply_action(state, "night_tick")
                last_night_tick = current_time

        screen.fill((0, 0, 0))
        from src.renderer import draw_board
        draw_board(screen, state, current_tool, camera_x, camera_y, mouse_pos, shop_open, active_tab, active_zone)
        
        if state["phase"] == "night":
            # Smooth fade-in for night filter
            if night_start_time is None:
                night_start_time = time.time()
            elapsed = time.time() - night_start_time
            fade_ratio = min(1.0, elapsed / NIGHT_FADE_DURATION)
            night_filter.set_alpha(int(150 * fade_ratio))
            screen.blit(night_filter, (0, 0))
        else:
            night_start_time = None  # Reset when day begins

        # 思索模式：dim the (still-visible, just paused) world and show a
        # short, situational hint. F now also works while the shop is open
        # (section 五/八 of the Hover Thought upgrade -- Buy/Sell
        # tabs/item cards/prices are real, hoverable UI too, and get their
        # own Thought entries in thought.py rather than a separate tooltip
        # system). The screen-dimming filter is skipped while the shop is
        # open -- the shop's own semi-transparent overlay already dims the
        # world, so stacking a second dim filter on top would just double
        # up for no visual benefit -- but the Thought panel itself still
        # draws (on top of the shop, since draw_board -> draw_shop already
        # ran by this point), appearing instantly rather than fading in.
        if f_held:
            if not shop_open:
                elapsed = time.time() - f_held_since if f_held_since else 0.0
                fade_ratio = min(1.0, elapsed / CONTEMPLATION_FADE_DURATION)
                contemplation_filter.set_alpha(int(120 * fade_ratio))
                screen.blit(contemplation_filter, (0, 0))
            else:
                fade_ratio = 1.0
            if fade_ratio >= 1.0:
                # The fade-in fully completed (or the shop was already open,
                # which counts as an instant genuine hold) -- the player
                # genuinely held F long enough to read a line, not just
                # tapped the key.
                note_event(state, "f_thought_used")
            lines = get_contemplation_lines(
                state, active_zone, current_tool, shop_open, hover_pos, mouse_pos, active_tab,
            )
            draw_contemplation(screen, lines, fade_ratio)

        # 新手任務側欄：always visible (not gated on F), so progress is
        # readable at a glance the same way the hotbar/top panel are.
        # Suppressed while the shop is open -- its own overlay already
        # covers this screen region, same rule draw_contemplation follows.
        if not shop_open:
            draw_tutorial_sidebar(screen, state)

        pygame.display.flip()
        clock.tick(30)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    play()
