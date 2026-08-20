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
    DefenseType, BuildingType, EnemyType, EnemyState, DogState, EventType,
    MAP_CONFIG, FARM_LEVELS, CROP_DATA, DECORATION_DATA, DEFENSE_DATA, BUILDING_DATA,
    DOG_CONFIG, CAT_CONFIG, ENEMY_DATA, ORDER_CROP_ALIASES, GameEvent
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

CELL_SIZE = 60  # 原本 50，配合網格從 18x13 裁到 16x11 換來 +20% 放大
ANIMATION_SPEED = 0.2  # 熔爐 Sprite Sheet 動畫每幀停留秒數（frame[1]/frame[2] 來回切換的節奏）
GRID_X = 24
# 【系統修復：UI 元素重疊/文字溢出/導覽列被切斷】原本 GRID_Y=86，只比
# 頂部資源列 (0~70) 多留 16px；但正下方緊貼的飛船 AI 任務橫幅
# (MISSION_BANNER_Y=84, 高 32px，涵蓋到 y=116) 卻幾乎整條都落在
# GRID_Y=86 之後——因為 _render() 的繪製順序是「先畫頭部資源列→畫任務
# 橫幅→再畫農田地圖」，農田地圖範圍從 y=86 開始整片鋪色，會直接蓋掉
# 任務橫幅下半部 (86~116) 這 30px，畫面上看起來就像「頂部導覽列被地圖
# 背景截斷」。修正做法是把 GRID_Y（連帶所有從它推算座標的地圖/商店
# 面板/建築/特效座標）整體往下挪，讓農田地圖真正從任務橫幅結束之後才
# 開始，兩者不再有任何重疊，不需要為了圖層順序另外犧牲繪製效能重畫。
GRID_Y = 124

# 扁平現代色彩（地圖/農田本身維持原本清爽的現代配色，這次改版只動
# UI 外殼——頂部狀態列、右側商店面板、商品卡片這些「介面」，農田視覺
# 不變，兩者風格刻意分開，農田才是玩家實際盯著看的主體）
C_MEADOW_BG = (230, 235, 225)       # 純色柔和綠草地
C_FARM_SOIL = (205, 195, 175)        # 純色溫暖農田底色
C_FARM_SHADOW = (180, 142, 102)      # 農田投影
C_FARM_BORDER = (156, 116, 78)       # 苗圃外框色

# ---- 鄉村木質風格 (Rustic Wooden Style) UI 色票 ----------------------------
# 這裡集中定義「UI 外殼」（頂部狀態列、右側商店大底框、商品卡片、按鈕）
# 用的木頭色系，取代原本的深灰現代化配色，跟農場主題更搭。
C_WOOD_DARK = (78, 52, 46)          # 深木頭色：狀態列/商店大底框/標題橫幅背景
C_WOOD_MID = (109, 76, 65)          # 中層木板色：狀態列裡凸起的小面板（金幣卡/等級卡/按鈕）
C_PARCHMENT = (215, 204, 200)       # 淺木板／羊皮紙色：商品卡片、面板內層底色
C_WOOD_BEVEL_LIGHT = (168, 138, 122)  # 立體雕刻邊框的「高光」邊，見 draw_beveled_rect()
C_WOOD_BEVEL_DARK = (46, 28, 25)      # 立體雕刻邊框的「陰影」邊，比邊框色更深、營造凹陷刻痕
C_TEXT_ON_DARK = (245, 245, 220)    # 米白色文字：用在深木色背景上（狀態列文字）
C_TEXT_ON_LIGHT = (62, 39, 35)      # 深褐色文字：用在淺木/羊皮紙背景上（卡片文字）

C_NAVY_TOP = C_WOOD_DARK             # 頂部導航底色（原本是深藍灰，現在沿用木質風格的深木色）
C_WHITE = (255, 255, 255)
C_CARD_BG = C_PARCHMENT              # 卡片底色（原本是純白，現在是羊皮紙色）
C_CARD_BORDER = C_WOOD_BEVEL_DARK    # 卡片邊框（原本是淺灰 1px，現在搭配立體雕刻效果用深褐色）

C_TEXT_MAIN = C_TEXT_ON_LIGHT         # 淺色底（羊皮紙/木板）上的主要文字，原本是接近黑色
C_TEXT_MUTED = (140, 112, 100)        # 次要/停用文字，原本是純灰，現在偏木質的淡褐灰
C_GOLD = (255, 193, 7)                # 焦點/選取色，沿用不變——金色本來就很搭木頭
# 浮動文字專用的亮黃色：C_GOLD 是偏琥珀色的「金色」，拿來當 UI 焦點色很
# 好看，但直接拿來畫在草地/夜晚場景上的浮動文字時，彩度不夠、容易讀起來
# 是「暗黃色」。這個顏色只給浮動文字用，跟 C_GOLD 的 UI 焦點色用途分開，
# 不會互相影響。
C_FLOATTEXT_GOLD = (255, 241, 118)
# 未解鎖商品鎖定原因文字的紅色：原本 (255,130,130) 疊在半透明深色遮罩上
# 對比度不夠，改用更亮的紅（跟浮動文字錯誤提示的 C_RED 系列同一個色階）。
C_LOCK_TEXT_RED = (255, 85, 85)
# 科技點數 HUD 專用的螢光「科技綠」：跟金幣的暖色系金黃、繁榮度進度條的
# 沉穩草綠 (C_GREEN) 都拉開差距，一眼就能認出這是另一種資源，不會被
# 誤認成金幣或繁榮度數字。
C_TECH_GREEN = (0, 230, 130)
C_GREEN = (76, 175, 80)
C_RED = (239, 83, 80)
C_BLUE = (33, 150, 243)
C_PURPLE = (156, 39, 176)
C_CYAN = (0, 188, 212)
C_ORANGE = (255, 152, 0)
C_BLOOD_RED = (211, 47, 47)


def draw_beveled_rect(surface, rect, base_color, border_radius=8, depth=2, pressed=False,
                       light_color=None, dark_color=None):
    """畫一個帶有「立體雕刻 (Beveled/Carved)」感的木頭色塊，取代單純的
    1px 純色邊框：先填滿底色，再於矩形的「上邊、左邊」疊一條較亮的高光
    線、「下邊、右邊」疊一條更深的陰影線，讓玩家感覺這塊木頭是刻出來、
    凸起在畫面上的，而不是貼上去的平面色塊。

    pressed=True 時把高光/陰影對調（下、右變亮，上、左變暗），做出
    「按下去凹陷」的視覺錯覺——例如目前鎖定、點不了的商品卡片，或是
    滑鼠正按著的按鈕，用這個參數就能重用同一個函式表達「凹進去」而不
    是「凸出來」，不用另外寫一份繪製邏輯。

    light_color / dark_color 預設吃 C_WOOD_BEVEL_LIGHT / C_WOOD_BEVEL_DARK，
    需要跟特定底色更搭配的高光/陰影色時可以個別覆寫。

    【貼圖彈性預留】：如果之後在 assets/ui/ 放了 wood_panel.png 這種
    木紋貼圖，想直接貼圖取代純色底，改法是在下面這行
        pygame.draw.rect(surface, base_color, rect, border_radius=border_radius)
    前面插入類似：
        wood_tex = loader.get("ui_wood_panel")  # 需要先在 asset_loader.py 建立對應的載入邏輯
        if wood_tex:
            scaled = pygame.transform.smoothscale(wood_tex, rect.size)
            surface.blit(scaled, rect.topleft)
        else:
            pygame.draw.rect(surface, base_color, rect, border_radius=border_radius)
    然後把原本的純色 pygame.draw.rect 包進 else 分支當作貼圖缺失時的
    後備方案即可，下面疊加的高光/陰影刻痕線可以照樣保留在貼圖上，
    紋理貼圖加上手繪立體邊框通常比純貼圖更有層次感。
    """
    light = light_color if light_color is not None else C_WOOD_BEVEL_LIGHT
    dark = dark_color if dark_color is not None else C_WOOD_BEVEL_DARK
    if pressed:
        light, dark = dark, light

    pygame.draw.rect(surface, base_color, rect, border_radius=border_radius)

    inset = border_radius
    pygame.draw.line(surface, light, (rect.left + inset, rect.top + 1), (rect.right - inset, rect.top + 1), depth)
    pygame.draw.line(surface, light, (rect.left + 1, rect.top + inset), (rect.left + 1, rect.bottom - inset), depth)
    pygame.draw.line(surface, dark, (rect.left + inset, rect.bottom - 2), (rect.right - inset, rect.bottom - 2), depth)
    pygame.draw.line(surface, dark, (rect.right - 2, rect.top + inset), (rect.right - 2, rect.bottom - inset), depth)


