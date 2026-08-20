"""
夜巡農場 (Nightwatch Farm) - 素材圖像載入器 (AssetLoader)
自動載入 assets/ 目錄下的所有透明 PNG 圖片（10種作物、13種景觀、防禦與生物）。
"""

import os
import pygame
from typing import Dict, Tuple, Optional

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
    def __init__(self, cell_size: int = 50, screen_size: Tuple[int, int] = (1260, 800)):
        self.cell_size = cell_size
        # 【系統升級：動態劇情背景圖切換】title_bg/bg_crash/
        # bg_iron_flower 這三張全螢幕背景圖都要縮放成「整個遊戲視窗
        # 大小」，但 SCREEN_WIDTH/SCREEN_HEIGHT 這兩個常數
        # 定義在 advanced_nightwatch_farm-v3.py（呼叫端），asset_loader.py
        # 不能反過來 import 那個檔案（那會是循環 import：主程式本來就要
        # import 這個檔案裡的 AssetLoader）。改成呼叫端在建立 AssetLoader
        # 時把 (SCREEN_WIDTH, SCREEN_HEIGHT) 當參數傳進來，這裡存成
        # self.screen_size 給 load_all() 用；預設值 (1260, 800) 只是防呆
        # （例如其他測試腳本直接 AssetLoader() 不傳這個參數時仍能正常
        # 運作），實際遊戲執行時一律由主程式傳入當下真正的螢幕尺寸。
        self.screen_size = screen_size
        self.images: Dict[str, pygame.Surface] = {}
        # 視覺升級：熔爐 Sprite Sheet 特定影格動畫。
        #
        # 這裡沒有沿用使用者要求的 self.assets['furnace_anim'] 這個命名，
        # 是因為 self.assets 這個屬性在整個專案裡從來不存在——AssetLoader
        # 一直以來唯一的存放處都是 self.images（單一 Surface，靠 get()
        # 取用）。如果硬塞一個 self.assets 字典進來，會跟既有的 self.images
        # 命名慣例互相打架，還會讓人誤以為兩者是同一份資料。改用一個平行
        # 的 self.building_anim_frames: Dict[str, list[Surface]]，維持
        # get() 「回傳單一 Surface 或 None」的既有契約不被破壞，動畫幀
        # 另外透過 get_anim_frames() 取用，兩條路徑互不干擾。
        self.building_anim_frames: Dict[str, list] = {}
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

    # 視覺升級：動態生成佔位圖 (Procedural Placeholder) 系統。
    #
    # name -> 底色/特徵分類的對照表。用「category」這個明確參數而不是
    # 完全靠字串猜測，是為了避開一個真實存在的地雷：這個專案既有的
    # 資產鍵名裡，"sundial_tower"（向日葵叢景觀）這個 key 本身就含有
    # "tower" 這個字，如果 generate_placeholder() 純粹用「name 裡有沒
    # 有出現 tower 關鍵字」來判斷要不要畫成防禦塔樣式，會把向日葵叢的
    # 佔位圖誤判成金屬防禦塔，畫出完全不搭的視覺。所以這裡採用「呼叫端
    # 明確指定 category 優先；沒指定才退回關鍵字猜測」的兩層設計——
    # load_all() 裡新增的 7 種機台資產一律明確傳入 category，不會誤
    # 判；generate_placeholder() 本身仍然保留關鍵字猜測邏輯，滿足「根據
    # name 給予不同底色」的原始需求，只是這條路徑目前只有在呼叫端沒有
    # 明確指定 category 時才會生效。
    _PLACEHOLDER_KEYWORDS = {
        "furnace": ("furnace", "oven", "kiln", "熔", "爐", "窯", "烤", "焦"),
        "lumberyard": ("lumberyard", "伐木"),
        "tower": ("tesla", "turret", "防禦塔"),
        # 視覺升級：32x32 富鐵花，新增一個作物專屬分類。這次是這個專案
        # 第一個「作物」有自己的佔位圖分類——其餘 10 種既有作物完全沒有
        # 對應的關鍵字，會繼續落到最後的通用半透明灰色方塊；只有這裡
        # 特別加分類是因為使用者這次明確供了成熟階段的真實美術規格
        # （綠色色鍵），值得順手讓「圖檔還沒放上去之前」的過渡期也有一個
        # 看得出來是「礦物/金屬」的佔位圖，而不是跟其他作物一樣的灰色
        # 方塊，之後真的放上 iron_flower.png 就會自動蓋掉這個佔位圖。
        "iron_flower": ("iron_flower",),
    }

    def _infer_placeholder_category(self, name: str) -> Optional[str]:
        key = (name or "").lower()
        for category, keywords in self._PLACEHOLDER_KEYWORDS.items():
            for kw in keywords:
                if kw in key:
                    return category
        return None

    def generate_placeholder(self, name: str, size: Tuple[int, int],
                              category: Optional[str] = None) -> pygame.Surface:
        """在沒有外部 PNG 圖檔時，依照 name/category 生成一張有基本辨識
        度的佔位圖，取代原本「隨便畫一個半透明灰色方塊」的做法。三種
        目前有實作特徵的分類：
          furnace     機台/熔爐/烤箱/炭窯類：深灰底 + 下方橘紅色矩形
                      （代表爐火/加熱）。
          lumberyard  伐木場：棕色底 + 幾條深色橫線（代表木紋/原木堆疊）。
          tower       防禦塔（目前這個專案還沒有實際的防禦塔建築類型，
                      這個分類先實作起來，供未來新增防禦塔類建築時直接
                      使用，不用等到那時候才回頭補這個函式）：金屬銀色
                      底 + 頂部一個亮藍色小圓形（代表塔頂的感應器/砲台）。
          iron_flower 富鐵花（成熟階段）：草綠色底 + 中央一顆灰色/銀白
                      色同心圓（代表花蕊包著的鐵礦），只有這個佔位圖
                      是給「作物」用的，其餘作物沒有專屬分類。
          其他/無法辨識 沿用專案原本的半透明灰色方塊風格，不強加不合適
                      的視覺，維持向下相容——原本能正常顯示（不管是真的
                      有 PNG，還是走這個 fallback）的東西，行為不變。
        不論哪一種分類，最後都會在 Surface 邊緣描一圈深色框線，讓格子
        在地圖上多一點立體感，這是所有分類共用的收尾動作。"""
        w, h = size
        surf = pygame.Surface(size, pygame.SRCALPHA)
        cat = category or self._infer_placeholder_category(name)

        if cat == "furnace":
            pygame.draw.rect(surf, (58, 58, 64), (0, 0, w, h))
            flame_w = max(4, int(w * 0.5))
            flame_h = max(4, int(h * 0.35))
            flame_rect = pygame.Rect((w - flame_w) // 2, h - flame_h - max(2, h // 12), flame_w, flame_h)
            pygame.draw.rect(surf, (224, 92, 38), flame_rect, border_radius=3)
        elif cat == "lumberyard":
            pygame.draw.rect(surf, (122, 86, 53), (0, 0, w, h))
            grain_color = (84, 57, 33)
            grain_lines = 3
            for i in range(grain_lines):
                gy = int(h * (i + 1) / (grain_lines + 1))
                pygame.draw.line(surf, grain_color, (max(2, w // 12), gy), (w - max(2, w // 12), gy),
                                  max(1, h // 20))
        elif cat == "tower":
            pygame.draw.rect(surf, (168, 172, 180), (0, 0, w, h))
            radius = max(3, w // 6)
            pygame.draw.circle(surf, (58, 150, 255), (w // 2, max(radius + 2, int(h * 0.28))), radius)
        elif cat == "iron_flower":
            # 富鐵花（成熟階段）：草綠色底代表花株本體，中央疊一顆偏灰
            # 帶一點金屬光澤的圓點代表花蕊裡包著的鐵礦，跟其餘作物共用
            # 的通用灰色方塊區分開，一眼能看出「這是會產礦物的作物」。
            pygame.draw.rect(surf, (58, 120, 62), (0, 0, w, h))
            core_r = max(4, int(min(w, h) * 0.28))
            pygame.draw.circle(surf, (150, 150, 158), (w // 2, h // 2), core_r)
            pygame.draw.circle(surf, (196, 196, 204), (w // 2, h // 2), max(2, core_r // 2))
        else:
            pygame.draw.rect(surf, (200, 200, 200, 150), (4, 4, w - 8, h - 8), border_radius=4)

        # 統一收尾：邊緣描一圈深色框線做出立體感。格子太小 (< 24px) 時
        # 用 1px 框，避免細框線把整個小圖塊吃掉大半面積；正常尺寸用 2px。
        border_width = 1 if min(w, h) < 24 else 2
        pygame.draw.rect(surf, (28, 28, 32), surf.get_rect(), width=border_width)
        return surf

    def _load_image(self, rel_path: str, size: Tuple[int, int],
                     name: Optional[str] = None, category: Optional[str] = None) -> pygame.Surface:
        """載入一張圖片；找不到檔案或載入失敗（格式錯誤/毀損等）都會被
        這裡的 except 攔下來，統一改呼叫 generate_placeholder() 生成佔
        位圖，不會讓遊戲直接壞掉。這裡刻意不再像舊版那樣先用
        os.path.exists() 判斷檔案存不存在、只在「檔案存在但載入失敗」
        時才印警告——現在不管是「檔案根本不存在」還是「檔案存在但讀取
        失敗」，都會走同一條 pygame.image.load() 呼叫，由 except 統一
        攔截處理，行為更單純、也更貼近使用者這次要求的「攔截例外錯
        誤」寫法。只有在檔案確實存在、卻還是載入失敗時才印出警告訊息
        （檔案單純不存在是這個專案目前的常態——很多素材本來就還沒畫，
        不需要每次啟動都印一堆「找不到檔案」的雜訊）。"""
        full_path = os.path.join(ASSET_ROOT, rel_path)
        try:
            img = pygame.image.load(full_path).convert_alpha()
            return pygame.transform.scale(img, size)
        except Exception as e:
            if os.path.exists(full_path):
                print(f"[AssetLoader] 載入 {rel_path} 失敗: {e}")
            placeholder_name = name or os.path.splitext(os.path.basename(rel_path))[0]
            return self.generate_placeholder(placeholder_name, size, category=category)

    def _load_1x4_spritesheet(self, key: str, rel_path: str, target_size: Tuple[int, int],
                               colorkey: Optional[Tuple[int, int, int]] = None,
                               placeholder_category: Optional[str] = None) -> None:
        """系統修復：通用的「單排 4 幀 (1x4) 水平 Sprite Sheet」切圖器。

        取代前一階段兩個各自為政的舊寫法：熔爐/伐木場共用的 3x3 九宮格
        切法 (_load_building_anim_frames())，以及富鐵花專用、只切一張
        靜態圖的 _load_iron_flower_mature()（已整個刪除，不再保留）。
        使用者這次明確說明新素材（伐木場_3.jpg / 富鐵花.png）是同一種
        規格：單排橫向 4 格，不是 3x3，也不是單張圖，兩者共用這一份
        邏輯。熔爐目前沒有換新素材，還是沿用舊的
        _load_building_anim_frames()，這個函式不影響熔爐。

        去背邏輯依 colorkey 參數決定：
          colorkey 給實際顏色（例如伐木場的黑色 (0,0,0)）：一律用
            convert() + set_colorkey(colorkey)。.jpg 格式本身不可能帶
            alpha 通道，伐木場素材是 .jpg，不用另外判斷。
          colorkey 是 None（富鐵花的情況）：自動偵測——用
            pygame.image.load() 讀出來的原始 Surface 的 get_masks()[3]
            （alpha 遮罩）是否非 0，判斷來源檔案是否原生就有 alpha
            通道；有的話直接 convert_alpha()（沿用專案裡其餘 PNG 素材
            的標準做法）；沒有的話退回 convert() +
            set_colorkey((255, 255, 255))（視為白底去背），符合使用者
            「若有 Alpha 通道則直接 convert_alpha()，否則視為白底
            set_colorkey」的規格描述。

        找不到檔案、載入失敗、或切出來的單幀尺寸異常（寬或高 <= 0，
        通常代表來源圖檔根本不是 1x4 格式）都會印出提示，並且改用
        generate_placeholder() 生成 4 張佔位圖頂替，而不是讓
        self.building_anim_frames 完全沒有這個 key。這裡刻意跟舊版
        _load_building_anim_frames()（載入失敗就直接 return、完全不寫
        任何佔位動畫幀）不一樣：熔爐/伐木場是「建築」，就算動畫幀載入
        失敗，_render_building_tile() 還有 self.images[key] 這條「buildings
        清單載入的靜態備援圖」可以退回；但富鐵花是「作物」，沒有這樣一
        條備援路徑，如果這裡不自己補佔位幀，取用端
        (`get_anim_frames("iron_flower")`) 拿到空 list 時，渲染邏輯完全
        沒東西可畫，富鐵花會在成熟階段整格消失不見，比其他任何素材缺
        失時的體驗都差，所以統一在這裡補齊，不管是哪個呼叫端都保證拿
        到 4 張非 None 的 Surface。

        成功時額外把 self.images[key] 覆寫成 frame[0]（跟舊版
        _load_building_anim_frames() 同一個慣例），讓商店卡片
        （ActionCard.draw() 只呼叫 loader.get(asset_key)，不知道動畫幀
        這回事）也能顯示真的貼圖。
        """
        full_path = os.path.join(ASSET_ROOT, rel_path)

        def _make_placeholder_frames() -> list:
            return [self.generate_placeholder(f"{key}_{i}", target_size, category=placeholder_category)
                    for i in range(4)]

        if not os.path.exists(full_path):
            print(f"[AssetLoader] 提示：{rel_path} 不存在，{key} 動畫將使用佔位圖，不影響遊戲運作。")
            self.building_anim_frames[key] = _make_placeholder_frames()
            return

        try:
            raw = pygame.image.load(full_path)
            has_alpha = colorkey is None and raw.get_masks()[3] != 0
            if has_alpha:
                sheet = raw.convert_alpha()
            else:
                sheet = raw.convert()
                sheet.set_colorkey(colorkey if colorkey is not None else (255, 255, 255))

            sheet_w, sheet_h = sheet.get_size()
            frame_w, frame_h = sheet_w // 4, sheet_h
            if frame_w <= 0 or frame_h <= 0:
                print(f"[AssetLoader] 警告：{rel_path} 尺寸異常 ({sheet_w}x{sheet_h})，"
                      f"無法切出 1x4 影格，{key} 動畫將使用佔位圖。")
                self.building_anim_frames[key] = _make_placeholder_frames()
                return

            frames = []
            for i in range(4):
                rect = pygame.Rect(i * frame_w, 0, frame_w, frame_h)
                frame = sheet.subsurface(rect).copy()
                frames.append(pygame.transform.scale(frame, target_size))

            self.building_anim_frames[key] = frames
            self.images[key] = frames[0]
        except Exception as e:
            print(f"[AssetLoader] 警告：{rel_path} 載入失敗（{e}），{key} 動畫將使用佔位圖。")
            self.building_anim_frames[key] = _make_placeholder_frames()

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
            # 富鐵花 (CropType.IRON_FLOWER) 刻意不放進這個清單——【系統
            # 修復：1x4 精準切圖】階段改成整個作物（種子/幼苗/成長中/
            # 成熟四個視覺狀態）統一從同一張 1x4 Sprite Sheet
            # (crops/富鐵花.png) 切出來，用連續成長比例挑幀，不是像其餘
            # 作物一樣靠 "{asset_key}_{stage}" 這套離散 per-stage 檔名去
            # 查表。載入呼叫在下面 3e.（跟伐木場的 1x4 素材共用同一個
            # _load_1x4_spritesheet() 輔助函式），渲染層的挑幀邏輯見
            # advanced_nightwatch_farm-v3.py 的
            # _render_flat_meadow_and_farm() 說明。
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
        ]
        for key, path in decos:
            self.images[key] = self._load_image(path, sz)

        # 【系統邏輯更新：替換風車外觀為藍頂木屋】"windmill" 這個 key
        # 原本也在上面 decos 清單裡、單純用 _load_image() 讀
        # decorations/windmill.png（1x1 純景觀，商店卡片顯示名稱其實
        # 早就是「莊園木屋」，只有這個內部 key 名稱還留著舊的
        # "windmill"，故意不改 key/asset_key，避免牽動
        # DECORATION_DATA/商店卡片/存檔相容性，單純換底圖）。這次改成
        # 讀 assets/decorations/House_1_Wood_Base_Blue.png，並單獨拉出
        # 這段防呆邏輯——不確定新圖是單張靜態圖還是 1x4 Sprite Sheet：
        #   寬度 >= 高度的 3 倍以上，視為 1x4 橫向 Sprite Sheet，沿用
        #   既有的 _load_1x4_spritesheet() 切成 4 幀（它本身就會在成功
        #   時把 self.images["windmill"] 覆寫成 frame[0]，商店卡片/地圖
        #   渲染都能正常拿到圖）。
        #   否則視為單張靜態圖，直接縮放成 sz（景觀目前一律是 1x1 單格，
        #   不是 2x2——跟 FURNACE/LUMBERYARD/SPRINKLER 這種有 is_active/
        #   動畫迴圈的「建築」不同，DECORATION_DATA 完全沒有 "size"
        #   欄位、_render_flat_meadow_and_farm() 畫景觀時也是單純
        #   `self.loader.get(k)` 拿一張 Surface 貼在單一格子上，不會走
        #   任何 get_anim_frames() 逐幀播放的邏輯，所以這裡刻意不套用
        #   使用者規格裡「2x2 網格」的尺寸，避免圖片被放大成 2 格卻只
        #   貼在 1 格的座標上，蓋到隔壁格子），同時仍然把
        #   self.building_anim_frames["windmill"] 補上 [image]*4，跟
        #   Sprite Sheet 分支輸出的資料形狀一致、也符合使用者要求的
        #   「動畫陣列只包含這一張圖，避免渲染迴圈報錯」——目前沒有任何
        #   呼叫端會真的去讀這個 key 的動畫幀（景觀渲染完全不看
        #   get_anim_frames()），但先備著，之後如果想把這棟木屋升級成
        #   有動畫的正式「建築」，這份資料已經是正確格式，不用重新切圖。
        windmill_path = os.path.join(ASSET_ROOT, "decorations/House_1_Wood_Base_Blue.png")
        windmill_is_spritesheet = False
        if os.path.exists(windmill_path):
            try:
                raw = pygame.image.load(windmill_path)
                img_w, img_h = raw.get_size()
                windmill_is_spritesheet = img_h > 0 and img_w >= img_h * 3
            except Exception as e:
                print(f"[AssetLoader] 讀取 decorations/House_1_Wood_Base_Blue.png 尺寸失敗: {e}")

        if windmill_is_spritesheet:
            self._load_1x4_spritesheet("windmill", "decorations/House_1_Wood_Base_Blue.png", sz,
                                        colorkey=None, placeholder_category=None)
        else:
            windmill_img = self._load_image("decorations/House_1_Wood_Base_Blue.png", sz, name="windmill")
            self.images["windmill"] = windmill_img
            self.building_anim_frames["windmill"] = [windmill_img] * 4

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

        # 3b. 加工機台/生產設施（烤箱/熔爐/炭窯/伐木場/礦場/灑水器/自動
        # 採收機）。視覺升級（熔爐動畫）階段已移除 OVEN/KILN，目前剩 5
        # 個 asset_key，從 Phase 2 起就一直存在於
        # BUILDING_DATA 裡（_render_building_tile() 會呼叫
        # self.loader.get(asset_key)），但 AssetLoader 之前從來沒有真的
        # 幫這些 key 呼叫過 _load_image()——self.images 字典裡根本沒有
        # 這幾個 key，get() 永遠回傳 None，所以畫面上一直是
        # _render_building_tile() 自己手畫的色塊 + 文字圖示這條退回路
        # 徑，從來沒有機會走到「有貼圖就用貼圖」那個分支。這次視覺升級
        # 補上這幾個 key 的載入呼叫，assets/buildings/ 底下目前還沒有
        # 對應的 PNG（本來就還沒畫），所以一定會透過 _load_image() 的
        # except 分支落到 generate_placeholder()，改用有底色/特徵區分
        # 的動態佔位圖取代原本 _render_building_tile() 手畫的純色塊。
        # category 這裡明確指定，不靠 asset_key 字串去猜——避免日後這幾
        # 個 key 命名調整時，猜測邏輯悄悄失準也不會發現。
        # 視覺升級（熔爐動畫）階段：使用者要求整批移除 OVEN（烤箱）跟
        # KILN（炭窯）這兩個建築，這裡同步拿掉 "oven"/"kiln" 兩筆載入
        # 呼叫，避免載入兩個已經不會被任何 BuildingType 用到的 key。
        # 系統大重構 Phase 7：MINE（礦場）連同它的 asset_key 載入呼叫一併
        # 移除——BuildingType.MINE 已經從 game_config.py 整批刪除，這裡
        # 留著會去讀一個已經不存在於 BUILDING_DATA 的 key，且畫面上也
        # 沒有任何建築會再用到 "mine" 這個 asset_key，屬於死代碼。
        # UI 視覺優化（2x2 建築圖片放大）階段：FURNACE/LUMBERYARD 在
        # game_config.py 的 BUILDING_DATA 已經改成 "size": (2, 2)，貼圖
        # 如果還是照舊縮放到單格 CELL_SIZE，畫在地圖上就只會佔滿 2x2
        # 範圍裡的左上角那 1/4 面積（_render_building_tile() 用
        # midbottom 置中對齊整個 2x2 範圍，圖片本身太小只是「置中飄在
        # 一大塊空白裡」，不是真的把圖放大）。這裡刻意不匯入
        # game_config.BUILDING_DATA 去查 size——asset_loader.py 目前完全
        # 不依賴 game_config（只認得純字串 key/路徑），為了兩張圖的縮放
        # 尺寸而新增一條模組間耦合不划算，改用一份只在載入層自己使用的
        # 簡單對照表，跟 BUILDING_DATA["size"] 的值手動保持一致即可
        # （目前只有這兩座建築是 2x2，沒有的 key 一律預設 (1, 1)，維持
        # 原本單格大小）。
        BUILDING_SPRITE_GRID_SPAN = {
            "furnace": (2, 2),
            "lumberyard": (2, 2),
            # 【系統更新：自動灑水器 2x2 建築邏輯】跟 game_config.py
            # BUILDING_DATA[SPRINKLER]["size"] 手動保持一致。
            "sprinkler": (2, 2),
        }
        buildings = [
            ("furnace", "buildings/furnace.png", "furnace"),
            ("lumberyard", "buildings/lumberyard.png", "lumberyard"),
            # 【系統更新：自動灑水器 2x2 建築邏輯】跟 furnace/lumberyard
            # 同一個理由補上這筆：下面 _load_1x4_spritesheet("sprinkler",
            # ...) 成功時會覆寫 self.images["sprinkler"] = frames[0]，
            # 但如果 decorations/灑水器.png 缺檔或載入失敗，
            # _load_1x4_spritesheet() 只會補 building_anim_frames，不會
            # 補 self.images——這裡先用這份清單把 self.images["sprinkler"]
            # 賦值成一張佔位圖（buildings/sprinkler.png 目前也還沒放進
            # assets/，一樣會走 generate_placeholder()），保證商店卡片
            # （ActionCard.draw() 只呼叫 loader.get("sprinkler")，不知道
            # 動畫幀那條路徑）不管哪一層載入失敗都至少有圖可以顯示，不
            # 會是空白卡片。
            ("sprinkler", "buildings/sprinkler.png", "sprinkler"),
        ]
        for key, path, category in buildings:
            span_w, span_h = BUILDING_SPRITE_GRID_SPAN.get(key, (1, 1))
            building_sz = (self.cell_size * span_w, self.cell_size * span_h)
            self.images[key] = self._load_image(path, building_sz, name=key, category=category)

        # 3c. 熔爐 Sprite Sheet 特定影格動畫 (assets/decorations/熔爐.png)。
        # 只切第一排 3 格，縮放到跟上面 buildings 清單一樣的 sz
        # (CELL_SIZE x CELL_SIZE)，存進 self.building_anim_frames["furnace"]。
        # 上面 buildings 清單裡 ("furnace", "buildings/furnace.png",
        # "furnace") 這一筆仍然保留——那張圖目前不存在，
        # self.images["furnace"] 原本會落到 generate_placeholder()，是
        # 「動畫幀也載入失敗時」的第二層防呆退回路徑。但這次追加需求
        # 要求建造選單卡片（ActionCard.draw() 直接呼叫
        # loader.get(asset_key)，不會走動畫幀那條路徑）也要顯示真的熔爐
        # 圖，所以 _load_building_anim_frames() 切出動畫幀成功時，會
        # 順手把 self.images["furnace"] 覆寫成 frame[0]（靜態幀），這樣
        # 商店卡片、以及任何其他呼叫 loader.get("furnace") 的地方都能拿
        # 到真圖，不用另外為卡片渲染寫一條專用邏輯；地圖上蓋好的熔爐
        # 建築本體則是靠 _render_building_tile() 優先檢查
        # get_anim_frames("furnace") 播放 3 幀動畫。
        # UI 視覺優化（2x2 建築圖片放大）階段：熔爐動畫幀改傳
        # building_sz（= 2 * cell_size，跟上面 3b. 靜態圖載入時同一份
        # BUILDING_SPRITE_GRID_SPAN 對照表算出來的尺寸一致），畫格切出
        # 來之後才不會比 3b. 那筆靜態備援圖小一半、兩者對齊不起來。
        # pygame.transform.scale()（非 smoothscale）本身就是不做內插的
        # 最近鄰縮放，放大 2 倍後像素邊緣依然銳利，不會糊掉——這也是
        # _load_building_anim_frames() 內部畫格縮放一直在用的函式，不用
        # 額外改成 pygame.transform.scale2x()（scale2x 是專門的邊緣感知
        # 演算法，僅支援固定的整數倍放大，這裡的 span 是讀 BUILDING_DATA
        # 算出來的一般化倍率，用泛用的 pygame.transform.scale() 更符合
        # 「以後這兩張圖以外的建築也可能是不同尺寸」的彈性）。
        furnace_span_w, furnace_span_h = BUILDING_SPRITE_GRID_SPAN.get("furnace", (1, 1))
        furnace_sz = (self.cell_size * furnace_span_w, self.cell_size * furnace_span_h)
        self._load_building_anim_frames("furnace", "decorations/熔爐.png", furnace_sz)

        # 3d. 伐木場 Sprite Sheet 特定影格動畫。
        # 【檔名修正】使用者一開始說的檔名是 decorations/伐木場_3.jpg，
        # 但那個檔案從頭到尾都沒有真的放進 assets/（雲端環境跟裝置上都
        # 用 device_list_dir/find 確認過），後來使用者改口直接指定用
        # 既有的 decorations/伐木場.png（這個檔案先前已經被使用者換成
        # 新內容，用 PIL 實際檢查過尺寸是 1024x254——寬度剛好整除 4，
        # 是這次 1x4 規格，不是先前的 3x3 九宮格）。
        # colorkey 這裡改傳 None（原本是寫死 (0,0,0)）：實際用 PIL 抽樣
        # 檢查過這張 PNG 的像素，背景本來就是真正 alpha=0 透明，而且
        # 抽樣範圍內找得到「顏色接近黑色、但 alpha 不透明」的像素（伐木
        # 場本體的黑色描邊/陰影線條）——如果照舊寫死 set_colorkey
        # ((0,0,0))，這些本來就不透明的黑色像素會被一併挖空，變成有破
        # 洞的貼圖。這張圖其實不是 .jpg（不可能帶 alpha），是已經有原生
        # alpha 透明度的 .png，改傳 colorkey=None 讓
        # _load_1x4_spritesheet() 的自動偵測邏輯直接走 convert_alpha()
        # 那條路徑，保留原生透明度，不會誤挖黑色描邊。縮放尺寸沿用跟
        # 3b./3c. 同一份 BUILDING_SPRITE_GRID_SPAN 對照表算出來的 2x2
        # 大小，跟建築本體佔地格數、_render_building_tile() 的
        # span_w/span_h 定位公式保持一致。
        lumberyard_span_w, lumberyard_span_h = BUILDING_SPRITE_GRID_SPAN.get("lumberyard", (1, 1))
        lumberyard_sz = (self.cell_size * lumberyard_span_w, self.cell_size * lumberyard_span_h)
        self._load_1x4_spritesheet("lumberyard", "decorations/伐木場.png", lumberyard_sz,
                                    colorkey=None, placeholder_category="lumberyard")

        # 3d-2. 自動灑水器 Sprite Sheet 特定影格動畫。
        # 【系統更新：自動灑水器 2x2 建築邏輯】使用者已經把
        # decorations/灑水器.png 放進 assets/，明確說明是「1x4 的橫向
        # 長條圖」——跟伐木場/富鐵花是同一種規格，直接沿用同一份通用的
        # _load_1x4_spritesheet()，不需要另外寫一套載入邏輯。
        #
        # colorkey 傳 None：需求文字寫「若背景為純白則 set_colorkey
        # ((255,255,255))，若有 Alpha 通道則 convert_alpha()」，這正是
        # _load_1x4_spritesheet() 內部 colorkey=None 時的既有自動偵測
        # 行為（讀 raw.get_masks()[3] 判斷來源圖是否原生帶 alpha，有就
        # convert_alpha()，沒有就退回 convert() + set_colorkey
        # ((255,255,255))），完全符合規格描述，不用另外手寫判斷式。
        #
        # 縮放尺寸用跟 3b./3c./3d. 同一份 BUILDING_SPRITE_GRID_SPAN 對照
        # 表算出來的 sprinkler_sz（2 * cell_size，也就是需求裡的
        # tile_size * 2），跟 game_config.py 這次新增的
        # BUILDING_DATA[SPRINKLER]["size"] = (2, 2) 對齊，
        # _render_building_tile() 既有的 span_w/span_h 定位公式不用改
        # 就能正確處理這個新的 2x2 建築。
        #
        # placeholder_category 這裡刻意留 None（不新增一個
        # "sprinkler" 專屬佔位圖分類）：找不到檔案時會退回
        # generate_placeholder() 最泛用的半透明灰色方塊，不影響遊戲
        # 運作，之後如果想要更有辨識度的佔位圖，可以再仿照
        # _PLACEHOLDER_KEYWORDS 裡 "furnace"/"lumberyard" 的寫法加一組
        # 專屬分類，這次不在需求範圍內，不順手多做。
        sprinkler_span_w, sprinkler_span_h = BUILDING_SPRITE_GRID_SPAN.get("sprinkler", (1, 1))
        sprinkler_sz = (self.cell_size * sprinkler_span_w, self.cell_size * sprinkler_span_h)
        self._load_1x4_spritesheet("sprinkler", "decorations/灑水器.png", sprinkler_sz,
                                    colorkey=None, placeholder_category=None)

        # 3e. 富鐵花 (CropType.IRON_FLOWER) 成熟視覺。
        # 【檔名修正】使用者一開始說的檔名是 crops/富鐵花.png，同樣沒有
        # 真的放進 assets/，後來改口指定用既有的 crops/iron_flower.png
        # （這個檔案是更早一版單張 32x32 綠色色鍵素材的舊檔名，但使用者
        # 已經把內容換成新的 1024x254、寬度整除 4 的 1x4 素材——用 PIL
        # 實際檢查過，不是原本的 32x32）。colorkey 繼續傳 None，
        # _load_1x4_spritesheet() 的自動偵測邏輯會檢查到這張圖也是原生
        # alpha 透明（PIL 抽樣確認過），一樣直接走 convert_alpha()，不會
        # 誤用白底色鍵去背。縮放尺寸是 sz（單一格 CELL_SIZE x
        # CELL_SIZE，1x1，不是伐木場的 2x2）。這裡切出來的 4 幀不是
        # 「不同生長階段各自一張獨立圖」的舊架構，而是渲染層依連續成長
        # 比例挑幀（見 advanced_nightwatch_farm-v3.py 的
        # _render_flat_meadow_and_farm() 說明），所以刻意不再把
        # "iron_flower_seed"/"_sprout"/"_growing"/"_mature" 這幾個
        # per-stage key 塞進上面的 crops 清單。
        # 【修復：重新綁定路徑】富鐵花作物本體的路徑改回
        # crops/iron_flower.png（上一版曾經改成 crops/bg_iron_flower.png
        # ——但那其實是同一次改動裡另外新增、給 STORY 開場劇情用的全
        # 螢幕背景圖 assets/bg_iron_flower.png 搞混了路徑；作物本體跟
        # 劇情背景圖是兩張完全不同用途、不同尺寸規格的圖，這次改回
        # crops/iron_flower.png 才是正確的作物 sprite sheet 路徑）。
        #
        # 切圖邏輯本身完全不用改，也不需要另外手寫一套新的載入程式碼
        # ——_load_1x4_spritesheet()（定義見上方，約第 283 行）本來就
        # 已經完整實作了這次需求描述的每一個步驟：
        #   - frame_w, frame_h = sheet_w // 4, sheet_h（單幀尺寸計算）
        #   - colorkey=None 時自動偵測 raw.get_masks()[3]：有 alpha 就
        #     convert_alpha()，沒有就退回 convert() +
        #     set_colorkey((255, 255, 255))（視為白底去背）
        #   - 橫向切 4 格、pygame.transform.scale() 縮放成 sz（單一格
        #     CELL_SIZE x CELL_SIZE，1x1 網格大小）
        #   - 4 幀存進 self.building_anim_frames["iron_flower"]，透過
        #     get_anim_frames("iron_flower") 取用
        # 這裡只需要換路徑字串，不需要另外新增一套平行的載入邏輯。
        self._load_1x4_spritesheet("iron_flower", "crops/iron_flower.png", sz,
                                    colorkey=None, placeholder_category="iron_flower")

        # 【系統升級：動態劇情背景圖切換】三張全螢幕劇情/選單背景圖，
        # 統一強制縮放至 self.screen_size（呼叫端傳入的 (SCREEN_WIDTH,
        # SCREEN_HEIGHT)），讓它們剛好貼滿整個遊戲視窗。
        #
        # 使用者這次明確指出三張圖「目前都統一放在 assets/ 根目錄
        # 下」，不是 crops/ 子目錄——路徑因此都是 rel_path 直接給檔名，
        # 不带 "crops/" 前綴。上一版 main_menu_bg 讀的是
        # "crops/bg_crash.png"（子目錄），這次改成 "bg_crash.png"（根
        # 目錄）；同時把上一版單獨的 main_menu_bg key 併入這組統一的
        # 三張圖清單，key 直接命名成 "bg_crash"，跟 title_bg/
        # bg_iron_flower 用同一套 key 命名風格（也是
        # advanced_nightwatch_farm-v3.py 主選單改讀 "bg_crash" 這個 key
        # 的原因），不再維護一個名稱不一致、單獨存在的 "main_menu_bg"。
        #
        # 這裡刻意存進既有的 self.images（用 get(key) 取用），不是使用
        # 者需求文字裡寫的 self.assets[...]——AssetLoader 這個類別從頭
        # 到尾都只有 self.images 這一個「單一 Surface、靠 get() 取用」
        # 的字典（見 __init__ 裡 self.building_anim_frames 那段既有註
        # 解，之前就因為同樣理由特地不引入 self.assets 這個新字典，避
        # 免兩套命名並存互相打架），這次沿用同一個既有慣例，不新增第二
        # 套存放機制。
        #
        # 用既有的 _load_image() 而不是 _load_1x4_spritesheet()：這三張
        # 都是單張完整的背景場景圖，不是 4 幀 Sprite Sheet，_load_image()
        # 本來就是給「單張圖片、縮放到指定尺寸、找不到就退回佔位圖」這
        # 種需求用的既有共用函式，不用另外寫新邏輯。
        #
        # 特別注意 "bg_iron_flower" 這個 key 跟上面第 3e 節
        # "crops/bg_iron_flower.png" 是兩張完全不同的圖、走完全不同的
        # 用途：上面那張是農田格子上富鐵花作物本體的 1x4 sprite sheet
        # （key="iron_flower"，透過 get_anim_frames() 取用），這裡這張
        # 是劇情畫面用的全螢幕背景場景圖（key="bg_iron_flower"，透過
        # get() 取用單一 Surface），兩者恰好都叫 bg_iron_flower.png、
        # 但實際檔案路徑不同（"crops/bg_iron_flower.png" vs 根目錄的
        # "bg_iron_flower.png"）、key 也刻意取得不一樣（"iron_flower"
        # vs "bg_iron_flower"），不會互相覆蓋。
        # 【系統修復與文本重構：綁定劇情背景圖與農場風文本全面替換】
        # 遊戲從「硬派外星求生」轉型成「溫馨奇幻農場」，這三張全螢幕
        # 背景圖的 key/檔名也跟著劇情一起換血：bg_crash（墜毀太空船）
        # 改成 bg_abandoned（荒廢已久的祖傳農莊），bg_iron_flower（富鐵
        # 花的宿主星球）改成 bg_premium_crop（劇情裡那株會發光的特級
        # 農產）。title_bg 維持不變。使用者需求文字裡寫的是
        # self.assets[key] = ...load(...)，但 AssetLoader 從頭到尾只有
        # self.images 這一個字典（見上方既有註解，避免跟 self.assets
        # 兩套命名並存），這裡繼續沿用既有慣例，透過 get(key) 取用。
        for bg_key, bg_filename in (
            ("title_bg", "title_bg.png"),
            ("bg_abandoned", "bg_abandoned.png"),
            ("bg_premium_crop", "bg_premium_crop.png"),
        ):
            self.images[bg_key] = self._load_image(bg_filename, self.screen_size, name=bg_key)

        # 目前這個專案的 DefenseType 只有刺藤木柵/鋼鐵捕獸夾/農田稻草人/
        # 蜜蜂守衛巢四種，實際貼圖都已經存在於 assets/defenses/ 底下（見
        # 上面的 defs 清單），完全不會走到 generate_placeholder() 的
        # fallback，所以這裡沒有東西需要為「防禦塔 (tower)」這個分類
        # 補上載入呼叫——tower 這個分類是主動預留給未來如果新增電磁塔/
        # 砲塔類防禦建築時直接使用，屆時只要在這裡（或 game_config.py
        # 新增 DefenseType 之後對應的位置）用跟上面 buildings 一樣的寫
        # 法、指定 category="tower" 呼叫 _load_image() 即可，不用再回頭
        # 修改 generate_placeholder() 本身。

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

        # 8. 彈窗 (暫停選單/遊戲結束畫面) 用的木紋九宮格 (9-slice) 貼圖。
        # 這兩張圖目前 (assets/ui/ 底下只有 flashlight.png / shovel.png)
        # 還不存在，所以以下只是「先把載入邏輯寫好、貼圖一放進去就自動
        # 生效」的預留鉤子——不存在時保持原尺寸不做 _load_image 的
        # cell_size 強制縮放 (九宮格繪製函式 draw_9_slice() 需要吃原始
        # 解析度的貼圖自己去切邊角，如果先被縮到跟格子一樣大，九宮格的
        # 邊框比例會跑掉)，且完全不寫進 self.images，讓呼叫端
        # `loader.get("ui_wood_panel")` 拿到 None，自動觸發
        # draw_wood_panel() 裡的 draw_beveled_rect() 後備方案，不會讓
        # 遊戲壞掉或噴例外。
        for ui_key, ui_rel_path in (
            ("ui_wood_panel", "ui/wood_panel.png"),
            ("ui_wood_button", "ui/wood_button.png"),
        ):
            ui_full_path = os.path.join(ASSET_ROOT, ui_rel_path)
            if os.path.exists(ui_full_path):
                try:
                    self.images[ui_key] = pygame.image.load(ui_full_path).convert_alpha()
                except Exception as e:
                    print(f"[AssetLoader] 警告：{ui_rel_path} 載入失敗（{e}），"
                          f"彈窗將退回立體木頭色塊繪製。")
            else:
                print(f"[AssetLoader] 提示：{ui_rel_path} 尚未放進 assets/ui/，"
                      f"彈窗將先用立體木頭色塊 (draw_beveled_rect) 繪製，"
                      f"之後放上真的九宮格貼圖會自動生效，不用改程式碼。")

    def get(self, key: str) -> pygame.Surface:
        return self.images.get(key)

    def get_anim_frames(self, key: str) -> list:
        """回傳指定 key 的動畫影格列表；沒有的話回傳空 list（不是
        None），讓呼叫端可以直接用 `if frames:` 判斷，不用另外防 None。
        """
        return self.building_anim_frames.get(key, [])

    def _load_building_anim_frames(self, key: str, rel_path: str, size: Tuple[int, int],
                                    frame_count: int = 3) -> None:
        """
        視覺升級：3x3 Sprite Sheet 特定影格提取（熔爐/伐木場共用同一套
        邏輯）。sheet 一律是 3 欄 x 3 列共 9 格的網格，frame_count 決定
        實際要用幾格：
          - frame_count=3：只切第一排 (Y=0) 的 3 格 (X=0, 1, 2)，索引
            3~8（第二、三排）不讀取——熔爐用這個模式，「經典像素跳動
            感」只需要 3 幀（見 furnace 呼叫端的說明）。
          - frame_count=9：把全部 9 格依「先橫向再往下一列」的順序
            (row-major：0,1,2 是第一排，3,4,5 第二排，6,7,8 第三排)
            全部切出來——伐木場用這個模式，使用者原始需求明確說「為了
            呈現鋸木頭的流暢動態，請提取所有的 9 個影格」，鋸木頭這種
            動作比熔爐的火焰跳動更需要多張過渡影格才不會看起來卡頓。

        使用者原始需求提到的檔名是 furnace_anim.jpg / 伐木場.jpg，但
        實際放進 assets/decorations/ 的檔案分別是「熔爐.png」「伐木場
        .png」——這裡直接用真實存在的檔名，不是照著需求文字裡的假設
        檔名去找一個不存在的檔案。

        使用者也要求「用 set_colorkey((0,0,0)) 去背」，但用 PIL 實際
        檢查過這兩張圖後發現：兩張都是背景本來就是真正 alpha=0 透明的
        RGBA PNG（不是不透明黑底的 JPG），而且兩張圖裡都找得到「顏色
        接近黑色、但 alpha 是不透明」的像素（熔爐第一格內 7,156 個、
        伐木場第一格內 414 個抽樣命中）——這些是機台本體的黑色描邊/
        陰影線條。如果照字面上跑 set_colorkey((0,0,0))，pygame 只看
        RGB 顏色比對、不管原本的 alpha 狀態，會把這些本來就不透明的
        黑色像素一併挖空，畫面上會變成有破洞的貼圖。所以這裡只呼叫
        convert_alpha() 保留圖片原生的 alpha 透明度，不呼叫
        set_colorkey()——這個作法跟專案裡所有其他真實 PNG 素材的載入
        方式（decos/defs/chars 清單）完全一致。
        """
        full_path = os.path.join(ASSET_ROOT, rel_path)
        if not os.path.exists(full_path):
            print(f"[AssetLoader] 提示：{rel_path} 不存在，"
                  f"{key} 動畫將退回既有的安全字元/色塊繪製，不影響遊戲運作。")
            return
        try:
            sheet = pygame.image.load(full_path).convert_alpha()
        except Exception as e:
            print(f"[AssetLoader] 警告：{rel_path} 載入失敗（{e}），"
                  f"{key} 動畫將退回既有的安全字元/色塊繪製。")
            return

        sheet_w, sheet_h = sheet.get_size()
        cell_w, cell_h = sheet_w // 3, sheet_h // 3
        if cell_w <= 0 or cell_h <= 0:
            print(f"[AssetLoader] 警告：{rel_path} 尺寸異常 ({sheet_w}x{sheet_h})，"
                  f"無法切出 3x3 網格，{key} 動畫將退回既有繪製方式。")
            return

        frames = []
        for i in range(frame_count):
            col = i % 3
            row = i // 3
            cell_rect = pygame.Rect(col * cell_w, row * cell_h, cell_w, cell_h)
            frame = sheet.subsurface(cell_rect).copy()
            # 縮放到跟其他建築貼圖一致的 CELL_SIZE（呼叫端傳進來的
            # size），不是需求文字裡的範例尺寸 32x32/40x40——那兩個數字
            # 只是舉例，真正要對齊的是這個專案實際的地圖網格尺寸，否則
            # 這座機台會比同排的其他建築明顯小一圈或大一圈。
            frames.append(pygame.transform.scale(frame, size))
        self.building_anim_frames[key] = frames
        # 額外把 self.images[key] 覆寫成 frame[0]（閒置幀），這樣建造
        # 選單卡片（ActionCard.draw() 只呼叫 loader.get(asset_key)，不知
        # 道動畫幀這回事）也能顯示真的貼圖，不用另外為卡片渲染寫一條
        # 專用邏輯——地圖上蓋好的建築本體則交給 _render_building_tile()
        # 優先用 get_anim_frames() 播放完整的動畫幀。
        self.images[key] = frames[0]
