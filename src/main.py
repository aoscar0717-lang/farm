import sys
import os
import pygame
import time
from copy import deepcopy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize pygame before loading modules
pygame.init()

from src.config import WIDTH, HEIGHT, MARGIN_TOP, MARGIN_BOTTOM, WORLD_W, WORLD_H
from src.capstone_contract import new_game, apply_action, is_terminal
from src.assets import screen, get_bg_surfs, night_filter
from src.renderer import draw_board
from src.input_handler import handle_mouse_click, handle_keyboard_events

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
    
    pygame.mouse.get_rel()
    
    last_night_tick = 0
    night_tick_delay = 33
    night_start_time = None   # time.time() when night phase began
    NIGHT_FADE_DURATION = 2.0  # seconds for night to fully darken
    
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
                if not is_terminal(state):
                    state = apply_action(state, "tick")
                
            if event.type == pygame.MOUSEBUTTONDOWN:
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
            if active_zone == "decor":
                camera_x = 50 * 32  # Snap to decor map start
            else:
                camera_x = 0  # Snap to farm map start
                
        from src.input_handler import update_camera
        camera_x, camera_y = update_camera(
            camera_x, camera_y, 
            mouse_buttons[2], mouse_rel, keys_dict, 
            WORLD_W, WORLD_H, WIDTH, HEIGHT, active_zone
        )
            
        if state["phase"] == "night" and not is_terminal(state):
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
            
        pygame.display.flip()
        clock.tick(30)
        
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    play()