def draw_9_slice(surface, rect, texture, border=16):
    """真正的九宮格 (9-slice) 貼圖繪製：把 `texture` 切成四角 + 四邊 + 中央
    共 9 塊，四角原尺寸貼上不變形，四邊只沿單一軸縮放拉伸，中央兩軸都縮放
    填滿 `rect` 內部——這樣不管 `rect` 被撐多大/多小，貼圖四個角落的雕花
    /圓角都不會被拉伸走樣，只有中間的素色/紋理區域會被拉伸，是遊戲 UI
    最常見的「木牌/面板貼圖可任意縮放」處理方式。

    `texture` 必須是已經載入好的 pygame.Surface（例如
    `self.loader.get("ui_wood_panel")`）；呼叫端要自行確認它不是 None，
    這個函式本身不處理貼圖缺失的後備方案——缺圖後備邏輯統一寫在
    `draw_wood_panel()` 裡（見下方），這裡只單純負責「有貼圖的話怎麼切」。
    """
    tw, th = texture.get_size()
    b = max(1, min(border, tw // 2 - 1, th // 2 - 1))
    rw, rh = rect.width, rect.height
    if rw < 2 * b or rh < 2 * b:
        # 目標矩形比貼圖的邊框還小，九宮格切法會出錯，退化成整張貼圖
        # 直接等比例縮放貼滿，勉強堪用總比噴例外好。
        scaled = pygame.transform.smoothscale(texture, (max(1, rw), max(1, rh)))
        surface.blit(scaled, rect.topleft)
        return

    tl = texture.subsurface((0, 0, b, b))
    tr = texture.subsurface((tw - b, 0, b, b))
    bl = texture.subsurface((0, th - b, b, b))
    br = texture.subsurface((tw - b, th - b, b, b))
    top = texture.subsurface((b, 0, tw - 2 * b, b))
    bottom = texture.subsurface((b, th - b, tw - 2 * b, b))
    left = texture.subsurface((0, b, b, th - 2 * b))
    right = texture.subsurface((tw - b, b, b, th - 2 * b))
    center = texture.subsurface((b, b, tw - 2 * b, th - 2 * b))

    cw, ch = rw - 2 * b, rh - 2 * b
    surface.blit(tl, rect.topleft)
    surface.blit(tr, (rect.right - b, rect.top))
    surface.blit(bl, (rect.left, rect.bottom - b))
    surface.blit(br, (rect.right - b, rect.bottom - b))
    if cw > 0:
        surface.blit(pygame.transform.scale(top, (cw, b)), (rect.left + b, rect.top))
        surface.blit(pygame.transform.scale(bottom, (cw, b)), (rect.left + b, rect.bottom - b))
    if ch > 0:
        surface.blit(pygame.transform.scale(left, (b, ch)), (rect.left, rect.top + b))
        surface.blit(pygame.transform.scale(right, (b, ch)), (rect.right - b, rect.top + b))
    if cw > 0 and ch > 0:
        surface.blit(pygame.transform.scale(center, (cw, ch)), (rect.left + b, rect.top + b))


def draw_wood_panel(surface, rect, loader, texture_key, base_color, border_radius=14, depth=3,
                     pressed=False, border=16):
    """面板/按鈕背景繪製的統一入口。優先嘗試從 `loader.get(texture_key)`
    拿到真正的木紋九宮格貼圖並用 `draw_9_slice()` 繪製；如果貼圖還沒放進
    `assets/ui/`（`loader.get()` 回傳 None，就跟 `grass_img =
    self.loader.get("grass_tile")` 這種既有寫法遇到缺圖時一樣），就自動
    退回目前已經在商店面板/頂部狀態列驗證過可行的 `draw_beveled_rect()`
    立體木頭色塊畫法。呼叫端完全不用關心貼圖存不存在，兩種畫法在這裡
    無縫切換；未來只要把 `wood_panel.png` / `wood_button.png` 放進
    `assets/ui/`，畫面會自動改用真正的九宮格貼圖，不用再改呼叫端程式碼。
    """
    texture = loader.get(texture_key) if loader is not None else None
    if texture is not None:
        draw_9_slice(surface, rect, texture, border=border)
    else:
        draw_beveled_rect(surface, rect, base_color, border_radius=border_radius, depth=depth, pressed=pressed)


def blit_text_with_shadow(surface, font, text, color, topleft=None, center=None,
                           shadow_color=(20, 20, 20)):
    """畫帶有四方向黑色描邊/陰影的文字，確保在木紋（偏棕/偏暗）背景上
    仍然清楚可讀——跟 FloatingText/鎖定商品卡片既有的描邊寫法同一套
    技巧，這裡抽成共用函式給彈窗（暫停選單、遊戲結束畫面）使用。
    回傳最終文字的 Rect，方便呼叫端接著算後續版面位置。
    """
    shadow_surf = font.render(text, True, shadow_color)
    main_surf = font.render(text, True, color)
    if center is not None:
        r = main_surf.get_rect(center=center)
    else:
        r = main_surf.get_rect(topleft=topleft)
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        surface.blit(shadow_surf, (r.x + dx, r.y + dy))
    surface.blit(main_surf, r)
    return r


def draw_text_with_outline(surface, text, font, text_color, outline_color, center_pos, outline_width=2):
    """畫帶有完整 8 方向（上下左右 + 四個斜角）描邊的文字，用來解決淺色
    文字疊在亮度不固定的背景圖（例如主選單的太空船背景圖）上「吃色」、
    對比度不足看不清楚的問題。

    跟上面既有的 blit_text_with_shadow() 不是同一個函式、刻意沒有讓
    這個新函式去呼叫/重構那個舊函式：blit_text_with_shadow() 只往
    上下左右 4 個方向各偏移固定 1px（原本是給彈窗這種本來就是深色/
    木紋背景設計的，背景本身已經夠暗，4 方向 1px 的描邊已經夠讀），
    這裡的需求明確是「背景亮度不可預期、太空船背景可能比文字本身還
    亮」，需要更強的 8 方向描邊 + 可調粗細（outline_width）才夠可靠，
    直接沿用舊函式的固定 4 方向/1px 沒辦法達到這個强度，所以另外獨立
    實作一個函式，職責分開、互不影響彼此既有的呼叫端。
    """
    outline_surf = font.render(text, True, outline_color)
    main_surf = font.render(text, True, text_color)
    r = main_surf.get_rect(center=center_pos)
    for dx, dy in (
        (-outline_width, 0), (outline_width, 0), (0, -outline_width), (0, outline_width),
        (-outline_width, -outline_width), (outline_width, -outline_width),
        (-outline_width, outline_width), (outline_width, outline_width),
    ):
        surface.blit(outline_surf, (r.x + dx, r.y + dy))
    surface.blit(main_surf, r)
    return r


# ------------------------------------------------------------------
# 中文字型載入 (fixes "□" tofu-box rendering)
#
# 舊寫法的問題：pygame.font.match_font(name) 對 SDL 來說是很寬鬆的模糊比對，
# 就算清單裡四個名字全部比對失敗，match_font 也常常不會回傳 None，而是回退到
# 隨便一個系統預設字型（通常是 Arial 之類的西方字型），完全不含中文字形，
# 於是遊戲畫面上的中文字全部變成「□」豆腐塊，而且不會有任何錯誤訊息。
#
# 技術債清理（系統字型 Fallback 版本）：這個開發/沙箱環境沒辦法放置完整
# 的外部字型檔（前一個階段規劃要換用的 Cubic_11.ttf 檔案本身一直沒有
# 實際放進 assets/fonts/），先前綁定的 NotoSansTC-GameSubset.otf 又是裁
# 切過的殘缺子集（Phase 4.75 調查發現 140+ 常用字缺字），這兩個因素疊
# 在一起，代表「專案自帶字型」這個管道在目前的開發環境裡實質上是失效
# 的。這次把優先順序整個反過來：
#   1. 系統字型（新的第一優先）：用 pygame.font.get_fonts() 列出「這台
#      機器真的偵測到」的字型名單，跟一份跨平台中文字型名稱清單取交
#      集，只在確認系統真的裝了某個中文字型時才使用它——玩家自己的電
#      腦（Windows 幾乎都有微軟正黑體、macOS 幾乎都有蘋方、大多數
#      Linux 桌面環境也會有 Noto Sans CJK 之類的套件），這些系統字型
#      通常是「完整字集」，不會有子集裁切缺字的問題，比目前殘缺的專案
#      自帶字型更可靠。
#   2. 專案自帶字型（次要 fallback）：assets/fonts/ 底下的字型檔，只有
#      系統偵測不到任何中文字型時才會用到——保留這一層是為了在「完全
#      沒有中文系統字型」的極端環境（例如某些精簡過的 Linux 容器）下，
#      至少還有機會顯示出部分中文，好過整個環境完全沒有字型可用直接
#      崩潰；即使目前這個檔案（NotoSansTC-GameSubset.otf）字集不完整，
#      「顯示大部分常用字、少數字變豆腐塊」也優於「完全沒有中文字型、
#      滿螢幕豆腐塊」。
#   3. 都找不到才退回 Arial，並在終端機印出明確警告，而不是默默顯示豆腐塊。
#
# 【這個環境沒辦法驗證的部分，如實揭露】這個沙箱是 headless 環境，沒有
# 安裝任何桌面版中文字型，pygame 本身在這裡甚至無法 import（整個 session
# 都是這樣，見先前幾個階段的說明），所以 pygame.font.get_fonts() 實際
# 會偵測到什麼字型、match_font() 找不找得到，完全沒辦法在這裡執行驗證
# ——這個新的系統字型優先邏輯，需要使用者在自己真的裝了中文字型的電腦
# 上執行才能驗證是否正確運作。
# ------------------------------------------------------------------
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "fonts")

# 上一個技術債清理階段留下的常數：assets/fonts/ 資料夾裡如果有這個檔
# 案（完整字庫），次要 fallback（_find_bundled_font_path()）會優先選
# 它，而不是掃到什麼字型檔就用什麼。這次系統字型變成第一優先之後，這
# 個常數的實際影響範圍縮小了（只在系統完全沒有中文字型時才會用到），
# 但不刪除它——如果之後使用者真的把 Cubic_11.ttf 放進資料夾，這裡還
# 是能在「系統字型優先」失效的極端情況下正確選到它，而不是選到舊的
# NotoSansTC-GameSubset.otf。
PREFERRED_FONT_FILENAME = "Cubic_11.ttf"

# 系統中文字型優先清單。原本 _CJK_SYSTEM_FONT_HINTS 這份清單已經涵蓋
# Windows/macOS/Linux 常見中文字型，這次額外併入使用者這次指定的清單
# （'pingfang' 泛用別名、'stheiti'、'arialunicodems'——'microsoftjhenghei'
# 已經在原本清單裡，'simhei' 也是），用 dict.fromkeys() 去重但保留原本
# 的優先順序（原清單在前，新增項目接在後面，不會打亂既有的比對順序）。
_USER_SUPPLIED_CJK_HINTS = [
    "microsoftjhenghei", "pingfang", "stheiti", "simhei", "arialunicodems",
]

_CJK_SYSTEM_FONT_HINTS = list(dict.fromkeys([
    # Windows
    "microsoftjhenghei", "microsoftjhengheiui", "microsoftjhengheiuibold",
    "microsoftyahei", "microsoftyaheiui", "simhei", "simsun", "mingliu", "dfkaisb",
    # macOS
    "pingfangtc", "pingfangsc", "pingfang", "heititc", "heitisc", "stheititc", "stheitisc",
    # Linux
    "notosanscjktc", "notosanscjksc", "notosanscjk", "wqymicrohei", "wqyzenhei",
    "droidsansfallback",
    # 這次使用者額外指定、上面尚未涵蓋到的名稱
    *_USER_SUPPLIED_CJK_HINTS,
]))


def _find_bundled_font_path() -> Optional[str]:
    """只在系統偵測不到任何中文字型時才會被呼叫到的次要 fallback。
    PREFERRED_FONT_FILENAME 沿用上一個技術債清理階段的設計——如果
    assets/fonts/ 資料夾裡有 Cubic_11.ttf（完整字庫），優先用它；沒有
    的話才退回掃資料夾抓第一個字型檔（目前資料夾裡實際存在的是舊的
    NotoSansTC-GameSubset.otf 子集字型）。這一層邏輯保留但不再是主要
    路徑——現在系統字型才是第一優先，這裡只在系統完全沒有中文字型時
    才會派上用場。"""
    if not os.path.isdir(FONT_DIR):
        return None

    preferred_path = os.path.join(FONT_DIR, PREFERRED_FONT_FILENAME)
    if os.path.isfile(preferred_path):
        return preferred_path

    for fn in sorted(os.listdir(FONT_DIR)):
        if fn.lower().endswith((".ttf", ".ttc", ".otf")):
            return os.path.join(FONT_DIR, fn)
    return None


def _find_system_cjk_font_path() -> Optional[str]:
    """用 pygame.font.get_fonts() 取得這台機器真的偵測到的字型名單，跟
    _CJK_SYSTEM_FONT_HINTS 取交集，只在確認系統真的裝了某個中文字型時
    才呼叫 match_font() 取得實際路徑——刻意不直接呼叫
    pygame.font.SysFont(name_list, size)，因為 SysFont() 內部一樣是用
    match_font() 模糊比對，清單裡的名字全部比對失敗時一樣可能默默退回
    某個不含中文字形的西方字型，而不是老實回傳「找不到」，跟上面文件
    開頭那段「舊寫法的問題」講的是同一個陷阱，用這裡的寫法可以在
    「系統字型清單裡沒有真的找到中文字型」時明確得到 None，而不是一個
    看似成功、實際上顯示豆腐塊的字型物件。"""
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


_SYSTEM_CJK_FONT_PATH = _find_system_cjk_font_path()
_BUNDLED_FONT_PATH = None if _SYSTEM_CJK_FONT_PATH else _find_bundled_font_path()
_RESOLVED_FONT_PATH = _SYSTEM_CJK_FONT_PATH or _BUNDLED_FONT_PATH

if _RESOLVED_FONT_PATH is None:
    print(
        "[字型警告] 找不到可顯示中文的字型，UI 文字可能會顯示「□」。"
        f"請安裝一套系統中文字型（例如微軟正黑體/蘋方/Noto Sans CJK），"
        f"或把一個中文 .ttf/.ttc/.otf 字型檔放進 {FONT_DIR} 資料夾"
        "，程式下次啟動會自動偵測使用，不需要改任何程式碼。"
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
    Misc Symbols 這些字型通常沒有字形的字元），確保丟進 font.render 的
    字串一定乾淨，不會跑出缺字符方塊「☒」。

    技術債清理備註：Phase 4.75 曾經調查過，發現舊字型
    NotoSansTC-GameSubset.otf 是裁切過的子集字型，實際顯示文字裡有
    140+ 個字不在收錄範圍內（「科」「技」「訂」「關」「灑」等大量既有
    UI 文字用字都中標），當時因為那個範圍太大、這個環境又沒辦法執行
    pygame 實際驗證，決定不擴大 safe_text() 的過濾範圍，只針對機台簡
    寫做局部替換，並把完整問題揭露給使用者建議另外處理。這次換成完整
    字庫的 Cubic_11.ttf 之後，那個「字型子集缺字」的根本原因已經不存
    在（只要新字型檔案真的有完整涵蓋繁體中文常用字）——這個函式維持
    原本「按 Unicode 區段過濾」的簡單邏輯即可，不需要、也不必再加上
    當時評估過的 fontTools 動態 cmap 檢查那層複雜度。這裡仍然保留區段
    過濾（不是整個拿掉這個函式），是因為就算換成點陣中文字型，通常也
    不會內建 Emoji 字形，emoji 字元還是需要被濾掉，道理跟原本一樣。"""
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

# 技術債清理（系統字型 Fallback 版本）：拔除合成粗體 + 微調字級。
#
# 拔除合成粗體：pygame/SDL_ttf 的 bold=True 是用「加粗筆畫」模擬出來的
# 合成粗體（不是字型檔案裡真的有一份粗體字形），對系統字型或點陣風格
# 字型常常會讓筆畫糊成一團、邊緣不銳利，這次照要求把 FONT_MD/FONT_LG/
# FONT_TITLE 的 bold=True 全部拿掉，改成用字級大小做視覺區分（原本就
# 是 XS < SM < MD < LG < TITLE 這個遞增的階層，拿掉粗體之後這個字級落
# 差本身就足以做出視覺層級，不需要額外再疊加顏色或其他手段）。
#
# 字級微調：拿掉粗體後純用字級撐視覺重量，加上系統字型的字重普遍比原
# 本綁定的 Noto Sans TC 更輕盈纖細，這裡把四級字級統一調大，確保拿掉
# 粗體後可讀性不會下降。改成 FONT_SIZE_* 具名常數（而不是直接把數字寫
# 在 get_font() 呼叫裡）是刻意的：使用者提到「保留變數彈性讓我能在本
# 地端測試時快速調整」，具名常數集中在這裡，之後要微調只要改這幾行數
# 字，不用在整份檔案裡到處找 get_font() 呼叫。
#
# 【這個環境沒辦法驗證的部分，如實揭露】這個沙箱沒辦法執行 pygame 渲
# 染，這幾個字級數字是「合理的起始值」，不是實測校準過的最終值——麻
# 煩使用者在本機用真正的系統中文字型跑起來後，依照畫面實際排版空間
# （尤其是商店卡片、HUD 數字這些空間比較緊的地方會不會因為字變大而
# 溢出/换行跑版）微調這幾個常數。
FONT_SIZE_XS = 13     # 原本 12
FONT_SIZE_SM = 15     # 原本 14
FONT_SIZE_MD = 18     # 原本 16（且拿掉了 bold=True）
FONT_SIZE_LG = 22     # 原本 20（且拿掉了 bold=True）
FONT_SIZE_TITLE = 28  # 原本 26（且拿掉了 bold=True）

FONT_XS = get_font(FONT_SIZE_XS)
FONT_SM = get_font(FONT_SIZE_SM)
FONT_MD = get_font(FONT_SIZE_MD)
FONT_LG = get_font(FONT_SIZE_LG)
FONT_TITLE = get_font(FONT_SIZE_TITLE)


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

        bg_col = C_PARCHMENT
        if self.is_locked:
            bg_col = (196, 186, 180)
        elif is_selected:
            bg_col = (231, 210, 165)   # 選中時偏金褐色，跟金色選取狀態呼應
        elif self.is_hovered:
            bg_col = (225, 214, 208)

        # 立體雕刻邊框：平常是「凸起」的木牌質感；鎖定時改成 pressed=True
        # 的「凹陷」效果，視覺上就像這塊木牌被壓下去、點不動了，跟遮罩
        # 文字一起加強「目前不能點」的訊號。
        draw_beveled_rect(surface, self.rect, bg_col, border_radius=10, pressed=self.is_locked)

        # 選中狀態額外疊一圈金色外框（焦點色沿用 C_GOLD，跟木頭色很搭），
        # 蓋在立體雕刻邊框之上，比木頭本身的高光/陰影更顯眼。
        if is_selected:
            pygame.draw.rect(surface, C_GOLD, self.rect, width=2, border_radius=10)

        # 選中時左側加一條實色色條，跟分類色呼應，一眼就能認出裝備中的項目。
        if is_selected:
            accent = pygame.Rect(self.rect.x, self.rect.y + 6, 4, self.rect.height - 12)
            pygame.draw.rect(surface, C_ORANGE, accent, border_radius=2)

        # 圖示放進一塊淡色圓角底框裡，而不是直接貼在卡片背景上，質感更豐富。
        icon_bg = pygame.Rect(self.rect.x + 8, self.rect.y + (self.rect.height - 50) // 2, 50, 50)
        icon_tint = tuple(min(255, c + 165) for c in tint)
        pygame.draw.rect(surface, icon_tint if not self.is_locked else (206, 198, 192), icon_bg, border_radius=10)
        icon_surf = loader.get(self.asset_key)
        if icon_surf:
            # 商店 UI 的圖示縮放邏輯要跟農田渲染完全獨立：農田那邊改成
            # 等比例縮放後（asset_loader.py 的 _scale_keep_aspect），部分
            # 作物圖片（胡蘿蔔、玉米...）已經不是正方形，可能比 icon_bg
            # 這個 50x50 的圖示框還要高。如果直接用 topleft blit 原圖，
            # 長條形的圖會往下溢出圖示框、蓋到下面的文字。
            # 這裡用「等比例縮小塞進框內 (Contain)」：寬高各自算一個縮放
            # 倍率，取較小的那個，確保縮放後的圖無論長寬都不會超出
            # icon_bg，再用 center 對齊（不是 midbottom，UI 列表不需要
            # 「站在格子上」的視覺語意，置中最自然）。
            orig_w, orig_h = icon_surf.get_size()
            if orig_w > 0 and orig_h > 0:
                scale_factor = min(icon_bg.width / orig_w, icon_bg.height / orig_h)
                new_w = max(1, int(orig_w * scale_factor))
                new_h = max(1, int(orig_h * scale_factor))
                ui_img = pygame.transform.scale(icon_surf, (new_w, new_h))
                if self.is_locked:
                    ui_img = ui_img.copy()
                    ui_img.set_alpha(110)
                img_rect = ui_img.get_rect()
                img_rect.center = icon_bg.center
                surface.blit(ui_img, img_rect)

        text_x = icon_bg.right + 12
        avail_w = self.rect.right - 8 - text_x
        lbl_col = C_TEXT_MUTED if self.is_locked else C_TEXT_MAIN
        lbl_y = self.rect.y + (self.rect.height // 2 - 22 if self.cost_text else self.rect.height // 2 - 10)
        surface.blit(FONT_MD.render(self.label, True, lbl_col), (text_x, lbl_y))

        # 鎖定的卡片不畫售價：下面的鎖定遮罩會在同一個位置改印解鎖條件
        # 文字（例如「🔒 需莊園等級 Lv.2」），兩段文字疊在同一個座標會
        # 透過半透明遮罩互相穿插變成看不懂的亂碼，售價本來就該讓位。
        if self.cost_text and not self.is_locked:
            cost_col = (230, 81, 0)
            if FONT_SM.render(self.cost_text, True, cost_col).get_width() <= avail_w:
                surface.blit(FONT_SM.render(self.cost_text, True, cost_col), (text_x, lbl_y + 22))
            else:
                # 側欄變窄後（例如景觀分頁的三段式文案「$300 | +220繁榮 |
                # +66G/天」）FONT_SM 一行塞不下，依 " | " 分隔符貪婪地
                # 換成最多兩行、改用較小的 FONT_XS，而不是任由文字被卡片
                # 邊界硬生生切斷。
                parts = self.cost_text.split(" | ")
                lines, cur = [], ""
                for part in parts:
                    trial = f"{cur} | {part}" if cur else part
                    if not cur or FONT_XS.render(trial, True, cost_col).get_width() <= avail_w:
                        cur = trial
                    else:
                        lines.append(cur)
                        cur = part
                if cur:
                    lines.append(cur)
                cy = lbl_y + 21
                for ln in lines[:2]:
                    surface.blit(FONT_XS.render(ln, True, cost_col), (text_x, cy))
                    cy += 15

        if self.is_locked:
            # 半透明深色遮罩蓋住整張卡片（圖示/文字都被壓暗），讓玩家一眼
            # 就能看出這張卡片「目前點不了」，而不用等點下去才有反應。
            # (Note: we use border_radius=10 to match our new aesthetics)
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(overlay, (20, 20, 20, 128), overlay.get_rect(), border_radius=10)
            surface.blit(overlay, self.rect.topleft)

            # 遮罩之上疊印紅色解鎖條件文字（蓋掉原本售價那一行），
            # 例如「🔒 需繁榮度 50」或「🔒 需 Lv.2」，說明「為什麼」點不了。
            # 原本的紅字 (255,130,130) 疊在半透明深色遮罩上對比度不夠，
            # 改用更亮的紅 C_LOCK_TEXT_RED，並且比照 FloatingText 的做法
            # 先往四個方向畫一層黑色描邊/陰影再畫主色文字，在木紋卡片跟
            # 深色遮罩的混色背景上都能維持清楚的可讀性。
            if self.lock_reason:
                lock_text = f"🔒 {self.lock_reason}"
                lock_pos = (text_x, lbl_y + 22)
                shadow_surf = FONT_SM.render(lock_text, True, (20, 20, 20))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    surface.blit(shadow_surf, (lock_pos[0] + dx, lock_pos[1] + dy))
                lock_surf = FONT_SM.render(lock_text, True, C_LOCK_TEXT_RED)
                # Using text_x and lbl_y+22 so it aligns with the new layout
                surface.blit(lock_surf, lock_pos)
            else:
                lock_pos = (self.rect.right - 22, self.rect.y + 8)
                shadow_surf = FONT_XS.render("🔒", True, (20, 20, 20))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    surface.blit(shadow_surf, (lock_pos[0] + dx, lock_pos[1] + dy))
                lock_surf = FONT_XS.render("🔒", True, C_LOCK_TEXT_RED)
                if lock_surf.get_width() > 0:
                    surface.blit(lock_surf, lock_pos)


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

        # 【Phase 6：外層遊戲狀態】主選單/遊玩狀態切換。'MENU' = 開始
        # 畫面（開機預設狀態，玩家會先看到這個畫面才能進農場）、
        # 'PLAYING' = 原本整套農場遊戲。run() 主迴圈依這個狀態決定要
        # 攔截事件走選單分支、還是照舊跑遊戲的 update/render。
        self.app_state = 'MENU'
        # 【系統升級：動態劇情背景圖切換】self.title_bg /
        # self._load_title_bg() 這條獨立於 AssetLoader 之外、自己用
        # os.path + pygame.image.load() 讀 assets/title_bg.png 的路徑
        # 已經整個移除——title_bg.png 現在跟 bg_crash.png/
        # bg_iron_flower.png 一起統一交給 AssetLoader 管理（見下面
        # self.loader = AssetLoader(...) 之後、_render_story()/
        # _render_main_menu() 都改成呼叫 self.loader.get("title_bg")/
        # get("bg_crash")），不再維護兩套各自獨立的背景圖載入邏輯。
        # 選單三顆按鈕的點擊判定 Rect，每幀由 _render_main_menu() 算好
        # 存起來，跟既有 self.btn_speed_down_rect 這種「渲染時順便算好
        # 點擊判定矩形」的既有模式一致，不是新發明的寫法。開機第一幀
        # 還沒畫過選單時是 None，點擊判斷要先檢查非 None 再
        # collidepoint，避免第一幀點擊噴例外。
        self.btn_new_game_rect = None
        self.btn_continue_rect = None
        self.btn_exit_rect = None
        # 【Phase 7】選單上的短暫提示訊息（目前唯一用途是「⚠ 沒有找到
        # 存檔」）。跟 self.floating_texts 不是同一套機制——floating_texts
        # 是畫在世界地圖座標上、只有 PLAYING 狀態的 _render() 才會畫，
        # MENU 狀態下根本不會被畫到；這裡另外用一組「文字 + 倒數計時」
        # 存在 App 上，由 run() 每幀遞減、_render_main_menu() 依剩餘時間
        # 決定要不要畫，是專屬選單畫面的獨立小型提示系統。
        self.menu_message = None
        self.menu_message_timer = 0.0
        # run() 原本用區域變數 running 控制主迴圈是否繼續，但「離開」
        # 按鈕的點擊處理是在 _handle_menu_mouse_down() 這個獨立方法裡，
        # 摸不到 run() 內部的區域變數，所以這裡改成 self.running 這個
        # 實例屬性，讓任何方法都能直接設 self.running = False 來要求
        # 結束主迴圈，run() 的 while 迴圈條件也改讀這個屬性。

        self.running = True

        self.game = GameState()
        self.sound = SoundManager(sfx_enabled=True)
        # 【系統升級：動態劇情背景圖切換】AssetLoader 的 screen_size
        # 參數用來把 title_bg/bg_crash/bg_iron_flower 這三張全螢幕背景
        # 圖（見 asset_loader.py load_all()）都強制縮放到剛好貼滿整個
        # 視窗——這裡把 (SCREEN_WIDTH, SCREEN_HEIGHT) 傳進去，
        # AssetLoader 本身不 import 這兩個常數（避免跟這個檔案循環
        # import），單純把呼叫端已經算好的螢幕尺寸原樣轉交進去。
        self.loader = AssetLoader(cell_size=CELL_SIZE, screen_size=(SCREEN_WIDTH, SCREEN_HEIGHT))

        # 【系統升級：打字機開場劇情 + 無縫 AI 任務引導】app_state 沿用
        # 既有的字串狀態機（'MENU'/'PLAYING'，見上面的說明），這次新增
        # 一個中間狀態：
        #   'STORY'    開場打字機劇情，點擊「新遊戲」後的第一站，播完
        #              直接進 'PLAYING'——跟先前 Phase 8 舊版不同，這次
        #              不再有會鎖死操作的 'TUTORIAL' 中間狀態，玩家一進
        #              PLAYING 就是完全自由的，教學改用不鎖操作的
        #              「飛船 AI 任務」橫幅（self.missions）在背景引導。
        #
        # 劇情台詞/打字機速度沿用實例屬性寫法（current_story_index/
        # story_char_index/typing_speed），之後如果玩家「新遊戲」重玩
        # 一次，_handle_menu_mouse_down() 會把 current_story_index/
        # story_char_index 重新歸零，這裡的初始值只是避免屬性不存在。
        #
        # 【系統修復與文本重構：綁定劇情背景圖與農場風文本全面替換】
        # story_lines 維持「{"text":..., "bg_key":...} 字典陣列」這個
        # 既有結構不變（上一個任務就已經是這個結構，不是這次才改的），
        # 這次真正變動的是兩件事：
        #   1. bg_key 對應的三張背景圖鍵名跟著世界觀重新命名，從
        #      title_bg/bg_crash/bg_iron_flower 改成
        #      title_bg/bg_abandoned/bg_premium_crop（見 asset_loader.py
        #      對應的載入清單），不再是「墜毀太空船」跟「富鐵花宿主
        #      星球」這種硬派外星求生場景。
        #   2. 台詞內容整段重寫：遊戲已經從「硬派外星求生」轉型成
        #      「溫馨奇幻農場」，原本「主引擎受損／迫降未知星球／工業
        #      金屬／防禦護盾／變異生物」這些科幻詞彙全部替換掉，改成
        #      「繼承一座荒廢已久的祖傳農莊、重新開墾、守護收成」的
        #      溫馨故事線，跟新的 bg_abandoned（荒廢農莊）/
        #      bg_premium_crop（發光的特級農產）背景圖意境呼應。
        self.story_lines = [
            {"text": "在遙遠的山谷深處，有一座被世人遺忘許久的農莊，靜靜等待著它的新主人。", "bg_key": "title_bg"},
            {"text": "荒煙蔓草間，古老的柵欄早已傾頹，土地也失去了往日的生機……", "bg_key": "bg_abandoned"},
            {"text": "但當你踏入這片土地時，卻在角落發現一株散發微光的『富鐵花』——傳說中的特級農產！", "bg_key": "bg_premium_crop"},
            {"text": "只不過，夜晚的森林裡，總有一些貪嘴的野生動物，會被作物的香氣悄悄吸引而來。", "bg_key": "bg_abandoned"},
            {"text": "你得重新豎起柵欄、佈置一些巧妙的機關，才能守護得來不易的每一份收成。", "bg_key": "bg_abandoned"},
            {"text": "只要用心耕耘，這片荒地終將重新綻放，成為遠近馳名的夢幻莊園。", "bg_key": "bg_premium_crop"},
            {"text": "『夜巡農場』的故事，就從今天，由你親手寫下第一頁。準備好了嗎？", "bg_key": "title_bg"},
        ]
        self.current_story_index = 0
        self.story_char_index = 0.0
        self.typing_speed = 30.0  # 每秒顯示字元數

        # 飛船 AI 任務引導：跟舊版 'TUTORIAL' 狀態最大的差異是「完全不
        # 鎖玩家操作」——PLAYING 狀態下 self.game.update() 照常正常執行
        # （時間繼續流動、作物照樣會成熟），任務只是在畫面上方疊一條
        # 橫幅提示，玩家隨時可以無視任務直接自由遊玩，事件比對照樣會在
        # 背景默默推進進度（見 _process_events()）。missions[5]（完成）
        # 是純提示訊息，沒有 target/type，達到之後橫幅固定停在這句，
        # 不會再繼續比對任何事件。
        # 【系統修復與文本重構】任務引導的發話者從「飛船AI」改成
        # 「莊園精靈」，措辭也一併從「資金/防禦單位/鐵礦/科技樹」這種
        # 硬派外星求生用語，換成溫馨奇幻農場該有的口吻；type/target 等
        # 判定邏輯完全不動，只換玩家看得到的文字。
        self.missions = [
            {"text": "莊園精靈：想讓農莊運作起來，需要一點資金喔。打開商店，種下任意一種基礎作物吧！", "type": "plant_crop", "exclude_iron": True, "target": 1},
            {"text": "莊園精靈：作物成熟需要一點時間，耐心等它長大後點擊採收，就能換得金幣囉。", "type": "harvest_crop", "exclude_iron": True, "target": 1},
            {"text": "莊園精靈：夜幕降臨後，附近的野生動物會伺機而動。快去商店部署一些防禦設施吧！", "type": "place_defense", "target": 1},
            {"text": "莊園精靈：防線穩固、資金也充裕了，來試著種下珍貴的『富鐵花』吧！", "type": "plant_crop", "iron_only": True, "target": 1},
            {"text": "莊園精靈：材料已經備齊，快建造伐木場或熔爐，讓農莊的手藝更上一層樓！", "type": "place_building_2x2", "target": 1},
            {"text": "莊園精靈：農莊已經穩定運作了。往後的故事，就交給你親手書寫，祝你順心如意！", "type": "complete", "target": 0},
        ]
        self.current_mission_idx = 0
        self.mission_progress = 0  # 目前這個任務已經達成幾次（跟 target 比對）

        self.show_intro = True
        self.show_pause_menu = False
        self.active_tab = "CROPS"
        self.selected_action = "PLANT_RADISH"

        # 每日訂單佈告欄面板開關；O 鍵或點擊頭部狀態列的「📋」按鈕切換。
        # 面板開啟時攔截所有點擊（跟暫停選單一樣），但刻意不暫停遊戲時間
        # ——訂單交付本來就該是「白天正常經營時隨手可以做的事」，不像
        # 暫停選單是真的要停下整個遊戲。
        self.show_order_board = False
        # 這兩個由 _render_order_board() 每幀算好存起來，供
        # _handle_mouse_down() 判斷點擊落在哪個「交付」按鈕/關閉按鈕上；
        # 跟既有的 self.tab_buttons/self.action_cards 是同一套「渲染時
        # 順便算好點擊判定矩形」的既有模式，不是新發明的寫法。
        self._order_deliver_rects = []
        self._order_board_close_rect = None
        
        self.floating_texts = []
        self.particles = []
        self.log_messages = ["🌾 歡迎來到夜巡農場！精緻像素莊園，中央為農田與防線，四周為景觀與寵物！"]
        self.hovered_grid = None
        self.mouse_pos = (0, 0)
        self.anim_time = 0.0

        # 拖曳連續種植/建造 (Drag-to-Build)：按住左鍵不放、滑鼠掃過去的
        # 每一格都會自動觸發跟點一下一樣的動作，玩家不用瘋狂連點。
        self.is_dragging_action = False  # 左鍵是否正按著（且起點是地圖，不是 UI 面板）
        self.last_action_grid = None     # 上一次成功觸發動作的網格座標，避免同一格重複觸發
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
            ("CROPS", "農田耕作 (11)", pygame.Rect(0, 0, 0, 0)),
            ("DECO", "莊園景觀 (20)", pygame.Rect(0, 0, 0, 0)),
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
                ("PLANT_CARROT", "紅蘿蔔", "$55 | 12s熟", "carrot_mature"),
                ("PLANT_PUMPKIN", "巨型金南瓜", "$80 | 15s熟", "pumpkin_mature"),
                ("PLANT_CORN", "香甜玉米", "$110 | 18s熟", "corn_mature"),
                ("PLANT_WHEAT", "小麥", "$140 | 20s熟", "sunflower_mature"),
                ("PLANT_BLUEBERRY", "藍莓", "$180 | 24s熟", "blueberry_mature"),
                ("PLANT_GRAPE", "皇家紫葡萄", "$220 | 26s熟", "grape_mature"),
                ("PLANT_STARLIGHT", "永恆星光果", "$300 | 30s熟", "starlight_mature"),
                # 系統大重構 Phase 7：富鐵花，取代原本 DECO 分頁裡的
                # PLACE_MINE（礦場）卡片——礦場整批移除，改成種在農田
                # 核心區的作物，所以卡片自然歸在 CROPS 分頁而不是 DECO。
                # 【系統修復】商店卡片圖示的 asset_key 從 "iron_flower_mature"
                # 改成 "iron_flower"——這次改用 1x4 Sprite Sheet 之後，
                # AssetLoader._load_1x4_spritesheet() 統一把切好的第一幀
                # 寫回 self.images["iron_flower"]（不再有 "_mature" 這個
                # key 了，成熟階段改由 get_anim_frames("iron_flower") 依
                # 成長比例挑幀，見渲染層的說明），卡片圖示要跟著改，不然
                # loader.get("iron_flower_mature") 會拿到 None，卡片會沒
                # 有圖示。
                # 【系統修復與文本重構】原本充滿工業感的「富鐵花」改名為
                # 「晨露高麗菜」——action_id/asset_key（"PLANT_IRON_
                # FLOWER"/"iron_flower"）跟 CropType.IRON_FLOWER 這個
                # enum 成員維持不變（只是內部識別字，玩家看不到，改了
                # 反而要動到存檔相容性/測試等一大串東西，超出這次純文本
                # 替換的範圍），output_key 也仍然是 metal_ore（供應熔爐
                # 改名後的磚造烤窯煉製）——這裡把它解讀成「這株奇特蔬菜
                # 吸收了地脈礦砂，篩出來的礦石結晶」，而不是硬派科幻的
                # 「工業金屬」，機制不變、只是說法換了一套更貼合溫馨奇幻
                # 農場世界觀的解釋。
                # 【使用者回饋：熔爐/伐木場/富鐵花 保留】名稱改回原本的
                # 「富鐵花」，描述文字（產1礦石結晶）維持上一版的修改。
                ("PLANT_IRON_FLOWER", "富鐵花", "$150 | 15s熟 | 產1礦石結晶", "iron_flower"),
            ],
            "DECO": [
                ("PLACE_PATH", "石板小徑", "$20 | +10繁榮 | +3G/天", "stone_path"),
                ("PLACE_FLOWER", "鮮花盆栽", "$35 | +20繁榮 | +6G/天", "flower_bed"),
                ("PLACE_BENCH", "休閒木椅", "$45 | +30繁榮 | +9G/天", "garden_bench"),
                ("PLACE_PINE", "針葉松樹", "$50 | +35繁榮 | +10G/天", "pine_tree"),
                ("PLACE_APPLE_TREE", "紅葉楓樹", "$60 | +40繁榮 | +12G/天", "apple_tree"),
                ("PLACE_LANTERN", "夜巡路燈", "$75 | +50繁榮 | +15G/天", "soul_lantern"),
                ("PLACE_SAKURA_TREE", "莊園大樹", "$85 | +55繁榮 | +16G/天", "sakura_tree"),
                ("PLACE_BIRD_BATH", "森林野菇", "$95 | +65繁榮 | +19G/天", "bird_bath"),
                ("PLACE_STATUE", "神秘寶箱", "$110 | +75繁榮 | +22G/天", "ancient_statue"),
                ("PLACE_PET_HOUSE", "木材柴堆", "$130 | +90繁榮 | +27G/天", "pet_house"),
                ("PLACE_FOUNTAIN", "野餐竹籃", "$160 | +110繁榮 | +33G/天", "fountain"),
                ("PLACE_SUNDIAL", "向日葵叢", "$220 | +160繁榮 | +48G/天", "sundial_tower"),
                ("PLACE_WINDMILL", "莊園木屋", "$300 | +220繁榮 | +66G/天", "windmill"),
                # 加工機台 (Phase 2)：跟其餘景觀裝飾一樣放在 DECO 分頁、
                # 建在「四周莊園景觀區」——沒有另外開新分頁，是因為商店
                # 的 2x2 分頁格版面 (_layout_shop_tabs) 是照剛好 4 個分頁
                # 寫死的，硬塞第 5 個分頁要重新設計整塊版面配置，風險/
                # 工程量都遠超過這次「加入生產線機台」的需求範圍；機台
                # 本來就跟裝飾一樣蓋在同一個區域，歸在同一個分頁在邏輯
                # 上也說得通。
                # 視覺升級（熔爐 Sprite Sheet 動畫）階段：使用者確認熔爐
                # 貼圖+動畫做好之後，要求整批刪除「烤箱 (OVEN)」跟「炭窯
                # (KILN)」這兩張卡片，含它們對應的 BuildingType/建造動作
                # 處理分支（見上方 _handle_mouse_up 已同步移除）。熔爐的
                # 配方也同步從「metal_ore + charcoal」改成單純
                # 「metal_ore x2」，不再依賴已刪除的炭窯產出的 charcoal。
                # 【系統修復與文本重構】「熔爐」改名為「磚造烤窯」——
                # action_id/asset_key/BuildingType.FURNACE 這個 enum
                # 成員都不動，只換玩家看到的名稱/說明文字。使用者建議的
                # 說明文字是「用溫暖的柴火烘焙特級農產品，提升作物附加
                # 價值」，但這棟建築實際的配方是 metal_ore x2 ->
                # metal_ingot（煉礦石成鐵錠，供應風車磨坊/灑水器等機台
                # 的建造成本），並不是消耗作物、也不是幫作物加值——如果
                # 照字面套用會變成文字騙人、跟實際點下去的效果對不上。
                # 這裡改用一句貼合實際配方、但用詞從「熔爐煉鋼」換成更
                # 溫馨的「柴火烤窯煉礦」講法，維持機制與文本一致。
                # 【使用者回饋：熔爐/伐木場/富鐵花 保留】名稱改回原本的
                # 「熔爐」，描述文字維持上一版的修改。
                ("PLACE_FURNACE", "熔爐", "$200+18工藝 | 柴火烘烤礦石→精鐵錠", "furnace"),
                # Phase 4：自動化農業科技，一樣沿用同一個 DECO 分頁、同一
                # 個「四周莊園景觀區」放置規則，理由跟 Phase 2 加熔爐時
                # 一樣——沒有另外開新分頁。花費是 metal_ingot（背包
                # 物品）而不是金幣，卡片說明文字用「2錠」/「5錠+100科技」
                # 表示，跟其餘卡片「$金額」的呈現風格有意識地做出區分，
                # 讓玩家一眼看出這兩張卡「要花的不是錢」。
                # 【系統更新：自動灑水器 2x2 建築邏輯】卡片說明文字同步
                # 更新：不再是「蓋下去就永久生效」的持續雙倍生長，改成
                # 「需要玩家開啟，開啟後每隔一段時間對周圍作物澆水一次」
                # ——跟 game_config.py BUILDING_DATA[SPRINKLER] 的
                # water_interval=8.0 秒對應。
                # 【系統修復與文本重構】說明文字改成使用者要求的「木製
                # 水車齒輪自動運轉、提供潔淨溪水」的意象，取代原本偏機械
                # 感的「自動澆水」講法；名稱「自動灑水器」維持不變（使用
                # 者這次只要求改描述，沒有要求改名）。
                ("PLACE_SPRINKLER", "自動灑水器", "2錠 | 水車齒輪自動運轉，每8秒為周圍3x3灌溉溪水", "sprinkler"),
                ("PLACE_AUTO_HARVESTER", "自動採收機", "5錠+100工藝 | 自動採收3x3", "auto_harvester"),
                # Phase 4.5：打通上游生產線的基礎設施，一樣是「純資本」
                # ——只花金幣，不消耗任何背包物品，所以說明文字維持跟
                # 一般景觀裝飾一致的「$金額」格式，不用像灑水器/採收機
                # 那樣特別標注「錠」。
                # 系統大重構 Phase 7：PLACE_MINE（礦場）卡片整批移除，
                # 由新增的 PLANT_IRON_FLOWER 作物卡（CROPS 分頁）取代同
                # 樣的 metal_ore 產出角色。伐木場同一階段改成 2x2 佔地
                # （BUILDING_DATA[LUMBERYARD]["size"]），卡片說明文字/
                # 售價/產出不變，只有實際佔地格數變大。
                # 【系統修復與文本重構】「伐木場」改名為「風車磨坊」，
                # action_id/asset_key/BuildingType.LUMBERYARD 不動。
                # 使用者建議的說明是「利用風力磨製麵粉，產出農莊所需的
                # 基礎工藝點數」，但這棟建築實際的 output_key 是
                # "wood"（每 10 秒產 1 木頭），不是工藝點數——工藝點數
                # 目前在遊戲裡完全沒有任何被動產出來源（只透過訂單交付
                # 拿到），如果照字面改成「產出工藝點數」會變成文字騙人。
                # 這裡維持「風車磨坊」這個溫馨改名，但說明文字照實際
                # output_key 寫成「風力研磨，產出農莊建設所需的木料」，
                # 機制跟文本才對得上。
                # 【使用者回饋：熔爐/伐木場/富鐵花 保留】名稱改回原本的
                # 「伐木場」——描述文字原本配合上一版改名「風車磨坊」寫
                # 成「風力研磨」，跟「伐木場」搭在一起語意不通順，這裡
                # 一併調整回貼合伐木場本身、但保留溫馨語氣的說法。
                ("PLACE_LUMBERYARD", "伐木場", "$50 | 每10s產1木料", "lumberyard"),
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
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.anim_time += dt

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue

                # 【Phase 6：外層遊戲狀態】主選單狀態下，把事件處理整個
                # 攔截到獨立的分支——只認滑鼠左鍵點擊（判斷點在哪顆按鈕）
                # 跟 F11 全螢幕切換，其餘原本 PLAYING 狀態才有意義的滑鼠
                # 移動/放開/滾輪、鍵盤快捷鍵（P 暫停、O 訂單板、R 重開…）
                # 全部不處理，避免選單畫面被還沒開始的那一局遊戲的殘留
                # 狀態（例如 self.game.game_over）誤觸發。
                if self.app_state == 'MENU':
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        self._handle_menu_mouse_down(event)
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    continue

                # 【系統升級：打字機開場劇情】開場劇情狀態下，同樣把事件
                # 處理整個攔截到獨立分支，理由跟上面 MENU 分支一致——這
                # 個狀態下畫面上只有劇情文字、沒有任何農場地圖/商店可以
                # 互動，讓滑鼠/鍵盤事件落到下面 PLAYING 專用的那一大串
                # 處理（點格子種田、P 暫停、O 訂單板…）完全沒有意義，而
                # 且 self.game 這時候雖然已經建立好，但玩家根本還沒看到
                # 地圖，任何游戲內互動都不該在這個階段被觸發。
                # 只認滑鼠左鍵點擊與空白鍵：兩者效果相同——文字還沒打完
                # 就直接顯示全句；已經顯示全句就換下一句（播完最後一句
                # 直接切到 'PLAYING'，不再像舊版那樣經過會鎖死操作的
                # 'TUTORIAL' 中間狀態——這次改用不鎖操作的飛船 AI 任務
                # 橫幅取代）。F11 全螢幕維持任何狀態都能切換。
                if self.app_state == 'STORY':
                    if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or \
                       (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                        self._advance_story()
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._handle_mouse_down(event)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._handle_mouse_up(event)
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_mouse_move(event)
                elif event.type == pygame.MOUSEWHEEL:
                    self._handle_mouse_wheel(event)
                elif event.type == pygame.KEYDOWN:
                    # 【系統升級：無縫 AI 任務引導】這次不再有會鎖死操作
                    # 的 'TUTORIAL' 中間狀態——STORY 播完直接進 'PLAYING'，
                    # 玩家從頭到尾操作完全自由，任務進度只是在背景默默
                    # 比對事件（見 _process_events()）。下面這串
                    # self.app_state == 'PLAYING' 限制沿用自舊版：STORY
                    # 已經在上面整段攔截掉了，這裡的條件單純是「STORY 播
                    # 放期間這些快捷鍵不該生效」的防呆，不影響 PLAYING
                    # 狀態下的任何操作。
                    if event.key == pygame.K_RETURN and self.show_intro:
                        self.show_intro = False
                    elif event.key == pygame.K_F11:
                        self._toggle_fullscreen()
                    elif event.key == pygame.K_r and self.game.game_over and self.app_state == 'PLAYING':
                        self.game = GameState()
                        self.log_messages.clear()
                        self.log_messages.append("🌾 遊戲已重新開始！")
                    elif event.key == pygame.K_SPACE and self.app_state == 'PLAYING':
                        self.log_messages.append("💡 提示：請點選下方工具列【強光手電筒】，用滑鼠直接點擊敵人發射強光照暈！")
                    elif event.key == pygame.K_o and self.app_state == 'PLAYING':
                        # 暫停選單/開場教學開著的時候不能切換訂單佈告欄，
                        # 避免兩個彈窗疊在一起搶點擊；遊戲結束畫面同理。
                        if not self.show_pause_menu and not self.show_intro and not self.game.game_over:
                            self.show_order_board = not self.show_order_board
                            self.sound.play("ui_click")
                    elif event.key == pygame.K_p and self.app_state == 'PLAYING':
                        if self.time_scale > 0:
                            self.time_scale_before_pause = self.time_scale
                            self.time_scale = 0.0
                            self.log_messages.append("⏸ 已暫停")
                        else:
                            # 記住暫停前的速度（可能是 1.5 這種 0.1 級距值，
                            # 不是只能回到 1.0），恢復時原樣還原。
                            self.time_scale = self.time_scale_before_pause
                            self.log_messages.append(f"▶ 恢復 {self.time_scale:.1f}x")
                    elif event.key == pygame.K_LEFTBRACKET and self.app_state == 'PLAYING':
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
                    elif event.key == pygame.K_RIGHTBRACKET and self.app_state == 'PLAYING':
                        new_scale = round(self.time_scale + self.TIME_SCALE_STEP, 1)
                        self.time_scale = max(self.TIME_SCALE_MIN, min(self.TIME_SCALE_MAX, new_scale))
                        if self.time_scale > 0:
                            self.time_scale_before_pause = self.time_scale

            # 【Phase 6：外層遊戲狀態】只有進入 PLAYING 狀態之後，才跑
            # 原本整套農場遊戲的 update（時間流逝、作物生長、敵人 AI、
            # 建築生產…）。MENU 狀態下這些都不執行，玩家還沒開始玩，
            # 農場世界應該完全靜止，不會有任何背景模擬在跑。
            if self.app_state == 'PLAYING':
                if not self.show_intro and not self.show_pause_menu:
                    self.game.update(dt * self.time_scale)

                if self.flash_vfx_timer > 0 and not self.show_pause_menu:
                    self.flash_vfx_timer = max(0.0, self.flash_vfx_timer - dt)

                self._process_events()
                self._update_card_states()

                if not self.show_pause_menu:
                    self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]
                    self.particles = [p for p in self.particles if p.update(dt)]
            elif self.app_state == 'STORY':
                # 【系統升級：打字機開場劇情】每幀累加「已顯示字元數」，
                # 累加到超過目前這一句的全長就自動停在全長（不會一直往
                # 上加到超出字串長度，下面 _render_story() 用
                # int(self.story_char_index) 去切字串，多出來的小數部分
                # 不影響顯示，只是還沒被下一次累加吃到而已，停在原地等
                # 玩家按空白鍵/點擊進到下一句）。self.game 這個階段完全
                # 不會被 update()，農場世界還沒開始跑。
                if self.current_story_index < len(self.story_lines):
                    # 【系統升級：動態劇情背景圖切換】story_lines 現在是
                    # {"text":..., "bg_key":...} 字典陣列，這裡跟下面
                    # _advance_story()/_render_story() 三處都要改成讀
                    # ["text"] 才能拿到真正的字串長度，不是整個 dict。
                    current_text = self.story_lines[self.current_story_index]["text"]
                    if self.story_char_index < len(current_text):
                        self.story_char_index = min(
                            len(current_text), self.story_char_index + self.typing_speed * dt)
            elif self.menu_message_timer > 0:
                # 【Phase 7】選單提示訊息（例如「⚠ 沒有找到存檔」）的倒數，
                # 只在 MENU 狀態才需要跑，PLAYING 狀態用不到這個計時器。
                self.menu_message_timer = max(0.0, self.menu_message_timer - dt)

            # 渲染依 app_state 分流：MENU 只畫選單畫面；STORY 只畫打字機
            # 劇情畫面（完全不畫農場地圖，這個階段玩家還沒進農場）；
            # PLAYING 維持原本只畫 _render()——飛船 AI 任務橫幅
            # (_render_mission_ui()) 這次不是疊在渲染分流這一層，而是
            # 整合進 _render() 內部、緊接在頭部資源列橫幅之後畫（見
            # _render() 裡的呼叫），因為任務橫幅只在 PLAYING 才有意義，
            # 而 _render() 本來就只有 PLAYING 這個分流會呼叫到。
            if self.app_state == 'MENU':
                self._render_main_menu()
            elif self.app_state == 'STORY':
                self._render_story()
            else:
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

        # 拖曳連續種植/建造 (Drag-to-Build)：左鍵按住不放的期間，滑鼠
        # 移動到新的一格就重播一次跟點擊一樣的判定，不用瘋狂連點。
        # - self.hovered_grid 為 None 代表游標已經滑出地圖範圍（例如滑到
        #   右側商店面板），天然滿足「拖曳動作只在世界地圖範圍內生效，
        #   不要拖到 UI 按鈕上還誤觸發」的要求，不用另外判斷面板範圍。
        # - 用 != self.last_action_grid 防呆，同一格不會因為滑鼠在格子
        #   內小幅晃動就重複觸發。
        # - 暫停選單/開場彈窗/遊戲結束畫面開著時不觸發，避免拖曳的殘留
        #   狀態在跳出這些模態視窗時還偷偷對地圖做事。
        if (
            self.is_dragging_action
            and self.hovered_grid is not None
            and self.hovered_grid != self.last_action_grid
            and not self.show_pause_menu
            and not self.show_intro
            and not self.game.game_over
        ):
            self.last_action_grid = self.hovered_grid
            self._perform_grid_interaction(mx, my, is_drag=True)

    # 這幾個放置動作各自要求的地圖分區（跟 game_state.py 的
    # place_decoration/place_defense/plant_crop 判斷條件一致，只用來畫
    # 「這格能不能放」的視覺提示，不是權威判定——實際成功/失敗還是要
    # 靠點擊後呼叫對應的 game.xxx() 函式，那邊的失敗原因字串已經在
    # _apply_grid_action() 裡轉成紅色 FloatingText 顯示了，這裡不重複。
    # UI 視覺優化（2x2 建造預覽修正）階段：這份「商店卡片 action_id ->
    # BuildingType」對照表原本只寫死在 _update_card_states() 內部（本地
    # 變數 _card_building_type），這次建造預覽框也需要同一份對照關係
    # （從 selected_action 反查建築的 size，決定預覽框要畫多大），與其
    # 複製一份幾乎一樣的字典、日後容易兩邊改一邊漏改，改成拉到 class
    # 層級成為共用常數，_update_card_states() 跟預覽框繪製都讀這裡。
    _CARD_BUILDING_TYPES = {
        "PLACE_FURNACE": BuildingType.FURNACE,
        "PLACE_SPRINKLER": BuildingType.SPRINKLER,
        "PLACE_AUTO_HARVESTER": BuildingType.AUTO_HARVESTER,
        "PLACE_LUMBERYARD": BuildingType.LUMBERYARD,
    }

    _DEFENSE_ACTION_IDS = {"PLACE_FENCE", "PLACE_TRAP", "PLACE_SCARECROW", "PLACE_BEEHIVE"}
    # 各防禦設施的警戒/攻擊範圍（格數），只有真的有「範圍」概念的設施才會
    # 在放置預覽時畫光圈；捕獸夾/木柵沒有範圍屬性，維持原樣不畫圈。
    _DEFENSE_ACTION_RANGE = {
        "PLACE_SCARECROW": DEFENSE_DATA.get(DefenseType.SCARECROW, {}).get("scare_radius"),
        "PLACE_BEEHIVE": DEFENSE_DATA.get(DefenseType.BEEHIVE, {}).get("attack_range"),
    }

    def _selected_building_footprint(self) -> Tuple[int, int]:
        """目前選中的工具如果是「蓋建築」的動作，回傳該建築的佔地格數
        (size_w, size_h)（讀 BUILDING_DATA 的 "size"，沒有這個欄位的
        建築預設 (1, 1)）；不是建築動作（種作物/景觀/防禦/工具）一律
        回傳 (1, 1)。UI 視覺優化階段新增，建造預覽框跟 footprint 合法性
        判定 (_grid_preview_is_invalid) 共用同一份查詢邏輯，避免兩處各
        寫一次、日後容易兜不起來。"""
        building_type = self._CARD_BUILDING_TYPES.get(self.selected_action)
        if building_type is None:
            return (1, 1)
        return BUILDING_DATA[building_type].get("size", (1, 1))

    def _grid_preview_is_invalid(self, gx: int, gy: int) -> bool:
        """判斷目前選中的工具，放在 (gx, gy) 這格『大致上』會不會失敗，
        純粹用來畫格子高光的顏色（白色=可以／紅色=不行），不影響任何
        實際遊戲邏輯。成熟作物一律可以直接採收，所以永遠視為有效。

        UI 視覺優化（2x2 建造預覽修正）階段：選中的是 FURNACE/LUMBERYARD
        這種 2x2 建築時，只檢查 (gx, gy) 這一格「大致上」合不合法已經
        不夠準——實際 place_building() 是四格（(gx,gy)/(gx+1,gy)/
        (gx,gy+1)/(gx+1,gy+1)）全部合法才會成功，只看錨點那一格會出現
        「預覽框顯示白色（可以蓋），實際點下去卻因為右邊或下面那格被
        佔用而建造失敗」的誤導。這裡改成用 _selected_building_footprint()
        展開完整 footprint，任何一格不合法就整體判定紅色；非建築動作
        (size 恆為 (1, 1)) 的行為跟修改前完全相同。"""
        size_w, size_h = self._selected_building_footprint()
        footprint = [(gx + dx, gy + dy) for dy in range(size_h) for dx in range(size_w)]

        for (fx, fy) in footprint:
            tile = self.game.get_tile(fx, fy)
            if not tile:
                return True
            if len(footprint) == 1 and tile.crop and tile.crop.is_mature:
                # 成熟作物一律可以直接採收——這個特例只在 1x1（非建築）
                # 動作下有意義，2x2 建築本來就不可能蓋在農田核心區的
                # 作物格上（zone 檢查一定會先擋下來），不用重複判斷。
                return False

            act = self.selected_action
            if act.startswith("PLANT_") or act in self._DEFENSE_ACTION_IDS:
                if tile.zone != ZoneType.FARM_ZONE or not tile.is_empty:
                    return True
            elif act.startswith("PLACE_"):
                # 其餘 PLACE_* 都是景觀裝飾/加工機台，只能放在莊園景觀區。
                if tile.zone != ZoneType.DECORATION_ZONE or not tile.is_empty:
                    return True
            elif act == "WATER_CROP":
                if not (tile.crop and not tile.crop.is_mature):
                    return True
            elif act == "SHOVEL":
                if tile.is_empty:
                    return True
            elif act == "HARVEST":
                if not (tile.crop and tile.crop.is_mature):
                    return True

        return False

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

    def _handle_menu_mouse_down(self, event):
        """【Phase 6：外層遊戲狀態】主選單三顆按鈕的點擊判定。三個 Rect
        由 _render_main_menu() 每幀算好存起來，這裡只負責讀取判斷，跟
        _handle_mouse_down() 裡其餘按鈕的既有寫法一致。第一幀選單還沒
        畫過時三個 Rect 都是 None，先檢查非 None 再 collidepoint，避免
        開機瞬間點擊噴例外。"""
        mx, my = event.pos

        if self.btn_new_game_rect and self.btn_new_game_rect.collidepoint(mx, my):
            # 新遊戲：明確重置 GameState，清空原本進度（就算玩家先前已經
            # 玩過一局又回到選單，這裡也會拿到全新的一局，不會延續舊
            # 進度），一併清掉浮動文字/特效/訊息記錄，避免上一局的殘留
            # 畫面元素飄進新的一局。
            #
            # 【Phase 7】需求文字要求「刪除舊的 savegame.json（或覆蓋
            # 它）」，這裡選擇「覆蓋」而不是刪除檔案：立刻對這個全新的
            # GameState 呼叫一次 save_game()，讓 savegame.json 內容變成
            # 這局剛開始、day=1、gold=初始值的乾淨狀態。選覆蓋不選刪除
            # 的理由是：覆蓋永遠會留下一個「格式正確、可以被 load_game()
            # 成功讀回」的檔案；如果改成刪除檔案，玩家在新遊戲之後、還
            # 沒撐過第一次破曉自動存檔之前如果不小心點到選單，
            # 「繼續遊戲」會因為檔案不存在而被判定成「沒有存檔」，即使
            # 玩家明明才剛新遊戲、遊戲根本沒有真的重置到「從未玩過」的
            # 狀態——覆蓋寫入可以避免這個時間窗內的行為不一致。
            self.game = GameState()
            self.game.save_game()
            self.floating_texts.clear()
            self.particles.clear()
            self.log_messages = ["🌾 歡迎來到夜巡農場！精緻像素莊園，中央為農田與防線，四周為景觀與寵物！"]
            # 【系統升級】新遊戲不再直接切到 'PLAYING'，改先進 'STORY'
            # （開場打字機劇情），播完直接進 'PLAYING'——飛船 AI 任務
            # 引導在 PLAYING 狀態下以不鎖操作的橫幅背景運作，不需要
            # 額外的中間狀態。
            #
            # show_intro 這次改成 False（原本是 True，會在 PLAYING 狀態
            # 第一幀跳出 _render_story_modal() 那個靜態的「新手速成指南」
            # 三步驟卡片）：新的 STORY 開場劇情 + 飛船 AI 任務橫幅流程
            # 本來就是要取代這個舊的一次性靜態說明卡，兩套引導系統疊在
            # 一起會變成玩家一進 PLAYING 就先被另一個說明彈窗攔下來，
            # 體驗上是重複且突兀的，所以這裡不再設成 True。
            #
            # current_story_index/story_char_index 歸零、missions 進度
            # 歸零：如果玩家先前玩過一局又按「新遊戲」，這幾個追蹤變數
            # 不會殘留上一局播到一半/推進到一半的進度。
            self.current_story_index = 0
            self.story_char_index = 0.0
            self.current_mission_idx = 0
            self.mission_progress = 0
            self.show_intro = False
            self.show_pause_menu = False
            self.show_order_board = False
            self.app_state = 'STORY'
            self.sound.play("build")
        elif self.btn_continue_rect and self.btn_continue_rect.collidepoint(mx, my):
            # 【Phase 7】繼續遊戲：檢查 savegame.json 存不存在。存在就用
            # 一個全新的 GameState 呼叫 load_game() 讀回存檔內容（不是在
            # 原本 __init__ 就建立、可能已經被把玩過的那個 self.game 上
            # 疊讀檔結果——先歸零再讀，才不會有舊 self.game 殘留的
            # 屬性/物件混進讀檔後的狀態）；不存在就播放 error 音效、在
            # 選單畫面顯示 2 秒「⚠ 沒有找到存檔」提示，並且直接 return，
            # 不執行下面的 app_state 切換，維持在 MENU。
            #
            # show_intro 這裡明確設成 False（不是像新遊戲那樣設 True）：
            # 讀檔代表玩家是回來繼續一局已經在進行中的遊戲，不應該再看
            # 到新手教學彈窗——這是原本 Phase 6 版本「繼續遊戲不動
            # show_intro」遺留的小瑕疵（当時 show_intro 從開機 __init__
            # 就是 True，從未被清掉，等於舊版「繼續遊戲」其實也會顯示
            # 教學彈窗），這次一併修正。
            if GameState.has_save():
                self.game = GameState()
                self.game.load_game()
                self.floating_texts.clear()
                self.particles.clear()
                self.log_messages = ["🌾 歡迎回來！已讀取上次的莊園進度。"]
                self.show_intro = False
                self.show_pause_menu = False
                self.show_order_board = False
                self.app_state = 'PLAYING'
                self.sound.play("build")
            else:
                self.menu_message = "⚠ 沒有找到存檔"
                self.menu_message_timer = 2.0
                self.sound.play("error")
        elif self.btn_exit_rect and self.btn_exit_rect.collidepoint(mx, my):
            self.running = False

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
            modal_w, modal_h = 420, 366
            mx0 = (SCREEN_WIDTH - modal_w) // 2
            my0 = (SCREEN_HEIGHT - modal_h) // 2
            btn_resume = pygame.Rect(mx0 + (modal_w - 220) // 2, my0 + 150, 220, 52)
            btn_restart2 = pygame.Rect(mx0 + (modal_w - 220) // 2, my0 + 216, 220, 52)
            btn_mute = pygame.Rect(mx0 + (modal_w - 220) // 2, my0 + 282, 220, 52)
            if btn_resume.collidepoint(mx, my):
                self.show_pause_menu = False
                self.sound.play("build")
            elif btn_restart2.collidepoint(mx, my):
                self.game = GameState()
                self.log_messages.clear()
                self.log_messages.append("🌾 遊戲已重新開始！")
                self.show_pause_menu = False
                self.sound.play("harvest")
            elif btn_mute.collidepoint(mx, my):
                # 只切換靜音狀態，選單留著開（玩家可能還想調別的），
                # 不像繼續/重新開始那樣直接關閉選單。播 ui_click 而不是
                # 依賴音樂本身當回饋 -- 剛靜音那瞬間音樂沒了，玩家反而
                # 需要一個音效當「有生效」的確認。
                self.sound.toggle_music_mute()
                self.sound.play("ui_click")
            return

        # 訂單佈告欄開啟中：面板內的「交付」/「✕」按鈕優先判定，點擊
        # 面板外的半透明遮罩、或再點一次「📋」按鈕，都當作關閉面板。
        # 跟暫停選單一樣攔下這一輪剩下所有的點擊，不會讓點擊穿透到
        # 底下的地圖/商店。
        if self.show_order_board:
            order_btn_rect = self._order_board_button_rect()
            if self._order_board_close_rect and self._order_board_close_rect.collidepoint(mx, my):
                self.show_order_board = False
                self.sound.play("ui_click")
                return
            if order_btn_rect.collidepoint(mx, my):
                self.show_order_board = False
                self.sound.play("ui_click")
                return
            for order_id, deliver_rect in self._order_deliver_rects:
                if deliver_rect.collidepoint(mx, my):
                    # 成功時特意不在這裡直接播音效/跳浮動文字：跟既有的
                    # 「採收成功」走同一套模式——GameState.fulfill_order()
                    # 成功會 emit EventType.ORDER_FULFILLED，交給
                    # _process_events() 的事件迴圈統一處理音效/浮動文字/
                    # 粒子特效（讀 ev.data 裡的 reward_gold/reward_tech），
                    # 這裡只負責呼叫。失敗則不會有事件（GameState 只在
                    # 成功時 emit），所以失敗的音效/紅字回饋維持在點擊
                    # 現場直接處理，這跟其餘商店卡片/採收失敗的既有寫法
                    # 完全一致。
                    success, msg = self.game.fulfill_order(order_id)
                    if not success:
                        self.sound.play("error")
                        self.floating_texts.append(FloatingText(f"❌ {msg}", mx - 70, my - 20, C_RED, duration=1.6))
                        self.log_messages.append(f"❌ {msg}")
                    return
            if not self._order_board_rect().collidepoint(mx, my):
                self.show_order_board = False
                self.sound.play("ui_click")
            return

        # 右上角選單按鈕（☰）：點擊暫停遊戲並開啟選單
        menu_btn_rect = pygame.Rect(SCREEN_WIDTH - 56, 15, 40, 40)
        if menu_btn_rect.collidepoint(mx, my):
            self.show_pause_menu = True
            self.sound.play("build")
            return

        # 「📋 訂單」按鈕：開啟訂單佈告欄。位置緊貼在選單按鈕左側（見
        # _order_board_button_rect() 的座標計算與版面配置說明）。
        if self._order_board_button_rect().collidepoint(mx, my):
            self.show_order_board = True
            self.sound.play("ui_click")
            return

        # 分頁標籤（點擊切換分頁時捲動歸零，避免新分頁一開就是捲到一半的畫面）
        for tab_id, label, rect in self.tab_buttons:
            if rect.collidepoint(mx, my):
                self.active_tab = tab_id
                self.sound.play("ui_click")
                return

        # 卡片點擊
        for card in self.action_cards:
            if card.tab_id == self.active_tab and card.rect.collidepoint(mx, my):
                if card.action_id == "BUY_DOG":
                    success, msg = self.game.buy_guard_dog()
                    if not success:
                        self.log_messages.append(f"❌ {msg}")
                        self.floating_texts.append(FloatingText(f"❌ {msg}", mx - 45, my - 12, C_RED))
                        self.sound.play("error")
                elif card.action_id == "BUY_CAT":
                    success, msg = self.game.buy_farm_cat()
                    if not success:
                        self.log_messages.append(f"❌ {msg}")
                        self.floating_texts.append(FloatingText(f"❌ {msg}", mx - 45, my - 12, C_RED))
                        self.sound.play("error")
                else:
                    if not card.is_locked:
                        self.selected_action = card.action_id
                        self.sound.play("ui_click")
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

        # 走到這裡代表這一下點擊/拖曳落在地圖上，不是任何 UI 面板/按鈕
        # ——上面一長串 UI 元素的 collidepoint 檢查全部沒命中才會到這，
        # 天然滿足「拖曳動作只在世界地圖範圍內生效」的要求，不用另外
        # 判斷一次。這裡開始正式進入拖曳連續種植/建造 (Drag-to-Build)：
        # 按下當下把這一格記成拖曳起點，之後滑鼠移動只要進入新的一格
        # 就會重播一次同樣的判定（見 _handle_mouse_move）。
        self.is_dragging_action = True
        self.last_action_grid = self.hovered_grid

        self._perform_grid_interaction(mx, my, is_drag=False)

    def _perform_grid_interaction(self, mx: int, my: int, is_drag: bool):
        """左鍵在地圖上按下、或拖曳滑過新的一格時，實際要執行的判定
        (跟原本 _handle_mouse_down 尾端完全同一份邏輯，抽出來給拖曳
        重複呼叫，兩邊行為保證一致)。

        is_drag=True 時只重播「會採收/種植/建造/剷除/澆水」這幾種可以
        連續動作的分支（優先權 1 跟 3），跳過手電筒照暈 (優先權 0) 跟
        指揮哨 (優先權 2) 這兩個瞄準型的主動技能——這兩個不是「連續種植
        或建造」的範疇，如果拖曳掃過去的每一格都照暈/吹哨，手感會很奇怪
        （而且手電筒還有冷卻時間，拖曳只會洗一堆冷卻中的失敗訊息）。
        普通點擊 (is_drag=False) 完全不受影響，跟修改前一模一樣。
        """
        # 地圖座標換算
        world_gx = (mx - GRID_X) / CELL_SIZE
        world_gy = (my - GRID_Y) / CELL_SIZE

        # 拖曳時手電筒/指揮哨這兩個瞄準型技能整個不參與（見這個函式的
        # docstring）：不能讓拖曳掃過的格子落到下面第 3 優先權的
        # _apply_grid_action()，那邊的 elif 鏈沒有 FLASHLIGHT/WHISTLE
        # 對應分支，會掉進「未知操作」分支狂噴失敗浮動文字，這裡直接
        # 提前 return 當作這一次拖曳移動沒有動作，安靜跳過。
        if is_drag and self.selected_action in ("FLASHLIGHT", "WHISTLE"):
            return

        # 0. 最優先權（僅限夜晚 + 已裝備手電筒）：優先判定敵人。
        # 夜晚會自動裝備手電筒，這裡要排在「格子上有成熟作物就先採收」
        # 判定的前面——否則敵人剛好站在成熟作物格子上時，玩家點擊想照暈
        # 敵人，會被下面第 1 優先權攔截去跑採收邏輯（雖然夜晚採收一定會
        # 失敗，但點擊已經被消耗掉、直接 return，手電筒永遠沒機會判定）。
        # use_flashlight_stun() 內部本來就會依游標位置比對 self.game.enemies
        # 的距離（含未命中時的最近敵人輔助瞄準），等同於「碰撞判定」，
        # 沿用它可以維持跟原本一致的冷卻/瞄準輔助手感，不用另外重寫一份。
        if not is_drag and self.game.phase == GamePhase.NIGHT and self.selected_action == "FLASHLIGHT":
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

        # 1b. 若點擊格子上有「加工機台」，同樣無論目前選了什麼工具，一律
        # 直接跟機台互動，不用先切到某個特定工具才能操作已經蓋好的機台
        # ——跟上面「成熟作物優先直接採收」是同一種手感。crop 跟 building
        # 不會同時存在同一格 (Tile.is_empty 的定義)，兩個判斷不會互相搶著
        # 處理同一格。
        # Phase 3：點擊不再是「投料/採收」兩種手動操作，而是單純「切換
        # 開關」——toggle_building() 內部會處理開啟時的原料預檢查。
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            tile = self.game.get_tile(gx, gy)
            if tile and tile.building is not None:
                success, msg = self.game.toggle_building(gx, gy)
                if not success:
                    px = GRID_X + gx * CELL_SIZE + CELL_SIZE // 2
                    py = GRID_Y + gy * CELL_SIZE + CELL_SIZE // 2
                    self.log_messages.append(f"⚙️ {msg}")
                    self.floating_texts.append(FloatingText(f"❌ {msg}", px - 60, py - 12, C_RED))
                    self.sound.play("error")
                # 成功切換開/關的音效跟浮動文字交給 BUILDING_TOGGLED /
                # BUILDING_STARTED / BUILDING_COLLECTED / BUILDING_STOPPED
                # 事件在 _process_events() 裡統一處理，這裡不重複播，跟
                # 訂單交付、採收成功是同一套既有模式。
                return

        # 2. 第二優先權：主動戰術工具 (指揮哨；手電筒的夜晚情境已在最上面
        # 處理掉了，走到這裡代表選了手電筒但現在是白天)
        if not is_drag and self.selected_action == "FLASHLIGHT":
            self.log_messages.append("☀️ 白天無入侵敵人！已為您自動切換至農耕播種模式。")
            self.active_tab = "CROPS"
            self.selected_action = "PLANT_RADISH"
            return

        if not is_drag and self.selected_action == "WHISTLE":
            success, msg = self.game.use_dog_whistle(world_gx, world_gy)
            if not success:
                self.log_messages.append(f"🔔 {msg}")
            else:
                self._spawn_particles(mx, my, C_CYAN, count=12)
            return

        # 3. 第三優先權：地圖建築、播種、澆水操作
        if self.hovered_grid:
            gx, gy = self.hovered_grid
            self._apply_grid_action(gx, gy, mx, my)

    def _handle_mouse_up(self, event):
        if event.button == 1:
            self.is_dragging_action = False
            self.last_action_grid = None

    def _apply_grid_action(self, gx: int, gy: int, mx: int = None, my: int = None):
        tile = self.game.get_tile(gx, gy)

        # 失敗時要在滑鼠點擊的位置跳浮動文字，沒有傳入 mx/my（例如舊的呼叫
        # 端）時退回格子中心，確保這個 helper 不管誰呼叫都能給出合理位置。
        if mx is None or my is None:
            mx = GRID_X + gx * CELL_SIZE + CELL_SIZE // 2
            my = GRID_Y + gy * CELL_SIZE + CELL_SIZE // 2

        # 【一鍵直接採收】：若點擊成熟作物，一律直接採收獲取金幣，無須切換任何工具！
        if tile and tile.crop and tile.crop.is_mature:
            success, reward, msg = self.game.harvest_crop(gx, gy)
            if not success:
                self.log_messages.append(f"❌ {msg}")
                self.floating_texts.append(FloatingText(f"❌ {msg}", mx - 45, my - 12, C_RED))
                self.sound.play("error")
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
        elif act == "PLANT_IRON_FLOWER":
            # 系統大重構 Phase 7：富鐵花，種在農田核心區（跟其餘 10 種
            # 作物一樣走 plant_crop()，place_building() 那套 2x2 佔地
            # 邏輯跟它無關——它是作物不是建築）。
            success, msg = self.game.plant_crop(gx, gy, CropType.IRON_FLOWER)
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
        # 加工機台 (Phase 2)：跟景觀裝飾一樣放在「四周莊園景觀區」，
        # PLACE_ 開頭但沒有加進 _DEFENSE_ACTION_IDS，_grid_preview_is_invalid()
        # 就會自動照景觀裝飾的規則檢查 DECORATION_ZONE，不用另外處理。
        elif act == "PLACE_FURNACE":
            success, msg = self.game.place_building(gx, gy, BuildingType.FURNACE)
        elif act == "PLACE_SPRINKLER":
            success, msg = self.game.place_building(gx, gy, BuildingType.SPRINKLER)
        elif act == "PLACE_AUTO_HARVESTER":
            success, msg = self.game.place_building(gx, gy, BuildingType.AUTO_HARVESTER)
        elif act == "PLACE_LUMBERYARD":
            success, msg = self.game.place_building(gx, gy, BuildingType.LUMBERYARD)
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
            # 側邊日誌面板在改版後已經拿掉，玩家點擊失敗（金幣不足/該格
            # 已被佔用/不是農田範圍...等）如果沒有畫面回饋會誤以為是
            # Bug。這裡直接沿用 game_state.py 各個 action 函式已經算好的
            # 詳細失敗原因字串 (msg)，在滑鼠點擊位置跳出紅色浮動文字，
            # 不额外重複判斷一次條件（避免跟遊戲邏輯的判斷條件兩邊不同步）。
            self.floating_texts.append(FloatingText(f"❌ {msg}", mx - 45, my - 12, C_RED))
            self.sound.play("error")

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

            # --- 飛船 AI 任務引導：任務進度推進判定 ---------------------
            # GameState.poll_events() 每次呼叫都會清空事件佇列，所以任務
            # 進度的比對只能放在這個既有的迴圈裡面做一次性判斷，不能另外
            # 開一個方法再 poll 一次（那樣永遠只會拿到空清單，跟上一版
            # 'TUTORIAL' 系統遇到的坑一樣）。這裡刻意不用 elif 接在下面
            # 那條長長的 if/elif 鏈上，而是獨立一個 if 區塊：同一個事件
            # （例如 CROP_PLANTED）除了推進任務進度之外，底下對應的
            # elif 分支通常沒有專門處理，兩邊互不影響。
            #
            # 跟舊版 'TUTORIAL' 最大的差異：這裡完全不管 self.app_state
            # 是不是某個特定狀態——只要玩家人在 'PLAYING'，任務就會在
            # 背景默默比對，玩家完全不需要照著任務順序操作，隨時可以先
            # 去做任務 3 的事、任務進度一樣會正確累計，不會鎖住任何操作。
            if self.app_state == 'PLAYING' and self.current_mission_idx < len(self.missions):
                current_mission = self.missions[self.current_mission_idx]
                m_type = current_mission.get("type")
                matched = False

                if m_type == "plant_crop" and ev.event_type == EventType.CROP_PLANTED:
                    # crop_type 是 CropType.value 字串（例如 "WHITE_RADISH"、
                    # "IRON_FLOWER"），exclude_iron/iron_only 兩個旗標互斥，
                    # 分別對應任務 0（種任意非富鐵花作物）跟任務 3（種富
                    # 鐵花）。
                    is_iron = ev.data.get("crop_type") == CropType.IRON_FLOWER.value
                    if current_mission.get("iron_only") and is_iron:
                        matched = True
                    elif current_mission.get("exclude_iron") and not is_iron:
                        matched = True
                elif m_type == "harvest_crop" and ev.event_type == EventType.CROP_HARVESTED:
                    # CROP_HARVESTED 事件資料裡沒有直接帶 crop_type（見
                    # game_state.py harvest_crop()），但只有 IRON_FLOWER 這
                    # 一種作物的 CROP_DATA 設了 output_key（見同一份檔案
                    # harvest_crop() 的註解），所以「output_key 是否有值」
                    # 就是「這次採收的是不是富鐵花」的可靠判斷依據，不用
                    # 另外改 game_state.py 的事件資料格式。
                    is_iron_harvest = bool(ev.data.get("output_key"))
                    if current_mission.get("exclude_iron") and not is_iron_harvest:
                        matched = True
                elif m_type == "place_defense" and ev.event_type == EventType.DEFENSE_PLACED:
                    matched = True
                elif m_type == "place_building_2x2" and ev.event_type == EventType.BUILDING_PLACED:
                    # 目前 BUILDING_DATA 裡僅有的兩種建築（LUMBERYARD/
                    # FURNACE）都已經是 2x2 佔地（系統大重構 Phase 7），
                    # 這裡改用 BUILDING_DATA[...]["size"] 動態比對而不是
                    # 寫死字串清單，未來如果新增非 2x2 的建築類型，這條
                    # 任務條件不用跟著改。
                    bt_value = ev.data.get("building_type")
                    bt = next((b for b in BuildingType if b.value == bt_value), None)
                    if bt is not None and BUILDING_DATA.get(bt, {}).get("size") == (2, 2):
                        matched = True

                if matched:
                    self.mission_progress += 1
                    if self.mission_progress >= current_mission.get("target", 1):
                        self.current_mission_idx += 1
                        self.mission_progress = 0
                        if self.current_mission_idx < len(self.missions):
                            self.log_messages.append(f"✨ {self.missions[self.current_mission_idx]['text']}")
                        else:
                            self.log_messages.append("✨ 莊園精靈：全部任務已完成！")

            if ev.event_type == EventType.CROP_HARVESTED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"+{ev.data['reward']} G", px - 15, py - 10, C_FLOATTEXT_GOLD))
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
                # 【UI 佈局修復】原本 y=95 是配合舊版「柴犬管家」教學列
                # （佔用 y=58~84）往下避開；舊版教學列已整段移除，改成
                # 飛船 AI 任務橫幅常駐佔用
                # MISSION_BANNER_Y ~ MISSION_BANNER_Y + MISSION_BANNER_H
                # （目前是 y=84~116），這裡改成讀這兩個共用常數往下推，
                # 兩則「清晨結算」文字才不會疊在任務橫幅上看不清楚。
                y_base = self.MISSION_BANNER_Y + self.MISSION_BANNER_H + 10
                # 【系統修復與文本重構】原本「地租維護費」的說法比較像
                # 硬派生存遊戲的資源壓力機制，改成「農莊擴建投資」——
                # 扣款的金額/時機/邏輯完全不變，只是把「每天被迫繳一筆
                # 租金」的說法，換成「每天投入一筆資金持續擴建農莊」的
                # 溫馨框架。
                self.floating_texts.append(FloatingText(f"🏡 農莊擴建投資 -{ev.data['tax']} G", 460, y_base, (239, 83, 80)))
            elif ev.event_type == EventType.PROSPERITY_DIVIDEND:
                y_base = self.MISSION_BANNER_Y + self.MISSION_BANNER_H + 34
                self.floating_texts.append(FloatingText(f"🏡 莊園分紅 +{ev.data['dividend']} G", 460, y_base, C_FLOATTEXT_GOLD))
            elif ev.event_type == EventType.ENEMY_STUNNED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                self.floating_texts.append(FloatingText("⚡ 暈眩 2.5s", px - 20, py - 15, C_FLOATTEXT_GOLD))
                self._spawn_particles(px, py, (255, 235, 59), count=14)
            elif ev.event_type == EventType.BEE_ATTACK:
                fx = GRID_X + ev.data["from_x"] * CELL_SIZE + CELL_SIZE // 2
                fy = GRID_Y + ev.data["from_y"] * CELL_SIZE + CELL_SIZE // 2
                tx = GRID_X + ev.data["to_x"] * CELL_SIZE + CELL_SIZE // 2
                ty = GRID_Y + ev.data["to_y"] * CELL_SIZE + CELL_SIZE // 2
                self.floating_texts.append(FloatingText(f"🐝 -{int(ev.data['damage'])}", tx - 15, ty - 12, C_FLOATTEXT_GOLD))
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
                    self.floating_texts.append(FloatingText(f"🐱 +{ev.data['bonus']} G (招財)", px - 15, py, C_FLOATTEXT_GOLD))
                    self._spawn_particles(px, py, C_GOLD, count=6)
            elif ev.event_type == EventType.FARM_LEVEL_UP:
                self.floating_texts.append(FloatingText(f"⭐ 莊園繁榮升級 Lv.{ev.data['new_level']}！", SCREEN_WIDTH // 2 - 90, 220, C_FLOATTEXT_GOLD, duration=2.5))
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
            elif ev.event_type == EventType.ORDER_FULFILLED:
                # 交付成功的浮動文字/粒子特效統一在這裡處理（音效交給
                # sound_manager.handle_game_event 映射 ORDER_FULFILLED ->
                # "gold"），跟 CROP_HARVESTED 等既有的成功事件同一套模式。
                # 座標固定畫在訂單佈告欄按鈕正下方附近，而不是滑鼠位置
                # ——這個事件被 poll 到的當下，滑鼠可能已經移動，
                # ev.data 裡也沒有存點擊當下的座標，用固定位置比較穩妥。
                order_btn_rect = self._order_board_button_rect()
                px, py = order_btn_rect.centerx - 60, order_btn_rect.bottom + 10
                self.floating_texts.append(FloatingText(
                    f"📦 +{ev.data['reward_gold']} G  +{ev.data['reward_tech']} 工藝",
                    px, py, C_TECH_GREEN, duration=1.8
                ))
                self._spawn_particles(order_btn_rect.centerx, order_btn_rect.bottom, C_TECH_GREEN, count=14)
            elif ev.event_type == EventType.ORDERS_GENERATED:
                # 被動通知，不用玩家點什麼——每天早上訂單自動刷新，用一
                # 條浮動文字提醒「有新訂單」，玩家想看細節再自己按 O /
                # 點📋按鈕開訂單佈告欄，這裡不用強制彈窗打斷操作。
                order_count = len(ev.data.get("order_ids", []))
                self.floating_texts.append(
                    FloatingText(f"📋 今日新訂單 x{order_count}！按 O 查看", 460, 143, C_TECH_GREEN)
                )
            elif ev.event_type == EventType.BUILDING_STARTED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                self.floating_texts.append(FloatingText("⚙️ 開始運作...", px - 35, py - 14, (200, 190, 178)))
            # 注意：EventType.BUILDING_READY（Phase 2 的「完成待手動採收」
            # 通知）在 Phase 3 已經不會再被 emit——機台改成開關式自動化，
            # 完成的當下直接自動採收、併進 BUILDING_COLLECTED，不再有
            # 「等待玩家點擊採收」這個中間狀態，所以這裡原本對應的 elif
            # 分支已經移除（原本會畫一條「✨ 可以採收了！」浮動文字，現在
            # 用不到了）。
            elif ev.event_type == EventType.BUILDING_TOGGLED:
                # 玩家手動點擊切換開關的即時回饋。ev.data["is_active"] 是
                # 切換後的新狀態；「關閉但這一輪還在跑」跟「已經完全關閉」
                # 在 toggle_building() 回傳的 msg 裡文字不同，但事件資料本身
                # 只帶 is_active，這裡用顏色區分開/關即可，細節文字已經在
                # 點擊當下由 toggle_building() 的回傳值決定（未來如需要更
                # 精細的「本輪結束後停工」提示，可以在 event data 裡加一個
                # will_finish_current_round 欄位，目前先用最簡單的開/關
                # 二元呈現）。
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                if ev.data.get("is_active"):
                    self.floating_texts.append(FloatingText("🟢 已開啟", px - 25, py - 14, C_TECH_GREEN))
                    self._spawn_particles(px, py, C_TECH_GREEN, count=6)
                else:
                    self.floating_texts.append(FloatingText("🔴 已關閉", px - 25, py - 14, (200, 120, 110)))
            elif ev.event_type == EventType.BUILDING_STOPPED:
                # 被動通知：機台因為原料不足被系統自動關閉（不是玩家手動
                # 點擊），用偏警告色的紅字提醒，跟上面玩家主動關閉的
                # 「🔴 已關閉」文字內容不同，讓玩家一眼看出這次是「原料
                # 用完了」而不是自己點的。
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                self.floating_texts.append(FloatingText("⏸️ 原料不足，已自動停工", px - 55, py - 14, C_RED))
            elif ev.event_type == EventType.BUILDING_COLLECTED:
                px = GRID_X + ev.data["x"] * CELL_SIZE + CELL_SIZE // 2
                py = GRID_Y + ev.data["y"] * CELL_SIZE
                self.floating_texts.append(FloatingText(
                    f"+{ev.data['output_qty']} {ev.data['output_key']}", px - 20, py - 14, C_FLOATTEXT_GOLD
                ))
                self._spawn_particles(px, py, C_GOLD, count=12)

            # 夜晚降臨時（含血月）自動裝備強光手電筒，玩家不必再去商店手動點選。
            # 特意寫成獨立的 if（不是掛在上面的 elif 鏈上）：BLOOD_MOON_WARNING
            # 這個事件本身已經被上面的 elif 分支吃掉（顯示血月紅字），若把這段
            # 也寫成 elif 就永遠輪不到它執行；獨立判斷才能讓一般夜晚與血月夜
            # 都能觸發。原本這裡監聽的是 PHASE_CHANGED 事件，但 game_state.py
            # 從未送出這個事件，所以自動裝備邏輯過去從來沒有真正執行過。
            if ev.event_type in (EventType.NIGHT_STARTED, EventType.BLOOD_MOON_WARNING):
                self.active_tab = "TOOLS"
                self.selected_action = "FLASHLIGHT"
                self.floating_texts.append(FloatingText("🔦 已裝備強光手電筒！滑鼠點擊敵人照暈！", SCREEN_WIDTH // 2 - 140, 200, C_FLOATTEXT_GOLD, duration=2.5))

    # 【UI 佈局修復：解決任務橫幅重疊與移除舊版教學系統】
    # 這裡原本是 _get_mascot_guide_data()，舊版「柴犬管家」動態教學列
    # 的文字資料來源（依日夜/天數/採收狀態回傳徽章文字、對話、步驟
    # 標籤），唯一呼叫端在 _render_flat_meadow_and_farm() 尾端，畫在
    # y = GRID_Y - 28 ~ GRID_Y - 2（GRID_Y=86，也就是 y=58~84）。
    #
    # 新版「飛船 AI 任務橫幅」(self.missions / _render_mission_ui()，見
    # 下方) 職責跟這套系統完全重疊（兩者都是畫在農場上方的常駐引導
    # 文字），新版橫幅原本畫在 y=70 起，跟舊版的 y=58~84 大幅重疊，
    # 兩條文字疊在一起互相遮擋——這正是這次回報的 UI 重疊問題的根本
    # 原因。兩套系統只留一套，這裡連同 _render_flat_meadow_and_farm()
    # 尾端呼叫這個方法、畫柴犬教官對話框的那一段程式碼一併整段刪除
    # （不是註解掉）：只註解掉的話，方法本體跟呼叫端還留在檔案裡，
    # 之後容易有人以為這套系統還在運作、繼續往裡面加新教學文案，反而
    # 製造混淆；直接刪除能確保「柴犬管家教學列」不會再被任何地方
    # 意外呼叫到、也不會再跟任何新版 UI 衝突版面。



    def _update_card_states(self):
        for card in self.action_cards:
            # 作物解鎖判定
            if card.action_id in ("PLANT_CORN", "PLANT_CARROT", "PLANT_STRAWBERRY"):
                card.is_locked = not self.game.is_crop_unlocked(CropType.SWEET_CORN)
                card.lock_reason = "需莊園等級 Lv.2"
            elif card.action_id in ("PLANT_PUMPKIN", "PLANT_BLUEBERRY", "PLANT_WHEAT", "PLANT_IRON_FLOWER"):
                # 富鐵花 (IRON_FLOWER) 的 unlock_level 在 CROP_DATA 裡跟
                # MAGIC_PUMPKIN/BLUEBERRY/WHEAT 一樣是 Lv.3（刻意跟
                # FURNACE 熔爐同一階解鎖，見 game_config.py 的說明），
                # 歸進同一組鎖卡判定，不用另外寫一個 elif 分支。
                card.is_locked = not self.game.is_crop_unlocked(CropType.MAGIC_PUMPKIN)
                card.lock_reason = "需莊園等級 Lv.3"
            elif card.action_id in ("PLACE_FURNACE", "PLACE_SPRINKLER", "PLACE_AUTO_HARVESTER",
                                     "PLACE_LUMBERYARD"):
                # 熔爐/灑水器/自動採收機/伐木場/礦場的
                # unlock_level 都直接讀 BUILDING_DATA 定義比對
                # self.game.farm_level，不用另外走 is_crop_unlocked 那套
                # 只吃 CropType 的介面。金幣/科技點數/metal_ingot 材料
                # 不足都不會鎖卡——維持跟其餘商店卡片一致的「可以點，
                # 點了會跳紅字說明缺什麼」既有手感，只有等級這種「不管
                # 有沒有錢都做不到」的門檻才會直接鎖卡。
                # 視覺升級（熔爐動畫）階段整批移除 OVEN/KILN 之後，這裡
                # 同步拿掉 "PLACE_OVEN"/"PLACE_KILN" 兩個 key，避免對照表
                # 裡留著已經不存在的 BuildingType 成員。
                # UI 視覺優化階段：改讀 class 層級的 _CARD_BUILDING_TYPES
                # 共用常數，不再是這裡的本地變數，見該常數定義處的說明。
                _card_building_type = self._CARD_BUILDING_TYPES[card.action_id]
                req_lvl = BUILDING_DATA[_card_building_type]["unlock_level"]
                card.is_locked = self.game.farm_level < req_lvl
                card.lock_reason = f"需莊園等級 Lv.{req_lvl}"
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
    # 【系統升級】打字機開場劇情 / 飛船 AI 任務引導
    # ==========================================
    def _advance_story(self):
        """STORY 狀態下玩家按空白鍵/點滑鼠的統一處理：目前這句還沒打完
        （story_char_index < 這句字數）就直接補滿顯示全句；已經打完了
        就換下一句、字元進度歸零重算。播到最後一句之後再按一次，代表
        整段開場劇情結束，直接切到 'PLAYING'——這次不再經過會鎖死操作
        的 'TUTORIAL' 中間狀態，任務引導改由 missions/current_mission_idx
        在 PLAYING 狀態下背景運作（見 _process_events()/_render_mission_ui()）。
        """
        if self.current_story_index >= len(self.story_lines):
            return
        current_text = self.story_lines[self.current_story_index]["text"]
        if self.story_char_index < len(current_text):
            self.story_char_index = float(len(current_text))
            return
        self.current_story_index += 1
        self.story_char_index = 0.0
        if self.current_story_index >= len(self.story_lines):
            self.app_state = 'PLAYING'

    def _render_story(self):
        """打字機開場劇情畫面。

        【系統修復與文本重構】背景圖依 self.story_lines[current_story_
        index]["bg_key"] 動態決定要畫哪一張——bg_key 是 "title_bg"/
        "bg_abandoned"/"bg_premium_crop" 三者之一（世界觀重構後的鍵
        名，取代原本的 "bg_crash"/"bg_iron_flower"），實際 Surface
        透過 self.loader.get(bg_key) 向 AssetLoader 拿（三張圖都在
        AssetLoader.load_all() 裡統一載入、強制縮放成
        (SCREEN_WIDTH, SCREEN_HEIGHT)，見 asset_loader.py）。這裡刻意
        用既有的 loader.get()，不是使用者需求文字裡寫的
        self.loader.assets[bg_key]——AssetLoader 從頭到尾沒有 assets
        這個字典，直接這樣寫會是 AttributeError，get() 是唯一正確的
        存取方式，效果完全等價。
        current_story_index 若已經跑到 len(story_lines)（理論上不會，
        因為播完最後一句 _advance_story() 就會直接切到 'PLAYING'，
        這裡是防呆）就沒有對應的 bg_key，退回跟其餘背景圖同一套後備
        深藍色純色 (12, 16, 38)。

        文字用 draw_text_with_outline()（8 方向描邊），理由跟主選單標題
        完全一樣：背景圖亮度不可預期，弱描邊在亮的區域會吃色。"""
        current_bg = None
        if self.current_story_index < len(self.story_lines):
            bg_key = self.story_lines[self.current_story_index]["bg_key"]
            current_bg = self.loader.get(bg_key)

        if current_bg:
            self.screen.blit(current_bg, (0, 0))
        else:
            self.screen.fill((12, 16, 38))

        # 半透明黑色遮罩：需求明確要求「加上半透明黑色遮罩」，這裡比
        # 主選單的遮罩再暗一階 (alpha 140 vs 90)，因為劇情畫面需要玩家
        # 專心閱讀對話文字，比起主選單只是襯托標題，這裡更需要壓低背景
        # 的視覺干擾。
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))

        if self.current_story_index < len(self.story_lines):
            current_text = self.story_lines[self.current_story_index]["text"]
            visible_text = current_text[:int(self.story_char_index)]

            # 對話框：畫在畫面下半部，用既有的 draw_wood_panel 木紋面板，
            # 跟遊戲其他彈窗（暫停選單/訂單佈告欄）維持同一套視覺語言，
            # 不是另外設計一套風格。
            box_w, box_h = SCREEN_WIDTH - 160, 140
            box_rect = pygame.Rect((SCREEN_WIDTH - box_w) // 2, SCREEN_HEIGHT - box_h - 60, box_w, box_h)
            draw_wood_panel(self.screen, box_rect, self.loader, "ui_wood_button",
                             (58, 44, 30), border_radius=14, depth=4)

            # 【系統修復與文本重構】劇情台詞從「飛船AI廣播」改成溫馨奇幻
            # 農場口吻的全知旁白，發話者標籤同步改成「🌙 農莊物語」，跟
            # 後面 PLAYING 狀態任務橫幅的「莊園精靈：」語氣呼應，都是
            # 溫暖、帶點奇幻色彩的敘事聲音，不再是冰冷的系統廣播。
            blit_text_with_shadow(self.screen, FONT_SM, "🌙 農莊物語", C_CYAN,
                                   topleft=(box_rect.x + 24, box_rect.y + 16))
            draw_text_with_outline(self.screen, visible_text, FONT_MD, C_TEXT_ON_DARK, (0, 0, 0),
                                    center_pos=(box_rect.centerx, box_rect.centery + 10), outline_width=1)

            # 完整顯示這句之後才提示「按空白鍵繼續」，避免玩家還沒看完
            # 打字機動畫就被提示字樣分心；提示文字閃爍效果沿用既有
            # pygame.time.get_ticks() 節奏（跟其他地方的提示閃爍手法
            # 一致），不用額外的計時器屬性。
            if self.story_char_index >= len(current_text):
                if int(pygame.time.get_ticks() / 400) % 2 == 0:
                    blit_text_with_shadow(self.screen, FONT_XS, "▼ 按空白鍵或點擊滑鼠繼續", (220, 220, 220),
                                           topleft=(box_rect.right - 220, box_rect.bottom - 26))

    # 任務橫幅的頂部 Y 座標與高度，抽成類別常數而不是寫死在方法內部的
    # 兩個數字：_process_events() 那邊的 DAILY_TAX_PAID/PROSPERITY_
    # DIVIDEND 浮動文字需要知道這條橫幅實際佔用到哪個 y 才不會互相
    # 重疊，兩處共用同一組常數，之後只要調這裡一個地方就好，不用同時
    # 改兩個檔案位置裡各自寫死的魔術數字。
    # 【系統修復：UI 元素重疊/文字溢出/導覽列被切斷】頭部資源列高度從
    # 70 加到 76（多留一點上下留白），任務橫幅緊接在下方 (82~114)，
    # GRID_Y 已同步改成 124，兩者跟農田地圖之間都留了乾淨的間距，不再
    # 互相重疊或被截斷。
    MISSION_BANNER_Y = 82
    MISSION_BANNER_H = 32

    def _render_mission_ui(self):
        """PLAYING 狀態下、頭部資源列橫幅正下方的飛船 AI 任務橫幅。跟
        舊版 'TUTORIAL' 對話框最大的不同：這裡完全不擋任何點擊、不暫停
        任何操作，純粹是一條常駐提示，_render() 每幀正常呼叫這個方法，
        玩家可以完全無視它照樣自由遊玩。current_mission_idx 超出
        missions 範圍（理論上不會發生，因為 missions[-1] 是永遠比對不到
        的 "complete" 類型，見 _process_events()）時直接不畫，純防呆。

        【UI 佈局修復】原本畫在 y=70（緊貼頭部資源列下緣），跟舊版
        「柴犬管家」教學列 (y=58~84) 重疊；舊版已整段移除，這裡改讀
        MISSION_BANNER_Y（=84），完整落在需求指定的 y=80~90 區間內，
        兩者不再有任何重疊。
        """
        if self.current_mission_idx >= len(self.missions):
            return
        mission = self.missions[self.current_mission_idx]

        # 半透明黑底 + 青色邊框（需求明確要求的「科技感」配色），跟
        # 頭部資源列那種不透明木紋底刻意做出區隔，讓玩家一眼就能分辨
        # 「這是額外疊加的提示」而不是遊戲原生 HUD 的一部分。
        banner_rect = pygame.Rect(0, self.MISSION_BANNER_Y, SCREEN_WIDTH, self.MISSION_BANNER_H)
        banner_surf = pygame.Surface((SCREEN_WIDTH, self.MISSION_BANNER_H), pygame.SRCALPHA)
        banner_surf.fill((10, 20, 24, 165))
        self.screen.blit(banner_surf, banner_rect.topleft)
        pygame.draw.rect(self.screen, C_CYAN, banner_rect, width=2)

        # 左側：AI 對話文字（淡藍色）。右側：進度 (例如 0/1)。兩者都用
        # center=(..., banner_rect.centery) 垂直置中對齊橫幅本身，而不是
        # 像舊版那樣寫死 topleft y 偏移——banner_rect 的高度改動時（例如
        # 之後又想再調整 MISSION_BANNER_H），文字位置會自動跟著置中，
        # 不用每次改高度都手動重算文字的 y 偏移。
        # missions[-1]（"complete" 類型）沒有真正的 target/progress 概念
        # （target 存的是 0，純粹只是占位避免 KeyError），這裡一律讀
        # mission.get("target", 0)，是 0 的話就不顯示進度數字，只顯示
        # 那句完成提示文字，避免玩家看到令人困惑的「0/0」。
        text_surf = FONT_SM.render(mission["text"], True, (140, 220, 255))
        text_rect = text_surf.get_rect(midleft=(20, banner_rect.centery))
        blit_text_with_shadow(self.screen, FONT_SM, mission["text"], (140, 220, 255),
                               topleft=text_rect.topleft)

        target = mission.get("target", 0)
        if target > 0:
            progress_text = f"{self.mission_progress}/{target}"
            prog_surf = FONT_SM.render(progress_text, True, C_GOLD)
            prog_rect = prog_surf.get_rect(midright=(SCREEN_WIDTH - 20, banner_rect.centery))
            blit_text_with_shadow(self.screen, FONT_SM, progress_text, C_GOLD,
                                   topleft=prog_rect.topleft)

    # ==========================================
    # 【Phase 6】外層遊戲狀態：主選單畫面
    # ==========================================
    def _render_main_menu(self):
        """開始畫面。

        主選單背景圖固定使用 "title_bg" 這個 key——title_bg 才是專屬給
        主選單用的標題背景圖，跟 _render_story() 分鏡表裡動態切換的
        "bg_abandoned"/"bg_premium_crop"（見 __init__ 的
        self.story_lines）是各自獨立的用途，不會互相影響。

        loader.get("title_bg") 理論上不會是 None：AssetLoader.
        load_all() 一律會呼叫 self._load_image("title_bg.png", ...)
        幫這個 key 賦值，就算檔案還沒放進 assets/ 目錄，_load_image()
        內部的 except 也會自動退回 generate_placeholder() 生成一張
        佔位圖，而不是回傳 None。這裡仍然保留 if/else 防呆判斷，跟這
        個檔案其餘 loader.get(...) 呼叫點的既有寫法一致，避免之後如果
        AssetLoader 的實作細節改變、真的回傳 None 時整個畫面直接壞掉。

        標題文字畫在正中央偏上，三顆按鈕直向排列在畫面下半部，跟既有
        _render_pause_menu() 一樣，用 draw_wood_panel（木紋面板，沒有
        真的貼圖時自動退回立體木頭色塊）+ blit_text_with_shadow（帶
        陰影文字，深色背景圖上也看得清楚）畫按鈕，維持跟遊戲其餘彈窗
        一致的視覺語言，不是另外設計一套風格。"""
        main_menu_bg = self.loader.get("title_bg")
        if main_menu_bg:
            self.screen.blit(main_menu_bg, (0, 0))
        else:
            # 找不到圖時的後備：深藍色純色背景，比純黑柔和，也呼應
            # 「星際拓荒」這個主題色調的暗示（深空藍），不會讓畫面
            # 看起來像壞掉、缺圖的空白畫面。
            self.screen.fill((12, 16, 38))

        # 半透明深色遮罩疊在背景圖上，讓標題文字跟按鈕不管背景圖本身
        # 亮不亮都維持足夠對比度，不會被背景圖的亮色區塊蓋過去看不清楚。
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 20, 90))
        self.screen.blit(overlay, (0, 0))

        # 【UI 視覺優化：修復主選單標題吃色問題】上面那層是整個畫面的
        # 淡淡遮罩（alpha 90，本來就存在），這裡另外疊一塊「只蓋在標題
        # 文字附近」、更暗一階的區域性遮罩（alpha 100，寬度等於整個
        # 螢幕、高度約 120px），專門把主標題「夜巡計畫：異星拓荒
        # (Project Nightwatch)」正後方那一小塊背景再壓暗一次——黃色
        # 文字最容易在 title_bg 背景圖本身較亮的區域（例如星空/艙體
        # 反光）被吃色，這塊局部加深的遮罩加上下面的文字描邊雙重保險，
        # 確保不管背景圖哪個區域剛好落在標題位置，文字都維持足夠對
        # 比度——這套機制是既有的，這次只是把註解裡引用的舊標題文字
        # 同步更新，機制本身不用改。
        title_band_h = 120
        title_band_y = SCREEN_HEIGHT // 2 - 180 - title_band_h // 2
        title_band = pygame.Surface((SCREEN_WIDTH, title_band_h), pygame.SRCALPHA)
        title_band.fill((0, 0, 0, 100))
        self.screen.blit(title_band, (0, title_band_y))

        # 【系統修復與文本重構】主選單文案這次跟著遊戲整體從「硬派外星
        # 求生」轉型成「溫馨奇幻農場」再改一次：拿掉上一版「主引擎受損
        # ／迫降未知座標」那套科幻求生說法，改成呼應新版 STORY 開場
        # 劇情（繼承一座荒廢已久的祖傳農莊）的溫馨副標題。
        #
        # 主標題/副標題改用 draw_text_with_outline()：8 方向黑色描邊 +
        # 正中央黃色/米白色主體文字，比原本 blit_text_with_shadow() 的
        # 4 方向 1px 描邊更強，搭配上面既有的局部遮罩，雙重解決背景圖
        # 亮度不可預期造成的吃色問題——這套「描邊 + 局部遮罩」的組合是
        # 既有機制，換了背景圖跟文案之後同樣適用，不需要另外加強。
        draw_text_with_outline(self.screen, "夜巡農場：奇幻拓荒記 (Nightwatch Farm)", FONT_TITLE, C_GOLD, (0, 0, 0),
                                center_pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 180), outline_width=2)
        draw_text_with_outline(self.screen, "一座被世人遺忘的祖傳農莊，正等待你重新拾起鋤頭與柵欄……", FONT_SM, C_TEXT_ON_DARK, (0, 0, 0),
                                center_pos=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 140), outline_width=2)

        def _draw_menu_button(rect, label, base_color, disabled=False):
            hovered = (not disabled) and rect.collidepoint(self.mouse_pos)
            draw_wood_panel(self.screen, rect, self.loader, "ui_wood_button",
                             base_color, border_radius=10, depth=3, pressed=hovered)
            if disabled:
                # 【Phase 7，選用需求】沒有存檔時「繼續遊戲」畫成灰階
                # Disabled 樣式：半透明深色遮罩壓暗整顆按鈕（跟既有
                # ActionCard.is_locked 鎖卡遮罩是同一種手法），文字改用
                # 較暗的顏色，讓玩家一眼就能看出這顆按鈕目前點了也沒用，
                # 不用等點下去才發現。點擊判定本身完全不受這個影響——
                # _handle_menu_mouse_down() 一樣會檢查 has_save()，就算
                # 玩家真的點了沒存檔的「繼續遊戲」，也只會觸發下面的
                # 「⚠ 沒有找到存檔」提示，不會出錯。
                overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(overlay, (20, 20, 20, 140), overlay.get_rect(), border_radius=10)
                self.screen.blit(overlay, rect.topleft)
                blit_text_with_shadow(self.screen, FONT_MD, label, (170, 170, 170), center=rect.center)
            else:
                blit_text_with_shadow(self.screen, FONT_MD, label, C_TEXT_ON_DARK, center=rect.center)

        btn_w, btn_h, gap = 260, 58, 20
        btn_x = SCREEN_WIDTH // 2 - btn_w // 2
        start_y = SCREEN_HEIGHT // 2 - 40

        self.btn_new_game_rect = pygame.Rect(btn_x, start_y, btn_w, btn_h)
        _draw_menu_button(self.btn_new_game_rect, "🌱 新遊戲", (90, 122, 74))

        has_save = GameState.has_save()
        self.btn_continue_rect = pygame.Rect(btn_x, start_y + (btn_h + gap), btn_w, btn_h)
        _draw_menu_button(self.btn_continue_rect, "▶ 繼續遊戲", (86, 108, 140), disabled=not has_save)

        self.btn_exit_rect = pygame.Rect(btn_x, start_y + (btn_h + gap) * 2, btn_w, btn_h)
        _draw_menu_button(self.btn_exit_rect, "✖ 離開", (150, 70, 60))

        # 【Phase 7】沒存檔時點「繼續遊戲」的短暫提示，畫在按鈕群下方，
        # 剩餘時間歸零（由 run() 每幀遞減 self.menu_message_timer）之後
        # 自動消失，不需要玩家手動關閉。
        if self.menu_message and self.menu_message_timer > 0:
            blit_text_with_shadow(
                self.screen, FONT_SM, self.menu_message, C_LOCK_TEXT_RED,
                center=(SCREEN_WIDTH // 2, self.btn_exit_rect.bottom + 36))

    # ==========================================
    # 純色扁平無網格渲染管道 (Flat Pipeline)
    # ==========================================
    def _render(self):
        # 畫面最底層的背景色：地圖跟商店面板不一定剛好貼齊填滿整個視窗
        # 邊緣（例如視窗被拉寬、或地圖區塊本身有圓角），縫隙會露出這個
        # 底色。原本是很亮的淺灰藍色，在夜晚模式下顯得刺眼、也跟木質
        # 風格的 UI 不搭；改成深邃的泥土色，跟 C_WOOD_DARK 呼應，露出來
        # 的縫隙看起來像木頭底下的陰影，而不是穿幫的畫布白邊。
        self.screen.fill((46, 34, 24))

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

        # 【系統修復：UI 元素重疊/文字溢出/導覽列被切斷】頭部資源列
        # (含金幣/科技點/莊園等級/晝夜進度) 跟正下方的任務橫幅，刻意搬到
        # _render() 幾乎最後才畫（只留彈窗類 modal 在它們之後）——即使
        # GRID_Y 已經調整到不會再跟地圖/商店面板重疊，這裡仍然依照需求
        # 明確要求的「頂部導覽列必須是最後繪製的 UI 圖層之一」，讓它們
        # 永遠疊在地圖、建築、特效、商店面板之上，不會被任何地圖元件
        # 意外蓋掉或穿透。
        self._render_header_banner()
        self._render_mission_ui()

        if self.show_intro:
            self._render_story_modal()
        elif self.game.game_over:
            self._render_game_over_modal()
        elif self.show_pause_menu:
            self._render_pause_menu()
        elif self.show_order_board:
            self._render_order_board()

    def _render_pause_menu(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        self.screen.blit(overlay, (0, 0))

        modal_w, modal_h = 420, 366
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)

        # 彈窗底框：跟商店面板/頂部狀態列同一套「先試貼圖、沒有就退回
        # 立體木頭色塊」邏輯 (draw_wood_panel)。目前 assets/ui/ 底下還沒有
        # wood_panel.png，所以現在畫出來的是 draw_beveled_rect() 版本，
        # 深木色底 + 立體刻痕邊框，跟主畫面風格一致；以後放了真的貼圖，
        # 這裡會自動改貼圖，不用再改這段程式碼。
        draw_wood_panel(self.screen, modal_rect, self.loader, "ui_wood_panel",
                         C_WOOD_DARK, border_radius=14, depth=3)

        blit_text_with_shadow(self.screen, FONT_TITLE, "⏸ 遊戲暫停", C_GOLD,
                               center=(mx + modal_w // 2, my + 48))

        blit_text_with_shadow(
            self.screen, FONT_SM,
            f"第 {self.game.day_count} 天・繁榮度 {self.game.prosperity_score}",
            C_TEXT_ON_DARK, center=(mx + modal_w // 2, my + 96))

        def _draw_menu_button(rect, label, base_color):
            hovered = rect.collidepoint(self.mouse_pos)
            draw_wood_panel(self.screen, rect, self.loader, "ui_wood_button",
                             base_color, border_radius=8, depth=2, pressed=hovered)
            blit_text_with_shadow(self.screen, FONT_MD, label, C_TEXT_ON_DARK, center=rect.center)

        btn_resume = pygame.Rect(mx + (modal_w - 220) // 2, my + 150, 220, 52)
        # 用「恢復」而非「繼續」：這個選字原本是因為舊字型
        # NotoSansTC-GameSubset.otf 是裁切過的子集字型，「繼」字不在收錄
        # 範圍內會變成缺字方塊「□」。技術債清理階段換成完整字庫的
        # Cubic_11.ttf 之後，這個限制理論上已經不存在，但這裡沒有跟著
        # 改回「繼續」——P 鍵暫停/恢復本來就用「恢復」這個詞（見上方
        # run() 的 K_p 處理），兩處維持同一個詞語意更一致，純粹是用字
        # 習慣的選擇，不是缺字限制強迫的了。
        _draw_menu_button(btn_resume, "▶ 恢復", (90, 122, 74))

        btn_restart = pygame.Rect(mx + (modal_w - 220) // 2, my + 216, 220, 52)
        _draw_menu_button(btn_restart, "🔄 重新開始", (150, 96, 56))

        # 靜音只影響背景音樂，不影響採收/建造等音效；標籤跟按鈕顏色都會
        # 依目前狀態切換，不用另外開對話框確認就能立刻看到生效與否。
        # 用「靜音」而不加「音樂」二字：「樂」不在精簡字型子集裡。
        btn_mute = pygame.Rect(mx + (modal_w - 220) // 2, my + 282, 220, 52)
        muted = self.sound.music_muted
        _draw_menu_button(btn_mute, "🔊 取消靜音" if muted else "🔇 靜音",
                           (96, 88, 78) if muted else C_WOOD_MID)

    def _render_order_board(self):
        """訂單佈告欄面板：show_order_board 為 True 時畫在畫面正中央，
        半透明遮罩擋住底下地圖跟商店（但遊戲本身仍在跑，不像暫停選單
        會把 dt 歸零——訂單交付刻意設計成隨手可做的操作，見 __init__
        裡 self.show_order_board 旁的註解）。"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        panel = self._order_board_rect()
        # 跟暫停選單/結算畫面同一套 draw_wood_panel：目前 assets/ui/
        # 還沒有 wood_panel.png，所以現在畫出來的是立體木頭色塊退回版；
        # 貼圖之後放上去會自動生效。
        draw_wood_panel(self.screen, panel, self.loader, "ui_wood_panel",
                         C_WOOD_DARK, border_radius=16, depth=3)

        header_rect = pygame.Rect(panel.x, panel.y, panel.width, 48)
        pygame.draw.rect(self.screen, C_WOOD_BEVEL_DARK, header_rect,
                          border_top_left_radius=16, border_top_right_radius=16)
        blit_text_with_shadow(self.screen, FONT_TITLE, "📋 每日訂單佈告欄", C_GOLD,
                               center=(header_rect.centerx, header_rect.centery))

        close_rect = pygame.Rect(panel.right - 42, panel.y + 8, 32, 32)
        self._order_board_close_rect = close_rect
        is_close_hover = close_rect.collidepoint(self.mouse_pos)
        draw_wood_panel(self.screen, close_rect, self.loader, "ui_wood_button",
                         (150, 70, 60), border_radius=8, depth=2, pressed=is_close_hover)
        blit_text_with_shadow(self.screen, FONT_MD, "✕", C_TEXT_ON_DARK, center=close_rect.center)

        self.screen.blit(FONT_XS.render("按 O 鍵或點擊「✕」可關閉", True, (200, 190, 178)),
                          (panel.x + 16, header_rect.bottom + 2))

        self._order_deliver_rects = []

        orders = self.game.active_orders
        content_y = header_rect.bottom + 22
        card_h = 96
        card_gap = 12
        card_w = panel.width - 28

        if not orders:
            blit_text_with_shadow(self.screen, FONT_MD, "今天的訂單都交付完了！明天清晨會有新訂單喔～",
                                   C_TEXT_ON_DARK, center=(panel.centerx, panel.centery))
            return

        for i, order in enumerate(orders):
            card_rect = pygame.Rect(panel.x + 14, content_y + i * (card_h + card_gap), card_w, card_h)
            if card_rect.bottom > panel.bottom - 14:
                # 面板放不下更多張的保險判斷：ORDER_CONFIG 目前一天最多
                # 生成 3 張，正常情況下這裡永遠不會被觸發，寫出來只是
                # 避免萬一以後把 MAX_ORDERS_PER_DAY 調大時畫出面板外。
                break
            draw_wood_panel(self.screen, card_rect, self.loader, "ui_wood_panel",
                             C_PARCHMENT, border_radius=10, depth=2)

            # 左側：逐項需求，跟 self.game.crop_inventory（未來也可能含
            # self.game.inventory 的原料）比對目前持有量，滿足畫綠色、
            # 不滿足畫紅色。pygame 沒有內建的多色 inline 文字，這裡手動
            # 逐段畫、每段畫完用回傳的 Rect.right 往右累加下一段的 x。
            seg_x = card_rect.x + 16
            seg_y = card_rect.y + 14
            label_surf = FONT_SM.render("需求：", True, C_TEXT_ON_LIGHT)
            self.screen.blit(label_surf, (seg_x, seg_y))
            seg_x += label_surf.get_width() + 4
            for alias, need_qty in order.requirements.items():
                crop_type = ORDER_CROP_ALIASES.get(alias)
                display_name = CROP_DATA[crop_type]["name"] if crop_type else alias
                have_qty = self.game.crop_inventory.get(alias, self.game.inventory.get(alias, 0))
                met = have_qty >= need_qty
                seg_text = f"{display_name} {have_qty}/{need_qty}   "
                seg_color = C_GREEN if met else C_LOCK_TEXT_RED
                seg_r = blit_text_with_shadow(self.screen, FONT_SM, seg_text, seg_color,
                                               topleft=(seg_x, seg_y), shadow_color=(235, 228, 222))
                seg_x = seg_r.right + 2

            # 獎勵（金幣 + 科技點數，科技綠跟頭部 HUD 同一個顏色，讓玩家
            # 一眼就能把「這裡的科技點」跟「頭部狀態列的科技點」連起來）。
            reward_surf1 = FONT_SM.render(f"💰 {order.reward_gold} 金幣", True, (150, 108, 20))
            self.screen.blit(reward_surf1, (card_rect.x + 16, card_rect.y + 48))
            reward_surf2 = FONT_SM.render(f"⚡ {order.reward_tech} 工藝點", True, (0, 140, 80))
            self.screen.blit(reward_surf2, (card_rect.x + 16 + reward_surf1.get_width() + 16, card_rect.y + 48))

            # 交付按鈕：物資不足時仍然可以點（點了會跳紅字錯誤提示，見
            # _handle_mouse_down），但底色刻意調暗一階，讓玩家不用逐項
            # 核對就能大概看出「這張現在還交不了」。
            deliver_rect = pygame.Rect(card_rect.right - 132, card_rect.y + (card_h - 40) // 2, 116, 40)
            can_deliver = all(
                self.game.crop_inventory.get(a, self.game.inventory.get(a, 0)) >= q
                for a, q in order.requirements.items()
            )
            is_hover = deliver_rect.collidepoint(self.mouse_pos)
            btn_base = (90, 122, 74) if can_deliver else (95, 88, 80)
            draw_wood_panel(self.screen, deliver_rect, self.loader, "ui_wood_button", btn_base,
                             border_radius=8, depth=2, pressed=is_hover)
            blit_text_with_shadow(self.screen, FONT_SM, "📦 交付", C_TEXT_ON_DARK, center=deliver_rect.center)

            self._order_deliver_rects.append((order.order_id, deliver_rect))

    def _render_header_banner(self):
        is_day = (self.game.phase == GamePhase.DAY)
        # 【系統修復：UI 元素重疊/文字溢出/導覽列被切斷】高度從 70 加到
        # 76，讓頂部欄位本身、跟正下方緊接的任務橫幅之間多一點呼吸空間
        # （上下留白），不是緊貼著切齊 0px 間距。
        header_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 76)
        # 頂部狀態列的深木頭底色。這一整條是矩形貼齊畫面上緣，沒有圓角，
        # 立體雕刻邊框只在下緣畫一條陰影線，做出「這塊木頭嵌板釘在畫面
        # 頂端」的錯覺，不用整條套 draw_beveled_rect()（那是設計給四邊
        # 都完整可見的獨立色塊用的，貼齊畫面邊緣的長條套上去四個角會很
        # 奇怪）。
        # 【貼圖彈性預留】：以後要換成 assets/ui/wood_panel.png 木紋
        # 貼圖，就是把下面這行 pygame.draw.rect(...) 換成
        # screen.blit(pygame.transform.scale(wood_tex, header_rect.size), (0, 0))。
        pygame.draw.rect(self.screen, C_WOOD_DARK, header_rect)
        pygame.draw.line(self.screen, C_WOOD_BEVEL_DARK, (0, header_rect.bottom - 1), (SCREEN_WIDTH, header_rect.bottom - 1), 2)

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
        # 進度條軌道用「凹陷」的雕刻感：淺色刻痕在下/右、深色刻痕在上/左
        # (pressed=True)，看起來像木頭上挖出來的凹槽，填色的部分再疊上去。
        draw_beveled_rect(self.screen, bar_r, C_WOOD_BEVEL_DARK, border_radius=7, depth=1, pressed=True)
        fill_w = int(bar_r.width * prog)
        fill_col = C_GREEN if is_day else (C_BLOOD_RED if self.game.is_blood_moon else C_CYAN)
        if fill_w > 0:
            pygame.draw.rect(self.screen, fill_col, (bar_r.x, bar_r.y, fill_w, bar_r.height), border_radius=7)
        rem_surf = FONT_XS.render(f"{rem_time:.1f}s", True, C_TEXT_ON_DARK)
        self.screen.blit(rem_surf, (bar_r.right + 8, bar_r.y))

        # 倍速調整面板 [-] 1.0x [+] -- 緊接在倒數計時 "7.1s" 右側，滑鼠
        # 點擊 [-]/[+] 效果跟鍵盤 [ ] 完全一樣（同一顆 self.time_scale，
        # 同樣的 round(...,1) + max/min 夾值邏輯），兩種操作方式並存。
        panel_x = bar_r.right + 8 + rem_surf.get_width() + 14
        btn_size = 20
        btn_y = bar_r.y - 3
        self.btn_speed_down_rect = pygame.Rect(panel_x, btn_y, btn_size, btn_size)

        speed_txt_surf = FONT_SM.render(f"{self.time_scale:.1f}x", True, C_TEXT_ON_DARK)
        speed_box_w = speed_txt_surf.get_width() + 12
        speed_box_rect = pygame.Rect(self.btn_speed_down_rect.right + 4, btn_y, speed_box_w, btn_size)

        self.btn_speed_up_rect = pygame.Rect(speed_box_rect.right + 4, btn_y, btn_size, btn_size)

        def _draw_speed_btn(rect, label):
            hovered = rect.collidepoint(self.mouse_pos)
            # 按鈕平常是凸起的木牌，滑鼠按著/懸停時看起來像壓下去
            # (pressed=True 對調高光/陰影)，給出清楚的「有反應」回饋。
            btn_col = (130, 96, 82) if hovered else C_WOOD_MID
            draw_beveled_rect(self.screen, rect, btn_col, border_radius=5, depth=1, pressed=hovered)
            lbl_surf = FONT_SM.render(label, True, C_TEXT_ON_DARK)
            self.screen.blit(lbl_surf, lbl_surf.get_rect(center=rect.center))

        _draw_speed_btn(self.btn_speed_down_rect, "-")
        draw_beveled_rect(self.screen, speed_box_rect, C_WOOD_BEVEL_DARK, border_radius=5, depth=1, pressed=True)
        self.screen.blit(speed_txt_surf, speed_txt_surf.get_rect(center=speed_box_rect.center))
        _draw_speed_btn(self.btn_speed_up_rect, "+")

        # 金幣卡 / 科技點數卡 / 等級卡 (原本從 x=430 開始，讓給左邊新增的
        # 倍速面板一些空間，之後又為了新增「📋 訂單」按鈕，把這三張卡
        # 一起再瘦身、右邊界從 1204 再往左讓出 48px（40px 按鈕 + 8px
        # 間距）給訂單按鈕，整組右緣維持在選單按鈕左側 [x=1204] 前留
        # 8px 間距。三張卡的實際文字內容都用 assets/fonts 裡那套精簡
        # 字型實測過寬度，確認在新寬度下不會被裁切——量測方式與數字見
        # commit message，這裡不重覆貼落落長的計算過程。)
        # 【貼圖彈性預留】：這幾張狀態列小面板如果之後想換成 assets/ui/
        # 裡的木牌貼圖，就是把 draw_beveled_rect() 這行換成
        # screen.blit(貼圖, rect.topleft)，見 draw_beveled_rect() 的
        # docstring 有完整範例寫法。
        # 【系統修復：UI 元素重疊/文字溢出/導覽列被切斷】金幣卡/科技點數
        # 卡各縮 15px（155→140、145→130），把讓出來的 30px 全部挪給常常
        # 溢出的莊園等級卡；等級卡右邊界不再寫死 287 這個固定寬度，改成
        # 「動態算到訂單按鈕左側」，這樣不管以後訂單按鈕或選單按鈕的位置
        # 再怎麼調整，等級卡都保證有正確的可用寬度，不會又被寫死的數字
        # 卡死、擠壓到後面的進度條/文字。
        gold_rect = pygame.Rect(545, 12, 140, 44)
        draw_beveled_rect(self.screen, gold_rect, C_WOOD_MID, border_radius=10)
        pygame.draw.circle(self.screen, C_GOLD, (gold_rect.x + 22, gold_rect.centery), 12)
        self.screen.blit(FONT_SM.render("G", True, (60, 40, 0)), (gold_rect.x + 17, gold_rect.centery - 8))
        self.screen.blit(FONT_LG.render(f"{self.game.gold} 金幣", True, C_GOLD), (gold_rect.x + 44, gold_rect.centery - 11))

        # 科技點數卡：新的終局進度貨幣，用螢光科技綠 (C_TECH_GREEN) 跟
        # 金幣的暖金色系拉開差距，一眼就能分辨這是不同的資源。
        tech_rect = pygame.Rect(gold_rect.right + 8, 12, 130, 44)
        draw_beveled_rect(self.screen, tech_rect, C_WOOD_MID, border_radius=10)
        self.screen.blit(
            FONT_SM.render(f"⚡ 工藝點數: {self.game.tech_points}", True, C_TECH_GREEN),
            (tech_rect.x + 10, tech_rect.centery - 8)
        )

        lvl_rect_x = tech_rect.right + 8
        lvl_rect_right_limit = self._order_board_button_rect().x - 8
        lvl_rect = pygame.Rect(lvl_rect_x, 12, max(200, lvl_rect_right_limit - lvl_rect_x), 44)
        draw_beveled_rect(self.screen, lvl_rect, C_WOOD_MID, border_radius=10)
        lvl_name = FARM_LEVELS[self.game.farm_level]["name"]
        # 字級從 FONT_MD (18px) 降成 FONT_SM (15px)：等級名稱長度會隨玩家
        # 進度變動（"初級農莊"~"傳奇仙境" 都是 4 個中文字，但不同名稱的
        # 實際像素寬度仍有差異），縮小字級加上前面新加的動態寬度，雙重
        # 保證「莊園等級：Lv.X」這行文字不會頂到卡片邊緣。
        self.screen.blit(FONT_SM.render(f"🏆 莊園等級: Lv.{self.game.farm_level} ({lvl_name})", True, C_TEXT_ON_DARK), (lvl_rect.x + 14, lvl_rect.y + 6))

        goals = {1: 40, 2: 100, 3: 200, 4: 350, 5: 500}
        next_goal = goals.get(self.game.farm_level, 500)
        curr_p = self.game.prosperity_score
        p_ratio = min(1.0, curr_p / next_goal)

        # 進度條寬度改成跟著 lvl_rect 的實際寬度走（原本寫死 131px，是
        # 當初卡片只有 287px 寬時量出來的數字，卡片變寬之後繼續沿用舊
        # 數字沒有意義）：保留卡片左右各 14px 內距，右側再預留約 100px
        # 給「繁榮度: NNN / NNN」文字跟 12px 間距，算出來的寬度上限用
        # 131px 打底，卡片變寬時進度條會跟著等比變寬，不會出現「卡片明明
        # 變寬了、進度條卻還是舊尺寸擠在角落」的不協調感，右側文字也保證
        # 落在卡片範圍內、不再需要靠肉眼量測賭運氣。
        p_bar_w = max(131, lvl_rect.width - 14 - 14 - 100)
        p_bar = pygame.Rect(lvl_rect.x + 14, lvl_rect.y + 24, p_bar_w, 12)
        draw_beveled_rect(self.screen, p_bar, C_WOOD_BEVEL_DARK, border_radius=6, depth=1, pressed=True)
        if p_ratio > 0:
            # 原本是鮮豔的紫色，跟木質風格不搭；改用翠綠色，呼應「繁榮/
            # 生長」的意象，背景凹槽 (C_WOOD_BEVEL_DARK) 維持深色不變。
            pygame.draw.rect(self.screen, C_GREEN, (p_bar.x, p_bar.y, int(p_bar.width * p_ratio), p_bar.height), border_radius=6)
        self.screen.blit(FONT_SM.render(f"繁榮度: {curr_p} / {next_goal}", True, C_CYAN), (p_bar.right + 12, p_bar.y - 3))

        # 右上角選單按鈕（☰）：特意畫在 header 方法的最後面，確保一定疊在
        # 上方所有面板（金幣卡、莊園等級面板...）之上，不會被蓋住。
        menu_btn_rect = pygame.Rect(SCREEN_WIDTH - 56, 15, 40, 40)
        is_menu_hover = menu_btn_rect.collidepoint(self.mouse_pos)
        draw_beveled_rect(self.screen, menu_btn_rect, (130, 96, 82) if is_menu_hover else C_WOOD_MID,
                           border_radius=8, pressed=is_menu_hover)
        for i in range(3):
            line_y = menu_btn_rect.y + 11 + i * 9
            pygame.draw.line(self.screen, C_TEXT_ON_DARK, (menu_btn_rect.x + 8, line_y), (menu_btn_rect.x + 32, line_y), 3)

        # 「📋 查看訂單」按鈕：緊貼在選單按鈕左側（座標見
        # _order_board_button_rect()，畫這裡跟點擊判定共用同一份座標）。
        # 目前有未交付訂單時，按鈕外框改用科技綠高亮描邊，提醒玩家「有
        # 訂單可以交」，避免玩家忘了這個系統存在。
        order_btn_rect = self._order_board_button_rect()
        is_order_hover = order_btn_rect.collidepoint(self.mouse_pos)
        order_btn_active = self.show_order_board
        draw_beveled_rect(
            self.screen, order_btn_rect,
            (130, 96, 82) if (is_order_hover or order_btn_active) else C_WOOD_MID,
            border_radius=8, pressed=(is_order_hover or order_btn_active)
        )
        has_orders = len(self.game.active_orders) > 0
        if has_orders and not order_btn_active:
            pygame.draw.rect(self.screen, C_TECH_GREEN, order_btn_rect, width=2, border_radius=8)
        icon_surf = FONT_MD.render("📋", True, C_TEXT_ON_DARK)
        self.screen.blit(icon_surf, icon_surf.get_rect(center=order_btn_rect.center))

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
                    img = None
                    if df == DefenseType.WOODEN_FENCE and self.loader.fence_tiles:
                        # 柵欄自動連接 (Auto-tiling)：檢查上/右/下/左四個
                        # 相鄰格是否也是圍籬，算出 4-bit bitmask
                        # (上=1, 右=2, 下=4, 左=8)，換成對應的連接畫格。
                        # get_tile() 對超出邊界的座標會回傳 None，天然當作
                        #「該方向沒有圍籬」處理，不用另外判斷邊界。
                        def _is_fence(nx, ny):
                            ntile = self.game.get_tile(nx, ny)
                            return bool(ntile and ntile.defense and ntile.defense.defense_type == DefenseType.WOODEN_FENCE)

                        mask = (
                            (1 if _is_fence(x, y - 1) else 0) +
                            (2 if _is_fence(x + 1, y) else 0) +
                            (4 if _is_fence(x, y + 1) else 0) +
                            (8 if _is_fence(x - 1, y) else 0)
                        )
                        img = self.loader.fence_tiles.get(mask)

                    if img is None:
                        # Fences.png 還沒放進 assets/、切圖失敗，或這格不是
                        # 圍籬時，退回原本的單一靜態圖片，不會讓遊戲壞掉。
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

                    if ct == CropType.IRON_FLOWER:
                        # 【系統修復與視覺升級】富鐵花改用 1x4 Sprite
                        # Sheet 切出來的 4 幀動畫（asset_loader.py 的
                        # get_anim_frames("iron_flower")），不是其餘作物
                        # 共用的「{asset_key}_{stage}」離散 per-stage
                        # 查表。這裡用法跟需求裡寫的 `_render_crops` 不
                        # 一樣——這個專案沒有獨立的 _render_crops() 方
                        # 法，作物渲染本來就是這個逐格迴圈裡的
                        # `if tile.crop:` 區塊，這裡直接在原地加特例分
                        # 支，不新建一個方法。
                        #
                        # 挑幀依連續成長比例（不是離散 stage 列舉），跟
                        # 下面成長進度條用的是同一個 ratio 算法
                        # （growth_timer / grow_time），只是這裡額外拿來
                        # 決定要畫哪一幀：
                        #   ratio < 0.33        -> frame[0]（幼苗）
                        #   0.33 <= ratio < 1.0 -> frame[1]（生長中）
                        #   ratio >= 1.0（成熟）-> frame[2]（帶鐵礦）
                        # frame[3]（需求裡標「可選」的「剛採收的枯枝」）
                        # 這次刻意不用：harvest_crop() 採收成功後會立刻
                        # 把 tile.crop 設回 None（demolish_tile()/敵人偷
                        # 竊破壞作物也是同樣做法），資料模型裡沒有任何
                        # 「已採收但還殘留在格子上」的過渡狀態可以掛
                        # frame[3]，勉強生出一個假的殘留計時器已經超出
                        # 這次請求的範圍，先如實留白，不假裝支援一個不
                        # 存在的狀態。
                        iron_frames = self.loader.get_anim_frames("iron_flower")
                        ratio = 1.0 if tile.crop.is_mature else min(1.0, tile.crop.growth_timer / tile.crop.grow_time)
                        if ratio >= 1.0:
                            frame_idx = 2
                        elif ratio >= 0.33:
                            frame_idx = 1
                        else:
                            frame_idx = 0
                        img = iron_frames[frame_idx] if iron_frames else None
                    else:
                        base_key = CROP_DATA[ct].get("asset_key", "radish")
                        st_key = tile.crop.stage.name.lower()
                        img = self.loader.get(f"{base_key}_{st_key}")

                    if img:
                        # 作物圖片現在是等比例縮放的（asset_loader.py 的
                        # _scale_keep_aspect），長條形作物（如胡蘿蔔）的
                        # Surface 寬度等於 CELL_SIZE，但高度可能比格子高。
                        # 用「底部中心 (midbottom)」對齊格子底部，讓比較
                        # 高的作物自然往上延伸，不會歪一邊或超出格子下方。
                        img_rect = img.get_rect(midbottom=(px + CELL_SIZE // 2, py + CELL_SIZE))
                        self.screen.blit(img, img_rect)

                    # Phase 4 bug fix：這一整塊（月光加成光點/成熟金色高
                    # 光/成長進度條）原本被誤縮排在下面 `if tile.building:`
                    # 區塊裡面——但 tile.crop 跟 tile.building 是互斥的
                    # (Tile.is_empty 的定義)，同一格不可能兩者同時存在，
                    # 代表這整塊「只要格子上是作物就一定不是建築」的程式
                    # 碼實質上永遠不會被執行到，這就是「成熟進度條消失」
                    # 的真正原因。移到這裡、掛在 `if tile.crop:` 底下才是
                    # 正確位置，且確保這是這個格子最後畫的東西（在作物
                    # 圖片本體之後），Z 軸順序上一定畫在最上層，不會被
                    # 土地或其他格子物件的判定框蓋掉。
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

                # 加工機台 (Phase 2)：需求裡提到可以畫在 _render_defenses
                # 或新建的 _render_buildings，但這個專案裡防禦設施/景觀/
                # 作物其實都是同一個逐格迴圈裡畫的（沒有獨立的
                # _render_defenses 方法），這裡沿用同一個既有寫法、加在
                # 同一個迴圈裡，而不是另外拆一個獨立的渲染 pass，跟其餘
                # 格子物件的繪製順序/風格保持一致。
                # 系統大重構 Phase 7：2x2 建築（FURNACE/LUMBERYARD）的
                # 佔地格全部指向同一個 Building 物件（見 game_state.py
                # place_building()），這個逐格迴圈原本一格就畫一次，
                # 2x2 建築沒特別處理的話會被畫 4 次、每次都各自用自己
                # 那一格的 px/py 當錨點，疊出 4 張互相錯位重疊的貼圖。
                # 加上 (x, y) == (tile.building.x, tile.building.y) 這個
                # 條件，只有掃到「建築的左上角錨點格」那一格才真正呼叫
                # _render_building_tile()，確保不管建築是 1x1 還是 2x2
                # 都只畫一次；_render_building_tile() 內部再自己用
                # BUILDING_DATA 的 size 算出完整 2x2 範圍置中繪製（見
                # 該方法內的說明），這裡不用預先算 span。
                if tile.building and (x, y) == (tile.building.x, tile.building.y):
                    self._render_building_tile(tile.building, px, py)

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
            hx = GRID_X + gx * CELL_SIZE
            hy = GRID_Y + gy * CELL_SIZE
            cx = hx + CELL_SIZE // 2
            cy = hy + CELL_SIZE // 2

            # UI 視覺優化（修正 2x2 建造預覽）：選中的是 FURNACE/
            # LUMBERYARD 這種 2x2 建築時，_selected_building_footprint()
            # 回傳 (2, 2)，預覽框的寬高要跟著放大成兩倍格子大小
            # （例如 CELL_SIZE=32 時變成 64x64），才能精準覆蓋住實際會
            # 被佔用的四個格子；非建築動作（種作物/景觀/防禦/工具）一律
            # 回傳 (1, 1)，預覽框維持原本的單格大小，行為完全不變。
            # hovered_grid 記的 (gx, gy) 本來就是滑鼠所在格，同時也是
            # place_building() 展開 footprint 時採用的左上角錨點座標，
            # 兩邊的座標定義是一致的，預覽框跟實際佔地範圍不會對不齊。
            size_w, size_h = self._selected_building_footprint()
            preview_w = size_w * CELL_SIZE
            preview_h = size_h * CELL_SIZE

            # 網格瞄準高光：淺白色半透明填色 + 亮白邊框；如果目前選中的
            # 工具放在這一格（或 2x2 建築的整個佔地範圍）「大致上」會
            # 失敗（例如在莊園景觀區選種子、或 2x2 建築的其中一格已被
            # 佔用），動態變成淺紅色，點擊前就先給玩家提示，不用等點
            # 下去失敗才看到 FloatingText。
            is_invalid = self._grid_preview_is_invalid(gx, gy)
            fill_col = (255, 90, 90, 90) if is_invalid else (255, 255, 255, 90)
            border_col = (255, 120, 120) if is_invalid else (255, 255, 255)
            highlight_s = pygame.Surface((preview_w, preview_h), pygame.SRCALPHA)
            pygame.draw.rect(highlight_s, fill_col, highlight_s.get_rect(), border_radius=4)
            pygame.draw.rect(highlight_s, border_col, highlight_s.get_rect(), width=2, border_radius=4)
            self.screen.blit(highlight_s, (hx, hy))

            # 防禦設施範圍預覽：目前選中的工具若有對應的警戒/攻擊範圍
            # (稻草人的 scare_radius、蜂巢的 attack_range)，以懸停格為
            # 圓心畫一個半透明淺藍色光圈，讓玩家下手前就能看到涵蓋範圍。
            range_val = self._DEFENSE_ACTION_RANGE.get(self.selected_action)
            if range_val:
                radius_px = int(range_val * CELL_SIZE)
                if radius_px > 0:
                    range_s = pygame.Surface((radius_px * 2, radius_px * 2), pygame.SRCALPHA)
                    pygame.draw.circle(range_s, (135, 206, 250, 60), (radius_px, radius_px), radius_px)
                    pygame.draw.circle(range_s, (135, 206, 250, 170), (radius_px, radius_px), radius_px, width=2)
                    self.screen.blit(range_s, (cx - radius_px, cy - radius_px))

        # 【UI 佈局修復】原本這裡是「即時情境【柴犬教官】動態新手對話
        # 框」，畫在 GRID_Y - 28（y=58~84），跟新版飛船 AI 任務橫幅
        # (_render_mission_ui()，畫在 y=70 起) 高度重疊、文字互相遮擋，
        # 已整段移除，改由飛船 AI 任務橫幅統一負責常駐引導提示，不再
        # 保留兩套並存的引導系統。


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

    # 機台圖示文字對照表：Phase 4.75 為了迴避舊字型
    # NotoSansTC-GameSubset.otf（裁切過的子集字型）缺字，把這裡全部改
    # 成單一「字型驗證過真的有字形」的安全字元，犧牲了辨識度。技術債
    # 清理階段換成完整字庫的 Cubic_11.ttf 之後，缺字限制理論上已經解
    # 除，這裡照使用者要求復原成更完整、更好辨識的詞彙：
    #   LUMBERYARD (伐木場)     木  -> 伐木
    #   MINE       (礦場)       鐵  -> 採礦
    #   KILN       (炭窯)       火  -> 燒炭
    #   OVEN       (烤箱)       熟  -> 烘烤
    #   FURNACE    (熔爐)       鋼  -> 熔煉
    #
    # SPRINKLER/AUTO_HARVESTER 這兩個使用者給的是「Emoji 或更完整中文
    # 名稱擇一」的彈性指示，這裡選擇中文詞彙（灑水/採收）而不是照
    # Phase 4 原樣復原成 💧/🤖 這兩個 emoji，原因是：這次換的
    # Cubic_11.ttf 是點陣風格的「中文」字型，這類字型通常只收錄中文/
    # 標點/基本符號的字形，不太會內建全彩 Emoji 字形（那通常是作業系統
    # 層級的 Emoji 字型負責的範疇，不是一般中文字型檔會做的事）；而且
    # 目前綁定字型的實際檔案還沒放進這個環境，沒辦法用 fontTools 驗證
    # Emoji 字形是否存在。與其賭一把「這次真的復原回去可能又變回豆腐
    # 塊」，不如選擇肯定落在完整繁體中文字型收錄範圍內的中文詞彙，跟
    # 其餘 5 種機台的呈現風格也保持一致。如果之後確認新字型真的支援
    # Emoji，要改回 💧/🤖 只要動這個字典即可。
    # 視覺升級（熔爐動畫）階段：使用者要求整批移除 OVEN（烤箱）跟
    # KILN（炭窯），這裡同步拿掉這兩個 key，避免字典裡留著已經不存在的
    # BuildingType 成員。這個字典目前只在 _render_building_tile() 貼圖
    # 缺失時的色塊+文字圖示防呆分支用得到——熔爐本身已經有真的
    # Sprite Sheet 動畫可以用，不會走到這裡，但保留 FURNACE 這一筆是
    # 為了萬一動畫幀載入失敗（例如 熔爐.png 被移除）時還能有安全字元
    # 可以退回，不會直接壞掉。
    # 系統大重構 Phase 7：BuildingType.MINE 已從 game_config.py 整批移除
    # （被 CropType.IRON_FLOWER 取代），這裡同步拿掉 "採礦" 這一筆，避免
    # 字典裡留著已經不存在的 BuildingType 成員（跟 OVEN/KILN 當初移除
    # 時的處理方式一致）。
    _BUILDING_ICONS = {
        BuildingType.FURNACE: "熔煉",
        BuildingType.SPRINKLER: "灑水",
        BuildingType.AUTO_HARVESTER: "採收",
        BuildingType.LUMBERYARD: "伐木",
    }

    def _render_building_tile(self, building, px: int, py: int):
        """畫一座機台。Phase 2/3 的烤箱/熔爐走「開關-配方-倒數」那套，
        右上角有明確的 ON/OFF 指示燈跟運作進度條；Phase 4 新增的自動
        採收機是 building.is_passive 為 True 的「蓋下去就永久生效」
        機台，完全沒有開關狀態，畫 ON/OFF 圓點反而會誤導玩家以為它也
        需要手動開啟，所以這裡改成一個穩定不閃爍的淡科技綠外框，代表
        「持續生效中」，跟可切換機台的圓點指示燈明確做出視覺區分。
        【系統更新：自動灑水器 2x2 建築邏輯】灑水器（SPRINKLER）這次
        不再屬於這一類——is_passive 現在只有 AUTO_HARVESTER 是 True，
        灑水器改成跟熔爐/伐木場一樣的開關式機台，會畫 ON/OFF 指示燈，
        不會畫這圈綠外框。
        視覺升級（動態佔位圖系統）之後，asset_loader 已經會為這幾個
        asset_key 呼叫 _load_image()，就算 assets/buildings/ 底下還沒
        有真的放對應 PNG（目前確實還沒有），也會經由
        AssetLoader.generate_placeholder() 產生一張有底色/特徵區分的
        動態佔位 Surface（機台類深灰底+橘紅火焰、伐木場棕色底+木紋），
        而不是回傳 None——所以這裡的 `if img:` 分支現在一定會成立，
        下面 else 分支手畫的木箱色塊 + 圖示文字目前實質上變成不會被走
        到的防禦性後備（保留著是因為萬一未來 asset_key 命名調整、或
        AssetLoader 那邊的載入呼叫被移除，這裡還是能安全地退回一個能
        看的樣子，不會直接壞掉）。等以後真的放上手繪 PNG 貼圖，
        loader.get() 一樣會自動抓到真圖，不用改這裡的任何邏輯（跟專案
        其他地方的貼圖後備模式一致）。ON/OFF 指示燈、運作進度條、被動
        機台的淡綠外框都畫在圖片之上，不受這次改動影響。
        """
        config = building.config
        asset_key = config.get("asset_key")
        img = self.loader.get(asset_key) if asset_key else None

        # 系統大重構 Phase 7：2x2 多格子建築。size 預設 (1, 1)，1x1 機台
        # （SPRINKLER/AUTO_HARVESTER 等）算出來 span_w == span_h ==
        # CELL_SIZE，跟改動前完全等價；FURNACE/LUMBERYARD 現在是
        # size=(2, 2)，span_w/span_h 變成 2*CELL_SIZE，下面所有原本寫死
        # CELL_SIZE 的定位運算（貼圖置中點、色塊防呆矩形、ON/OFF 指示
        # 燈座標、進度條寬度）改吃這兩個變數，貼圖/圓點/進度條就會一起
        # 隨著建築佔地格數放大、並置中對齊在整個 2x2 範圍的正中央，而
        # 不是只對齊左上角那一格。
        size_w, size_h = config.get("size", (1, 1))
        span_w = size_w * CELL_SIZE
        span_h = size_h * CELL_SIZE

        # 視覺升級：Sprite Sheet 特定影格動畫（熔爐/伐木場共用同一套
        # 播放邏輯）。asset_key 對應到有提取好動畫幀的機台時，優先用
        # 動畫幀取代單張靜態貼圖；沒有動畫幀（get_anim_frames 回傳空
        # list，例如貼圖缺檔或載入失敗）時，anim_frames 是 falsy，直接
        # 落到下面既有的 img/色塊防呆邏輯，不受影響。
        anim_frames = self.loader.get_anim_frames(asset_key) if asset_key else []
        if anim_frames:
            # 「開啟/運作中」該看哪個旗標，兩種機台的需求文字給的定義不
            # 一樣：熔爐當初明確要求看 is_processing（這一輪配方是否正在
            # 倒數，避免兩輪配方交接的空檔誤判成「關閉」而閃爍）；伐木場
            # 這次明確要求看 is_active（開關本身的狀態）。伐木場是
            # LUMBERYARD/MINE 那種空配方永動機，is_active 打開之後
            # is_processing 幾乎全程都是 True（只有极短的一幀交接空
            # 檔），兩者在這座機台身上實質差異很小，但既然使用者這次明
            # 確指定 is_active，就照literal 需求实作，不假設兩種機台
            # 應該共用同一個判斷欄位。
            is_running = building.is_processing if building.building_type == BuildingType.FURNACE else building.is_active
            if not is_running:
                # 關閉/閒置一律固定顯示 frame[0]，熔爐/伐木場共用同一條
                # 規則不變。
                frame_index = 0
            elif building.building_type == BuildingType.LUMBERYARD:
                # 【系統修復與視覺升級】伐木場換成 1x4 素材後，這次使用
                # 者明確要求改成「0/2 幀跳動」——不是像上一版那樣跑滿
                # frame[0]~frame[-1] 全部影格，也不是熔爐那種
                # frame[1]~frame[-1] 循環，而是運作中只在 frame[0] 跟
                # frame[2] 兩張之間切換，營造更猛烈的「機械打擊感」（兩張
                # 差異較大的影格快速交替，比連續多幀漸變動畫更有「一拍一
                # 下」的重擊視覺效果）。frame[1]/frame[3] 在運作中完全不
                # 會被畫到；frame[1] 只是伐木場 1x4 素材裡的過渡幀，
                # frame[3] 目前沒有對應用途（見下方富鐵花 frame[3] 的
                # 說明——兩張素材雖然規格一致，但用途不需要對稱）。
                # 使用者提供的參考公式寫的是 self.animation_timer，這個
                # 屬性在專案裡不存在（沿用先前已經確認過的
                # self.anim_time，run() 主迴圈每幀累加、不受暫停/日夜切
                # 換影響），這裡照專案實際的計時器名稱寫。
                step = int(self.anim_time / ANIMATION_SPEED) % 2
                frame_index = 2 if step == 1 else 0
            elif building.building_type == BuildingType.SPRINKLER:
                # 【系統更新：自動灑水器 2x2 建築邏輯】需求文字明確要求
                # 「若 is_active 為 True，則依序播放這 4 個影格」——不是
                # 像熔爐那樣把 frame[0] 保留給關閉態、運作中只在
                # frame[1]~最後一幀之間循環，而是單純 0→1→2→3→0... 完整
                # 跑滿全部 4 幀，所以另外開一個分支，不共用下面熔爐那條
                # 通用 else 規則。
                frame_index = int(self.anim_time / ANIMATION_SPEED) % len(anim_frames)
            else:
                # frame[0] 保留給「關閉/閒置」狀態，運作中的時候在
                # frame[1] ~ frame[len-1] 之間循環（熔爐只有 3 幀，等於
                # 在 frame[1]/frame[2] 兩幀來回切換）。用 len(anim_frames) - 1
                # 算模數，這裡沿用專案裡已經存在、每一幀都會無條件累加
                # 的 self.anim_time（run() 主迴圈裡 `self.anim_time += dt`，
                # 不受暫停/日夜切換影響），而不是另外新增一個
                # self.animation_timer——兩者效果完全一樣，但重用既有
                # 計時器可以避免專案裡多出一個語意重複的計時器變數。
                cycle_len = max(1, len(anim_frames) - 1)
                frame_index = 1 + int(self.anim_time / ANIMATION_SPEED) % cycle_len
            frame_img = anim_frames[frame_index]
            img_rect = frame_img.get_rect(midbottom=(px + span_w // 2, py + span_h))
            self.screen.blit(frame_img, img_rect)
        elif img:
            img_rect = img.get_rect(midbottom=(px + span_w // 2, py + span_h))
            self.screen.blit(img, img_rect)
        else:
            # 貼圖缺失後備：木箱色塊 + 機台圖示文字。開關式機台 (烤箱/
            # 熔爐) 的明暗看 is_active——一座「開啟中」的機台在兩輪配方
            # 之間會有短暫一幀 is_processing=False（剛收完、還沒開始下
            # 一輪），如果明暗跟著 is_processing 走，畫面會在這一幀閃一
            # 下「變亮」再馬上變暗，看起來像故障；改用 is_active 判斷就
            # 只有玩家真的關閉開關時才會變暗。被動機台 (灑水器/自動採收
            # 機) 沒有 is_active 這個概念，永遠用「開啟」的亮色調。
            body_rect = pygame.Rect(px + 6, py + 10, span_w - 12, span_h - 16)
            if building.is_passive:
                base_col = (94, 66, 50)
            else:
                base_col = (94, 66, 50) if building.is_active else (55, 48, 44)
            draw_beveled_rect(self.screen, body_rect, base_col, border_radius=6, depth=2,
                               pressed=building.is_processing)
            icon = self._BUILDING_ICONS.get(building.building_type, "🏭")
            icon_surf = FONT_MD.render(icon, True, C_TEXT_ON_DARK)
            self.screen.blit(icon_surf, icon_surf.get_rect(center=body_rect.center))

        if building.is_passive:
            # 被動永久生效：一圈穩定的淡科技綠外框，不閃爍、不需要玩家
            # 操作，跟下面「開關式機台」的圓點指示燈明確區分開，避免
            # 誤以為這種機台也有 ON/OFF 兩態。
            body_rect = pygame.Rect(px + 6, py + 10, span_w - 12, span_h - 16)
            pygame.draw.rect(self.screen, (90, 200, 150), body_rect, width=2, border_radius=6)
            return

        # ON/OFF 指示燈（只有開關式機台才有）：機台右上角一個小圓點，
        # 開=科技綠、關=暗紅，開啟時再疊一圈淡淡的光暈表示「自動運作中」。
        # 座標改用 span_w 對齊到整個 2x2 範圍的右上角，而不是固定停在
        # 左上角那一格的右上角（1x1 建築 span_w == CELL_SIZE，位置不變）。
        dot_center = (px + span_w - 12, py + 10)
        if building.is_active:
            pygame.draw.circle(self.screen, (30, 60, 40), dot_center, 7)
            glow_r = 6 + int(math.sin(self.anim_time * 5.0) * 1.5)
            pygame.draw.circle(self.screen, C_TECH_GREEN, dot_center, max(3, glow_r))
        else:
            pygame.draw.circle(self.screen, (40, 20, 18), dot_center, 7)
            pygame.draw.circle(self.screen, (200, 70, 60), dot_center, 5)

        # 運作中：機台上方畫一條小小的進度條，這是「運作動畫」的主要
        # 呈現方式，跟 Phase 2 一樣保留。
        if building.is_processing:
            total = float(config["process_time"])
            ratio = 0.0 if total <= 0 else max(0.0, min(1.0, 1.0 - building.processing_time_left / total))
            bar_w = span_w - 16
            bar_rect = pygame.Rect(px + 8, py + 2, bar_w, 6)
            draw_beveled_rect(self.screen, bar_rect, C_WOOD_BEVEL_DARK, border_radius=3, depth=1, pressed=True)
            if ratio > 0:
                pygame.draw.rect(self.screen, C_TECH_GREEN, (bar_rect.x, bar_rect.y, int(bar_w * ratio), bar_rect.height), border_radius=3)

    def _render_entities(self):
        if self.game.guard_dog:
            dog = self.game.guard_dog
            px = int(GRID_X + dog.x * CELL_SIZE)
            py = int(GRID_Y + dog.y * CELL_SIZE)
            # 白天狗不用出去咬人，改播坐姿待機動畫；晚上依
            # facing_direction 選方向、每 200ms 換下一幀播放走路動畫，
            # 跟野豬/血月首領共用同一套播放邏輯。guard_dog_walk.png 還沒
            # 放進 assets/characters/ 或切圖失敗時兩組動畫都是空的，
            # 自動退回原本的靜態 guard_dog 圖，不會壞掉。
            if self.game.phase == GamePhase.DAY:
                frames = self.loader.dog_sit_frames
            else:
                frames = self.loader.dog_walk_frames.get(dog.facing_direction, [])
            if frames:
                frame_index = (pygame.time.get_ticks() // 200) % len(frames)
                img = frames[frame_index]
            else:
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
    def _order_board_button_rect(self) -> pygame.Rect:
        """頭部狀態列上「📋 查看訂單」按鈕的固定座標。刻意獨立成方法而
        不是寫死在單一處，因為 _render_header_banner()（畫按鈕）跟
        _handle_mouse_down()（判斷點到沒）兩處都要用同一組座標，寫成
        方法保證兩邊永遠一致，不會有畫的位置跟點擊判定對不上的風險
        ——跟既有的 _shop_panel_rect() 是同一種寫法。
        緊貼在右上角「☰」選單按鈕 (x=SCREEN_WIDTH-56=1204) 左側，中間
        留 8px 間距。"""
        menu_btn_x = SCREEN_WIDTH - 56
        return pygame.Rect(menu_btn_x - 8 - 40, 15, 40, 40)

    def _order_board_rect(self) -> pygame.Rect:
        w, h = 860, 560
        x = (SCREEN_WIDTH - w) // 2
        y = (SCREEN_HEIGHT - h) // 2
        return pygame.Rect(x, y, w, h)

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

        # 商店大底框：深木頭色，立體雕刻邊框讓整塊面板像是嵌在畫面右側的
        # 木箱子，而不是一片貼上去的平面色塊。
        # 【貼圖彈性預留】：以後要用 assets/ui/wood_panel.png 這種木紋
        # 貼圖取代這片純色深木背景，改法是在下面這行 draw_beveled_rect(...)
        # 前面插入類似：
        #     wood_tex = self.loader.get("ui_wood_panel_large")
        #     if wood_tex:
        #         self.screen.blit(pygame.transform.smoothscale(wood_tex, panel.size), panel.topleft)
        #     else:
        #         draw_beveled_rect(self.screen, panel, C_WOOD_DARK, border_radius=14, depth=3)
        # 貼圖版一樣可以保留 draw_beveled_rect() 疊加的高光/陰影刻痕，
        # 讓平面貼圖也有立體感，不用整個重畫。
        draw_beveled_rect(self.screen, panel, C_WOOD_DARK, border_radius=14, depth=3)

        # 深色標題橫幅，跟頂部 HUD 同一套配色 (C_WOOD_DARK + C_GOLD)，
        # 讓商店面板一眼就能認出是同一套視覺語言，不是另外貼上去的東西。
        # 這裡疊在剛剛的木頭底框上緣，用更深一階的褐色區隔出「標題區」。
        header_rect = pygame.Rect(panel.x, panel.y, panel.width, 44)
        pygame.draw.rect(self.screen, C_WOOD_BEVEL_DARK, header_rect, border_top_left_radius=14, border_top_right_radius=14)
        title_surf = FONT_MD.render("莊園商店", True, C_GOLD)
        self.screen.blit(title_surf, (header_rect.centerx - title_surf.get_width() // 2, header_rect.centery - title_surf.get_height() // 2))

        # 2x2 分頁格
        tabs = self._layout_shop_tabs()
        self.tab_buttons = tabs
        for tab_id, label, rect in tabs:
            is_active = (self.active_tab == tab_id)
            # 懸停高光：非當前分頁時，滑鼠移上去背景稍微變亮＋邊框變成
            # 該分頁的主題色，讓玩家清楚知道這裡可以點。已經是當前分頁
            # 的話就不用疊加懸停效果，維持原本的「已選中」樣式。
            is_hover = (not is_active) and rect.collidepoint(self.mouse_pos)
            tint = SHOP_TAB_TINTS.get(tab_id, C_ORANGE)
            if is_active:
                bg_col = C_PARCHMENT
            elif is_hover:
                bg_col = (225, 214, 208)
            else:
                bg_col = C_WOOD_MID
            # 分頁格也是木牌質感：目前選中的那格「凸起」表示正在使用，
            # 其餘未選中的維持一般凸起（不用 pressed，選中/未選中的差異
            # 已經靠底色深淺跟邊框顏色表達，不需要再疊一層凹陷語意）。
            draw_beveled_rect(self.screen, rect, bg_col, border_radius=8, depth=1)
            if is_active or is_hover:
                pygame.draw.rect(self.screen, tint, rect, width=2, border_radius=8)
            txt_col = C_TEXT_ON_LIGHT if is_active else (C_TEXT_ON_DARK if not is_hover else C_TEXT_ON_LIGHT)
            t_surf = FONT_XS.render(label, True, txt_col)
            self.screen.blit(t_surf, (rect.centerx - t_surf.get_width() // 2, rect.centery - t_surf.get_height() // 2))

        # 分頁格跟卡片清單之間的分隔線
        area = self._shop_list_area()
        pygame.draw.line(self.screen, C_WOOD_BEVEL_DARK, (area.x, area.y - 8), (area.right, area.y - 8))

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

        # 內容超出可視範圍才畫捲軸滑塊，提示「還能往下滑」。捲軸軌道/
        # 滑塊原本是淺灰色，是設計給白色面板背景用的對比色，現在面板底色
        # 換成深木頭色，改用木頭色系的深淺對比 (軌道用陰影色、滑塊用
        # 米白色) 才看得清楚，不會消失在深色背景裡。
        max_scroll = self._shop_scroll_bounds(len(items))
        if max_scroll > 0:
            track = pygame.Rect(area.right + 4, area.y, 4, area.height)
            pygame.draw.rect(self.screen, C_WOOD_BEVEL_DARK, track, border_radius=2)
            scroll = self.shop_scroll.get(self.active_tab, 0)
            thumb_h = max(24, int(area.height * area.height / (area.height + max_scroll)))
            thumb_y = area.y + int((area.height - thumb_h) * (scroll / max_scroll))
            thumb = pygame.Rect(track.x, thumb_y, 4, thumb_h)
            pygame.draw.rect(self.screen, C_TEXT_ON_DARK, thumb, border_radius=2)

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
        btn_txt = FONT_LG.render("🌾 我瞭解了，開始農莊冒險！", True, C_WHITE)
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

        # 跟暫停選單同一套 draw_wood_panel：沒有真的 wood_panel.png 貼圖時
        # 退回深木色 draw_beveled_rect()，維持跟主畫面一致的木紋風格；
        # 外框改用略帶血紅色調的深木色，暗示「結束/失敗」，但不再是刺眼
        # 的純白底 + 純紅描邊。
        draw_wood_panel(self.screen, modal_rect, self.loader, "ui_wood_panel",
                         (58, 34, 30), border_radius=14, depth=3)
        pygame.draw.rect(self.screen, C_RED, modal_rect, width=3, border_radius=14)

        blit_text_with_shadow(self.screen, FONT_TITLE, "💀 遊戲結束 (GAME OVER)", C_RED,
                               center=(mx + modal_w // 2, my + 38))

        blit_text_with_shadow(self.screen, FONT_MD, "農場資金斷絕，破產淘汰！", C_TEXT_ON_DARK,
                               center=(mx + modal_w // 2, my + 84))

        blit_text_with_shadow(self.screen, FONT_SM, self.game.game_over_reason, C_LOCK_TEXT_RED,
                               center=(mx + modal_w // 2, my + 116))

        blit_text_with_shadow(
            self.screen, FONT_SM,
            f"生存天數: {self.game.day_count} 天 | 最終繁榮度: {self.game.prosperity_score}",
            C_TEXT_ON_DARK, center=(mx + modal_w // 2, my + 150))

        btn_restart = pygame.Rect(mx + (modal_w - 200) // 2, my + 215, 200, 48)
        hovered = btn_restart.collidepoint(self.mouse_pos)
        draw_wood_panel(self.screen, btn_restart, self.loader, "ui_wood_button",
                         (90, 122, 74), border_radius=8, depth=2, pressed=hovered)
        blit_text_with_shadow(self.screen, FONT_MD, "🔄 重新挑戰農場", C_TEXT_ON_DARK,
                               center=btn_restart.center)


if __name__ == "__main__":
    app = NightwatchFarmApp()
    app.run()