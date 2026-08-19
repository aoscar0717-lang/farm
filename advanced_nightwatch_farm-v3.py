"""
夜巡農場 (Nightwatch Farm) - 純色扁平極簡風 (Flat Minimalist) 客戶端
核心升級：
1. 【5級莊園等級系統】擴展至 10 種農作物、13 種莊園景觀佈置！
2. 【5 秒強光手電筒充能】即時 CD 倒數顯示，戰術更具節奏感！
3. 【蜂巢與向日葵清晰區分】蜂巢採用深木吊掛支架與六角琥珀木條紋巢柱，向日葵為金色向陽大花盤！
4. 【防偷懶機制】空田過夜將洗劫中央金庫 35% 金幣，守護作物過夜享 +50% 月光滋養金幣加成！
"""

import sys
import os
import math
import random
from typing import List, Tuple, Optional, Dict, Any

# pygame.SCALED (used by the F11 fullscreen toggle below) upscales the
# fixed SCREEN_WIDTH x SCREEN_HEIGHT canvas to the real display via an
# SDL2 renderer. SDL2's default scale quality is linear/smoothed, which
# blurs pixel-art sprites badly once stretched past 1:1 -- setting this
# hint to "0" (nearest-neighbor) before pygame.init() keeps scaled-up
# frames crisp instead of blurry, matching the game's pixel-art look.
# Must be set before pygame.init() / the first set_mode() call.
os.environ.setdefault("SDL_RENDER_SCALE_QUALITY", "0")

import pygame

# 告訴 Windows 系統這個程式支援高 DPI，不要強制進行模糊縮放。沒有這行時，
# Windows 會把整個視窗當成一般「不支援 DPI」的舊程式，用作業系統層級的點陣
# 縮放把畫面拉伸到符合系統顯示設定的縮放比例（通常是 125%/150%），這層
# 拉伸跟上面 SDL_RENDER_SCALE_QUALITY 是兩回事、Pygame 完全不知情也管不到，
# 疊加在一起就是「明明已經設定 nearest-neighbor 了，畫面卻還是糊」的原因。
# 必須在 pygame.init() 之前呼叫（更精確地說是在第一次建立視窗之前），才能
# 阻止 Windows 對這個程式套用相容性縮放。
if os.name == 'nt':
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from game_config import (
    GamePhase, ZoneType, CropType, CropStage, DecorationType,
    DefenseType, EnemyType, EnemyState, DogState, EventType,
    MAP_CONFIG, FARM_LEVELS, CROP_DATA, DECORATION_DATA, DEFENSE_DATA,
    DOG_CONFIG, CAT_CONFIG, ENEMY_DATA, GameEvent
)
from game_state import GameState
from sound_manager import SoundManager
from asset_loader import AssetLoader

pygame.init()
pygame.font.init()

# ==========================================
# 視覺尺寸與純色扁平調色盤 (Flat Color Palette)
# ==========================================
SCREEN_WIDTH = 1260
SCREEN_HEIGHT = 800
FPS = 60

CELL_SIZE = 50
GRID_X = 24
GRID_Y = 86

# 扁平現代色彩
C_MEADOW_BG = (230, 235, 225)       # 純色柔和綠草地
C_FARM_SOIL = (205, 195, 175)        # 純色溫暖農田底色
C_FARM_SHADOW = (180, 142, 102)      # 農田投影
C_FARM_BORDER = (156, 116, 78)       # 苗圃外框色

C_NAVY_TOP = (38, 50, 56)           # 頂部導航底色
C_WHITE = (255, 255, 255)
C_CARD_BG = (255, 255, 255)
C_CARD_BORDER = (224, 224, 224)

C_TEXT_MAIN = (33, 33, 33)
C_TEXT_MUTED = (117, 117, 117)
C_GOLD = (255, 193, 7)
C_GREEN = (76, 175, 80)
C_RED = (239, 83, 80)
C_BLUE = (33, 150, 243)
C_PURPLE = (156, 39, 176)
C_CYAN = (0, 188, 212)
C_ORANGE = (255, 152, 0)
C_BLOOD_RED = (211, 47, 47)


# ------------------------------------------------------------------
# 中文字型載入 (fixes "□" tofu-box rendering)
#
# 舊寫法的問題：pygame.font.match_font(name) 對 SDL 來說是很寬鬆的模糊比對，
# 就算清單裡四個名字全部比對失敗，match_font 也常常不會回傳 None，而是回退到
# 隨便一個系統預設字型（通常是 Arial 之類的西方字型），完全不含中文字形，
# 於是遊戲畫面上的中文字全部變成「□」豆腐塊，而且不會有任何錯誤訊息。
#
# 新寫法分兩層 Fallback，優先順序如下：
#   1. 專案自帶字型：assets/fonts/ 底下第一個 .ttf/.ttc/.otf 檔（最可靠，
#      不依賴玩家電腦裝了什麼系統字型，換一台機器也保證看得到中文）。
#      要掛載開源中文字體，只要把 .ttf 檔案丟進 assets/fonts/ 資料夾即可，
#      不用改任何程式碼，例如思源黑體 Traditional Chinese (Noto Sans TC)：
#      https://fonts.google.com/noto/specimen/Noto+Sans+TC
#   2. 系統字型：改用 pygame.font.get_fonts() 列出「這台機器真的偵測到」的
#      字型名單，再跟一份跨平台的中文字型名稱清單取交集，而不是像舊寫法
#      直接盲猜 match_font 一定會成功。
#   3. 都找不到才退回 Arial，並在終端機印出明確警告，而不是默默顯示豆腐塊。
# ------------------------------------------------------------------
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

_CJK_SYSTEM_FONT_HINTS = [
    # Windows
    "microsoftjhenghei", "microsoftjhengheiui", "microsoftjhengheiuibold",
    "microsoftyahei", "microsoftyaheiui", "simhei", "simsun", "mingliu", "dfkaisb",
    # macOS
    "pingfangtc", "pingfangsc", "pingfang", "heititc", "heitisc", "stheititc", "stheitisc",
    # Linux
    "notosanscjktc", "notosanscjksc", "notosanscjk", "wqymicrohei", "wqyzenhei",
    "droidsansfallback",
]


def _find_bundled_font_path() -> Optional[str]:
    if not os.path.isdir(FONT_DIR):
        return None
    for fn in sorted(os.listdir(FONT_DIR)):
        if fn.lower().endswith((".ttf", ".ttc", ".otf")):
            return os.path.join(FONT_DIR, fn)
    return None


def _find_system_cjk_font_path() -> Optional[str]:
    try:
        available = set(pygame.font.get_fonts())
    except Exception:
        return None
    for hint in _CJK_SYSTEM_FONT_HINTS:
        if hint in available:
            match = pygame.font.match_font(hint)
            if match:
                return match
    return None


_BUNDLED_FONT_PATH = _find_bundled_font_path()
_SYSTEM_CJK_FONT_PATH = None if _BUNDLED_FONT_PATH else _find_system_cjk_font_path()
_RESOLVED_FONT_PATH = _BUNDLED_FONT_PATH or _SYSTEM_CJK_FONT_PATH

if _RESOLVED_FONT_PATH is None:
    print(
        "[字型警告] 找不到可顯示中文的字型，UI 文字可能會顯示「□」。"
        f"請把一個中文 .ttf/.ttc/.otf 字型檔放進 {FONT_DIR} 資料夾"
        "（例如思源黑體 Noto Sans TC），程式下次啟動會自動優先使用它，"
        "不需要改任何程式碼。"
    )


# ------------------------------------------------------------------
# 缺字符 "☒" 方塊修復
#
# 中文字型已經正常顯示了，但字串裡摻的 Emoji/特殊符號（🌾🔦💰⚔️ 等）不在
# assets/fonts/NotoSansTC-GameSubset.otf 的字集裡（那個字型本身就沒有
# emoji 字形，不是子集裁切掉的），font.render 遇到字型裡真的沒有的字形，
# SDL_ttf 就會畫出一個「缺字符方塊」(☒)。
#
# 採用最穩定的做法：不逐一去改 42 處 .render() 呼叫、也不去改
# game_config.py 或這個檔案裡每一條字串常數（emoji 到處都是，改字串很
# 容易漏），而是在唯一的共同關卡上做一次過濾——用 _SafeFont 包住
# pygame.font.Font，攔截每一次 .render() 呼叫，渲染前先用 safe_text()
# 把字型不支援的字元濾掉。因為所有畫面文字都是透過 FONT_XS/FONT_SM/
# FONT_MD/FONT_LG/FONT_TITLE 這幾個物件呼叫 .render()，只要在這裡包一層，
# 不管是寫死的字串常數還是動態組出來的日誌訊息，全部自動套用，不會漏掉。
# ------------------------------------------------------------------
_SAFE_TEXT_ALLOWED_RANGES = (
    (0x0020, 0x007E),   # ASCII 可印字元（含基本英數字與標點）
    (0x00A0, 0x00FF),   # Latin-1 補充（少數帶重音的字母，安全字元）
    (0x2010, 0x2027),   # 一般標點（連接號、引號、刪節號等）
    (0x3000, 0x303F),   # CJK 標點符號（、。「」【】等）
    (0x3400, 0x4DBF),   # CJK 擴充 A
    (0x4E00, 0x9FFF),   # CJK 統一表意文字（絕大多數中文字都在這個區段）
    (0xF900, 0xFAFF),   # CJK 相容表意文字
    (0xFF00, 0xFFEF),   # 全形符號（全形括號、標點等）
)


def safe_text(text) -> str:
    """把字串裡任何落在允許範圍外的字元濾掉（主要是 Emoji、Dingbats、
    Misc Symbols 這些目前綁定字型沒有字形的字元），確保丟進 font.render
    的字串一定乾淨，不會跑出缺字符方塊「☒」。"""
    if not text:
        return text
    text = str(text)
    return "".join(
        ch for ch in text
        if any(lo <= ord(ch) <= hi for lo, hi in _SAFE_TEXT_ALLOWED_RANGES)
    )


class _SafeFont:
    """包住 pygame.font.Font 的輕量代理：.render() 前自動呼叫 safe_text()
    過濾，其他方法（.size()、.get_height() 等）原封不動轉發給底層字型，
    行為跟直接用 pygame.font.Font 完全一樣，呼叫端不需要知道有這層包裝。"""

    def __init__(self, font: pygame.font.Font):
        self._font = font

    def render(self, text, antialias, color, *args, **kwargs):
        return self._font.render(safe_text(text), antialias, color, *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._font, name)


def get_font(size: int, bold: bool = False):
    if _RESOLVED_FONT_PATH:
        try:
            f = pygame.font.Font(_RESOLVED_FONT_PATH, size)
            f.set_bold(bold)
            return _SafeFont(f)
        except Exception:
            pass
    return _SafeFont(pygame.font.SysFont('arial', size, bold=bold))

FONT_XS = get_font(12)
FONT_SM = get_font(14)
FONT_MD = get_font(16, bold=True)
FONT_LG = get_font(20, bold=True)
FONT_TITLE = get_font(26, bold=True)


# ==========================================
# 粒子與浮動文字
# ==========================================
class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, size: float, life: float):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.max_life = life
        self.life = life

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.size = max(0.5, self.size * (self.life / self.max_life))
        return self.life > 0

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        s = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
        c = (self.color[0], self.color[1], self.color[2], alpha)
        pygame.draw.circle(s, c, (int(self.size), int(self.size)), int(self.size))
        surface.blit(s, (int(self.x - self.size), int(self.y - self.size)))


