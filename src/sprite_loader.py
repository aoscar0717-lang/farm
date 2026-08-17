import pygame
import os

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

class SpriteLoader:
    def __init__(self):
        self.cache = {}
        
    def load_sheet(self, filename, sprite_w=16, sprite_h=16):
        cache_key = f"{filename}_{sprite_w}x{sprite_h}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        path = os.path.join(ASSETS_DIR, filename)
        if not os.path.exists(path):
            print(f"Warning: Sprite sheet not found at {path}")
            return None
            
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except pygame.error as e:
            print(f"Error loading {path}: {e}")
            return None
            
        sheet_w, sheet_h = sheet.get_size()
        cols = sheet_w // sprite_w
        rows = sheet_h // sprite_h
        
        sprites = []
        for row in range(rows):
            row_sprites = []
            for col in range(cols):
                rect = pygame.Rect(col * sprite_w, row * sprite_h, sprite_w, sprite_h)
                image = sheet.subsurface(rect)
                row_sprites.append(image)
            sprites.append(row_sprites)
            
        self.cache[cache_key] = sprites
        return sprites

    def get_sprite(self, filename, row, col, sprite_w=16, sprite_h=16, target_size=None):
        sheet = self.load_sheet(filename, sprite_w, sprite_h)
        if sheet and row < len(sheet) and col < len(sheet[row]):
            img = sheet[row][col]
            if target_size:
                img = pygame.transform.scale(img, target_size)
            return img
        return None
