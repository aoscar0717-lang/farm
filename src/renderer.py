import pygame
import time
from src.config import *
from src.assets import images, night_filter, get_bg_surfs, sprite_loader
from src.ui import draw_hud, draw_shop, draw_game_over
from src.capstone_contract import is_terminal, fence_damage_state, DECOR_MAX_HP
from src import ui_layout

def is_cell_occupied(zone, gx, gy):
    pos = (gx, gy)
    if pos in zone.get("crops", []): return True
    if any(f[0] == gx and f[1] == gy for f in zone.get("fences", [])): return True
    if pos in zone.get("trees", []): return True


def _screen_coords(gx, gy, camera_x, camera_y):
    """World-grid -> screen-pixel conversion. Phase 5: this used to be a
    closure (get_screen_coords) defined fresh inside draw_board every
    frame; pulled out to module level, with camera_x/camera_y passed
    explicitly, so it can be shared by draw_board's now-split-out
    per-layer render functions below without each of them needing their
    own copy or a shared nested closure."""
    return gx * CELL_SIZE - camera_x, gy * CELL_SIZE - camera_y


# ---------------------------------------------------------------------------
# Phase 5: draw_board() used to be a single ~700-line function covering every
# world-space layer (background, trees, rocks, farmland, crops, fences,
# traps, decorations, dogs, thief, boar, tool preview, grid overlay,
# building-task ghosts, hotbar, harvestable glow, minimap) plus the HUD/shop
# calls at the end. Split into one function per layer, in the same order
# they used to render in -- this is a mechanical extraction (every line of
# drawing logic is unchanged), not a redesign: draw_board() below is now
# just the ordered list of layers, which makes "where does X get drawn"
# and "does layer A run before or after layer B" answerable by reading the
# orchestrator instead of scanning hundreds of lines.
# ---------------------------------------------------------------------------

def _draw_background(screen, active_zone, camera_x, camera_y):
    bg_left, bg_right = get_bg_surfs()
    bg = bg_left if active_zone == "farm" else bg_right
    pw, ph = bg.get_size()
    for y in range(-(camera_y % ph), HEIGHT, ph):
        for x in range(-(camera_x % pw), WIDTH, pw):
            screen.blit(bg, (x, y))


