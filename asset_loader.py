"""
夜巡農場 (Nightwatch Farm) - 素材圖像載入器 (AssetLoader)
自動載入 assets/ 目錄下的所有透明 PNG 圖片（10種作物、13種景觀、防禦與生物）。
"""

import os
import pygame
from typing import Dict, Tuple

ASSET_ROOT = os.path.join(os.path.dirname(__file__), "assets")

# ---- 血月首領 / 野豬王共用的 pig.png 精靈圖設定 --------------------
# 確認過的實際規格：1024x1024、5 欄 x 5 列 (SPRITE_COLS x SPRITE_ROWS)
# 的網格，每格 204x204，背景全黑 (0,0,0)。
SPRITE_COLS = 5
SPRITE_ROWS = 5
# 步行循環只取每個方向裡的 4 格，組成 [站立, 踏步1, 站立, 踏步2]，
# 站立幀出現兩次是為了讓「踏一步→回到站立→踏另一步→回到站立」的節奏
# 更自然，避免兩個踏步幀直接相接看起來像在滑步。
WALK_CYCLE_INDICES = [0, 2, 0, 3]
# 每個方向對應精靈圖的第幾「列」(row)：down=Row0、right=Row1、up=Row2。
# left 不佔額外的列，直接把 right 那組幀左右翻轉 (pygame.transform.flip)
# 取得，省素材也保證左右動作完全對稱。
BOSS_DIRECTION_ROWS = {"down": 0, "right": 1, "up": 2}
# 背景是純黑色去背 (Chroma Key)，不是 alpha 透明。
BOSS_CHROMA_KEY = (0, 0, 0)

# ---- 小偷 (assets/characters/theif.png) 精靈圖設定 -------------------------
# 實測 1024x568，是 8 欄 x 4 列的網格，每格 128x142，四個方向各自獨立畫好、
# 每個方向 8 幀（超流暢動作），不用像 pig.png 那樣靠翻轉湊出 left。
THIEF_COLS = 8
THIEF_ROWS = 4
# 每個方向對應第幾「列」(row)。
THIEF_DIRECTION_ROWS = {"down": 0, "right": 1, "left": 2, "up": 3}
# 注意：實測背景本來就是「真透明」(alpha=0)，不是純黑不透明去背——四個角落
# 與畫格空白處都是 (0,0,0,0)。而且畫面上小偷的頭髮/衣服本身就有大量「不透明
# 的黑色」像素（RGB 全 0 但 alpha=255），如果再對整張圖套用
# set_colorkey((0,0,0)) 去背，會把這些真正的黑色畫面內容一起挖空。
# 所以這裡直接用 convert_alpha() 吃原本就有的 per-pixel alpha，不套用
# chroma key，避免誤傷素材本身的黑色部分。

# ---- 玉米 (assets/crops/玉米.png) 精靈圖設定 -------------------------------
# 實測 128x32，原本以為是 4 格橫向排列、每格 32x32，但其實每組是 2 個 16x32 並排
# (左邊健康，右邊枯萎)。將寬度減半為 16 以排除連在一起的枯萎版本。
CORN_FRAME_WIDTH = 16  # 寬度減半：原本 32 -> 改為 16
CORN_FRAME_HEIGHT = 32
# 欄數加倍，只取偶數欄 (0, 2, 4, 6) 即代表健康版本
CORN_STAGE_COLUMNS = {"seed": 0, "sprout": 2, "growing": 4, "mature": 6}

# ---- 胡蘿蔔/番茄/土豆/藍莓 (assets/crops/胡蘿蔔_番茄_土豆_藍莓.png) --------
# 實測 224x192，是 7 欄 x 4 列、每格 32x32 的網格：
#   row 0 = 胡蘿蔔 (carrot)，row 1 = 番茄 (tomato)，
#   row 2 = 土豆 (potato，目前遊戲沒有這個作物，切圖時直接跳過)，
#   row 3 = 藍莓 (blueberry)。
# 每一列裡實際上有 5 組「生長圖示」由左至右依序變大，每組本身是兩個並排的變體
# (左邊健康，右邊枯萎)。將寬度減半為 16 以排除枯萎圖案。
MIX_FRAME_WIDTH = 16  # 寬度減半：原本 32 -> 改為 16
MIX_FRAME_HEIGHT = 32
MIX_ROW_CROPS = {"carrot": 0, "tomato": 1, "blueberry": 3}  # row 2 (potato) 略過
# 原本的 col (0, 1, 3, 4) 乘以 2 轉換為 16px 的新欄位索引，只取健康版本 (左半邊)
MIX_STAGE_COLUMNS = {"seed": 0, "sprout": 2, "growing": 6, "mature": 8}

