import pygame
import os
import random
from src.config import ITEM_PX, WIDTH, HEIGHT, CELL_SIZE
from src.sprite_loader import SpriteLoader

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("農場防禦 - 開放世界沙盒版")

sprite_loader = SpriteLoader()
assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets'))
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)

images = {}


def _register_sprite(asset_id, filename, row, col, sprite_w, sprite_h, target_size):
    """Load one grid cell out of a sprite sheet and store it under
    images[asset_id]. Identical behavior to the old inline
    `images["x"] = sprite_loader.get_sprite(...)` calls on success; the only
    change is that a missing file / out-of-range row-col now also prints a
    single-line, greppable [ASSET ERROR] to the console (sprite_loader's own
    get_sprite already returns None gracefully in both cases -- this just
    surfaces *why* at the call site instead of leaving it silent)."""
    img = sprite_loader.get_sprite(filename, row, col, sprite_w, sprite_h, target_size)
    if img is None:
        print(f"[ASSET ERROR] ID: {asset_id} Path: {filename} Reason: sprite not found or row/col ({row},{col}) out of range")
    images[asset_id] = img
    return img


def _register_image(asset_id, filename, target_size):
    """Same as _register_sprite but for a single standalone image (no sheet
    slicing) via sprite_loader.get_image()."""
    img = sprite_loader.get_image(filename, target_size)
    if img is None:
        print(f"[ASSET ERROR] ID: {asset_id} Path: {filename} Reason: image not found")
    images[asset_id] = img
    return img


def _register_sprite_region(asset_id, filename, x, y, w, h, target_size):
    """Same as _register_sprite but for an arbitrary pixel rect (x, y, w, h)
    instead of a row/col grid cell -- use this when one sprite's artwork on
    a sheet doesn't start at a multiple of that sheet's normal grid size
    (see fruit_tree below for a concrete case)."""
    img = sprite_loader.get_sprite_region(filename, x, y, w, h, target_size)
    if img is None:
        print(f"[ASSET ERROR] ID: {asset_id} Path: {filename} Reason: region ({x},{y},{w},{h}) out of range")
    images[asset_id] = img
    return img


def load_image(filename, target_size=(ITEM_PX, ITEM_PX)):
    filepath = os.path.join(assets_dir, filename)
    if os.path.exists(filepath):
        img = pygame.image.load(filepath).convert_alpha()
        img = pygame.transform.scale(img, target_size)
        width, height = img.get_size()
        visited = set()
        queue = [(0, 0), (width-1, 0), (0, height-1), (width-1, height-1)]
        while queue:
            x, y = queue.pop(0)
            if (x, y) in visited: continue
            if x < 0 or x >= width or y < 0 or y >= height: continue
            visited.add((x, y))
            r, g, b, a = img.get_at((x, y))
            if r > 240 and g > 240 and b > 240:
                img.set_at((x, y), (255, 255, 255, 0))
                queue.extend([(x+1, y), (x-1, y), (x, y+1), (x, y-1)])
        return img
    return None

