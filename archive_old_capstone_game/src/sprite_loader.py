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

    def get_sprite_region(self, filename, x, y, w, h, target_size=None):
        """Extract an arbitrary pixel rect (x, y, w, h) from a sheet/image,
        rather than a uniform row*sprite_w/row*sprite_h grid cell. Needed
        when one sprite's artwork doesn't start at a multiple of the grid
        size used for the rest of that sheet (e.g. a shorter/taller object
        sitting partway down a sheet that's otherwise sliced at a fixed
        cell size for its neighbors) -- forcing it through the row/col grid
        math in that case reads the wrong pixels, or, if the resulting
        offset falls outside the sheet entirely, silently returns None.
        Reuses get_image()'s cache so the raw sheet is only loaded once no
        matter how many regions are cut from it."""
        img = self.get_image(filename)
        if img is None:
            return None
        sheet_w, sheet_h = img.get_size()
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > sheet_w or y + h > sheet_h:
            return None
        region = img.subsurface(pygame.Rect(x, y, w, h))
        if target_size:
            region = pygame.transform.scale(region, target_size)
        return region

    def get_image(self, filename, target_size=None):
        cache_key = f"image_{filename}"
        if cache_key not in self.cache:
            path = os.path.join(ASSETS_DIR, filename)
            if not os.path.exists(path): return None
            try:
                self.cache[cache_key] = pygame.image.load(path).convert_alpha()
            except pygame.error:
                return None
        img = self.cache[cache_key]
        if target_size:
            img = pygame.transform.scale(img, target_size)
        return img