class FloatingText:
    def __init__(self, text: str, x: float, y: float, color=(255, 255, 255), duration: float = 1.2):
        self.text = text
        self.x = x
        self.y = y
        self.color = color
        self.duration = duration
        self.elapsed = 0.0

    def update(self, dt: float) -> bool:
        self.elapsed += dt
        self.y -= 24.0 * dt
        return self.elapsed < self.duration

    def draw(self, surface):
        alpha = max(0, min(255, int(255 * (1.0 - (self.elapsed / self.duration)))))
        stroke = FONT_MD.render(self.text, True, (20, 20, 20))
        stroke.set_alpha(alpha)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            surface.blit(stroke, (int(self.x + dx), int(self.y + dy)))
            
        t_surf = FONT_MD.render(self.text, True, self.color)
        t_surf.set_alpha(alpha)
        surface.blit(t_surf, (int(self.x), int(self.y)))


# ==========================================
# 扁平操作卡片 (Action Card)
# ==========================================
# 分類色，用來給側邊商店的圖示底框、選中卡片的左側色條上色，
# 跟舊版側欄「作物=綠/景觀=紫/設施=藍」的配色邏輯一致，只是從純文字
# 說明搬到卡片本身上色。
SHOP_TAB_TINTS = {
    "CROPS": (76, 175, 80),      # C_GREEN
    "DECO": (156, 39, 176),      # C_PURPLE
    "DEFENSE": (33, 150, 243),   # C_BLUE
    "TOOLS": (230, 81, 0),       # 深橘，跟主動工具（手電筒/哨子）的警示感呼應
}


