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

images["thief"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Character/Walk.png", 0, 0, 32, 32, (60, 60))
images["fence"] = sprite_loader.get_sprite("Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Tilesets/Fences.png", 3, 0, 16, 16, (ITEM_PX, ITEM_PX))
images["dog"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Male Cow Brown.png", 0, 0, 32, 32, (60, 60))
images["cat"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Baby Chicken Yellow.png", 0, 0, 16, 16, (60, 60))
images["goose"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Chicken Red.png", 0, 0, 16, 16, (60, 60))
images["owl"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Farm Animals/Chicken Blonde  Green.png", 0, 0, 16, 16, (60, 60))
images["scarecrow"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 13, 16, 16, (60, 60))
images["strawberry"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 5, 16, 16, (60, 60))
images["radish"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, 5, 16, 16, (60, 60))
images["carrot"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 5, 5, 16, 16, (60, 60))
images["onion"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 7, 5, 16, 16, (60, 60))
images["stone_path"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Road copiar.png", 0, 0, 16, 16, (ITEM_PX, ITEM_PX))
images["flower"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 1, 12, 16, 16, (ITEM_PX, ITEM_PX))
images["bench"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Fence's copiar.png", 0, 1, 16, 16, (ITEM_PX, ITEM_PX))
images["trap"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Interior.png", 3, 5, 16, 16, (ITEM_PX, ITEM_PX))
tool_sprite = "Sprout Lands - Sprites - Basic pack/Sprout Lands - Sprites - Basic pack/Objects/Basic_tools_and_meterials.png"
images["hoe"] = sprite_loader.get_sprite(tool_sprite, 0, 2, 16, 16, (60, 60))
images["axe"] = sprite_loader.get_sprite(tool_sprite, 0, 1, 16, 16, (60, 60))
images["pickaxe"] = sprite_loader.get_sprite(tool_sprite, 0, 0, 16, 16, (60, 60)) # Watering can in Sprout Lands
images["shovel"] = sprite_loader.get_sprite("RPG Items/rpgItems.png", 3, 6, 16, 16, (60, 60)) # Iron Shovel
images["scythe"] = sprite_loader.get_sprite("RPG Items/rpgItems.png", 5, 7, 16, 16, (60, 60)) # Iron Sickle/Scythe
images["wood"] = sprite_loader.get_sprite(tool_sprite, 1, 0, 16, 16, (60, 60))
images["fertilizer"] = sprite_loader.get_sprite("Farm RPG FREE 16x16 - Tiny Asset Pack/Objects/Spring Crops.png", 3, 12, 16, 16, (60, 60))

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
