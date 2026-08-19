"""One-off migration script: crops real sprite art out of the main
project's assets/ (Sprout Lands / Sunnyside / Farm RPG / etc. packs) and
writes it into nightwatch_farm/assets/<category>/<key>.png, replacing the
flat-color placeholder art generate_assets.py produced. Every source is
either an exact-name real asset already wired in src/assets.py, or (where
no exact match exists anywhere in the asset library -- confirmed by
exhaustive filename search) an honestly-disclosed closest-available
substitute, matching this project's established "never fabricate, always
disclose substitutes" convention. See juicy substitution notes in the
accompanying report for the reasoning behind each substitute.

Run once from the repo root: `python3 migrate_assets.py`
"""
import os
from PIL import Image

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_ASSETS = os.path.join(REPO_ROOT, "assets")
DST_ASSETS = os.path.join(REPO_ROOT, "nightwatch_farm", "assets")


def load_sheet(rel_path):
    full = os.path.join(SRC_ASSETS, rel_path)
    return Image.open(full).convert("RGBA")


def crop_grid(sheet, row, col, w, h):
    x, y = col * w, row * h
    return sheet.crop((x, y, x + w, y + h))


def crop_region(sheet, x, y, w, h):
    return sheet.crop((x, y, x + w, y + h))


def save(img, category, filename):
    out_dir = os.path.join(DST_ASSETS, category)
    os.makedirs(out_dir, exist_ok=True)
    img.save(os.path.join(out_dir, filename))
    print(f"  wrote {category}/{filename}  ({img.width}x{img.height})")


# ---------------------------------------------------------------------------
# CROPS -- nightwatch_farm's AssetLoader expects "<crop>_<stage>.png" with
# stage in {seed, sprout, growing, mature}. Sunnyside's Crops sheet has a
# real 6-frame growth sequence (00..05) for 11 vegetable types; we sample
# frames 0/2/4/5 as seed/sprout/growing/mature. Only radish/pumpkin/
# sunflower are exact name matches -- everything else below is a disclosed
# substitute (no tomato/corn/eggplant/watermelon/strawberry-growth/grape/
# starlight art exists anywhere in the asset library; confirmed by an
# exhaustive filename search across every pack before picking these).
# ---------------------------------------------------------------------------
CROPS_DIR = "Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Crops"

CROP_MAP = {
    "radish": "radish",          # exact match
    "pumpkin": "pumpkin",        # exact match
    "sunflower": "sunflower",    # exact match
    "tomato": "beetroot",        # substitute: closest round/red root veg
    "corn": "wheat",             # substitute: closest grain/stalk plant
    "eggplant": "cabbage",       # substitute: closest round vegetable (no purple art exists)
    "watermelon": "cauliflower", # substitute: closest large round vegetable
    "grape": "potato",           # substitute: weak match, no clustered-fruit art exists at all
    "starlight": "parsnip",      # substitute: fictional crop, pale root chosen as a placeholder
}
STAGE_NAMES = ["seed", "sprout", "growing", "mature"]
STAGE_FRAMES = [0, 2, 4, 5]


def migrate_crops():
    print("== crops ==")
    for nw_name, src_name in CROP_MAP.items():
        for stage_name, frame in zip(STAGE_NAMES, STAGE_FRAMES):
            sheet_path = f"{CROPS_DIR}/{src_name}_{frame:02d}.png"
            img = Image.open(os.path.join(SRC_ASSETS, sheet_path)).convert("RGBA")
            save(img, "crops", f"{nw_name}_{stage_name}.png")

    # strawberry: no growth-stage art exists anywhere (only a single mature
    # icon, from Farm RPG's Spring Crops sheet, already used by main for
    # the exact same reason). Reuse that one icon for all 4 stages --
    # disclosed limitation, not a fabricated growth sequence.
    spring_crops = load_sheet("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png")
    strawberry_icon = crop_grid(spring_crops, 1, 5, 16, 16)
    for stage_name in STAGE_NAMES:
        save(strawberry_icon, "crops", f"strawberry_{stage_name}.png")