class ActionCard:
    def __init__(self, action_id: str, label: str, cost_text: str, tab_id: str, asset_key: str, rect: pygame.Rect):
        self.action_id = action_id
        self.label = label
        self.cost_text = cost_text
        self.tab_id = tab_id
        self.asset_key = asset_key
        self.rect = rect
        self.is_hovered = False
        self.is_locked = False
        self.lock_reason = ""

    def draw(self, surface, is_selected: bool, loader: AssetLoader):
        tint = SHOP_TAB_TINTS.get(self.tab_id, C_ORANGE)

        # 輕微投影：往右下偏移畫一塊半透明深色，營造卡片浮起的立體感。
        shadow = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (20, 25, 30, 35), shadow.get_rect(), border_radius=10)
        surface.blit(shadow, (self.rect.x + 2, self.rect.y + 3))

        bg_col = (255, 255, 255)
        if self.is_locked:
            bg_col = (243, 243, 243)
        elif is_selected:
            bg_col = (255, 249, 230)
        elif self.is_hovered:
            bg_col = (250, 250, 252)

        pygame.draw.rect(surface, bg_col, self.rect, border_radius=10)

        border_col = C_ORANGE if is_selected else ((215, 215, 220) if not self.is_hovered else tint)
        border_w = 2 if (is_selected or self.is_hovered) else 1
        pygame.draw.rect(surface, border_col, self.rect, width=border_w, border_radius=10)

        # 選中時左側加一條實色色條，跟分類色呼應，一眼就能認出裝備中的項目。
        if is_selected:
            accent = pygame.Rect(self.rect.x, self.rect.y + 6, 4, self.rect.height - 12)
            pygame.draw.rect(surface, C_ORANGE, accent, border_radius=2)

        # 圖示放進一塊淡色圓角底框裡，而不是直接貼在卡片背景上，質感更豐富。
        icon_bg = pygame.Rect(self.rect.x + 8, self.rect.y + (self.rect.height - 50) // 2, 50, 50)
        icon_tint = tuple(min(255, c + 165) for c in tint)
        pygame.draw.rect(surface, icon_tint if not self.is_locked else (232, 232, 232), icon_bg, border_radius=10)
        icon_surf = loader.get(self.asset_key)
        if icon_surf:
            if self.is_locked:
                icon_surf = icon_surf.copy()
                icon_surf.set_alpha(110)
            surface.blit(icon_surf, icon_bg.topleft)

        text_x = icon_bg.right + 12
        lbl_col = C_TEXT_MUTED if self.is_locked else C_TEXT_MAIN
        lbl_y = self.rect.y + (self.rect.height // 2 - 22 if self.cost_text else self.rect.height // 2 - 10)
        surface.blit(FONT_MD.render(self.label, True, lbl_col), (text_x, lbl_y))

        if self.cost_text:
            cost_col = C_RED if self.is_locked else (230, 81, 0)
            surface.blit(FONT_SM.render(self.cost_text, True, cost_col), (text_x, lbl_y + 22))

        if self.is_locked:
            # 半透明深色遮罩蓋住整張卡片（圖示/文字都被壓暗），讓玩家一眼
            # 就能看出這張卡片「目前點不了」，而不用等點下去才有反應。
            # (Note: we use border_radius=10 to match our new aesthetics)
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(overlay, (20, 20, 20, 128), overlay.get_rect(), border_radius=10)
            surface.blit(overlay, self.rect.topleft)

            # 遮罩之上疊印紅色解鎖條件文字（蓋掉原本售價那一行），
            # 例如「🔒 需繁榮度 50」或「🔒 需 Lv.2」，說明「為什麼」點不了。
            if self.lock_reason:
                lock_surf = FONT_SM.render(f"🔒 {self.lock_reason}", True, (255, 130, 130))
                # Using text_x and lbl_y+22 so it aligns with the new layout
                surface.blit(lock_surf, (text_x, lbl_y + 22))
            else:
                lock_surf = FONT_XS.render("🔒", True, (255, 130, 130))
                if lock_surf.get_width() > 0:
                    surface.blit(lock_surf, (self.rect.right - 22, self.rect.y + 8))


# ==========================================
# 主遊戲視窗 (NightwatchFarmApp)
# ==========================================
class NightwatchFarmApp:
    def __init__(self):
        # 全螢幕切換 (F11)：邏輯解析度固定在 SCREEN_WIDTH x SCREEN_HEIGHT，
        # 全螢幕時加上 pygame.SCALED，讓 SDL2 自動把這個邏輯畫面等比例縮放、
        # 置中貼到實際螢幕解析度上（畫面比例不會跑掉，多出來的部分自動黑邊）。
        # SCALED 也會自動幫滑鼠事件座標做對應換算，所以 _handle_mouse_move /
        # _handle_mouse_down 裡讀 event.pos 的邏輯完全不用改。
        self.is_fullscreen = False
        self.screen = self._create_display(fullscreen=False)
        pygame.display.set_caption("夜巡農場 (Nightwatch Farm) - 經典精緻像素塔防農場")
        self.clock = pygame.time.Clock()
        
        self.game = GameState()
        self.sound = SoundManager(sfx_enabled=True)
        self.loader = AssetLoader(cell_size=CELL_SIZE)
        
        self.show_intro = True
        self.show_pause_menu = False
        self.active_tab = "CROPS"
        self.selected_action = "PLANT_RADISH"
        
        self.floating_texts = []
        self.particles = []
        self.log_messages = ["🌾 歡迎來到夜巡農場！精緻像素莊園，中央為農田與防線，四周為景觀與寵物！"]
        self.hovered_grid = None
        self.mouse_pos = (0, 0)
        self.anim_time = 0.0
        self.sound.play_bgm(is_day=True)
        # Time-scale control -- 0.1 級距微調 (0.0 暫停 ~ 2.0 二倍速)。
        # 用 +/-0.1 直接運算取代查表，TIME_SCALE_MIN/MAX/STEP 只是夾值用的
        # 邊界常數，不再是一份固定速度清單。
        self.time_scale = 1.0
        self.time_scale_before_pause = 1.0
        self.TIME_SCALE_MIN = 0.0
        self.TIME_SCALE_MAX = 2.0
        self.TIME_SCALE_STEP = 0.1
        # 滑鼠可點擊的倍速面板 [-]/[+] 按鈕 Rect，畫面每幀在
        # _render_header_banner() 裡重新算好存起來，_handle_mouse_down()
        # 讀這兩個值判斷有沒有點中。開場動畫還沒畫過第一幀時是 None，
        # 點擊判斷要先檢查非 None 再 collidepoint，避免第一幀點擊噴例外。
        self.btn_speed_down_rect = None
        self.btn_speed_up_rect = None

        self.flash_vfx_timer = 0.0
        self._init_ui()

    def _init_ui(self):
        # 商店已經搬到右側面板（原本「即時狀態探測」的位置），窄面板
        # (294px 寬) 放不下原本橫向的長標籤，改成 2x2 格的短標籤。
        # rect 先放 Rect(0,0,0,0) 佔位，實際位置由 _layout_shop_tabs()
        # 每一幀依面板座標算出來（跟卡片列表一樣，位置不是寫死的）。
        self.tab_buttons = [
            ("CROPS", "農田耕作 (10)", pygame.Rect(0, 0, 0, 0)),
            ("DECO", "莊園景觀 (13)", pygame.Rect(0, 0, 0, 0)),
            ("DEFENSE", "防禦寵物 (6)", pygame.Rect(0, 0, 0, 0)),
            ("TOOLS", "主動工具 (4)", pygame.Rect(0, 0, 0, 0)),
        ]
        # 商店改成側邊直向可捲動清單，捲動位置每個分頁各自獨立記憶。
        self.shop_scroll = {"CROPS": 0, "DECO": 0, "DEFENSE": 0, "TOOLS": 0}

        self.cards_by_tab = {
            "CROPS": [
                ("PLANT_RADISH", "白蘿蔔", "$10 | 4s熟", "radish_mature"),
                ("PLANT_STRAWBERRY", "鮮甜草莓", "$20 | 6s熟", "strawberry_mature"),
                ("PLANT_TOMATO", "紅番茄", "$35 | 8s熟", "tomato_mature"),
                ("PLANT_CARROT", "胡蘿蔔", "$55 | 12s熟", "carrot_mature"),
                ("PLANT_PUMPKIN", "巨型金南瓜", "$80 | 15s熟", "pumpkin_mature"),
                ("PLANT_CORN", "香甜玉米", "$110 | 18s熟", "corn_mature"),
                ("PLANT_WHEAT", "小麥", "$140 | 20s熟", "sunflower_mature"),
                ("PLANT_BLUEBERRY", "藍莓", "$180 | 24s熟", "blueberry_mature"),
                ("PLANT_GRAPE", "皇家紫葡萄", "$220 | 26s熟", "grape_mature"),
                ("PLANT_STARLIGHT", "永恆星光果", "$300 | 30s熟", "starlight_mature"),
            ],
            "DECO": [
                ("PLACE_PATH", "石板小徑", "$20 | +10繁榮", "stone_path"),
                ("PLACE_FLOWER", "鮮花盆栽", "$35 | +20繁榮", "flower_bed"),
                ("PLACE_BENCH", "休閒木椅", "$45 | +30繁榮", "garden_bench"),
                ("PLACE_PINE", "針葉松樹", "$50 | +35繁榮", "pine_tree"),
                ("PLACE_APPLE_TREE", "紅葉楓樹", "$60 | +40繁榮", "apple_tree"),
                ("PLACE_LANTERN", "夜巡路燈", "$75 | +50繁榮", "soul_lantern"),
                ("PLACE_SAKURA_TREE", "莊園大樹", "$85 | +55繁榮", "sakura_tree"),
                ("PLACE_BIRD_BATH", "森林野菇", "$95 | +65繁榮", "bird_bath"),
                ("PLACE_STATUE", "神秘寶箱", "$110 | +75繁榮", "ancient_statue"),
                ("PLACE_PET_HOUSE", "木材柴堆", "$130 | +90繁榮", "pet_house"),
                ("PLACE_FOUNTAIN", "野餐竹籃", "$160 | +110", "fountain"),
                ("PLACE_SUNDIAL", "向日葵叢", "$220 | +160", "sundial_tower"),
                ("PLACE_WINDMILL", "莊園木屋", "$300 | +220", "windmill"),
            ],
            "DEFENSE": [
                ("PLACE_FENCE", "原木木柵", "$15 | 阻擋+反傷", "wooden_fence"),
                ("PLACE_TRAP", "地刺陷阱", "$20 | 120傷害", "bear_trap"),
                ("PLACE_SCARECROW", "農田稻草人", "$35 | 驚嚇小偷", "scarecrow"),
                ("PLACE_BEEHIVE", "蜜蜂守衛巢", "$85 | 自動射擊", "beehive"),
                ("BUY_DOG", "看門柴犬", "$100 | 夜間撲咬", "guard_dog"),
                ("BUY_CAT", "招財小雞", "$80 | 白天贈金", "farm_cat"),
            ],
            "TOOLS": [
                ("SHOVEL", "鐵鏟 / 拆除", "免費 | 挖除退80%", "shovel"),
                ("WATER_CROP", "黃金澆水壺", "$5 | 加速50%", "watering_can"),
                ("FLASHLIGHT", "強光手電筒", "就緒 | 3s充能", "flashlight"),
                ("WHISTLE", "守衛指揮哨", "免費 | 指揮狗狗衝刺", "guard_dog"),
            ]

        }

        # 側邊商店是單欄直向清單，每張卡片的實際 y 座標要扣掉捲動位移，
        # 是動態值不是固定值，這裡先用佔位 Rect，實際位置交給
        # _layout_shop_list()（跟商店面板背景、點擊判定共用同一份幾何
        # 常數，畫面畫哪裡跟滑鼠點得到哪裡保證是同一組數字）。
        self.action_cards = []
        for tab_id, items in self.cards_by_tab.items():
            for act_id, lbl, cost, asset_key in items:
                r = pygame.Rect(0, 0, 0, 0)
                self.action_cards.append(ActionCard(act_id, lbl, cost, tab_id, asset_key, r))

    def _create_display(self, fullscreen: bool):
        flags = (pygame.FULLSCREEN | pygame.SCALED) if fullscreen else (pygame.RESIZABLE | pygame.SCALED)
        return pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)

    def _toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.screen = self._create_display(self.is_fullscreen)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse_move(event)
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_mouse_wheel(event)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and self.show_intro:
                        self.show_intro = False
                    elif event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    elif event.key == pygame.K_r and self.game.game_over:
                        self.game = GameState()
                        self.log_messages.clear()
                        self.log_messages.append("🌾 遊戲已重新開始！")
                    elif event.key == pygame.K_SPACE:
                        self.log_messages.append("💡 提示：請點選下方工具列【強光手電筒】，用滑鼠直接點擊敵人發射強光照暈！")
                    elif event.key == pygame.K_p:
                        if self.time_scale > 0:
                            self.time_scale_before_pause = self.time_scale
                            self.time_scale = 0.0
                            self.log_messages.append("⏸ 已暫停")
                        else:
                            # 記住暫停前的速度（可能是 1.5 這種 0.1 級距值，
                            # 不是只能回到 1.0），恢復時原樣還原。
                            self.time_scale = self.time_scale_before_pause
                            self.log_messages.append(f"▶ 恢復 {self.time_scale:.1f}x")
                    elif event.key == pygame.K_LEFTBRACKET:
                        # 直接 -0.1 運算，而不是查表。Python 浮點數
                        # 0.1 這種值沒辦法精確表示，連續相加減會累積誤差
                        # (例如 0.7 - 0.1 可能變成 0.5999999999999999)，
                        # 所以每次運算完都用 round(..., 1) 修回乾淨的一位
                        # 小數，再用 max/min 夾在 [TIME_SCALE_MIN,
                        # TIME_SCALE_MAX] 範圍內。
                        new_scale = round(self.time_scale - self.TIME_SCALE_STEP, 1)
                        self.time_scale = max(self.TIME_SCALE_MIN, min(self.TIME_SCALE_MAX, new_scale))
                        if self.time_scale > 0:
                            self.time_scale_before_pause = self.time_scale
                    elif event.key == pygame.K_RIGHTBRACKET:
                        new_scale = round(self.time_scale + self.TIME_SCALE_STEP, 1)
                        self.time_scale = max(self.TIME_SCALE_MIN, min(self.TIME_SCALE_MAX, new_scale))
                        if self.time_scale > 0:
                            self.time_scale_before_pause = self.time_scale


            if not self.show_intro and not self.show_pause_menu:
                self.game.update(dt * self.time_scale)

            if self.flash_vfx_timer > 0 and not self.show_pause_menu:
                self.flash_vfx_timer = max(0.0, self.flash_vfx_timer - dt)

            self._process_events()
            self._update_card_states()

            if not self.show_pause_menu:
                self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]
                self.particles = [p for p in self.particles if p.update(dt)]

            self._render()

            pygame.display.flip()


        pygame.quit()

    def _handle_mouse_move(self, event):
        mx, my = event.pos
        self.mouse_pos = (mx, my)

        for card in self.action_cards:
            if card.tab_id == self.active_tab:
                card.is_hovered = card.rect.collidepoint(mx, my)

        gx = (mx - GRID_X) // CELL_SIZE
        gy = (my - GRID_Y) // CELL_SIZE
        if 0 <= gx < self.game.width and 0 <= gy < self.game.height:
            self.hovered_grid = (gx, gy)
        else:
            self.hovered_grid = None

    def _handle_mouse_wheel(self, event):
        """商店清單捲動。只在滑鼠停在清單範圍內時生效，避免在地圖上
        滾滑鼠意外捲動到看不見的商店。"""
        area = self._shop_list_area()
        if not area.collidepoint(self.mouse_pos):
            return
        items = [c for c in self.action_cards if c.tab_id == self.active_tab]
        max_scroll = self._shop_scroll_bounds(len(items))
        if max_scroll <= 0:
            return
        current = self.shop_scroll.get(self.active_tab, 0)
        # event.y 一次滾動通常是 ±1，乘上單行高度感覺比較像「滾一格」
        # 而不是每次只移動 1px。
        new_scroll = current - event.y * 40
        self.shop_scroll[self.active_tab] = max(0, min(max_scroll, new_scroll))

    def _handle_mouse_down(self, event):
        mx, my = event.pos

        # 開場新手速成圖卡彈窗
        if self.show_intro:
            if event.button == 1:
                modal_w, modal_h = 840, 580
                mod_x = (SCREEN_WIDTH - modal_w) // 2
                mod_y = (SCREEN_HEIGHT - modal_h) // 2
                btn_start = pygame.Rect(mod_x + (modal_w - 280) // 2, mod_y + 500, 280, 54)
                if btn_start.collidepoint(mx, my) or not pygame.Rect(mod_x, mod_y, modal_w, modal_h).collidepoint(mx, my):
                    self.show_intro = False
                    self.sound.play("build")
            return

        # 滑鼠右鍵：一鍵快速鐵鏟剷除/拆除
        if event.button == 3:
            if self.hovered_grid:
                gx, gy = self.hovered_grid
                success, msg, refund = self.game.demolish_tile(gx, gy)
                if success:
                    px = GRID_X + gx * CELL_SIZE + CELL_SIZE // 2
                    py = GRID_Y + gy * CELL_SIZE + CELL_SIZE // 2
                    ref_str = f" +{refund}G" if refund > 0 else ""
                    self.floating_texts.append(FloatingText(f"🔨 剷除{ref_str}", px - 25, py - 12, (200, 200, 200)))
                    self._spawn_particles(px, py, (160, 140, 110), count=12)
                    self.sound.play("build")
                    self.log_messages.append(f"🔨 {msg}")
                else:
                    self.log_messages.append(f"ℹ️ {msg}")
            return

        if event.button != 1:
            return

        # 倍速調整面板 [-]/[+] 點擊 -- 邏輯跟鍵盤 [ / ] 完全一樣，
        # 同一顆 self.time_scale，同樣的 round(...,1) + max/min 夾值。
        # 加上 not self.show_pause_menu：暫停選單開啟時這兩顆按鈕在畫面上
        # 被暗色遮罩蓋住，但若不擋掉點擊，暫停中仍能偷改 time_scale，連
        # 「暫停前速度」的記憶也會被覆蓋，導致按下「繼續」後速度跟暫停前
        # 不一致。
        if not self.show_pause_menu and self.btn_speed_down_rect and self.btn_speed_down_rect.collidepoint(mx, my):
            new_scale = round(self.time_scale - self.TIME_SCALE_STEP, 1)
            self.time_scale = max(self.TIME_SCALE_MIN, min(self.TIME_SCALE_MAX, new_scale))
            if self.time_scale > 0:
                self.time_scale_before_pause = self.time_scale
            self.sound.play("build")
            return
        if not self.show_pause_menu and self.btn_speed_up_rect and self.btn_speed_up_rect.collidepoint(mx, my):
            new_scale = round(self.time_scale + self.TIME_SCALE_STEP, 1)
            self.time_scale = max(self.TIME_SCALE_MIN, min(self.TIME_SCALE_MAX, new_scale))
            if self.time_scale > 0:
                self.time_scale_before_pause = self.time_scale
            self.sound.play("build")
            return

        # 遊戲結束
        if self.game.game_over:
            btn_restart = pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 70, 200, 48)
            if btn_restart.collidepoint(mx, my):
                self.game = GameState()
                self.log_messages.clear()
                self.log_messages.append("🌾 遊戲已重新開始！")
                self.sound.play("harvest")
            return

        # 暫停選單開啟中：只有選單內的按鈕能點，其餘全部攔下
        if self.show_pause_menu:
            modal_w, modal_h = 420, 300
            mx0 = (SCREEN_WIDTH - modal_w) // 2
            my0 = (SCREEN_HEIGHT - modal_h) // 2
            btn_resume = pygame.Rect(mx0 + (modal_w - 220) // 2, my0 + 150, 220, 52)
            btn_restart2 = pygame.Rect(mx0 + (modal_w - 220) // 2, my0 + 216, 220, 52)
            if btn_resume.collidepoint(mx, my):
                self.show_pause_menu = False
                self.sound.play("build")
            elif btn_restart2.collidepoint(mx, my):
                self.game = GameState()
                self.log_messages.clear()
                self.log_messages.append("🌾 遊戲已重新開始！")
                self.show_pause_menu = False
                self.sound.play("harvest")
            return

        # 右上角選單按鈕（☰）：點擊暫停遊戲並開啟選單
        menu_btn_rect = pygame.Rect(SCREEN_WIDTH - 56, 15, 40, 40)
        if menu_btn_rect.collidepoint(mx, my):
            self.show_pause_menu = True
            self.sound.play("build")
            return

        # 分頁標籤（點擊切換分頁時捲動歸零，避免新分頁一開就是捲到一半的畫面）
        for tab_id, label, rect in self.tab_buttons:
            if rect.collidepoint(mx, my):
                self.active_tab = tab_id
                self.sound.play("plant")
                return

        # 卡片點擊
        for card in self.action_cards:
            if card.tab_id == self.active_tab and card.rect.collidepoint(mx, my):
                if card.action_id == "BUY_DOG":
                    success, msg = self.game.buy_guard_dog()
                    if not success:
                        self.log_messages.append(f"❌ {msg}")
                elif card.action_id == "BUY_CAT":
                    success, msg = self.game.buy_farm_cat()
                    if not success:
                        self.log_messages.append(f"❌ {msg}")
                else:
                    if not card.is_locked:
                        self.selected_action = card.action_id
                        self.sound.play("plant")
                    else:
                        # 點到尚未解鎖的商品：不執行任何購買/選取邏輯，
                        # 在滑鼠位置跳出紅色浮動文字＋錯誤音效，讓玩家
                        # 立刻知道「為什麼點了沒反應」，而不是只寫進日誌。
                        reason_txt = card.lock_reason if card.lock_reason else "尚未解鎖"
                        self.floating_texts.append(
                            FloatingText(f"🔒 {reason_txt}", mx - 30, my - 12, C_RED)
                        )
                        self.log_messages.append(f"🔒 {reason_txt}")
                        self.sound.play("error")
                return

        # 地圖座標換算
        world_gx = (mx - GRID_X) / CELL_SIZE
        world_gy = (my - GRID_Y) / CELL_SIZE

        # 0. 最優先權（僅限夜晚 + 已裝備手電筒）：優先判定敵人。
        # 夜晚會自動裝備手電筒，這裡要排在「格子上有成熟作物就先採收」
        # 判定的前面——否則敵人剛好站在成熟作物格子上時，玩家點擊想照暈
        # 敵人，會被下面第 1 優先權攔截去跑採收邏輯（雖然夜晚採收一定會
        # 失敗，但點擊已經被消耗掉、直接 return，手電筒永遠沒機會判定）。
        # use_flashlight_stun() 內部本來就會依游標位置比對 self.game.enemies
        # 的距離（含未命中時的最近敵人輔助瞄準），等同於「碰撞判定」，
        # 沿用它可以維持跟原本一致的冷卻/瞄準輔助手感，不用另外重寫一份。
        if self.game.phase == GamePhase.NIGHT and self.selected_action == "FLASHLIGHT":
            success, msg = self.game.use_flashlight_stun(world_gx, world_gy)
            if success:
                self._spawn_particles(mx, my, (255, 255, 200), count=15)
            else:
                self.log_messages.append(f"🔦 {msg}")
            return

        # 1. 第一優先權：若點擊格子上有「成熟作物」，無論當前選中何種工具，一律直接採收！
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            tile = self.game.get_tile(gx, gy)
            if tile and tile.crop and tile.crop.is_mature:
                success, reward, msg = self.game.harvest_crop(gx, gy)
                if not success:
                    self.log_messages.append(f"❌ {msg}")
                return

        # 2. 第二優先權：主動戰術工具 (指揮哨；手電筒的夜晚情境已在最上面
        # 處理掉了，走到這裡代表選了手電筒但現在是白天)
        if self.selected_action == "FLASHLIGHT":
            self.log_messages.append("☀️ 白天無入侵敵人！已為您自動切換至農耕播種模式。")
            self.active_tab = "CROPS"
            self.selected_action = "PLANT_RADISH"
            return

        if self.selected_action == "WHISTLE":
            success, msg = self.game.use_dog_whistle(world_gx, world_gy)
            if not success:
                self.log_messages.append(f"🔔 {msg}")
            else:
                self._spawn_particles(mx, my, C_CYAN, count=12)
            return

        # 3. 第三優先權：地圖建築、播種、澆水操作
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            self._apply_grid_action(gx, gy)

    def _apply_grid_action(self, gx: int, gy: int):
        tile = self.game.get_tile(gx, gy)
        
        # 【一鍵直接採收】：若點擊成熟作物，一律直接採收獲取金幣，無須切換任何工具！
        if tile and tile.crop and tile.crop.is_mature:
            success, reward, msg = self.game.harvest_crop(gx, gy)
            if not success:
                self.log_messages.append(f"❌ {msg}")
            return

        act = self.selected_action

        # 作物 (10 種)
        if act == "PLANT_RADISH":
            success, msg = self.game.plant_crop(gx, gy, CropType.WHITE_RADISH)
        elif act == "PLANT_TOMATO":
            success, msg = self.game.plant_crop(gx, gy, CropType.RED_TOMATO)
        elif act == "PLANT_CORN":
            success, msg = self.game.plant_crop(gx, gy, CropType.SWEET_CORN)
        elif act == "PLANT_CARROT":
            success, msg = self.game.plant_crop(gx, gy, CropType.CARROT)
        elif act == "PLANT_STRAWBERRY":
            success, msg = self.game.plant_crop(gx, gy, CropType.SWEET_STRAWBERRY)
        elif act == "PLANT_PUMPKIN":
            success, msg = self.game.plant_crop(gx, gy, CropType.MAGIC_PUMPKIN)
        elif act == "PLANT_BLUEBERRY":
            success, msg = self.game.plant_crop(gx, gy, CropType.BLUEBERRY)
        elif act == "PLANT_WHEAT":
            success, msg = self.game.plant_crop(gx, gy, CropType.WHEAT)
        elif act == "PLANT_GRAPE":
            success, msg = self.game.plant_crop(gx, gy, CropType.ROYAL_GRAPE)
        elif act == "PLANT_STARLIGHT":
            success, msg = self.game.plant_crop(gx, gy, CropType.STARLIGHT_FRUIT)
        # 景觀 (13 種)
        elif act == "PLACE_PATH":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.STONE_PATH)
        elif act == "PLACE_FLOWER":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.FLOWER_BED)
        elif act == "PLACE_BENCH":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.GARDEN_BENCH)
        elif act == "PLACE_PINE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.PINE_TREE)
        elif act == "PLACE_APPLE_TREE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.APPLE_TREE)
        elif act == "PLACE_LANTERN":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.SOUL_LANTERN)
        elif act == "PLACE_SAKURA_TREE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.SAKURA_TREE)
        elif act == "PLACE_BIRD_BATH":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.BIRD_BATH)
        elif act == "PLACE_STATUE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.ANCIENT_STATUE)
        elif act == "PLACE_PET_HOUSE":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.PET_HOUSE)
        elif act == "PLACE_FOUNTAIN":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.CRYSTAL_FOUNTAIN)
        elif act == "PLACE_SUNDIAL":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.SUNDIAL_TOWER)
        elif act == "PLACE_WINDMILL":
            success, msg = self.game.place_decoration(gx, gy, DecorationType.WINDMILL)
        # 防禦
        elif act == "PLACE_FENCE":
            success, msg = self.game.place_defense(gx, gy, DefenseType.WOODEN_FENCE)
        elif act == "PLACE_TRAP":
            success, msg = self.game.place_defense(gx, gy, DefenseType.BEAR_TRAP)
        elif act == "PLACE_SCARECROW":
            success, msg = self.game.place_defense(gx, gy, DefenseType.SCARECROW)
        elif act == "PLACE_BEEHIVE":
            success, msg = self.game.place_defense(gx, gy, DefenseType.BEEHIVE)
        # 工具
        elif act == "SHOVEL":
            success, msg, refund = self.game.demolish_tile(gx, gy)
            if success:
                px = GRID_X + gx * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + gy * CELL_SIZE + CELL_SIZE // 2
                ref_str = f" +{refund}G" if refund > 0 else ""
                self.floating_texts.append(FloatingText(f"🔨 剷除{ref_str}", px - 25, py - 12, (200, 200, 200)))
                self._spawn_particles(px, py, (160, 140, 110), count=12)
                self.sound.play("build")
        elif act == "HARVEST":
            success, reward, msg = self.game.harvest_crop(gx, gy)
        elif act == "WATER_CROP":
            success, msg = self.game.water_crop(gx, gy)
        else:
            success, msg = False, "未知操作"


        if not success:
            self.log_messages.append(f"❌ {msg}")

    def _spawn_particles(self, px: float, py: float, color: tuple, count: int = 8):
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(25, 90)
            vx = math.cos(ang) * spd
            vy = math.sin(ang) * spd
            self.particles.append(Particle(px, py, vx, vy, color, random.uniform(3, 6), random.uniform(0.4, 0.8)))

    def _process_events(self):
        for ev in self.game.poll_events():
            self.sound.handle_game_event(ev)
            self.log_messages.append(ev.message)
            if len(self.log_messages) > 16:
                self.log_messages.pop(0)

            if ev.event_type == EventType.CROP_HARVESTED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"+{ev.data['reward']} G", px - 15, py - 10, C_GOLD))
                self._spawn_particles(px, py, C_GOLD, count=12)
            elif ev.event_type == EventType.CROP_WATERED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"💧 加速生長！", px - 25, py - 12, C_CYAN))
                self._spawn_particles(px, py, C_CYAN, count=10)
            elif ev.event_type == EventType.VAULT_RAIDED:
                vx, vy = MAP_CONFIG["VAULT_POS"]
                px = GRID_X + vx * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + vy * CELL_SIZE
                self.floating_texts.append(FloatingText(f"🚨 金庫被洗劫 -{ev.data['gold_lost']} G！", px - 40, py - 20, C_RED, duration=2.2))
                self._spawn_particles(px, py, C_RED, count=25)
            elif ev.event_type == EventType.DAILY_TAX_PAID:
                self.floating_texts.append(FloatingText(f"🏛️ 地租維護費 -{ev.data['tax']} G", 460, 60, (239, 83, 80)))
            elif ev.event_type == EventType.ENEMY_STUNNED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                self.floating_texts.append(FloatingText("⚡ 暈眩 2.5s", px - 20, py - 15, (255, 235, 59)))
                self._spawn_particles(px, py, (255, 235, 59), count=14)
            elif ev.event_type == EventType.BEE_ATTACK:
                fx = GRID_X + ev.data["from_x"] * CELL_SIZE + CELL_SIZE // 2
                fy = GRID_Y + ev.data["from_y"] * CELL_SIZE + CELL_SIZE // 2
                tx = GRID_X + ev.data["to_x"] * CELL_SIZE + CELL_SIZE // 2
                ty = GRID_Y + ev.data["to_y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"🐝 -{int(ev.data['damage'])}", tx - 15, ty - 12, C_GOLD))
                self._spawn_particles(tx, ty, C_GOLD, count=8)
            elif ev.event_type == EventType.BLOOD_MOON_WARNING:
                self.floating_texts.append(FloatingText("🩸 血月降臨！巨型野豬首領來襲！", SCREEN_WIDTH // 2 - 120, 220, C_BLOOD_RED, duration=3.0))
                self._spawn_particles(SCREEN_WIDTH // 2, 240, C_BLOOD_RED, count=40)
            elif ev.event_type == EventType.TRAP_TRIGGERED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"💥 {int(ev.data['damage'])}", px - 15, py - 15, C_RED))
                self._spawn_particles(px, py, (220, 50, 50), count=16)
            elif ev.event_type == EventType.DOG_ATTACK:
                if self.game.guard_dog:
                    px = GRID_X + self.game.guard_dog.x * CELL_SIZE + CELL_SIZE // 2
                    py = GRID_Y + self.game.guard_dog.y * CELL_SIZE
                    self.floating_texts.append(FloatingText(f"🐕 撲咬 -{int(ev.data['damage'])}", px - 20, py - 10, C_ORANGE))
                    self._spawn_particles(px, py, C_ORANGE, count=8)
            elif ev.event_type == EventType.CAT_BONUS:
                if self.game.farm_cat:
                    px = GRID_X + self.game.farm_cat.x * CELL_SIZE
                    py = GRID_Y + self.game.farm_cat.y * CELL_SIZE - 10
                    self.floating_texts.append(FloatingText(f"🐱 +{ev.data['bonus']} G (招財)", px - 15, py, C_GOLD))
                    self._spawn_particles(px, py, C_GOLD, count=6)
            elif ev.event_type == EventType.FARM_LEVEL_UP:
                self.floating_texts.append(FloatingText(f"⭐ 莊園繁榮升級 Lv.{ev.data['new_level']}！", SCREEN_WIDTH // 2 - 90, 220, C_GOLD, duration=2.5))
                self._spawn_particles(SCREEN_WIDTH // 2, 240, C_GOLD, count=30)
            elif ev.event_type == EventType.FENCE_DESTROYED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"💥 圍籬被衝破！", px - 35, py - 18, C_RED, duration=2.5))
                self._spawn_particles(px, py, (160, 100, 60), count=25)
            elif ev.event_type == EventType.DAY_STARTED:
                if self.active_tab == "TOOLS" or self.selected_action in ("FLASHLIGHT", "WHISTLE"):
                    self.active_tab = "CROPS"
                    self.selected_action = "PLANT_RADISH"

            # 夜晚降臨時（含血月）自動裝備強光手電筒，玩家不必再去商店手動點選。
            # 特意寫成獨立的 if（不是掛在上面的 elif 鏈上）：BLOOD_MOON_WARNING
            # 這個事件本身已經被上面的 elif 分支吃掉（顯示血月紅字），若把這段
            # 也寫成 elif 就永遠輪不到它執行；獨立判斷才能讓一般夜晚與血月夜
            # 都能觸發。原本這裡監聽的是 PHASE_CHANGED 事件，但 game_state.py
            # 從未送出這個事件，所以自動裝備邏輯過去從來沒有真正執行過。
            if ev.event_type in (EventType.NIGHT_STARTED, EventType.BLOOD_MOON_WARNING):
                self.active_tab = "TOOLS"
                self.selected_action = "FLASHLIGHT"
                self.floating_texts.append(FloatingText("🔦 已裝備強光手電筒！滑鼠點擊敵人照暈！", SCREEN_WIDTH // 2 - 140, 200, (255, 235, 59), duration=2.5))

    def _get_mascot_guide_data(self) -> Tuple[str, tuple, str, tuple, str]:
        """Returns (badge_text, badge_bg_color, main_dialogue, text_color, step_tag)"""
        if self.game.phase == GamePhase.NIGHT:
            if self.game.is_blood_moon:
                return (
                    "🩸 血月首領",
                    (211, 47, 47),
                    "【血月警報】巨型野豬首領來襲！點選【強光手電筒】滑鼠點擊 Boss 照暈，柴犬全力集火！",
                    (255, 180, 180),
                    "[滑鼠點擊 Boss 照暈]"
                )
            else:
                return (
                    "🔦 夜巡夜戰",
                    (33, 150, 243),
                    "【夜間防守】入侵者來襲！點選下方工具列【強光手電筒】，滑鼠直接點擊敵人照暈他！",
                    (179, 229, 252),
                    "[點選強光・滑鼠照暈]"
                )

        else:
            # Daytime
            crops_count = sum(1 for row in self.game.grid for tile in row if tile.crop)
            mature_count = sum(1 for row in self.game.grid for tile in row if tile.crop and tile.crop.is_mature)

            if self.game.day_count == 1:
                if crops_count == 0:
                    return (
                        "🐶 柴犬管家",
                        (255, 152, 0),
                        "領主你好！快點選下方【白蘿蔔種子】，在中央金色農田點擊 3~5 格播種賺錢！",
                        (255, 245, 157),
                        "[步驟 1/3：播種]"
                    )
                elif mature_count > 0:
                    return (
                        "🌾 採收豐收",
                        (76, 175, 80),
                        "作物成熟泛出金黃光芒了！請【直接滑鼠點擊作物】採收，換取第一桶金！",
                        (200, 230, 201),
                        "[步驟 2/3：採收]"
                    )
                elif self.game.time_in_phase > 15.0:
                    return (
                        "🛡️ 防守備戰",
                        (239, 83, 80),
                        "天色即將變暗！請點擊【防禦】分頁，購買【看門柴犬 ($100)】或【刺藤木柵】保護農田！",
                        (255, 204, 128),
                        "[步驟 3/3：防禦]"
                    )
                else:
                    return (
                        "⏳ 生長觀察",
                        (0, 188, 212),
                        "作物正在快速生長中！可點擊【黃金澆水壺】加速進度，靜候成熟採收！",
                        (220, 237, 200),
                        "[生長觀察]"
                    )
            elif self.game.day_count == 2:
                if mature_count > 0:
                    return (
                        "🌾 採收提醒",
                        (76, 175, 80),
                        "有成熟作物等待採收！天黑前記得收成，存活過夜作物更享有月光加成 +50%！",
                        (200, 230, 201),
                        "[點擊採收]"
                    )
                elif self.game.time_in_phase > 12.0:
                    return (
                        "🛡️ 防線加固",
                        (239, 83, 80),
                        "野豬即將加入夜襲！多配置幾條刺藤圍籬與捕獸夾，防止防線被衝破！",
                        (255, 204, 128),
                        "[佈置防禦]"
                    )
                else:
                    return (
                        "🌸 景觀擴建",
                        (156, 39, 176),
                        "第 2 天開始！到【景觀】分頁佈置果樹、噴泉提升繁榮度，解鎖甜玉米與草莓！",
                        (245, 245, 245),
                        "[莊園升級]"
                    )
            else:
                if mature_count > 0:
                    return (
                        "🌾 豐收時刻",
                        (76, 175, 80),
                        "請及時採收成熟作物，為莊園籌措升級資金與繳納每日領地地租！",
                        (200, 230, 201),
                        "[點擊採收]"
                    )
                else:
                    return (
                        "🏛️ 領地經營",
                        (156, 39, 176),
                        f"第 {self.game.day_count} 天莊園繁榮度: {self.game.prosperity_score}！持續佈置景觀解鎖高級魔法南瓜！",
                        (245, 245, 245),
                        f"[Lv.{self.game.farm_level}]"
                    )



    def _update_card_states(self):
        for card in self.action_cards:
            # 作物解鎖判定
            if card.action_id in ("PLANT_CORN", "PLANT_CARROT", "PLANT_STRAWBERRY"):
                card.is_locked = not self.game.is_crop_unlocked(CropType.SWEET_CORN)
                card.lock_reason = "需莊園等級 Lv.2"
            elif card.action_id in ("PLANT_PUMPKIN", "PLANT_BLUEBERRY", "PLANT_WHEAT"):
                card.is_locked = not self.game.is_crop_unlocked(CropType.MAGIC_PUMPKIN)
                card.lock_reason = "需莊園等級 Lv.3"
            elif card.action_id == "PLANT_GRAPE":
                card.is_locked = not self.game.is_crop_unlocked(CropType.ROYAL_GRAPE)
                card.lock_reason = "需莊園等級 Lv.4"
            elif card.action_id == "PLANT_STARLIGHT":
                card.is_locked = not self.game.is_crop_unlocked(CropType.STARLIGHT_FRUIT)
                card.lock_reason = "需莊園等級 Lv.5"
            elif card.action_id == "BUY_DOG":
                card.is_locked = self.game.has_dog
                card.lock_reason = "已擁有看門柴犬"
            elif card.action_id == "BUY_CAT":
                card.is_locked = self.game.has_cat
                card.lock_reason = "已擁有招財小貓"
            elif card.action_id == "FLASHLIGHT":
                if self.game.flashlight_cooldown > 0:
                    card.cost_text = f"CD: {self.game.flashlight_cooldown:.1f}s"
                else:
                    card.cost_text = "就緒 | 暈眩2.5s"

    # ==========================================
    # 純色扁平無網格渲染管道 (Flat Pipeline)
    # ==========================================
    def _render(self):
        self.screen.fill((240, 244, 248))

        self._render_header_banner()
        self._render_flat_meadow_and_farm()

        if self.game.phase == GamePhase.NIGHT:
            self._render_night_overlay()

        self._render_entities()

        for p in self.particles:
            p.draw(self.screen)
        for ft in self.floating_texts:
            ft.draw(self.screen)

        # 全螢幕強光閃爍特效 (Flashlight Stun VFX)
        if self.flash_vfx_timer > 0:
            flash_alpha = int((self.flash_vfx_timer / 0.28) * 160)
            flash_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            flash_s.fill((255, 255, 220, flash_alpha))
            self.screen.blit(flash_s, (0, 0))

        self._render_shop_panel()

        if self.show_intro:
            self._render_story_modal()
        elif self.game.game_over:
            self._render_game_over_modal()
        elif self.show_pause_menu:
            self._render_pause_menu()

    def _render_pause_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 420, 300
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)

        pygame.draw.rect(self.screen, C_WHITE, modal_rect, border_radius=14)
        pygame.draw.rect(self.screen, C_BLUE, modal_rect, width=3, border_radius=14)

        t1 = FONT_TITLE.render("⏸ 遊戲暫停", True, C_TEXT_MAIN)
        self.screen.blit(t1, (mx + (modal_w - t1.get_width()) // 2, my + 40))

        r1 = FONT_SM.render(f"第 {self.game.day_count} 天・繁榮度 {self.game.prosperity_score}", True, C_TEXT_MUTED)
        self.screen.blit(r1, (mx + (modal_w - r1.get_width()) // 2, my + 90))

        btn_resume = pygame.Rect(mx + (modal_w - 220) // 2, my + 150, 220, 52)
        pygame.draw.rect(self.screen, C_GREEN, btn_resume, border_radius=8)
        # 用「恢復」而非「繼續」：後者的「繼」字不在專案自帶的精簡字型子集
        # (assets/fonts/NotoSansTC-GameSubset.otf) 收錄範圍內，會顯示成缺字
        # 方塊「□」。P 鍵暫停/恢復本來就用「恢復」這個詞（見上方 run() 的
        # K_p 處理），這裡沿用同一個詞，語意一致，也保證字型一定有收錄。
        resume_txt = FONT_MD.render("▶ 恢復", True, C_WHITE)
        self.screen.blit(resume_txt, (btn_resume.centerx - resume_txt.get_width() // 2, btn_resume.centery - resume_txt.get_height() // 2))

        btn_restart = pygame.Rect(mx + (modal_w - 220) // 2, my + 216, 220, 52)
        pygame.draw.rect(self.screen, C_ORANGE, btn_restart, border_radius=8)
        restart_txt = FONT_MD.render("🔄 重新開始", True, C_WHITE)
        self.screen.blit(restart_txt, (btn_restart.centerx - restart_txt.get_width() // 2, btn_restart.centery - restart_txt.get_height() // 2))

    def _render_header_banner(self):
        is_day = (self.game.phase == GamePhase.DAY)
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 70)
        pygame.draw.rect(self.screen, C_NAVY_TOP, header_rect)

        self.screen.blit(FONT_TITLE.render("🌾 夜巡農場 (Harvest & Hordes)", True, C_GOLD), (24, 8))

        if self.game.is_blood_moon and not is_day:
            phase_txt = f"🩸 第 {self.game.day_count} 天・血月首領戰！"
            phase_col = (255, 82, 82)
        else:
            phase_txt = f"☀️ 第 {self.game.day_count} 天・白天 (經營期)" if is_day else f"🌙 第 {self.game.day_count} 天・夜晚 (守衛期)"
            phase_col = (255, 235, 59) if is_day else (129, 212, 250)

        self.screen.blit(FONT_MD.render(phase_txt, True, phase_col), (24, 40))

        max_dur = self.game.day_duration if is_day else self.game.night_duration
        rem_time = max(0.0, max_dur - self.game.time_in_phase)
        prog = max(0.0, min(1.0, 1.0 - (self.game.time_in_phase / max_dur)))

        bar_r = pygame.Rect(230, 43, 140, 14)
        pygame.draw.rect(self.screen, (20, 25, 30), bar_r, border_radius=7)
        fill_w = int(bar_r.width * prog)
        fill_col = C_GREEN if is_day else (C_BLOOD_RED if self.game.is_blood_moon else C_CYAN)
        if fill_w > 0:
            pygame.draw.rect(self.screen, fill_col, (bar_r.x, bar_r.y, fill_w, bar_r.height), border_radius=7)
        rem_surf = FONT_XS.render(f"{rem_time:.1f}s", True, C_WHITE)
        self.screen.blit(rem_surf, (bar_r.right + 8, bar_r.y))

        # 倍速調整面板 [-] 1.0x [+] -- 緊接在倒數計時 "7.1s" 右側，滑鼠
        # 點擊 [-]/[+] 效果跟鍵盤 [ ] 完全一樣（同一顆 self.time_scale，
        # 同樣的 round(...,1) + max/min 夾值邏輯），兩種操作方式並存。
        panel_x = bar_r.right + 8 + rem_surf.get_width() + 14
        btn_size = 20
        btn_y = bar_r.y - 3
        self.btn_speed_down_rect = pygame.Rect(panel_x, btn_y, btn_size, btn_size)

        speed_txt_surf = FONT_SM.render(f"{self.time_scale:.1f}x", True, C_WHITE)
        speed_box_w = speed_txt_surf.get_width() + 12
        speed_box_rect = pygame.Rect(self.btn_speed_down_rect.right + 4, btn_y, speed_box_w, btn_size)

        self.btn_speed_up_rect = pygame.Rect(speed_box_rect.right + 4, btn_y, btn_size, btn_size)

        def _draw_speed_btn(rect, label):
            hovered = rect.collidepoint(self.mouse_pos)
            pygame.draw.rect(self.screen, (80, 100, 110) if hovered else (45, 58, 64), rect, border_radius=5)
            pygame.draw.rect(self.screen, (150, 170, 180), rect, width=1, border_radius=5)
            lbl_surf = FONT_SM.render(label, True, C_WHITE)
            self.screen.blit(lbl_surf, lbl_surf.get_rect(center=rect.center))

        _draw_speed_btn(self.btn_speed_down_rect, "-")
        pygame.draw.rect(self.screen, (30, 40, 46), speed_box_rect, border_radius=5)
        self.screen.blit(speed_txt_surf, speed_txt_surf.get_rect(center=speed_box_rect.center))
        _draw_speed_btn(self.btn_speed_up_rect, "+")

        # 金幣卡 (原本從 x=430 開始，讓給左邊新增的倍速面板一些空間，
        # 跟等級卡一起整組往右挪，右邊界維持在原本的 1236 不變)
        gold_rect = pygame.Rect(545, 12, 180, 44)
        pygame.draw.rect(self.screen, (55, 71, 79), gold_rect, border_radius=10)
        pygame.draw.circle(self.screen, C_GOLD, (gold_rect.x + 22, gold_rect.centery), 12)
        self.screen.blit(FONT_SM.render("G", True, (60, 40, 0)), (gold_rect.x + 17, gold_rect.centery - 8))
        self.screen.blit(FONT_LG.render(f"{self.game.gold} 金幣", True, C_GOLD), (gold_rect.x + 44, gold_rect.centery - 11))

        # 等級與繁榮度 (x=745 為金幣卡右移後的座標；寬度從 491 再縮短到 447，
        # 右緣停在選單按鈕左側 [x=1204] 前留 12px 間距，避免被蓋住)
        lvl_rect = pygame.Rect(745, 12, 447, 44)
        pygame.draw.rect(self.screen, (55, 71, 79), lvl_rect, border_radius=10)
        lvl_name = FARM_LEVELS[self.game.farm_level]["name"]
        self.screen.blit(FONT_MD.render(f"🏆 莊園等級: Lv.{self.game.farm_level} ({lvl_name})", True, C_WHITE), (lvl_rect.x + 14, lvl_rect.y + 4))

        goals = {1: 40, 2: 100, 3: 200, 4: 350, 5: 500}
        next_goal = goals.get(self.game.farm_level, 500)
        curr_p = self.game.prosperity_score
        p_ratio = min(1.0, curr_p / next_goal)

        p_bar = pygame.Rect(lvl_rect.x + 14, lvl_rect.y + 24, 270, 12)
        pygame.draw.rect(self.screen, (25, 30, 40), p_bar, border_radius=6)
        if p_ratio > 0:
            pygame.draw.rect(self.screen, C_PURPLE, (p_bar.x, p_bar.y, int(p_bar.width * p_ratio), p_bar.height), border_radius=6)
        self.screen.blit(FONT_SM.render(f"繁榮度: {curr_p} / {next_goal}", True, C_CYAN), (p_bar.right + 12, p_bar.y - 3))

        # 右上角選單按鈕（☰）：特意畫在 header 方法的最後面，確保一定疊在
        # 上方所有面板（金幣卡、莊園等級面板...）之上，不會被蓋住。
        menu_btn_rect = pygame.Rect(SCREEN_WIDTH - 56, 15, 40, 40)
        is_menu_hover = menu_btn_rect.collidepoint(self.mouse_pos)
        pygame.draw.rect(self.screen, (68, 84, 92) if is_menu_hover else (54, 70, 78), menu_btn_rect, border_radius=8)
        for i in range(3):
            line_y = menu_btn_rect.y + 11 + i * 9
            pygame.draw.line(self.screen, C_WHITE, (menu_btn_rect.x + 8, line_y), (menu_btn_rect.x + 32, line_y), 3)

    def _render_flat_meadow_and_farm(self):
        map_w = self.game.width * CELL_SIZE
        map_h = self.game.height * CELL_SIZE
        map_rect = pygame.Rect(GRID_X, GRID_Y, map_w, map_h)
        pygame.draw.rect(self.screen, C_MEADOW_BG, map_rect, border_radius=16)

        grass_img = self.loader.get("grass_tile")
        soil_img = self.loader.get("soil_tile")

        # 繪製像素草地與農田底層地磚
        for y in range(self.game.height):
            for x in range(self.game.width):
                px = GRID_X + x * CELL_SIZE
                py = GRID_Y + y * CELL_SIZE
                tile = self.game.grid[y][x]
                if tile.zone == ZoneType.FARM_ZONE:
                    if soil_img:
                        self.screen.blit(soil_img, (px, py))
                    else:
                        pygame.draw.rect(self.screen, C_FARM_SOIL, (px, py, CELL_SIZE, CELL_SIZE))
                else:
                    if grass_img:
                        self.screen.blit(grass_img, (px, py))
                    else:
                        pygame.draw.rect(self.screen, C_MEADOW_BG, (px, py, CELL_SIZE, CELL_SIZE))

        fx_min, fx_max = MAP_CONFIG["FARM_X_RANGE"]
        fy_min, fy_max = MAP_CONFIG["FARM_Y_RANGE"]
        farm_rx = GRID_X + fx_min * CELL_SIZE
        farm_ry = GRID_Y + fy_min * CELL_SIZE
        farm_rw = (fx_max - fx_min + 1) * CELL_SIZE
        farm_rh = (fy_max - fy_min + 1) * CELL_SIZE

        # 農田外框陰影與邊界線
        pygame.draw.rect(self.screen, C_FARM_BORDER, (farm_rx - 2, farm_ry - 2, farm_rw + 4, farm_rh + 4), width=2, border_radius=8)

        # 中央農莊金庫標誌
        vx, vy = MAP_CONFIG["VAULT_POS"]
        v_px = GRID_X + vx * CELL_SIZE
        v_py = GRID_Y + vy * CELL_SIZE
        pygame.draw.circle(self.screen, (255, 215, 0, 100), (v_px + CELL_SIZE // 2, v_py + CELL_SIZE // 2), 16)
        pygame.draw.rect(self.screen, (141, 110, 99), (v_px + 12, v_py + 14, 26, 22), border_radius=4)
        pygame.draw.circle(self.screen, C_GOLD, (v_px + 25, v_py + 25), 5)

        for y in range(self.game.height):
            for x in range(self.game.width):

                tile = self.game.grid[y][x]
                px = GRID_X + x * CELL_SIZE
                py = GRID_Y + y * CELL_SIZE

                if tile.decoration:
                    dt = tile.decoration.decoration_type
                    k = DECORATION_DATA[dt].get("asset_key", "stone_path")
                    img = self.loader.get(k)
                    if img:
                        self.screen.blit(img, (px, py))

                if tile.defense:
                    df = tile.defense.defense_type
                    k = DEFENSE_DATA[df].get("asset_key", "wooden_fence")
                    img = self.loader.get(k)
                    if img:
                        self.screen.blit(img, (px, py))

                    # 圍籬耐久度血條與受損視覺反饋
                    if df == DefenseType.WOODEN_FENCE and tile.defense.hp < tile.defense.max_hp:
                        ratio = max(0.0, tile.defense.hp / tile.defense.max_hp)
                        hb_w = CELL_SIZE - 8
                        hb_h = 4
                        hb_x = px + 4
                        hb_y = py + CELL_SIZE - 6
                        pygame.draw.rect(self.screen, (40, 40, 40), (hb_x, hb_y, hb_w, hb_h), border_radius=2)
                        bar_col = (76, 175, 80) if ratio > 0.5 else ((255, 152, 0) if ratio > 0.25 else (239, 83, 80))
                        pygame.draw.rect(self.screen, bar_col, (hb_x, hb_y, int(hb_w * ratio), hb_h), border_radius=2)

                    # 若敵人正在破壞這座圍籬，繪製危險攻擊警示框
                    if any(e.attacking_fence == (x, y) for e in self.game.enemies):
                        flash_alpha = int(120 + math.sin(self.anim_time * 15.0) * 80)
                        warn_s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                        pygame.draw.rect(warn_s, (255, 50, 50, flash_alpha), (0, 0, CELL_SIZE, CELL_SIZE), width=2, border_radius=4)
                        self.screen.blit(warn_s, (px, py))

                if tile.crop:
                    ct = tile.crop.crop_type
                    base_key = CROP_DATA[ct].get("asset_key", "radish")
                    st_key = tile.crop.stage.name.lower()
                    img = self.loader.get(f"{base_key}_{st_key}")
                    if img:
                        self.screen.blit(img, (px, py))

                    if tile.crop.is_moonlight_boosted:
                        pygame.draw.circle(self.screen, (129, 212, 250), (px + 10, py + 10), 4)

                    if tile.crop.is_mature:
                        bob = math.sin(self.anim_time * 6.0) * 3
                        pygame.draw.circle(self.screen, C_GOLD, (px + CELL_SIZE - 9, int(py + 9 + bob)), 6)
                        pygame.draw.circle(self.screen, (255, 255, 255), (px + CELL_SIZE - 9, int(py + 9 + bob)), 3)
                    else:
                        ratio = min(1.0, tile.crop.growth_timer / tile.crop.grow_time)
                        pb = pygame.Rect(px + 6, py + CELL_SIZE - 6, CELL_SIZE - 12, 3)
                        pygame.draw.rect(self.screen, (0, 0, 0, 80), pb)
                        pygame.draw.rect(self.screen, (76, 175, 80), (pb.x, pb.y, int(pb.width * ratio), 3))

        # 第 1 天未播種時，農田外框呈現金色呼吸引導光效
        if self.game.day_count == 1 and sum(1 for row in self.game.grid for tile in row if tile.crop) == 0:
            pulse = (math.sin(self.anim_time * 5.0) + 1.0) * 0.5
            glow_alpha = int(120 + pulse * 135)
            guide_s = pygame.Surface((farm_rw + 8, farm_rh + 8), pygame.SRCALPHA)
            pygame.draw.rect(guide_s, (255, 215, 0, glow_alpha), (0, 0, farm_rw + 8, farm_rh + 8), width=3, border_radius=18)
            self.screen.blit(guide_s, (farm_rx - 4, farm_ry - 4))
            
            # 中央飄浮新手引導標籤
            tip_w, tip_h = 210, 26
            tip_x = farm_rx + (farm_rw - tip_w) // 2
            tip_y = farm_ry + 20
            pygame.draw.rect(self.screen, (38, 50, 56, 230), (tip_x, tip_y, tip_w, tip_h), border_radius=6)
            pygame.draw.rect(self.screen, C_GOLD, (tip_x, tip_y, tip_w, tip_h), width=1, border_radius=6)
            self.screen.blit(FONT_SM.render("👇 請在此處點擊播種白蘿蔔", True, C_GOLD), (tip_x + 14, tip_y + 4))

        if self.hovered_grid:
            gx, gy = self.hovered_grid
            cx = GRID_X + gx * CELL_SIZE + CELL_SIZE // 2
            cy = GRID_Y + gy * CELL_SIZE + CELL_SIZE // 2
            glow_s = pygame.Surface((CELL_SIZE * 2, CELL_SIZE * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_s, (255, 255, 255, 110), (CELL_SIZE, CELL_SIZE), 24, 3)
            self.screen.blit(glow_s, (cx - CELL_SIZE, cy - CELL_SIZE))

        # 即時情境【柴犬教官】動態新手對話框
        badge_txt, badge_bg, main_txt, txt_col, step_tag = self._get_mascot_guide_data()
        banner_h = 26
        banner_rect = pygame.Rect(GRID_X, GRID_Y - 28, map_w, banner_h)
        pygame.draw.rect(self.screen, (28, 37, 46, 235), banner_rect, border_radius=8)
        pygame.draw.rect(self.screen, (70, 85, 100), banner_rect, width=1, border_radius=8)

        # 左側膠囊徽章 (Badge)
        badge_w = 95
        badge_r = pygame.Rect(banner_rect.x + 4, banner_rect.y + 3, badge_w, banner_h - 6)
        pygame.draw.rect(self.screen, badge_bg, badge_r, border_radius=6)
        b_surf = FONT_XS.render(badge_txt, True, C_WHITE)
        self.screen.blit(b_surf, (badge_r.centerx - b_surf.get_width() // 2, badge_r.centery - b_surf.get_height() // 2))

        # 中間主引導對話
        self.screen.blit(FONT_SM.render(main_txt, True, txt_col), (badge_r.right + 12, banner_rect.y + 4))

        # 右側步驟進度標籤
        tag_surf = FONT_XS.render(step_tag, True, (176, 190, 197))
        self.screen.blit(tag_surf, (banner_rect.right - tag_surf.get_width() - 10, banner_rect.y + 5))



    def _render_night_overlay(self):
        overlay = pygame.Surface((self.game.width * CELL_SIZE, self.game.height * CELL_SIZE), pygame.SRCALPHA)
        if self.game.is_blood_moon:
            overlay.fill((80, 15, 25, 185))
        else:
            overlay.fill((12, 18, 35, 180))

        # 手電筒聚光燈視野（隨滑鼠游標即時照明）
        mx, my = self.mouse_pos
        local_mx = mx - GRID_X
        local_my = my - GRID_Y
        if 0 <= local_mx <= self.game.width * CELL_SIZE and 0 <= local_my <= self.game.height * CELL_SIZE:
            # 挖空主視野圈（原本 115px，縮減為一半 57）
            pygame.draw.circle(overlay, (0, 0, 0, 0), (local_mx, local_my), 57)
            # 金黃柔光光暈（原本 125/140px，同比例縮減為一半 62/70）
            pygame.draw.circle(overlay, (255, 235, 150, 45), (local_mx, local_my), 62, 10)
            pygame.draw.circle(overlay, (255, 235, 150, 20), (local_mx, local_my), 70, 12)

        if self.game.guard_dog:
            dx = int(self.game.guard_dog.x * CELL_SIZE + CELL_SIZE // 2)
            dy = int(self.game.guard_dog.y * CELL_SIZE + CELL_SIZE // 2)
            pygame.draw.circle(overlay, (0, 0, 0, 0), (dx, dy), 75)

        for y in range(self.game.height):
            for x in range(self.game.width):
                tile = self.game.grid[y][x]
                if tile.decoration:
                    dt = tile.decoration.decoration_type
                    if dt in (DecorationType.CRYSTAL_FOUNTAIN, DecorationType.SOUL_LANTERN):
                        fx = int(x * CELL_SIZE + CELL_SIZE // 2)
                        fy = int(y * CELL_SIZE + CELL_SIZE // 2)
                        pygame.draw.circle(overlay, (0, 0, 0, 0), (fx, fy), 60)

        self.screen.blit(overlay, (GRID_X, GRID_Y))


    def _render_entities(self):
        if self.game.guard_dog:
            dog = self.game.guard_dog
            px = int(GRID_X + dog.x * CELL_SIZE)
            py = int(GRID_Y + dog.y * CELL_SIZE)
            img = self.loader.get("guard_dog")
            if img:
                self.screen.blit(img, (px, py))
            if dog.state in (DogState.CHASING, DogState.COMMANDED):
                bubble_r = pygame.Rect(px + CELL_SIZE - 6, py - 12, 26, 16)
                pygame.draw.rect(self.screen, (255, 255, 255), bubble_r, border_radius=4)
                txt = "汪!" if dog.state == DogState.CHASING else "衝!"
                self.screen.blit(FONT_XS.render(txt, True, C_RED), (bubble_r.x + 4, bubble_r.y + 1))

        if self.game.farm_cat:
            cat = self.game.farm_cat
            px = int(GRID_X + cat.x * CELL_SIZE)
            py = int(GRID_Y + cat.y * CELL_SIZE)
            img = self.loader.get("farm_cat")
            if img:
                self.screen.blit(img, (px, py))

        for enemy in self.game.enemies:
            px = int(GRID_X + enemy.x * CELL_SIZE)
            py = int(GRID_Y + enemy.y * CELL_SIZE)

            if enemy.enemy_type in (EnemyType.WILD_BOAR, EnemyType.BOSS_BOAR_KING):
                # 野豬 (WILD_BOAR) 跟血月首領 (BOSS_BOAR_KING) 共用同一張
                # pig_chroma.png 步行動畫，差別只有縮放後的大小：野豬王用
                # self.loader.boss_frames (放大 1.4x)，野豬用
                # self.loader.enemy_boar_frames (一般格子大小)。
                # 每 200ms 換下一幀，依 enemy.facing_direction 選方向；
                # 素材還沒放進 assets/characters/ 時對應字典是空的，
                # 自動退回原本的靜態圖，不會壞掉。
                is_boss = enemy.enemy_type == EnemyType.BOSS_BOAR_KING
                frame_dict = self.loader.boss_frames if is_boss else self.loader.enemy_boar_frames
                fallback_key = "boss_boar" if is_boss else "enemy_boar"

                frames = frame_dict.get(enemy.facing_direction, [])
                if frames:
                    frame_index = (pygame.time.get_ticks() // 200) % len(frames)
                    img = frames[frame_index]
                else:
                    img = self.loader.get(fallback_key)
                if img:
                    offset_y = -10 if is_boss else 0
                    self.screen.blit(img, (px, py + offset_y))
            elif enemy.enemy_type == EnemyType.THIEF:
                # 小偷 (THIEF) 用 theif.png 8 欄 x 4 列的超流暢動畫，方向
                # 沿用跟野豬/血月首領同一套 enemy.facing_direction（在
                # game_state.py 移動時依 dx/dy 更新），每 100ms 換下一幀
                # (8 幀，比野豬的 200ms 更快，符合「超流暢」的素材節奏)。
                # 素材還沒放進 assets/characters/ 時字典是空的，自動退回
                # 原本的靜態 enemy_thief 圖，不會讓遊戲壞掉。
                frames = self.loader.thief_frames.get(enemy.facing_direction, [])
                if frames:
                    frame_index = (pygame.time.get_ticks() // 100) % len(frames)
                    img = frames[frame_index]
                else:
                    img = self.loader.get("enemy_thief")
                if img:
                    self.screen.blit(img, (px, py))
            else:
                k = ENEMY_DATA[enemy.enemy_type].get("asset_key", "enemy_thief")
                img = self.loader.get(k)
                if img:
                    self.screen.blit(img, (px, py))

            if enemy.state == EnemyState.STUNNED:
                pygame.draw.circle(self.screen, (255, 235, 59), (px + CELL_SIZE // 2, py - 12), 8)
                self.screen.blit(FONT_XS.render("⚡", True, (60, 40, 0)), (px + CELL_SIZE // 2 - 4, py - 18))

            hp_ratio = max(0.0, min(1.0, enemy.hp / enemy.max_hp))
            bar_w = CELL_SIZE - 6 if enemy.enemy_type != EnemyType.BOSS_BOAR_KING else CELL_SIZE + 16
            bar_rect = pygame.Rect(px + 3, py - 6, bar_w, 5)
            pygame.draw.rect(self.screen, (30, 30, 30), bar_rect, border_radius=2)
            pygame.draw.rect(self.screen, C_RED, (bar_rect.x, bar_rect.y, int(bar_w * hp_ratio), 5), border_radius=2)

    # ==========================================
    # 側邊商店面板 -- 幾何常數集中在這三個 helper，畫面渲染與滑鼠點擊
    # 判定都呼叫同一份，位置不會不同步。
    # ==========================================
    def _shop_panel_rect(self) -> pygame.Rect:
        sb_x = GRID_X + self.game.width * CELL_SIZE + 18
        sb_w = SCREEN_WIDTH - sb_x - 24
        panel_h = SCREEN_HEIGHT - GRID_Y - 24
        return pygame.Rect(sb_x, GRID_Y, sb_w, panel_h)

    def _layout_shop_tabs(self):
        """回傳 [(tab_id, label, rect), ...]，面板內 2x2 分頁格。"""
        panel = self._shop_panel_rect()
        pad = 14
        gap = 8
        tab_w = (panel.width - 2 * pad - gap) // 2
        tab_h = 32
        top = panel.y + 44 + 12
        out = []
        for i, (tab_id, label, _old_rect) in enumerate(self.tab_buttons):
            col = i % 2
            row = i // 2
            x = panel.x + pad + col * (tab_w + gap)
            y = top + row * (tab_h + 6)
            out.append((tab_id, label, pygame.Rect(x, y, tab_w, tab_h)))
        return out

    def _shop_list_area(self) -> pygame.Rect:
        """分頁格下方、可捲動的卡片清單可視範圍（不含捲動位移）。"""
        panel = self._shop_panel_rect()
        tabs_bottom = panel.y + 44 + 12 + 2 * 32 + 6
        top = tabs_bottom + 14
        pad = 14
        return pygame.Rect(panel.x + pad, top, panel.width - 2 * pad - 8, panel.bottom - 14 - top)

    def _layout_shop_list(self):
        """把目前分頁裡的卡片依捲動位移排成一欄，回傳這份清單本身，
        同時把每張卡片的 .rect 更新成畫面上（可能捲出可視範圍外）的
        實際位置 -- 繪製跟點擊判定都讀這個屬性，兩者永遠一致。"""
        area = self._shop_list_area()
        row_h = 64 + 8
        scroll = self.shop_scroll.get(self.active_tab, 0)
        items = [c for c in self.action_cards if c.tab_id == self.active_tab]
        for i, card in enumerate(items):
            y = area.y + i * row_h - scroll
            card.rect = pygame.Rect(area.x, y, area.width, 64)
        return items

    def _shop_scroll_bounds(self, item_count: int) -> int:
        area = self._shop_list_area()
        row_h = 64 + 8
        total_h = item_count * row_h - 8 if item_count else 0
        return max(0, total_h - area.height)

    def _render_shop_panel(self):
        panel = self._shop_panel_rect()

        # 淡淡的投影，跟卡片一致的浮起質感。
        shadow = pygame.Surface((panel.width, panel.height), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (20, 25, 30, 30), shadow.get_rect(), border_radius=14)
        self.screen.blit(shadow, (panel.x + 3, panel.y + 4))

        pygame.draw.rect(self.screen, (255, 255, 255), panel, border_radius=14)
        pygame.draw.rect(self.screen, C_CARD_BORDER, panel, width=1, border_radius=14)

        # 深色標題橫幅，跟頂部 HUD 同一套配色 (C_NAVY_TOP + C_GOLD)，
        # 讓商店面板一眼就能認出是同一套視覺語言，不是另外貼上去的東西。
        header_rect = pygame.Rect(panel.x, panel.y, panel.width, 44)
        pygame.draw.rect(self.screen, C_NAVY_TOP, header_rect, border_top_left_radius=14, border_top_right_radius=14)
        title_surf = FONT_MD.render("莊園商店", True, C_GOLD)
        self.screen.blit(title_surf, (header_rect.centerx - title_surf.get_width() // 2, header_rect.centery - title_surf.get_height() // 2))

        # 2x2 分頁格
        tabs = self._layout_shop_tabs()
        self.tab_buttons = tabs
        for tab_id, label, rect in tabs:
            is_active = (self.active_tab == tab_id)
            tint = SHOP_TAB_TINTS.get(tab_id, C_ORANGE)
            bg_col = (255, 255, 255) if is_active else (240, 242, 245)
            pygame.draw.rect(self.screen, bg_col, rect, border_radius=8)
            border_col = tint if is_active else (210, 212, 216)
            pygame.draw.rect(self.screen, border_col, rect, width=2 if is_active else 1, border_radius=8)
            txt_col = C_TEXT_MAIN if is_active else C_TEXT_MUTED
            t_surf = FONT_XS.render(label, True, txt_col)
            self.screen.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.centery - t_surf.get_height() // 2))

        # 分頁格跟卡片清單之間的分隔線
        area = self._shop_list_area()
        pygame.draw.line(self.screen, (230, 235, 240), (area.x, area.y - 8), (area.right, area.y - 8))

        # 可捲動的卡片清單：先用 set_clip 把畫面限制在清單可視範圍內，
        # 捲出範圍的卡片畫出來也不會溢出面板底部。
        items = self._layout_shop_list()
        prev_clip = self.screen.get_clip()
        self.screen.set_clip(area)
        for card in items:
            if card.rect.bottom < area.y or card.rect.top > area.bottom:
                continue
            card.draw(self.screen, is_selected=(self.selected_action == card.action_id), loader=self.loader)
        self.screen.set_clip(prev_clip)

        # 內容超出可視範圍才畫捲軸滑塊，提示「還能往下滑」。
        max_scroll = self._shop_scroll_bounds(len(items))
        if max_scroll > 0:
            track = pygame.Rect(area.right + 4, area.y, 4, area.height)
            pygame.draw.rect(self.screen, (225, 228, 232), track, border_radius=2)
            scroll = self.shop_scroll.get(self.active_tab, 0)
            thumb_h = max(24, int(area.height * area.height / (area.height + max_scroll)))
            thumb_y = area.y + int((area.height - thumb_h) * (scroll / max_scroll))
            thumb = pygame.Rect(track.x, thumb_y, 4, thumb_h)
            pygame.draw.rect(self.screen, (170, 176, 184), thumb, border_radius=2)

    # ==========================================
    # 開場新手速成圖卡彈窗
    # ==========================================
    def _render_story_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 235))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 840, 580
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)

        pygame.draw.rect(self.screen, (255, 255, 255), modal_rect, border_radius=18)
        pygame.draw.rect(self.screen, C_ORANGE, modal_rect, width=3, border_radius=18)

        t = FONT_TITLE.render("🌾《夜巡農場》新手速成指南 (Quickstart Guide)", True, (38, 50, 56))
        self.screen.blit(t, (mx + (modal_w - t.get_width()) // 2, my + 20))
        sub_t = FONT_SM.render("掌握 3 大核心步驟，由「柴犬管家」手把手帶您守護農莊！", True, C_TEXT_MUTED)
        self.screen.blit(sub_t, (mx + (modal_w - sub_t.get_width()) // 2, my + 56))

        # 3 個直覺新手步驟卡片
        steps = [
            (
                "🌱 步驟 1：日間耕種與採收變現",
                (76, 175, 80),
                (240, 248, 240),
                [
                    "1. 點擊下方工具列【白蘿蔔種子 ($10)】，在中央深色農田點擊播種。",
                    "2. 作物成熟長大後（泛出金黃光芒），【直接點擊作物】即可採收賺取金幣！",
                    "3. 點選【黃金澆水壺 ($5)】可為作物加速生長 50%。"
                ]
            ),
            (
                "🛡️ 步驟 2：天黑前佈置防禦防線",
                (255, 152, 0),
                (255, 248, 238),
                [
                    "1. 天黑前切換至【防禦】分頁，購買【看門柴犬 ($100)】自動撲咬敵人！",
                    "2. 在農田四周建造【刺藤木柵 ($15)】阻擋怪物，或設置【鋼鐵捕獸夾 ($20)】。",
                    "3. 存活過夜的作物隔日採收享有【月光滋養 +50% 巨額金幣】回報！"
                ]
            ),
            (
                "🔦 步驟 3：夜晚夜巡與強光手電筒擊暈",
                (33, 150, 243),
                (240, 246, 255),
                [
                    "1. 天黑怪物突襲時，點選下方工具列【強光手電筒】。",
                    "2. 滑鼠游標直接【點擊地圖上的敵人】，即可瞬間發射強光照暈 2.5 秒（3秒充能）！",
                    "3. 阻止小偷與野豬掠奪作物與金庫，破曉後至【景觀】佈置松樹、楓樹提升莊園等級！"
                ]
            ),


        ]

        card_y = my + 88
        for title, b_col, bg_col, lines in steps:
            card_r = pygame.Rect(mx + 30, card_y, modal_w - 60, 110)
            pygame.draw.rect(self.screen, bg_col, card_r, border_radius=10)
            pygame.draw.rect(self.screen, b_col, card_r, width=2, border_radius=10)

            # 標題欄
            pygame.draw.rect(self.screen, b_col, (card_r.x, card_r.y, card_r.w, 28), border_top_left_radius=8, border_top_right_radius=8)
            self.screen.blit(FONT_MD.render(title, True, C_WHITE), (card_r.x + 12, card_r.y + 4))

            line_y = card_r.y + 34
            for l in lines:
                self.screen.blit(FONT_SM.render(l, True, (45, 55, 65)), (card_r.x + 14, line_y))
                line_y += 24

            card_y += 122

        # 底部提示文字
        bot_tip = FONT_XS.render("💡 提示：初始資金已充能為 $300 G，第 1 天提供 30 秒充裕時間，請跟隨畫面上方【柴犬管家】輕鬆遊玩！", True, (100, 115, 130))
        self.screen.blit(bot_tip, (mx + (modal_w - bot_tip.get_width()) // 2, my + 468))

        btn_start = pygame.Rect(mx + (modal_w - 280) // 2, my + 500, 280, 54)
        pygame.draw.rect(self.screen, C_GREEN, btn_start, border_radius=12)
        pygame.draw.rect(self.screen, (56, 142, 60), btn_start, width=2, border_radius=12)
        btn_txt = FONT_LG.render("🚀 我瞭解了，開始農莊冒險！", True, C_WHITE)
        self.screen.blit(btn_txt, (btn_start.centerx - btn_txt.get_width() // 2, btn_start.centery - btn_txt.get_height() // 2))


    # ==========================================
    # 遊戲結束彈窗
    # ==========================================
    def _render_game_over_modal(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 580, 330
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)

        pygame.draw.rect(self.screen, (255, 255, 255), modal_rect, border_radius=14)
        pygame.draw.rect(self.screen, C_RED, modal_rect, width=3, border_radius=14)

        t1 = FONT_TITLE.render("💀 遊戲結束 (GAME OVER)", True, C_RED)
        self.screen.blit(t1, (mx + (modal_w - t1.get_width()) // 2, my + 30))

        r1 = FONT_MD.render("農場資金斷絕，破產淘汰！", True, C_TEXT_MAIN)
        self.screen.blit(r1, (mx + (modal_w - r1.get_width()) // 2, my + 80))

        r2 = FONT_SM.render(self.game.game_over_reason, True, C_RED)
        self.screen.blit(r2, (mx + (modal_w - r2.get_width()) // 2, my + 112))

        d1 = FONT_SM.render(f"生存天數: {self.game.day_count} 天 | 最終繁榮度: {self.game.prosperity_score}", True, C_TEXT_MUTED)
        self.screen.blit(d1, (mx + (modal_w - d1.get_width()) // 2, my + 148))

        btn_restart = pygame.Rect(mx + (modal_w - 200) // 2, my + 215, 200, 48)
        pygame.draw.rect(self.screen, C_GREEN, btn_restart, border_radius=8)
        btn_txt = FONT_MD.render("🔄 重新挑戰農場", True, C_WHITE)
        self.screen.blit(btn_txt, (btn_restart.centerx - btn_txt.get_width() // 2, btn_restart.centery - btn_txt.get_height() // 2))


if __name__ == "__main__":
    app = NightwatchFarmApp()
    app.run()