# ---- 柵欄自動連接 (assets/Fences.png) 4-bit Bitmask 設定 -------------------
# 實測 64x64，是 4 欄 x 4 列、每格 16x16 的網格，剛好 16 種狀態，背景本身
# 就是真透明 (alpha=0)，沒有黑色像素混在裡面，直接 convert_alpha() 讀取
# 即可，不需要 set_colorkey。
FENCE_COLS = 4
FENCE_ROWS = 4
FENCE_FRAME_SIZE = 16

# 權重設定：上=1, 右=2, 下=4, 左=8（跟需求文件裡的定義一致）。
# 這張圖實際的排版不是單純 0~15 依序排列，而是「列決定上下連接狀態、
# 欄決定左右連接狀態」的兩軸組合：
#   row 0 = 只連下 (up=0, down=1)      row 2 = 只連上 (up=1, down=0)
#   row 1 = 上下都連 (up=1, down=1)    row 3 = 上下都不連 (up=0, down=0)
#   col 0 = 左右都不連 (left=0, right=0)   col 2 = 左右都連 (left=1, right=1)
#   col 1 = 只連右 (left=0, right=1)       col 3 = 只連左 (left=0(見上), left=1, right=0)
# 這個對應是用 PIL 實測每格四個邊緣是否有非透明像素延伸到邊界（有延伸=
# 該方向有連接）反推出來的，不是憑空猜的——例如 mask=0（完全獨立）對應
# 到 (col0, row3)，該格的不透明像素數量剛好是全表最少；mask=15（十字全
# 連）對應到 (col2, row1)，該格的不透明像素數量剛好是全表最多，兩者都
# 符合「連接越多、用到的畫面內容越多」的常識，可信度高。
# 如果之後你發現遊戲裡畫出來對不上（例如某個轉角圖案接不起來），這裡就是
# 要微調的地方：把對應 mask 的 (col, row) 改成正確的座標即可，不用動
# 切圖或渲染邏輯。
BITMASK_MAP = {
    0: (0, 3),   # 獨立木樁 (無連接)
    1: (0, 2),   # 只連上方
    2: (1, 3),   # 只連右方
    3: (1, 2),   # 連上+右
    4: (0, 0),   # 只連下方
    5: (0, 1),   # 連上+下 (垂直直線)
    6: (1, 0),   # 連右+下
    7: (1, 1),   # 連上+右+下 (缺左的 T 字)
    8: (3, 3),   # 只連左方
    9: (3, 2),   # 連上+左
    10: (2, 3),  # 連右+左 (水平直線)
    11: (2, 2),  # 連上+右+左 (缺下的 T 字)
    12: (3, 0),  # 連下+左
    13: (3, 1),  # 連上+下+左 (缺右的 T 字)
    14: (2, 0),  # 連右+下+左 (缺上的 T 字)
    15: (2, 1),  # 四面全連 (十字)
}


# ---- 看門柴犬走路動畫 (assets/characters/guard_dog_walk.png) --------------
# 實測 128x320，是 4 欄 x 8 列、每格 32x40 的網格。用透明間隙分析確認過
# 實際切割線，不是憑格數硬除。整張圖其實有兩組風格：第 0-3 列是「坐姿」
# 姿勢（含一頂派對帽的裝飾變體），第 4-7 列才是乾淨的四方向走路循環，
# 這裡只取第 4-7 列。
DOG_WALK_COLS = 4
DOG_WALK_ROWS_TOTAL = 8
DOG_WALK_FRAME_W = 32
DOG_WALK_FRAME_H = 40
# 每個方向對應精靈圖的第幾「列」。row4=面對鏡頭(down)、row5=背對鏡頭
# (up，看不到臉、只看得到尾巴)、row6=頭朝右(right)、row7=頭朝左(left)，
# 都是用 PIL 把每一列放大檢視、目視確認過朝向才定案，不是用格數猜的。
DOG_WALK_DIRECTION_ROWS = {"down": 4, "up": 5, "right": 6, "left": 7}
# 白天狗不用出去咬人，改播「坐姿面對鏡頭」的待機動畫，跟第 4 列
# (走路動畫的 down 方向) 不是同一列——第 4 列有戴一頂派對帽，這裡改用
# 第 2 列：沒有帽子、純坐姿的前視角，看起來更像「安靜坐著休息」。
DOG_DAY_SIT_ROW = 2