# ---------------------------------------------------------------------------
# DECORATIONS
# ---------------------------------------------------------------------------
def migrate_decorations():
    print("== decorations ==")
    road = load_sheet("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Road copiar.png")
    save(crop_grid(road, 0, 0, 16, 16), "decorations", "stone_path.png")

    interior = load_sheet("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png")
    save(crop_grid(interior, 0, 0, 16, 16), "decorations", "flower_bed.png")
    save(crop_grid(interior, 8, 2, 16, 16), "decorations", "garden_bench.png")  # substitute: a chair, no literal bench art exists

    pine = load_sheet("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Plants/spr_deco_tree_02_strip4.png")
    save(crop_grid(pine, 0, 0, 28, 43), "decorations", "pine_tree.png")

    fruit_sheet = load_sheet("Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Trees, stumps and bushes v2.png")
    save(crop_region(fruit_sheet, 0, 80, 32, 32), "decorations", "apple_tree.png")  # substitute: heart-fruit tree, no literal apple tree art exists
    save(crop_grid(fruit_sheet, 7, 0, 16, 16), "decorations", "sundial_tower.png")  # substitute: tree stump -- no dial/tower/clock art exists anywhere

    sakura_sheet = load_sheet("Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Cherry Blossom Biom.png")
    save(crop_region(sakura_sheet, 118, 0, 42, 40), "decorations", "sakura_tree.png")  # real cherry blossom tree, exact match

    winter_sheet = load_sheet("Sprout Sorry pack/Sprout Sorry pack/Early Access/Sprout winter/campfire.png")
    save(crop_grid(winter_sheet, 2, 6, 16, 16), "decorations", "soul_lantern.png")  # substitute: stacked woodpile -- no lantern/lamp art exists anywhere

    well_covered = load_sheet("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Gamemaker/sprites/spr_deco_well_covered/28ee3935-0d63-4141-b01a-2338fa50e040.png")
    save(well_covered, "decorations", "bird_bath.png")  # substitute: covered stone well/basin -- closest available basin shape, no bird bath art exists

    grass_biom = load_sheet("Sprout-Lands-Tilemap-0.2.0/Sprout-Lands-Tilemap-0.2.0/addons/sprout_lands_tilemap/assets/Objects/Basic Grass Biom things 1.png")
    save(crop_grid(grass_biom, 1, 8, 16, 16), "decorations", "ancient_statue.png")  # substitute: plain boulder -- no statue art exists anywhere

    well = load_sheet("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Gamemaker/sprites/spr_deco_well/c3d011a3-e1d2-4f14-83d7-d21b9f689713.png")
    save(well, "decorations", "fountain.png")  # real stone well, much closer than main's old "reuse the windmill" fallback

    small_house = load_sheet("Sprout Sorry pack/Sprout Sorry pack/Early Access/Village pack/houses/small house/small_House.png")
    save(crop_grid(small_house, 0, 0, 64, 64), "decorations", "pet_house.png")  # substitute: small cottage, no purpose-built doghouse/kennel art exists

    windmill = load_sheet("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Other/spr_deco_windmill_strip9.png")
    save(crop_grid(windmill, 0, 0, 112, 112), "decorations", "windmill.png")  # real windmill, exact match


# ---------------------------------------------------------------------------
# DEFENSES
# ---------------------------------------------------------------------------
def migrate_defenses():
    print("== defenses ==")
    fences = load_sheet("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Fences.png")
    save(crop_grid(fences, 3, 0, 16, 16), "defenses", "wooden_fence.png")

    spikes = load_sheet("Free-Magic-and-Traps-Top-Down-Pixel-Art-Asset/1 Spikes/1.png")
    save(crop_grid(spikes, 0, 2, 32, 32), "defenses", "bear_trap.png")  # substitute: floor spikes, no leg-hold trap art exists anywhere (same substitute main already uses)

    spring_crops = load_sheet("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png")
    save(crop_grid(spring_crops, 1, 13, 16, 16), "defenses", "scarecrow.png")

    beehive = Image.open(os.path.join(SRC_ASSETS, "Sprout Sorry pack/Sprout Sorry pack/Early Access/Plant update 2/Bee/beehive.png")).convert("RGBA")
    save(beehive, "defenses", "beehive.png")

    tools = load_sheet("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Objects/Basic_tools_and_meterials.png")
    save(crop_grid(tools, 0, 0, 16, 16), "defenses", "watering_can.png")  # real watering can (main's own code comments confirm this exact cell is a watering can, just registered under a different id there)


# ---------------------------------------------------------------------------
# CHARACTERS
# ---------------------------------------------------------------------------
def migrate_characters():
    print("== characters ==")
    dog_sheet = load_sheet("Goldie pack_v1.1/Goldie pack_v02/Goldie_v02.png")
    save(crop_grid(dog_sheet, 4, 0, 32, 40), "characters", "guard_dog.png")

    chicken = load_sheet("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png")
    save(crop_grid(chicken, 0, 0, 16, 16), "characters", "farm_cat.png")  # substitute: no real cat art exists anywhere in the asset library (main's own "cat" id has the same substitute)

    walk = load_sheet("Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png")
    save(crop_grid(walk, 0, 0, 32, 32), "characters", "enemy_thief.png")

    pig = load_sheet("Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_ASSET_PACK_V2.1/Sunnyside_World_Assets/Elements/Animals/spr_deco_pig_01_strip4.png")
    boar_frame = crop_grid(pig, 0, 0, 32, 32)
    save(boar_frame, "characters", "enemy_boar.png")  # substitute: pig -- this is the exact same asset main's own renderer.py already uses for its boar enemy
    boss = boar_frame.resize((int(32 * 1.4), int(32 * 1.4)), Image.LANCZOS)
    save(boss, "characters", "boss_boar.png")

    bat_sheet = load_sheet("Sprout Sorry pack/Sprout Sorry pack/Early Access/Dungeon Pack/enemies/bat_animations.png")
    save(crop_grid(bat_sheet, 0, 0, 32, 32), "characters", "enemy_bat.png")  # real bat art, exact match


if __name__ == "__main__":
    migrate_crops()
    migrate_decorations()
    migrate_defenses()
    migrate_characters()
    print("Done.")