_register_sprite("thief", "Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png", 0, 0, 32, 32, (60, 60))
_register_sprite("fence", "Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Fences.png", 3, 0, 16, 16, (ITEM_PX, ITEM_PX))
_register_sprite("dog", "Goldie pack_v1.1/Goldie pack_v02/Goldie_v02.png", 4, 0, 32, 40, (60, 60))
_register_sprite("cat", "Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png", 0, 0, 16, 16, (60, 60))
_register_sprite("goose", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_duck_01_strip4.png", 0, 0, 16, 16, (60, 60))
_register_sprite("sheep", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_sheep_01_strip4.png", 0, 0, 32, 32, (60, 60))
_register_sprite("bull", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_cow_strip4.png", 0, 0, 32, 32, (60, 60))
_register_sprite("owl", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_bird_01_strip4.png", 0, 0, 16, 16, (60, 60))
_register_sprite("scarecrow", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (60, 60))
_register_sprite("strawberry", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 5, 16, 16, (60, 60))
_register_sprite("radish", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, 5, 16, 16, (60, 60))

# carrot: Spring Crops.png row5,col5 is just a green leaf cluster with no
# orange visible at all -- not recognizable as a carrot. The world map
# already renders a correct, unambiguous orange carrot for planted carrots
# (Sunnyside carrot_00..05.png, see renderer.py _draw_crops), so the shop/
# sell icon is repointed to that same already-used, already-correct asset
# (mature stage, matching the "pumpkin" icon convention below) instead of
# the mismatched Spring Crops tile.
_register_image("carrot", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops/carrot_05.png", (60, 60))
_register_sprite("onion", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 7, 5, 16, 16, (60, 60))
_register_sprite("stone_path", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Road copiar.png", 0, 0, 16, 16, (ITEM_PX, ITEM_PX))

# flower: Spring Crops.png row1,col12 is a strawberry (row1 of that sheet is
# entirely strawberry growth/harvest frames) -- not a flower or flower pot.
# Interior.png row0,col0 is an unambiguous potted red flowering plant
# (visually confirmed), which matches "鮮花盆栽" far better than anything
# crop-related.
_register_sprite("flower", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 0, 0, 16, 16, (ITEM_PX, ITEM_PX))

# bench: Fence's copiar.png row0,col1 is a character portrait (head/face),
# not furniture at all. No literal bench exists anywhere in the project's
# asset packs (searched Farm RPG, Sprout Lands x4 packs, Sunnyside,
# mystic_woods, RPG Items, Free-Magic-and-Traps). Interior.png row8,col2 is
# the closest available substitute -- a single wooden chair/stool -- per the
# explicit fallback rule "找不到長椅則使用最接近的椅子/座椅素材". This is a
# disclosed substitute, not a literal bench: a chair, not a multi-seat bench.
_register_sprite("bench", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 8, 2, 16, 16, (ITEM_PX, ITEM_PX))

# trap: Interior.png row3,col5 is a fragment of a bed's headboard (Interior.png
# is an indoor-furniture sheet), not any kind of trap. No animal-trap/leg-hold
# style asset exists anywhere in the project. Free-Magic-and-Traps-Top-Down-
# Pixel-Art-Asset/1 Spikes/1.png (a 6-frame floor-spike animation, previously
# unused by the project) is the closest available "trap" concept. Because the
# available art is spikes rather than a leg-hold trap, the item's *display
# name* was changed from 捕獸夾 to 地刺陷阱 to match what the art actually
# shows (see TOOL_NAMES/SHOP_ITEM_DETAILS/thought.py/capstone_contract.py
# last_msg strings) -- the internal id "trap" and all game logic are
# unchanged. Frame index 2 (of 6) was chosen as the icon: it shows the most
# spikes risen, reading clearly as "trap" at a glance.
_register_sprite("trap", "Free-Magic-and-Traps-Top-Down-Pixel-Art-Asset/1 Spikes/1.png", 0, 2, 32, 32, (ITEM_PX, ITEM_PX))

# ---------------------------------------------------------------------------
# Landscape expansion (7 new decor items). All confirmed by cropping the
# actual sprite region and looking at it (see the analysis report delivered
# before this pass) -- none of these are filename guesses. "scarecrow" is
# NOT registered here because it already exists above (it was registered
# from day one but never wired to a purchasable decor item -- this pass
# finally connects it, see capstone_contract.py's DECOR_INFO).
# ---------------------------------------------------------------------------

# crate: Farm RPG chest.png, a clean 32x16 closed-chest frame (row0 of a
# 2-frame closed/open sheet) -- distinct from bench's Interior.png chair and
# from the mystic_woods chest (kept unused to avoid mixing two different art
# styles for the same concept).
_register_sprite("crate", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/chest.png", 0, 0, 32, 16, (ITEM_PX, ITEM_PX))

# bush: Basic Grass Biom things 1.png row1,col6 -- a small leafy shrub
# cluster. Modest but genuine plant content (category B in the analysis,
# not a top-tier match, disclosed as such).
_register_sprite("bush", "Sprout-Lands-Tilemap-0.2.0/Sprout-Lands-Tilemap-0.2.0/addons/sprout_lands_tilemap/assets/Objects/Basic Grass Biom things 1.png", 1, 6, 16, 16, (ITEM_PX, ITEM_PX))

# rock: same sheet, row1,col8 -- a clean gray boulder.
_register_sprite("rock", "Sprout-Lands-Tilemap-0.2.0/Sprout-Lands-Tilemap-0.2.0/addons/sprout_lands_tilemap/assets/Objects/Basic Grass Biom things 1.png", 1, 8, 16, 16, (ITEM_PX, ITEM_PX))

# sunflower: same sheet. The flower head alone (16x16) cropped the stem off
# at the bottom -- the full sprite (head + stem + leaves) is 16 wide x 32
# tall, spanning what would be rows 2-3 at a 16px grid. Sliced here with
# sprite_h=32 so row=1,col=8 captures the whole plant in one piece (see the
# corrected preview sent during analysis).
_register_sprite("sunflower", "Sprout-Lands-Tilemap-0.2.0/Sprout-Lands-Tilemap-0.2.0/addons/sprout_lands_tilemap/assets/Objects/Basic Grass Biom things 1.png", 1, 8, 16, 32, (ITEM_PX, ITEM_PX))

# pine_tree: Sunnyside spr_deco_tree_02_strip4.png, a clean 4-frame idle
# animation of a pine/conifer tree, distinct from the Maple big_tree below
# and from the obstacle tree already used in _draw_trees (spr_deco_tree_01).
# Frame 0 (of 4) used as the static shop/world icon; renderer.py may animate
# through the other 3 frames later the same way it already does for the
# windmill, but that's optional polish, not required for this to work.
_register_sprite("pine_tree", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_tree_02_strip4.png", 0, 0, 28, 43, (ITEM_PX, ITEM_PX))

# big_tree: Farm RPG Maple Tree.png. The full tree (canopy + trunk + ground
# shadow) is a 32x48 region, not 32x32 -- a first attempt that stopped at
# 32px tall cut the shadow off (see the corrected preview sent during
# analysis). Sliced here with sprite_h=48 so row=0,col=3 captures the whole
# tree.
_register_sprite("big_tree", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Maple Tree.png", 0, 3, 32, 48, (ITEM_PX, ITEM_PX))

# ---------------------------------------------------------------------------
# Landscape expansion, round 2 -- 8 more decor items found by scanning packs
# not fully explored in round 1 (Sprout Sorry pack's "Early Access" content,
# the rest of mystic_woods' objects/tilesets, and Farm RPG's Interior.png).
#
# Note: a "leafy_tree" candidate (Sunnyside spr_deco_tree_01_strip4.png) was
# investigated and DROPPED after visual verification -- that exact file is
# already used by renderer.py's _draw_trees() for the farm zone's wild
# obstacle trees (animated, drawn directly, not through this images{} dict).
# Registering it a second time as a purchasable decor item would make a
# bought decoration look pixel-identical to random world clutter the player
# didn't place -- confusing, not a real addition. Skipped rather than reused
# inappropriately.
# ---------------------------------------------------------------------------

# stump: same "Trees, stumps and bushes v2.png" sheet as fruit_tree below --
# a small round tree-stump icon, row7,col0 in the sheet's 16px grid.
_register_sprite("stump", "Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Trees, stumps and bushes v2.png", 7, 0, 16, 16, (ITEM_PX, ITEM_PX))

# mushroom: Sunnyside's red-and-white toadstool, a clean 4-frame idle
# animation (same convention as pine_tree/fountain) -- frame 0 used as the
# static icon.
_register_sprite("mushroom", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_mushroom_red_01_strip4.png", 0, 0, 16, 16, (ITEM_PX, ITEM_PX))

# picnic_basket: standalone 16x16 image (no sheet slicing needed).
_register_image("picnic_basket", "Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/piknik/Piknik basket.png", (ITEM_PX, ITEM_PX))

# woodpile: from the "Sprout winter" campfire-building sheet -- NOT a lit
# fire (that sheet has no flame frames, see analysis report), just the
# final "fully stacked crossed logs" frame at row2,col6 -- reused as plain
# firewood/woodpile decor, unrelated to the winter/seasonal theme of the
# source folder.
_register_sprite("woodpile", "Sprout Sorry pack/Sprout Sorry pack/Early Access/Sprout winter/campfire.png", 2, 6, 16, 16, (ITEM_PX, ITEM_PX))

# picnic_blanket: standalone 48x48 image, a checkered picnic blanket.
_register_image("picnic_blanket", "Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/piknik/Piknik blanket.png", (ITEM_PX, ITEM_PX))

# beehive: standalone 32x32 image.
_register_image("beehive", "Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Bee/beehive.png", (ITEM_PX, ITEM_PX))

# garden_table: Farm RPG's indoor Interior.png sheet -- a round table with
# a white cloth. Originally registered as row=7,col=4 at a 32x32 grid, but
# that sheet is only 192x144px, so a 32x32 grid only has 4 valid rows
# (0-3); row=7 was out of range (found the same way as the fruit_tree bug,
# while cross-checking every registered sprite's slice coordinates against
# each sheet's real pixel dimensions -- images["garden_table"] was
# silently None too). The table itself sits at pixel (64,112)-(96,144):
# x=64 happens to be 32-aligned, but y=112 is not (it's row 7 of the
# sheet's native 16px grid, same as bench/flower use for this same file) --
# so it can't be reached with row/col grid math at sprite_h=32 either.
# Extracted with get_sprite_region() using the exact confirmed pixel rect.
_register_sprite_region("garden_table", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 64, 112, 32, 32, (ITEM_PX, ITEM_PX))

# fruit_tree: same sheet as stump above. Originally registered as
# row=5,col=0 at a 32x32 grid -- but that sheet is only 192x128px, so a
# 32x32 grid only has 4 valid rows (0-3); row=5 was out of range and
# sprite_loader.get_sprite() was silently returning None the whole time
# (images["fruit_tree"] was None, so nothing ever drew -- found while
# verifying every registered sprite's actual pixel dimensions during an
# unrelated sprite-scaling investigation). The intended artwork (a round
# tree bearing three red heart-shaped fruits) does exist on this sheet, but
# it sits at pixel (0,80)-(32,112), which is not a multiple of 32 (it's row
# 5 of the sheet's native 16px grid) -- so it can't be reached with row/col
# grid math at sprite_h=32 either. Extracted with get_sprite_region() using
# the exact confirmed pixel rect instead of guessing another row/col pair.
_register_sprite_region("fruit_tree", "Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Trees, stumps and bushes v2.png", 0, 80, 32, 32, (ITEM_PX, ITEM_PX))

tool_sprite = "Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Objects/Basic_tools_and_meterials.png"
_register_sprite("hoe", tool_sprite, 0, 2, 16, 16, (60, 60))
_register_sprite("axe", tool_sprite, 0, 1, 16, 16, (60, 60))
_register_sprite("pickaxe", tool_sprite, 0, 0, 16, 16, (60, 60))  # Watering can in Sprout Lands
_register_sprite("shovel", "RPG Items/rpgItems.png", 3, 6, 16, 16, (60, 60))  # Iron Shovel
_register_sprite("scythe", "RPG Items/rpgItems.png", 5, 7, 16, 16, (60, 60))  # Iron Sickle/Scythe
_register_sprite("wood", tool_sprite, 1, 0, 16, 16, (60, 60))
_register_sprite("fertilizer", "Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, 12, 16, 16, (60, 60))

# pumpkin: Spring Crops.png (the sheet every other crop icon comes from) has
# no pumpkin sprite anywhere in it (visually verified frame-by-frame). The
# project's Sunnyside asset pack does have a real, unambiguous pumpkin icon
# already used elsewhere for the mature-crop stage, so it is reused here as
# the shop/tool icon per the confirmed priority-3 fallback rule (reuse an
# already-used real game image rather than inventing or substituting one).
_register_image("pumpkin", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops/pumpkin_05.png", (60, 60))

# fountain: no fountain/well art exists anywhere in any asset pack in this
# project (exhaustively searched). The decoration's own world sprite already
# reuses the windmill animation (see renderer.py _draw_decorations), and the
# user decided to rename the decoration's display identity from "小型噴泉"
# to "風車" (see DECOR_NAMES/TOOL_NAMES/SHOP_ITEM_DETAILS) to match the only
# asset that actually exists, rather than binding a mismatched icon under
# the old name. This icon is frame 0 of that same windmill strip.
_register_sprite("fountain", "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Other/spr_deco_windmill_strip9.png", 0, 0, 112, 112, (60, 60))

shop_bg_path = os.path.join(assets_dir, "Sprout Lands UI Pack/Sprout Lands - UI Pack - Basic pack/Sprite sheets/Setting menu.png")
if os.path.exists(shop_bg_path):
    try:
        images["shop_bg"] = pygame.image.load(shop_bg_path).convert_alpha()
    except:
        pass

night_filter = pygame.Surface((WIDTH, HEIGHT))
night_filter.fill((10, 10, 40))
night_filter.set_alpha(150)

# Build backgrounds
bg_surf_left = None
bg_surf_right = None

def get_bg_surfs():
    global bg_surf_left, bg_surf_right
    if bg_surf_left is None:
        TILE_W = 40
        TILE_H = 40
        chunk_w = 400
        chunk_h = 400
        
        # Left: Grass / Dirt
        bg_surf_left = pygame.Surface((chunk_w, chunk_h))
        t_center_left = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Tileset/Tileset Spring.png", 2, 9, 16, 16, (TILE_W, TILE_H))
        
        if t_center_left:
            t_center_var1 = t_center_left.copy()
            pygame.draw.rect(t_center_var1, (90, 150, 60), (10, 10, 4, 2))
            t_center_var2 = t_center_left.copy()
            pygame.draw.circle(t_center_var2, (255, 215, 0), (15, 20), 2)
            t_centers = [t_center_left, t_center_left, t_center_left, t_center_var1, t_center_var2]
            
            random.seed(42)
            for r in range(chunk_h // TILE_H):
                for c in range(chunk_w // TILE_W):
                    bg_surf_left.blit(random.choice(t_centers), (c * TILE_W, r * TILE_H))
            random.seed()
        else:
            bg_surf_left.fill((50, 100, 50))
            
        # Right: Yard / Stone
        bg_surf_right = pygame.Surface((chunk_w, chunk_h))
        
        if t_center_left:
            t_center_right = t_center_left.copy()
            # Tint it darker to look like dirt/stone
            t_center_right.fill((180, 150, 120), special_flags=pygame.BLEND_RGBA_MULT)
            
            t_centers_r = [t_center_right]
            for r in range(chunk_h // TILE_H):
                for c in range(chunk_w // TILE_W):
                    bg_surf_right.blit(random.choice(t_centers_r), (c * TILE_W, r * TILE_H))
        else:
            bg_surf_right.fill((120, 100, 70))

    return bg_surf_left, bg_surf_right

# Nightwatch farm animals
_register_sprite('cat', 'Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png', 0, 0, 16, 16, (60, 60))
_register_sprite('goose', 'Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_duck_01_strip4.png', 0, 0, 16, 16, (60, 60))
_register_sprite('sheep', 'Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_sheep_01_strip4.png', 0, 0, 16, 16, (60, 60))
_register_sprite('bull', 'Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_cow_strip4.png', 0, 0, 32, 32, (60, 60))
_register_sprite('owl', 'Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_bird_01_strip4.png', 0, 0, 16, 16, (60, 60))