class AssetLoader:
    def __init__(self, cell_size: int = 50):
        self.cell_size = cell_size
        self.images: Dict[str, pygame.Surface] = {}
        self.load_all()

    def _scale_keep_aspect(self, frame: pygame.Surface, cell_size: int) -> pygame.Surface:
        """
        等比例縮放：寬度固定等於 cell_size，高度依原始長寬比自動算出，
        不會強制拉伸/壓扁成正方形。長條形的作物畫格（例如胡蘿蔔的
        16x32）縮放後仍會維持瘦高的比例，不會變成矮胖的正方形。
        呼叫端 blit 時要記得改用 midbottom 對齊格子底部，而不是
        topleft，這樣比較高的圖才會自然往上延伸、不會超出格子下緣。
        """
        fw, fh = frame.get_size()
        if fw <= 0 or fh <= 0:
            return frame
        target_h = max(1, round(fh * (cell_size / fw)))
        return pygame.transform.scale(frame, (cell_size, target_h))

    def _load_image(self, rel_path: str, size: Tuple[int, int]) -> pygame.Surface:
        full_path = os.path.join(ASSET_ROOT, rel_path)
        if os.path.exists(full_path):
            try:
                img = pygame.image.load(full_path).convert_alpha()
                return pygame.transform.scale(img, size)
            except Exception as e:
                print(f"[AssetLoader] 載入 {rel_path} 失敗: {e}")
        
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (200, 200, 200, 150), (4, 4, size[0] - 8, size[1] - 8), border_radius=4)
        return surf

    def _load_corn_spritesheet(self, size: Tuple[int, int]):
        """
        從 assets/crops/玉米.png 切出玉米的 4 個生長階段，直接寫進
        self.images["corn_seed"] / "corn_sprout" / "corn_growing" /
        "corn_mature"，跟舊的單檔 {name}_{stage}.png 格式相容，渲染層
        完全不用改。找不到檔案時，四個 key 都填一個灰色佔位圖，不會
        讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, "crops/玉米.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 crops/玉米.png，corn 將使用灰色佔位圖。")
            for stage in CORN_STAGE_COLUMNS:
                self.images[f"corn_{stage}"] = self._load_image("crops/__missing__.png", size)
            return

        try:
            sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 載入 crops/玉米.png 失敗: {e}")
            for stage in CORN_STAGE_COLUMNS:
                self.images[f"corn_{stage}"] = self._load_image("crops/__missing__.png", size)
            return

        cell_size = size[0]
        for stage, col in CORN_STAGE_COLUMNS.items():
            rect = pygame.Rect(col * CORN_FRAME_WIDTH, 0, CORN_FRAME_WIDTH, CORN_FRAME_HEIGHT)
            frame = sheet.subsurface(rect).copy()
            # 等比例縮放，不強制壓成正方形 (見 _scale_keep_aspect 註解)。
            self.images[f"corn_{stage}"] = self._scale_keep_aspect(frame, cell_size)

    def _load_carrot_tomato_blueberry_spritesheet(self, size: Tuple[int, int]):
        """
        從 assets/crops/胡蘿蔔_番茄_土豆_藍莓.png 切出胡蘿蔔/番茄/藍莓
        各自的 4 個生長階段，寫進 self.images["carrot_seed"] /
        "tomato_seed" / "blueberry_seed" 等等，跟舊格式相容。
        土豆 (potato) 那一列目前遊戲用不到，直接跳過不切。
        找不到檔案時，三種作物、四個階段都填灰色佔位圖。
        """
        full_path = os.path.join(ASSET_ROOT, "crops/胡蘿蔔_番茄_土豆_藍莓.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 crops/胡蘿蔔_番茄_土豆_藍莓.png，carrot/tomato/blueberry 將使用灰色佔位圖。")
            for crop_name in MIX_ROW_CROPS:
                for stage in MIX_STAGE_COLUMNS:
                    self.images[f"{crop_name}_{stage}"] = self._load_image("crops/__missing__.png", size)
            return

        try:
            sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 載入 crops/胡蘿蔔_番茄_土豆_藍莓.png 失敗: {e}")
            for crop_name in MIX_ROW_CROPS:
                for stage in MIX_STAGE_COLUMNS:
                    self.images[f"{crop_name}_{stage}"] = self._load_image("crops/__missing__.png", size)
            return

        cell_size = size[0]
        for crop_name, row in MIX_ROW_CROPS.items():
            for stage, col in MIX_STAGE_COLUMNS.items():
                rect = pygame.Rect(col * MIX_FRAME_WIDTH, row * MIX_FRAME_HEIGHT, MIX_FRAME_WIDTH, MIX_FRAME_HEIGHT)
                frame = sheet.subsurface(rect).copy()
                # 等比例縮放，不強制壓成正方形 (見 _scale_keep_aspect 註解)。
                # 這張圖的原始畫格是 16x32 (1:2 長寬比)，若強制縮放成
                # cell_size x cell_size 的正方形，會讓胡蘿蔔/藍莓等偏瘦高
                # 的作物看起來被橫向壓扁、變形。
                self.images[f"{crop_name}_{stage}"] = self._scale_keep_aspect(frame, cell_size)

    def _load_pig_frames(self):
        """
        切出 pig.png 的 4 方向步行循環 (每方向 4 幀)，回傳
        Dict[str, List[Surface]] (key 是 'down'/'right'/'up'/'left')，
        畫格維持精靈圖原始尺寸 (204x204)，縮放留給呼叫端依用途處理
        （血月首領跟野豬王要縮成不同大小，見 load_all()）。

        找不到檔案 / 切不出畫格時回傳 {}，呼叫端要自己 fallback 回
        原本的靜態圖片，不要讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, "characters/pig.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 characters/pig.png，血月首領/野豬王動畫將退回靜態圖片。")
            return {}

        try:
            # 背景是純黑色去背，不是 alpha 透明：用 .convert() (無 alpha
            # 通道) 載入，指定 colorkey 之後再 convert_alpha() 把去背色
            # 烤成真正的 per-pixel alpha。
            sheet = pygame.image.load(full_path).convert()
        except Exception as e:
            print(f"[AssetLoader] 載入 pig.png 失敗: {e}")
            return {}

        sheet.set_colorkey(BOSS_CHROMA_KEY, pygame.RLEACCEL)

        sheet_w, sheet_h = sheet.get_size()
        frame_width = sheet_w // SPRITE_COLS
        frame_height = sheet_h // SPRITE_ROWS
        if frame_width <= 0 or frame_height <= 0:
            print(f"[AssetLoader] pig.png 尺寸 {sheet.get_size()} 切不出 {SPRITE_COLS}x{SPRITE_ROWS} 的畫格。")
            return {}

        def _cut(row: int, col: int) -> pygame.Surface:
            rect = pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
            frame = sheet.subsurface(rect).copy()
            frame.set_colorkey(BOSS_CHROMA_KEY, pygame.RLEACCEL)
            return frame.convert_alpha()

        frames = {}
        for direction, row in BOSS_DIRECTION_ROWS.items():
            frames[direction] = [_cut(row, col) for col in WALK_CYCLE_INDICES]

        # left 不額外佔一列，直接把 right 的幀水平翻轉。
        frames["left"] = [pygame.transform.flip(f, True, False) for f in frames["right"]]

        return frames

    def _load_thief_frames(self):
        """
        切出 theif.png 的 4 方向 x 8 幀動畫，回傳 Dict[str, List[Surface]]
        (key 是 'down'/'right'/'left'/'up')，畫格維持精靈圖原始尺寸
        (128x142)，縮放留給呼叫端依格子大小處理。

        找不到檔案 / 切不出畫格時回傳 {}，呼叫端要自己 fallback 回
        原本的靜態 enemy_thief.png，不要讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, "characters/theif.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 characters/theif.png，小偷動畫將退回靜態圖片。")
            return {}

        try:
            # 背景本身就是真透明 (alpha=0)，不是純黑去背，直接用
            # convert_alpha() 讀取即可，不套用 colorkey（見上方常數註解）。
            sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 載入 theif.png 失敗: {e}")
            return {}

        sheet_w, sheet_h = sheet.get_size()
        frame_width = sheet_w // THIEF_COLS
        frame_height = sheet_h // THIEF_ROWS
        if frame_width <= 0 or frame_height <= 0:
            print(f"[AssetLoader] theif.png 尺寸 {sheet.get_size()} 切不出 {THIEF_COLS}x{THIEF_ROWS} 的畫格。")
            return {}

        def _cut(row: int, col: int) -> pygame.Surface:
            rect = pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
            return sheet.subsurface(rect).copy()

        frames = {}
        for direction, row in THIEF_DIRECTION_ROWS.items():
            frames[direction] = [_cut(row, col) for col in range(THIEF_COLS)]

        return frames

    def _load_dog_walk_frames(self):
        """
        切出 guard_dog_walk.png 的 4 方向走路動畫 + 白天坐姿待機動畫，
        回傳 (walk_frames, sit_frames) 兩個值：
          walk_frames: Dict[str, List[Surface]]，key 是 'down'/'right'/
            'left'/'up'，晚上依移動方向播放。
          sit_frames: List[Surface]，4 幀坐姿面對鏡頭，白天播放（狗不用
            出去咬人，改坐著待機）。
        兩組動畫共用同一張精靈圖，只讀一次檔案。畫格維持精靈圖原始尺寸
        (32x40)，縮放留給呼叫端依格子大小處理。

        找不到檔案 / 切不出畫格時兩者都回傳空值 ({}, [])，呼叫端要自己
        fallback 回原本的靜態 guard_dog.png，不要讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, "characters/guard_dog_walk.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 characters/guard_dog_walk.png，看門狗動畫將退回靜態圖片。")
            return {}, []

        try:
            # 背景是真透明 (alpha=0)，直接 convert_alpha() 讀取即可，
            # 不套用 colorkey（跟 theif.png 是同一種去背方式）。
            sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 載入 guard_dog_walk.png 失敗: {e}")
            return {}, []

        sheet_w, sheet_h = sheet.get_size()
        frame_width = sheet_w // DOG_WALK_COLS
        frame_height = sheet_h // DOG_WALK_ROWS_TOTAL
        if frame_width <= 0 or frame_height <= 0:
            print(f"[AssetLoader] guard_dog_walk.png 尺寸 {sheet.get_size()} 切不出 {DOG_WALK_COLS}x{DOG_WALK_ROWS_TOTAL} 的畫格。")
            return {}, []

        def _cut(row: int, col: int) -> pygame.Surface:
            rect = pygame.Rect(col * frame_width, row * frame_height, frame_width, frame_height)
            return sheet.subsurface(rect).copy()

        walk_frames = {}
        for direction, row in DOG_WALK_DIRECTION_ROWS.items():
            walk_frames[direction] = [_cut(row, col) for col in range(DOG_WALK_COLS)]

        sit_frames = [_cut(DOG_DAY_SIT_ROW, col) for col in range(DOG_WALK_COLS)]

        return walk_frames, sit_frames

    def _load_fence_tiles(self, size: Tuple[int, int]) -> Dict[int, pygame.Surface]:
        """
        切出 assets/Fences.png 的 16 種 4-bit bitmask 連接狀態，回傳
        Dict[int, Surface]（key 是 0~15 的 mask 值），已縮放成格子大小
        (size)。原始畫格是 16x16 正方形，縮放成 (cell_size, cell_size)
        不會有長條作物那種壓扁問題，可以放心直接等比縮放成正方形。

        找不到檔案 / 切不出畫格時回傳 {}，呼叫端要自己 fallback 回原本的
        單一 wooden_fence 靜態圖，不要讓遊戲直接壞掉。
        """
        full_path = os.path.join(ASSET_ROOT, "Fences.png")
        if not os.path.exists(full_path):
            print("[AssetLoader] 找不到 assets/Fences.png，柵欄將使用單一靜態圖片，不會自動連接。")
            return {}

        try:
            # 背景本身就是真透明 (alpha=0)，直接 convert_alpha() 讀取。
            sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 載入 assets/Fences.png 失敗: {e}")
            return {}

        sheet_w, sheet_h = sheet.get_size()
        expected_w = FENCE_FRAME_SIZE * FENCE_COLS
        expected_h = FENCE_FRAME_SIZE * FENCE_ROWS
        if sheet_w < expected_w or sheet_h < expected_h:
            print(f"[AssetLoader] Fences.png 尺寸 {sheet.get_size()} 切不出 {FENCE_COLS}x{FENCE_ROWS} 的畫格。")
            return {}

        tiles = {}
        for mask, (col, row) in BITMASK_MAP.items():
            rect = pygame.Rect(col * FENCE_FRAME_SIZE, row * FENCE_FRAME_SIZE, FENCE_FRAME_SIZE, FENCE_FRAME_SIZE)
            frame = sheet.subsurface(rect).copy()
            tiles[mask] = pygame.transform.scale(frame, size)

        return tiles

    def load_all(self):
        sz = (self.cell_size, self.cell_size)

        # 0. 地磚 Tiles
        self.images["grass_tile"] = self._load_image("tiles/grass_tile.png", sz)
        self.images["soil_tile"] = self._load_image("tiles/soil_tile.png", sz)
        
        # 1. 作物（單檔案 {name}_{stage}.png 讀取方式）
        # tomato / corn 已經改成從新的整合精靈圖切圖（見下面第 1b 節），
        # 這裡拿掉，避免先讀一次舊的 tomato_*.png / corn_*.png 再馬上被
        # 蓋掉的無意義 IO。carrot / blueberry 是全新作物（原本
        # eggplant / watermelon 改名），本來就沒有 xxx_seed.png 這種單檔，
        # 只能從新素材切，所以也不放進這個清單。
        crops = [
            ("radish", ["seed", "sprout", "growing", "mature"]),
            ("strawberry", ["seed", "sprout", "growing", "mature"]),
            ("pumpkin", ["seed", "sprout", "growing", "mature"]),
            ("sunflower", ["seed", "sprout", "growing", "mature"]),  # 小麥 (WHEAT) 目前還沿用這組舊圖
            ("grape", ["seed", "sprout", "growing", "mature"]),
            ("starlight", ["seed", "sprout", "growing", "mature"]),
        ]
        for cname, stages in crops:
            for st in stages:
                key = f"{cname}_{st}"
                self.images[key] = self._load_image(f"crops/{cname}_{st}.png", sz)

        # 1b. 新版整合精靈圖：玉米 (corn) + 胡蘿蔔/番茄/藍莓 (potato 素材
        # 目前遊戲沒有用到，切圖時略過)。切好的畫格直接塞進
        # self.images["corn_seed"] 這些跟舊格式相容的 key，渲染層完全
        # 不用改。
        self._load_corn_spritesheet(sz)
        self._load_carrot_tomato_blueberry_spritesheet(sz)

        # 2. 景觀 (13 種)
        decos = [
            ("stone_path", "decorations/stone_path.png"),
            ("flower_bed", "decorations/flower_bed.png"),
            ("garden_bench", "decorations/garden_bench.png"),
            ("pine_tree", "decorations/pine_tree.png"),
            ("apple_tree", "decorations/apple_tree.png"),
            ("sakura_tree", "decorations/sakura_tree.png"),
            ("soul_lantern", "decorations/soul_lantern.png"),
            ("bird_bath", "decorations/bird_bath.png"),
            ("ancient_statue", "decorations/ancient_statue.png"),
            ("fountain", "decorations/fountain.png"),
            ("pet_house", "decorations/pet_house.png"),
            ("sundial_tower", "decorations/sundial_tower.png"),
            ("windmill", "decorations/windmill.png"),
        ]
        for key, path in decos:
            self.images[key] = self._load_image(path, sz)

        # 3. 防禦設施與工具
        defs = [
            ("wooden_fence", "defenses/wooden_fence.png"),
            ("bear_trap", "defenses/bear_trap.png"),
            ("scarecrow", "defenses/scarecrow.png"),
            ("beehive", "defenses/beehive.png"),
            ("watering_can", "defenses/watering_can.png"),
            ("shovel", "defenses/shovel.png"),
            ("flashlight", "defenses/flashlight.png"),
        ]
        for key, path in defs:
            self.images[key] = self._load_image(path, sz)


        # 4. 生物角色
        chars = [
            ("guard_dog", "characters/guard_dog.png"),
            ("farm_cat", "characters/farm_cat.png"),
            ("enemy_thief", "characters/enemy_thief.png"),
            ("enemy_boar", "characters/enemy_boar.png"),
            ("enemy_bat", "characters/enemy_bat.png"),
            ("boss_boar", "characters/boss_boar.png"),
        ]
        for key, path in chars:
            self.images[key] = self._load_image(path, sz if key != "boss_boar" else (int(sz[0]*1.4), int(sz[1]*1.4)))

        # 5. 血月首領 / 野豬王的移動動畫 (共用同一張 pig.png，
        # 差別只有縮放後的大小 -- 野豬王用一般格子大小，血月首領放大 1.4x)
        pig_frames_native = self._load_pig_frames()
        boss_size = (int(sz[0] * 1.4), int(sz[1] * 1.4))
        if pig_frames_native:
            self.boss_frames: Dict[str, list] = {
                d: [pygame.transform.scale(f, boss_size) for f in frames]
                for d, frames in pig_frames_native.items()
            }
            self.enemy_boar_frames: Dict[str, list] = {
                d: [pygame.transform.scale(f, sz) for f in frames]
                for d, frames in pig_frames_native.items()
            }
        else:
            # pig.png 還沒放進 assets/characters/，或切圖失敗時，
            # 兩個字典都是空的——渲染層要檢查並退回 boss_boar / enemy_boar
            # 靜態圖，不會讓遊戲壞掉。
            self.boss_frames: Dict[str, list] = {}
            self.enemy_boar_frames: Dict[str, list] = {}

        # 6. 小偷 (theif.png) 的 4 方向 x 8 幀移動動畫，縮放成一般格子大小。
        thief_frames_native = self._load_thief_frames()
        if thief_frames_native:
            self.thief_frames: Dict[str, list] = {
                d: [pygame.transform.scale(f, sz) for f in frames]
                for d, frames in thief_frames_native.items()
            }
        else:
            # theif.png 還沒放進 assets/characters/，或切圖失敗時，
            # 空字典——渲染層要檢查並退回 enemy_thief 靜態圖，不會讓遊戲壞掉。
            self.thief_frames: Dict[str, list] = {}

        # 6.5 看門柴犬 (guard_dog_walk.png) 的 4 方向走路動畫 (晚上用) +
        # 坐姿待機動畫 (白天用)，縮放成一般格子大小，寫法跟上面的小偷
        # 動畫對稱。
        dog_walk_frames_native, dog_sit_frames_native = self._load_dog_walk_frames()
        if dog_walk_frames_native:
            self.dog_walk_frames: Dict[str, list] = {
                d: [pygame.transform.scale(f, sz) for f in frames]
                for d, frames in dog_walk_frames_native.items()
            }
        else:
            # guard_dog_walk.png 還沒放進 assets/characters/，或切圖失敗
            # 時，空字典——渲染層要檢查並退回 guard_dog 靜態圖，不會讓
            # 遊戲壞掉。
            self.dog_walk_frames: Dict[str, list] = {}
        self.dog_sit_frames: list = [pygame.transform.scale(f, sz) for f in dog_sit_frames_native]

        # 7. 柵欄 (Fences.png) 的 16 種 4-bit bitmask 自動連接畫格。
        self.fence_tiles: Dict[int, pygame.Surface] = self._load_fence_tiles(sz)

    def get(self, key: str) -> pygame.Surface:
        return self.images.get(key)