def _draw_trees(screen, zstate, camera_x, camera_y):
    # Each tree has its own animation phase for natural look
    for tx, ty in zstate.get("trees", []):
        phase_offset = (tx * 7 + ty * 13) % 40 / 10.0  # unique phase per tree
        anim_frame = int((time.time() + phase_offset) * 3) % 4
        tree_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_tree_01_strip4.png", 0, anim_frame, 32, 34, (int(ITEM_PX * SPRITE_SCALES["tree"][0]), int(ITEM_PX * SPRITE_SCALES["tree"][1])))
        screen_x, screen_y = _screen_coords(tx, ty, camera_x, camera_y)
        if screen_x is None: continue
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            if tree_img:
                screen.blit(tree_img, (screen_x - ITEM_PX // 4, screen_y - int(ITEM_PX * 1.25)))
            else:
                rect = pygame.Rect(screen_x, screen_y, ITEM_PX, ITEM_PX)
                pygame.draw.rect(screen, (139, 69, 19), (rect.centerx - 10, rect.bottom - 30, 20, 30))
                pygame.draw.circle(screen, (34, 139, 34), (rect.centerx, rect.bottom - 40), 25)


def _draw_rocks(screen, zstate, camera_x, camera_y):
    rock_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Tileset/spr_tileset_sunnysideworld_16px.png", 61, 2, 16, 16, (int(ITEM_PX * SPRITE_SCALES["rock"][0]), int(ITEM_PX * SPRITE_SCALES["rock"][1])))
    for rx, ry in zstate.get("rocks", []):
        screen_x, screen_y = _screen_coords(rx, ry, camera_x, camera_y)
        if screen_x is None: continue
        if screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            if rock_img:
                screen.blit(rock_img, (screen_x, screen_y))
            else:
                rect = pygame.Rect(screen_x + 10, screen_y + 30, ITEM_PX - 20, ITEM_PX - 30)
                pygame.draw.ellipse(screen, (105, 105, 105), rect)


_TILLED_DIRT_PATH = "Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Tilled_Dirt.png"


def _draw_farmland(screen, zstate, camera_x, camera_y):
    # Sprout Lands Tilled_Dirt sprite (col=3, row=1 = center fully-tilled tile)
    _tilled_img = sprite_loader.get_sprite(
        _TILLED_DIRT_PATH,
        3, 1, 16, 16, (ITEM_PX, ITEM_PX)
    )
    for fx, fy in zstate.get("farmland", []):
        cx, cy = _screen_coords(fx, fy, camera_x, camera_y)
        if cx is None: continue
        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT: continue
        if _tilled_img:
            screen.blit(_tilled_img, (cx, cy))
        else:
            rect = pygame.Rect(cx, cy, ITEM_PX, ITEM_PX)
            pygame.draw.rect(screen, (110, 72, 38), rect)
            inner = rect.inflate(-4, -4)
            pygame.draw.rect(screen, (90, 56, 24), inner, 1)


def _draw_crops(screen, zstate, state, camera_x, camera_y):
    for crop in zstate["crops"]:
        data = zstate["crop_data"].get(crop)
        if not data: continue
        cx, cy = _screen_coords(crop[0], crop[1], camera_x, camera_y)
        if cx is None: continue

        if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT:
            continue

        c_type = data.get("type", "radish")

        # Calculate visual stage based on days passed + current day progress
        max_stage = data.get("max_stage", 5)
        current_day_progress = 0.0
        if state["phase"] == "day" and data["stage"] < max_stage:
            current_day_progress = max(0.0, min(1.0, (120 - state.get("time_left", 120)) / 120.0))
        elif data["stage"] >= max_stage:
            current_day_progress = 0.0

        total_progress = min(max_stage, data["stage"] + current_day_progress)
        cstage = int((total_progress / max(1, max_stage)) * 5)
        cstage = max(0, min(5, cstage))

        crop_img_path = f"Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops/{c_type}_{cstage:02d}.png"
        crop_img = sprite_loader.get_image(crop_img_path, (int(ITEM_PX * SPRITE_SCALES["crop"][0]), int(ITEM_PX * SPRITE_SCALES["crop"][1])))

        if crop_img:
            cw, ch = crop_img.get_size()
            offset_x = (ITEM_PX - cw) // 2
            offset_y = (ITEM_PX - ch) // 2
            screen.blit(crop_img, (cx + offset_x, cy + offset_y))
        else:
            # Fallback
            c_color = RED if c_type == "radish" else (WHITE if c_type == "turnip" else ((255, 165, 0) if c_type == "carrot" else (200, 200, 100)))
            size_ratio = 0.3 + 0.7 * (data["stage"] / max(1, data["max_stage"]))
            c_size = int((ITEM_PX // 2) * size_ratio)
            pygame.draw.circle(screen, c_color, (cx + ITEM_PX//2, cy + ITEM_PX//2), c_size)

        # Draw Progress Bar for Crops
        bar_w = ITEM_PX - 20
        bar_h = 6
        bar_x = cx + 10
        bar_y = cy + ITEM_PX - 12
        pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h))

        stage = data["stage"]
        max_stage = data["max_stage"]
        if stage < max_stage and state["phase"] == "day":
            day_progress = (120 - state["time_left"]) / 120.0
        else:
            day_progress = 0

        if stage >= max_stage: total_progress = 1.0
        else: total_progress = (stage + day_progress) / max_stage

        fill_w = int(bar_w * total_progress)
        color = (50, 205, 50) if stage < max_stage else (255, 215, 0)
        if fill_w > 0:
            pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h))


def _draw_scarecrows(screen, zstate, camera_x, camera_y):
    scarecrow_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (int(ITEM_PX * SPRITE_SCALES["scarecrow"][0]), int(ITEM_PX * SPRITE_SCALES["scarecrow"][1])))
    for sx, sy in zstate.get("scarecrows", []):
        cx, cy = _screen_coords(sx, sy, camera_x, camera_y)
        if cx is None: continue
        if scarecrow_img:
            screen.blit(scarecrow_img, (cx, cy))


def _draw_fences(screen, zstate, active_zone, camera_x, camera_y):
    # Wang tile bitmask: pick tile based on N/E/S/W neighbors
    # Sprout Lands Fences.png is 4x4 (64x64px, each tile 16x16)
    # Tile layout (col, row):
    #   Solo = (0,0), H-left-end=(1,0), H-right-end=(3,0), H-middle=(2,0)
    #   V-top-end=(0,1), V-bottom-end=(0,3), V-middle=(0,2)
    #   Corner TL=(1,1), Corner TR=(3,1), Corner BL=(1,3), Corner BR=(3,3)
    #   T-junction L=(0,2), R=(3,2), T=(1,1), B=(1,3)  — simplified cross=(1,2)
    _fence_path = "Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Fences.png"
    fence_set = {(f[0], f[1]) for f in zstate.get("fences", [])}

    def _fence_tile(row, col):
        return sprite_loader.get_sprite(_fence_path, row, col, 16, 16, (ITEM_PX, ITEM_PX))

    # Fence combat feedback (farm zone only -- the thief is the only thing
    # that fights fences; decor's boar keeps its own old per-tick behavior
    # untouched, so there's nothing new to visualize there).
    _attack_target = zstate.get("thief_attack_target_fence") if active_zone == "farm" else None
    _hit_flash_ticks = zstate.get("thief_hit_flash", 0) if active_zone == "farm" else 0

    for fx, fy, fhp in zstate.get("fences", []):
        screen_x, screen_y = _screen_coords(fx, fy, camera_x, camera_y)
        if screen_x is None: continue
        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT: continue

        # Check cardinal neighbors (grid coords aligned to ITEM_SIZE)
        N = (fx, fy - ITEM_SIZE) in fence_set
        S = (fx, fy + ITEM_SIZE) in fence_set
        E = (fx + ITEM_SIZE, fy) in fence_set
        W = (fx - ITEM_SIZE, fy) in fence_set

        # Bitmask: N=8, E=4, S=2, W=1
        mask = (N << 3) | (E << 2) | (S << 1) | W

        # Map bitmask to (row, col) in Fences.png
        FENCE_MAP = {
            0b0000: (3, 0),  # 0: isolated
            0b0001: (3, 3),  # 1: W only
            0b0010: (0, 0),  # 2: S only
            0b0011: (0, 3),  # 3: S, W
            0b0100: (3, 1),  # 4: E only
            0b0101: (3, 2),  # 5: E, W
            0b0110: (0, 1),  # 6: S, E
            0b0111: (0, 2),  # 7: S, E, W
            0b1000: (2, 0),  # 8: N only
            0b1001: (2, 3),  # 9: N, W
            0b1010: (1, 0),  # 10: N, S
            0b1011: (1, 3),  # 11: N, S, W
            0b1100: (2, 1),  # 12: N, E
            0b1101: (2, 2),  # 13: N, E, W
            0b1110: (1, 1),  # 14: N, S, E
            0b1111: (1, 2),  # 15: N, S, E, W
        }
        row, col = FENCE_MAP.get(mask, (3, 0))
        fence_img = _fence_tile(row, col)

        # --- Damage state (完整/受損/嚴重受損): intact/damaged/critical,
        # driven purely by fhp via the same fence_damage_state() helper
        # capstone_contract.py uses -- so the visual tier and the actual
        # gameplay tier can never disagree.
        dmg_state = fence_damage_state(fhp)

        # Is *this* fence the one currently being actively hit this frame?
        is_being_hit = (
            _hit_flash_ticks > 0
            and _attack_target is not None
            and _attack_target[0] == fx and _attack_target[1] == fy
        )

        # --- 敲擊感 (impact feel): a sharp jitter for the few ticks right
        # after a hit lands, plus a much smaller constant "unstable" wobble
        # once critically damaged so the state still reads at a glance
        # between hits, not just at the instant of impact.
        shake_x = shake_y = 0
        if is_being_hit:
            seed = int(time.time() * 60) + fx * 3 + fy * 7
            shake_x = (seed % 5) - 2
            shake_y = ((seed // 5) % 5) - 2
        elif dmg_state == "critical":
            wob = int(time.time() * 6 + fx * 0.5 + fy * 0.3)
            shake_x = (wob % 3) - 1

        draw_x, draw_y = screen_x + shake_x, screen_y + shake_y

        if fence_img:
            screen.blit(fence_img, (draw_x, draw_y))
        else:
            pygame.draw.rect(screen, (139, 69, 19), (draw_x + 5, draw_y + 5, ITEM_PX - 10, ITEM_PX - 10))

        # Damage tint + cracks -- darker/redder the worse it gets, so the
        # player can tell "this one's about to go" without a separate HP
        # bar cluttering every fence tile.
        if dmg_state == "damaged":
            overlay = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            overlay.fill((90, 45, 20, 70))
            screen.blit(overlay, (draw_x, draw_y))
        elif dmg_state == "critical":
            overlay = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            overlay.fill((60, 20, 10, 130))
            screen.blit(overlay, (draw_x, draw_y))
            crack = (25, 12, 5)
            pygame.draw.line(screen, crack, (draw_x + 3, draw_y + 3), (draw_x + ITEM_PX - 5, draw_y + ITEM_PX - 5), 2)
            pygame.draw.line(screen, crack, (draw_x + ITEM_PX - 5, draw_y + 5), (draw_x + 5, draw_y + ITEM_PX - 3), 2)

        # White hit-flash the moment(s) a blow actually lands.
        if is_being_hit:
            flash = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 90))
            screen.blit(flash, (draw_x, draw_y))

    # 摧毀動畫 (collapse animation): a fence that hit 0 HP doesn't just pop
    # out of existence -- capstone_contract.py hands it off to
    # collapsing_fences for a short countdown before actually removing it
    # (see _tick_collapsing_fences), and we draw that countdown here as a
    # shrinking, sinking, fading silhouette so the removal reads as a
    # collapse rather than a disappearance.
    _COLLAPSE_ANIM_TICKS = 12  # keep in sync with capstone_contract.py's collapsing_fences seed value
    for cx, cy, ticks_left in zstate.get("collapsing_fences", []):
        screen_x, screen_y = _screen_coords(cx, cy, camera_x, camera_y)
        if screen_x is None: continue
        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT: continue

        progress = 1.0 - max(0.0, min(1.0, ticks_left / _COLLAPSE_ANIM_TICKS))
        scale = max(0.15, 1.0 - progress * 0.8)
        alpha = max(0, int(255 * (1.0 - progress)))
        sink = int(progress * (ITEM_PX * 0.4))

        collapse_img = _fence_tile(3, 0)  # broken/isolated post stands in for rubble
        if collapse_img:
            w = max(1, int(ITEM_PX * scale))
            h = max(1, int(ITEM_PX * scale))
            scaled = pygame.transform.scale(collapse_img, (w, h))
            scaled.set_alpha(alpha)
            screen.blit(scaled, (screen_x + (ITEM_PX - w) // 2, screen_y + (ITEM_PX - h) // 2 + sink))
        else:
            rubble = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            pygame.draw.rect(
                rubble, (90, 60, 30, alpha),
                (int(ITEM_PX * 0.2), int(ITEM_PX * 0.6) + sink, int(ITEM_PX * 0.6), int(ITEM_PX * 0.3)),
            )
            screen.blit(rubble, (screen_x, screen_y))


def _draw_traps(screen, zstate, camera_x, camera_y):
    trap_img = images.get("trap")
    for tx, ty in zstate.get("traps", []):
        screen_x, screen_y = _screen_coords(tx, ty, camera_x, camera_y)
        if screen_x is None: continue
        if trap_img:
            screen.blit(trap_img, (screen_x, screen_y))
        elif screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
            pygame.draw.rect(screen, (100, 100, 100), (screen_x + 10, screen_y + ITEM_PX - 20, ITEM_PX - 20, 20))
            pygame.draw.line(screen, (200, 0, 0), (screen_x + 20, screen_y + ITEM_PX - 10), (screen_x + ITEM_PX - 20, screen_y + ITEM_PX - 10), 3)


def _draw_decorations(screen, zstate, active_zone, camera_x, camera_y):
    # V1.1 balance fix: decorations now actually have durability (the boar
    # lands cooldown-gated hits on the hp field instead of one-shotting
    # whatever it arrives at -- see _night_tick_boar), so give that damage
    # a simple, existing-asset-friendly visual: a proportional shake +
    # darkening tint while damaged, plus a brief white flash on the exact
    # tick(s) a hit lands. No new sprites/tiers needed -- just effects
    # layered on top of whatever art already renders each decor type.
    _decor_attack_target = zstate.get("target_decor") if active_zone == "decor" else None
    _decor_hit_flash_ticks = zstate.get("boar_hit_flash", 0) if active_zone == "decor" else 0

    for d in zstate.get("decorations", []):
        dx, dy, dtype, hp = d
        base_x, base_y = _screen_coords(dx, dy, camera_x, camera_y)
        if base_x is None: continue

        damage_frac = max(0.0, min(1.0, 1.0 - (hp / DECOR_MAX_HP))) if DECOR_MAX_HP else 0.0
        is_being_hit = (
            _decor_hit_flash_ticks > 0
            and _decor_attack_target is not None
            and _decor_attack_target[0] == dx and _decor_attack_target[1] == dy
        )

        shake_x = shake_y = 0
        if is_being_hit:
            seed = int(time.time() * 60) + dx * 3 + dy * 7
            shake_x = (seed % 5) - 2
            shake_y = ((seed // 5) % 5) - 2
        elif damage_frac > 0:
            # Gentle constant wobble, scaling with how damaged it is, so a
            # damaged decoration still reads as "unstable" between hits.
            wob = int(time.time() * 6 + dx * 0.5 + dy * 0.3)
            shake_x = ((wob % 3) - 1) if damage_frac > 0.4 else 0

        screen_x, screen_y = base_x + shake_x, base_y + shake_y

        if dtype == "fountain":
                anim_frame = int(time.time() * 9) % 9
                windmill_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Other/spr_deco_windmill_strip9.png", 0, anim_frame, 112, 112, (int(ITEM_PX * SPRITE_SCALES["windmill"][0]), int(ITEM_PX * SPRITE_SCALES["windmill"][1])))
                if windmill_img:
                    screen.blit(windmill_img, (screen_x - ITEM_PX//2, screen_y - ITEM_PX))
                else:
                    pygame.draw.rect(screen, (150, 150, 255), (screen_x + 5, screen_y + 5, ITEM_PX - 10, ITEM_PX - 10))
        else:
            dec_img = images.get(dtype)
            if dec_img:
                screen.blit(dec_img, (screen_x, screen_y))
            elif screen_x + ITEM_PX > 0 and screen_x < WIDTH and screen_y + ITEM_PX > 0 and screen_y < HEIGHT:
                if dtype == "stone_path":
                    pygame.draw.rect(screen, (150, 150, 150), (screen_x, screen_y, ITEM_PX, ITEM_PX))
                elif dtype == "flower":
                    pygame.draw.rect(screen, (139, 69, 19), (screen_x + 10, screen_y + 20, ITEM_PX - 20, ITEM_PX - 20))
                    pygame.draw.circle(screen, (255, 105, 180), (screen_x + ITEM_PX // 2, screen_y + 10), 20)
                elif dtype == "bench":
                    pygame.draw.rect(screen, (205, 133, 63), (screen_x + 10, screen_y + 30, ITEM_PX - 20, 20))
                    pygame.draw.rect(screen, (139, 69, 19), (screen_x + 10, screen_y + 10, 10, 40))
                    pygame.draw.rect(screen, (139, 69, 19), (screen_x + ITEM_PX - 20, screen_y + 10, 10, 40))

        # Damage tint: darkens/reddens proportionally to how much HP has
        # been lost (no discrete tiers, unlike the fence's 3-tier system --
        # "不要擅自增加新的景觀升級系統" means keep this to a single simple
        # continuous effect rather than a whole new damage-state UI).
        if damage_frac > 0:
            overlay = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            overlay.fill((70, 25, 15, int(140 * damage_frac)))
            screen.blit(overlay, (screen_x, screen_y))

        # White hit-flash the moment(s) a blow actually lands.
        if is_being_hit:
            flash = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 90))
            screen.blit(flash, (screen_x, screen_y))

    # 景觀物摧毀動畫: mirrors the fence collapse animation -- a decoration
    # that hit 0 HP lingers in collapsing_decorations for a short countdown
    # (see _tick_collapsing_decorations) instead of vanishing outright.
    _DECOR_COLLAPSE_ANIM_TICKS = 12  # keep in sync with capstone_contract.py's collapsing_decorations seed value
    for cx, cy, cdtype, ticks_left in zstate.get("collapsing_decorations", []):
        screen_x, screen_y = _screen_coords(cx, cy, camera_x, camera_y)
        if screen_x is None: continue
        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT: continue

        progress = 1.0 - max(0.0, min(1.0, ticks_left / _DECOR_COLLAPSE_ANIM_TICKS))
        scale = max(0.15, 1.0 - progress * 0.8)
        alpha = max(0, int(255 * (1.0 - progress)))
        sink = int(progress * (ITEM_PX * 0.4))

        collapse_img = images.get(cdtype)
        if collapse_img:
            w = max(1, int(ITEM_PX * scale))
            h = max(1, int(ITEM_PX * scale))
            scaled = pygame.transform.scale(collapse_img, (w, h))
            scaled.set_alpha(alpha)
            screen.blit(scaled, (screen_x + (ITEM_PX - w) // 2, screen_y + (ITEM_PX - h) // 2 + sink))
        else:
            rubble = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            pygame.draw.rect(
                rubble, (110, 90, 90, alpha),
                (int(ITEM_PX * 0.2), int(ITEM_PX * 0.6) + sink, int(ITEM_PX * 0.6), int(ITEM_PX * 0.3)),
            )
            screen.blit(rubble, (screen_x, screen_y))

def _draw_dogs(screen, zstate, camera_x, camera_y):
    # 畫出守護動物
    import time
    anim_frame = int(time.time() * 4) % 4
    
    # 1. 🐕 看門狗
    dog_img = sprite_loader.get_sprite("Goldie pack_v1.1/Goldie pack_v02/Goldie_v02.png", 4, anim_frame, 32, 40, (int(ITEM_PX * SPRITE_SCALES["dog"][0]), int(ITEM_PX * SPRITE_SCALES["dog"][1])))
    for dx, dy in zstate.get("dogs", []):
        screen_x, screen_y = _screen_coords(dx, dy, camera_x, camera_y)
        if screen_x is None: continue
        if dog_img:
            screen.blit(dog_img, (screen_x - ITEM_PX//4, screen_y - ITEM_PX//4))
        else:
            pygame.draw.circle(screen, (205, 133, 63), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)

    # 2. 🐱 招財小貓
    cat_img = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png", 0, anim_frame, 16, 16, (int(ITEM_PX * SPRITE_SCALES["cat"][0]), int(ITEM_PX * SPRITE_SCALES["cat"][1])))
    for cx, cy in zstate.get("cats", []):
        screen_x, screen_y = _screen_coords(cx, cy, camera_x, camera_y)
        if screen_x is None: continue
        if cat_img:
            screen.blit(cat_img, (screen_x - ITEM_PX//6, screen_y - ITEM_PX//6))
        else:
            pygame.draw.circle(screen, (255, 215, 0), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)

    # 3. 🪿 暴躁警戒鵝
    goose_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_duck_01_strip4.png", 0, anim_frame, 16, 16, (int(ITEM_PX * SPRITE_SCALES["goose"][0]), int(ITEM_PX * SPRITE_SCALES["goose"][1])))
    for gx, gy in zstate.get("geese", []):
        screen_x, screen_y = _screen_coords(gx, gy, camera_x, camera_y)
        if screen_x is None: continue
        if goose_img:
            screen.blit(goose_img, (screen_x - ITEM_PX//6, screen_y - ITEM_PX//6))
        else:
            pygame.draw.circle(screen, (240, 240, 240), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)

    # 4. 🐑 棉花守護羊
    sheep_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_sheep_01_strip4.png", 0, anim_frame, 16, 16, (int(ITEM_PX * SPRITE_SCALES["sheep"][0]), int(ITEM_PX * SPRITE_SCALES["sheep"][1])))
    for sx, sy in zstate.get("sheeps", []):
        screen_x, screen_y = _screen_coords(sx, sy, camera_x, camera_y)
        if screen_x is None: continue
        if sheep_img:
            screen.blit(sheep_img, (screen_x - ITEM_PX//4, screen_y - ITEM_PX//4))
        else:
            pygame.draw.circle(screen, (220, 220, 230), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)

    # 5. 🐮 鐵壁戰鬥牛
    bull_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_cow_strip4.png", 0, anim_frame, 32, 32, (int(ITEM_PX * SPRITE_SCALES["bull"][0]), int(ITEM_PX * SPRITE_SCALES["bull"][1])))
    for bx, by in zstate.get("bulls", []):
        screen_x, screen_y = _screen_coords(bx, by, camera_x, camera_y)
        if screen_x is None: continue
        if bull_img:
            screen.blit(bull_img, (screen_x - ITEM_PX//3, screen_y - ITEM_PX//3))
        else:
            pygame.draw.circle(screen, (139, 69, 19), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)

    # 6. 🦉 夜行守護鳥
    owl_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_bird_01_strip4.png", 0, anim_frame, 16, 16, (int(ITEM_PX * SPRITE_SCALES["owl"][0]), int(ITEM_PX * SPRITE_SCALES["owl"][1])))
    for ox, oy in zstate.get("owls", []):
        screen_x, screen_y = _screen_coords(ox, oy, camera_x, camera_y)
        if screen_x is None: continue
        if owl_img:
            screen.blit(owl_img, (screen_x - ITEM_PX//6, screen_y - ITEM_PX//6))
        else:
            pygame.draw.circle(screen, (100, 149, 237), (screen_x + ITEM_PX // 2, screen_y + ITEM_PX // 2), ITEM_PX // 2)


def _draw_thief(screen, zstate, camera_x, camera_y):
    # Farm zone only -- zstate.get("thief_pos") is always None while
    # viewing the decor map, since that key never gets set there.

    if zstate.get("thief_pos") is not None:
        tx, ty = zstate["thief_pos"]
        screen_x, screen_y = _screen_coords(tx, ty, camera_x, camera_y)
        if screen_x is None: pass

        thief_dir_row = 0
        flip_x = False

        if zstate.get("thief_path"):
            target = zstate["thief_path"][0]
            dx = target[0] - tx
            dy = target[1] - ty
            if abs(dx) > abs(dy):
                thief_dir_row = 2 # Right
                if dx < 0: flip_x = True # Left
            else:
                if dy < 0: thief_dir_row = 1 # Up
                else: thief_dir_row = 0 # Down

        anim_frame = int(time.time() * 8) % 8
        thief_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Characters/Goblin/PNG/spr_walk_strip8.png", 0, anim_frame, 96, 64, (int(ITEM_PX * SPRITE_SCALES["goblin"][0]), int(ITEM_PX * SPRITE_SCALES["goblin"][1])))
        if thief_img:
            if flip_x:
                thief_img = pygame.transform.flip(thief_img, True, False)
            screen.blit(thief_img, (screen_x - ITEM_PX, screen_y - ITEM_PX))
        else:
            pygame.draw.circle(screen, RED, (screen_x + ITEM_PX//2, screen_y + ITEM_PX//2), ITEM_PX // 2)

        hp = zstate.get("thief_hp", 3)
        pygame.draw.rect(screen, RED, (screen_x, screen_y - 10, ITEM_PX, 6))


def _draw_boar(screen, zstate, camera_x, camera_y):
    # Decor zone only -- same reasoning as the thief above.
    if zstate.get("boar_pos"):
        bx, by = zstate["boar_pos"]
        screen_x, screen_y = _screen_coords(bx, by, camera_x, camera_y)
        if screen_x is None: pass

        boar_dir_row = 0
        flip_x = False

        if zstate.get("boar_path"):
            target = zstate["boar_path"][0]
            dx = target[0] - bx
            dy = target[1] - by
            if abs(dx) > abs(dy):
                boar_dir_row = 2
                if dx < 0: flip_x = True
            else:
                if dy < 0: boar_dir_row = 1
                else: boar_dir_row = 0

        anim_frame = int(time.time() * 6) % 4
        boar_img = sprite_loader.get_sprite("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_pig_01_strip4.png", 0, anim_frame, 32, 32, (int(ITEM_PX * SPRITE_SCALES["boar"][0]), int(ITEM_PX * SPRITE_SCALES["boar"][1])))
        if boar_img:
            if flip_x: boar_img = pygame.transform.flip(boar_img, True, False)
            # Tint it dark/black to look like a boar if possible, or just draw black circle if none
            screen.blit(boar_img, (screen_x - ITEM_PX//4, screen_y - ITEM_PX//2))
        else:
            pygame.draw.circle(screen, (50, 50, 50), (screen_x + ITEM_PX//2, screen_y + ITEM_PX//2), ITEM_PX // 2)

        hp = zstate.get("boar_hp", 5)
        pygame.draw.rect(screen, RED, (screen_x, screen_y - 10, ITEM_PX, 6))
        pygame.draw.rect(screen, (0, 255, 0), (screen_x, screen_y - 10, ITEM_PX * (hp / max(1, hp, 5)), 6))


def _draw_tool_preview(screen, state, zstate, current_tool, mouse_pos, shop_open, camera_x, camera_y):
    if state['phase'] == "day" and mouse_pos and not shop_open:
        mx, my = mouse_pos
        if current_tool is not None and my >= 0 and my < HEIGHT:
            # Snap cursor to ITEM_PX grid
            world_x = mx + camera_x
            world_y = my + camera_y
            ITEM_PX_grid = CELL_SIZE * 10
            snap_gx = int(world_x // ITEM_PX_grid) * 10
            snap_gy = int(world_y // ITEM_PX_grid) * 10
            screen_x, screen_y = _screen_coords(snap_gx, snap_gy, camera_x, camera_y)

            # Determine if placeable
            occupied = is_cell_occupied(zstate, snap_gx, snap_gy)
            if current_tool == "axe":
                placeable = (snap_gx, snap_gy) in zstate.get("trees", [])
            elif current_tool == "scythe":
                placeable = (snap_gx, snap_gy) in zstate.get("crops", [])
            elif current_tool == "pickaxe":
                placeable = (snap_gx, snap_gy) in zstate.get("rocks", [])
            elif current_tool == "shovel":
                placeable = occupied
            elif current_tool == "fence" and (snap_gx, snap_gy) in zstate.get("farmland", []):
                placeable = False
            else:
                placeable = not occupied

            # Draw a clean single highlight box
            frame_color = (80, 255, 80, 200) if placeable else (255, 60, 60, 200)
            s = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
            # Semi-transparent fill
            fill_alpha = 40 if placeable else 60
            s.fill((*frame_color[:3], fill_alpha))
            # Bold border
            pygame.draw.rect(s, (*frame_color[:3], 220), s.get_rect(), 3, border_radius=4)

            # Tool icon centered
            preview_img = images.get(current_tool)
            if preview_img:
                icon = pygame.transform.scale(preview_img, (36, 36))
                s.blit(icon, ((ITEM_PX - 36) // 2, (ITEM_PX - 36) // 2))
            else:
                tool_name = TOOL_NAMES.get(current_tool, current_tool)[:2]
                txt = font_small.render(tool_name, True, (255, 255, 255))
                s.blit(txt, (ITEM_PX//2 - txt.get_width()//2, ITEM_PX//2 - txt.get_height()//2))

            screen.blit(s, (screen_x, screen_y))


def _draw_tool_grid_overlay(screen, current_tool, shop_open, camera_x, camera_y):
    if current_tool is not None and not shop_open:
        # Draw ITEM_PX grid overlay
        grid_surf = pygame.Surface((WIDTH, HEIGHT - MARGIN_TOP - MARGIN_BOTTOM), pygame.SRCALPHA)
        start_x = - (camera_x % ITEM_PX)
        start_y = - (camera_y % ITEM_PX)
        for x in range(start_x, WIDTH, ITEM_PX):
            pygame.draw.line(grid_surf, (255, 255, 255, 40), (x, 0), (x, HEIGHT))
        for y in range(start_y, HEIGHT, ITEM_PX):
            pygame.draw.line(grid_surf, (255, 255, 255, 40), (0, y), (WIDTH, y))
        screen.blit(grid_surf, (0, MARGIN_TOP))


def _building_task_preview_image(task):
    """Resolve the preview/ghost image for one building_tasks entry.

    The only task types capstone_contract.py ever actually creates are:
    farmland, crop, decor, fence, trap, dog (see apply_action's
    till/plant_crop/build_decor/build_fence/place_trap/place_dog branches).
    "cat"/"goose"/"owl" are NOT real task types -- nothing ever appends a
    building_tasks entry with those type strings, so those branches used to
    be dead code here. This function replaces the old dog/cat/goose/owl/fence
    chain: it drops the three dead branches (their images["cat"] etc. entries
    and any other use of those keys elsewhere are untouched) and adds the
    four previously-missing real types (farmland/crop/decor/trap), so each
    now shows an actual preview of what's being built instead of falling
    back to the generic ghost rectangle.
    """
    t_type = task["type"]
    if t_type == "farmland":
        return sprite_loader.get_sprite(_TILLED_DIRT_PATH, 3, 1, 16, 16, (ITEM_PX, ITEM_PX))
    elif t_type == "crop":
        return images.get(task.get("crop_type"))
    elif t_type == "decor":
        return images.get(task.get("decor_type"))
    elif t_type == "fence":
        return images.get("fence")
    elif t_type == "trap":
        return images.get("trap")
    elif t_type in ["dog", "cat", "goose", "sheep", "bull", "owl"]:
        return images.get(t_type)
    return None


def _draw_building_tasks(screen, zstate, camera_x, camera_y):
    # 畫建造中的項目（帶真實進度條）
    for task in zstate.get("building_tasks", []):
        x, y = task["pos"]
        screen_x, screen_y = _screen_coords(x, y, camera_x, camera_y)
        if screen_x is None: continue

        if screen_x + ITEM_PX < 0 or screen_x > WIDTH or screen_y + ITEM_PX < 0 or screen_y > HEIGHT:
            continue

        rect = pygame.Rect(screen_x, screen_y, ITEM_PX, ITEM_PX)
        progress_ratio = task["progress"] / max(1, task["max_progress"])

        img = _building_task_preview_image(task)

        # Ghost image
        ghost = pygame.Surface((ITEM_PX, ITEM_PX), pygame.SRCALPHA)
        if img:
            scaled = pygame.transform.scale(img, (ITEM_PX, ITEM_PX)).copy()
            scaled.set_alpha(120)
            ghost.blit(scaled, (0, 0))
        else:
            pygame.draw.rect(ghost, (180, 140, 80, 120), ghost.get_rect(), border_radius=4)
        screen.blit(ghost, rect.topleft)

        # Progress bar at bottom of cell
        bar_h = 5
        bar_y = screen_y + ITEM_PX - bar_h - 2
        pygame.draw.rect(screen, (40, 40, 40), (screen_x + 2, bar_y, ITEM_PX - 4, bar_h), border_radius=2)
        fill_w = int((ITEM_PX - 4) * progress_ratio)
        if fill_w > 0:
            pygame.draw.rect(screen, (80, 220, 80), (screen_x + 2, bar_y, fill_w, bar_h), border_radius=2)

        # Percentage label
        pct_txt = font_tiny.render(f"{int(progress_ratio*100)}%", True, WHITE)
        screen.blit(pct_txt, (rect.centerx - pct_txt.get_width()//2, screen_y + 4))


def _draw_hotbar(screen, state, current_tool, mouse_pos, shop_open):
    # ── Hotbar UI (with icons + glow) ─────────────────────────────────────
    if not shop_open:
        hb = ui_layout.hotbar_layout()
        bar_x, bar_y = hb["panel_rect"].x, hb["panel_rect"].y
        bar_w, bar_h = hb["panel_rect"].w, hb["panel_rect"].h
        slot_size = hb["slot_size"]

        # Panel background
        panel_surf = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, ui_layout.COLOR_HOTBAR_BG, panel_surf.get_rect(), border_radius=12)
        pygame.draw.rect(panel_surf, ui_layout.COLOR_HOTBAR_BORDER, panel_surf.get_rect(), 2, border_radius=12)
        screen.blit(panel_surf, (bar_x, bar_y))

        for slot in hb["slots"]:
            item = slot["item"]
            sx, sy = slot["rect"].x, slot["rect"].y
            selected = current_tool == item["id"]

            # Slot background
            slot_col = ui_layout.COLOR_SLOT_SELECTED if selected else ui_layout.COLOR_SLOT_NORMAL
            slot_surf = pygame.Surface((slot_size, slot_size), pygame.SRCALPHA)
            pygame.draw.rect(slot_surf, (*slot_col, 230), slot_surf.get_rect(), border_radius=8)
            if selected:
                # Golden glow border
                pygame.draw.rect(slot_surf, ui_layout.COLOR_SLOT_GLOW, slot_surf.get_rect(), 3, border_radius=8)
            screen.blit(slot_surf, (sx, sy))

            # Tool sprite icon
            icon_img = images.get(item["id"])
            if icon_img:
                icon_scaled = pygame.transform.scale(icon_img, (34, 34))
                screen.blit(icon_scaled, (sx + (slot_size - 34) // 2, sy + 6))

            # Hotkey label
            key_col = ui_layout.COLOR_SLOT_KEY_SELECTED if selected else ui_layout.COLOR_SLOT_KEY_NORMAL
            key_surf = font_tiny.render(item["key"], True, key_col)
            screen.blit(key_surf, (sx + 4, sy + slot_size - key_surf.get_height() - 3))

        # ── Inventory badge: show seed count next to hotbar for seed tools ──
        if current_tool in ("radish", "carrot", "pumpkin"):
            total = sum(state.get("inventory", {}).get(current_tool, {}).values())
            badge_txt = font_small.render(f"x{total}", True, (255, 255, 150))
            bx = bar_x + bar_w + 12
            by = bar_y + (bar_h - badge_txt.get_height()) // 2
            badge_bg = pygame.Surface((badge_txt.get_width() + 12, badge_txt.get_height() + 8), pygame.SRCALPHA)
            pygame.draw.rect(badge_bg, (0, 0, 0, 180), badge_bg.get_rect(), border_radius=6)
            screen.blit(badge_bg, (bx - 6, by - 4))
            screen.blit(badge_txt, (bx, by))

        # Mouse tooltip for current tool
        if current_tool and mouse_pos:
            tip = TOOL_NAMES.get(current_tool, current_tool)
            tip_surf = font_tiny.render(tip, True, (240, 240, 200))
            tip_bg = pygame.Surface((tip_surf.get_width() + 16, tip_surf.get_height() + 8), pygame.SRCALPHA)
            pygame.draw.rect(tip_bg, (0, 0, 0, 190), tip_bg.get_rect(), border_radius=6)
            mx_t, my_t = mouse_pos
            tx = mx_t + 18
            ty = my_t - tip_bg.get_height() - 6
            # Keep on screen
            if tx + tip_bg.get_width() > WIDTH: tx = mx_t - tip_bg.get_width() - 8
            if ty < 0: ty = my_t + 18
            screen.blit(tip_bg, (tx, ty))
            screen.blit(tip_surf, (tx + 8, ty + 4))


def _draw_harvestable_glow(screen, zstate, camera_x, camera_y):
    # ── Highlight fully-grown (harvestable) crops with golden glow ─────────
    for crop in zstate.get("crops", []):
        data = zstate["crop_data"].get(crop)
        if data and data["stage"] >= data["max_stage"]:
            cx, cy = _screen_coords(crop[0], crop[1], camera_x, camera_y)
            if cx is None: continue
            if cx + ITEM_PX < 0 or cx > WIDTH or cy + ITEM_PX < 0 or cy > HEIGHT: continue
            pulse = abs((time.time() * 3) % 2 - 1)
            glow_alpha = int(60 + 100 * pulse)
            glow = pygame.Surface((ITEM_PX + 8, ITEM_PX + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow, (255, 215, 0, glow_alpha), glow.get_rect(), border_radius=4)
            screen.blit(glow, (cx - 4, cy - 4))


def _draw_minimap(screen, zstate, camera_x, camera_y):
    # ── Minimap (bottom-left corner) ───────────────────────────────────────
    mm_w, mm_h = 160, 120
    mm_x, mm_y = 20, HEIGHT - mm_h - 148
    scale_x = mm_w / WORLD_W
    scale_y = mm_h / WORLD_H

    mm_surf = pygame.Surface((mm_w, mm_h), pygame.SRCALPHA)
    pygame.draw.rect(mm_surf, (20, 40, 20, 200), mm_surf.get_rect(), border_radius=6)
    pygame.draw.rect(mm_surf, (80, 100, 80, 220), mm_surf.get_rect(), 1, border_radius=6)

    # Farmland patches
    for fx, fy in zstate.get("farmland", []):
        mmfx = int(fx * CELL_SIZE * scale_x)
        mmfy = int(fy * CELL_SIZE * scale_y)
        pygame.draw.rect(mm_surf, (110, 72, 38), (mmfx, mmfy, max(2, int(ITEM_PX * scale_x)), max(2, int(ITEM_PX * scale_y))))

    # Crops (green dots)
    for cr in zstate.get("crops", []):
        data = zstate["crop_data"].get(cr)
        col = (255, 215, 0) if (data and data["stage"] >= data.get("max_stage", 5)) else (80, 200, 80)
        mmcx = int(cr[0] * CELL_SIZE * scale_x)
        mmcy = int(cr[1] * CELL_SIZE * scale_y)
        pygame.draw.rect(mm_surf, col, (mmcx, mmcy, 3, 3))

    # Trees (dark green)
    for tx2, ty2 in zstate.get("trees", []):
        pygame.draw.rect(mm_surf, (30, 100, 30), (int(tx2 * CELL_SIZE * scale_x), int(ty2 * CELL_SIZE * scale_y), 3, 3))

    # Fences (brown)
    for fx2, fy2, _ in zstate.get("fences", []):
        pygame.draw.rect(mm_surf, (139, 90, 43), (int(fx2 * CELL_SIZE * scale_x), int(fy2 * CELL_SIZE * scale_y), 2, 2))

    # Decorations (all landscape types combined, purple dots) -- this was
    # missing for every decor type, not just the 7 new ones added this pass
    # (stone_path/flower/bench/fountain never showed on the minimap either).
    # One generic loop over the same "decorations" list _draw_decorations
    # already reads, rather than a per-type special case.
    for dx3, dy3, _dtype3, _hp3 in zstate.get("decorations", []):
        pygame.draw.rect(mm_surf, (190, 130, 220), (int(dx3 * CELL_SIZE * scale_x), int(dy3 * CELL_SIZE * scale_y), 2, 2))

    # Enemies (whichever threat exists in the currently viewed zone)
    if zstate.get("thief_pos"):
        ex, ey = zstate["thief_pos"]
        pygame.draw.rect(mm_surf, (255, 50, 50), (int(ex * CELL_SIZE * scale_x) - 2, int(ey * CELL_SIZE * scale_y) - 2, 5, 5))
    if zstate.get("boar_pos"):
        bx2, by2 = zstate["boar_pos"]
        pygame.draw.rect(mm_surf, (200, 80, 20), (int(bx2 * CELL_SIZE * scale_x) - 2, int(by2 * CELL_SIZE * scale_y) - 2, 5, 5))

    # Camera viewport rectangle
    vp_x = int(camera_x * scale_x)
    vp_y = int(camera_y * scale_y)
    vp_w = int(WIDTH * scale_x)
    vp_h = int(HEIGHT * scale_y)
    pygame.draw.rect(mm_surf, (255, 255, 255, 160), (vp_x, vp_y, vp_w, vp_h), 1)

    screen.blit(mm_surf, (mm_x, mm_y))
    label = font_tiny.render("地圖", True, (200, 220, 200))
    screen.blit(label, (mm_x + mm_w // 2 - label.get_width() // 2, mm_y - label.get_height() - 2))


def draw_board(screen, state, current_tool, camera_x, camera_y, mouse_pos, shop_open, active_tab, active_zone):
    # Farm and decor are independent maps now -- everything drawn below
    # (except HUD-level globals like money/phase/inventory) reads from the
    # currently active zone's own entity lists, never the other zone's.
    zstate = state[active_zone]

    _draw_background(screen, active_zone, camera_x, camera_y)
    _draw_trees(screen, zstate, camera_x, camera_y)
    _draw_rocks(screen, zstate, camera_x, camera_y)
    _draw_farmland(screen, zstate, camera_x, camera_y)
    _draw_crops(screen, zstate, state, camera_x, camera_y)
    _draw_scarecrows(screen, zstate, camera_x, camera_y)
    _draw_fences(screen, zstate, active_zone, camera_x, camera_y)
    _draw_traps(screen, zstate, camera_x, camera_y)
    _draw_decorations(screen, zstate, active_zone, camera_x, camera_y)
    _draw_dogs(screen, zstate, camera_x, camera_y)
    _draw_thief(screen, zstate, camera_x, camera_y)
    _draw_boar(screen, zstate, camera_x, camera_y)
    _draw_tool_preview(screen, state, zstate, current_tool, mouse_pos, shop_open, camera_x, camera_y)
    _draw_tool_grid_overlay(screen, current_tool, shop_open, camera_x, camera_y)
    _draw_building_tasks(screen, zstate, camera_x, camera_y)
    _draw_hotbar(screen, state, current_tool, mouse_pos, shop_open)
    _draw_harvestable_glow(screen, zstate, camera_x, camera_y)
    _draw_minimap(screen, zstate, camera_x, camera_y)

    draw_hud(screen, state, current_tool, active_zone, mouse_pos)
    draw_shop(screen, state, shop_open, active_tab, mouse_pos)
    draw_game_over(screen, state)
