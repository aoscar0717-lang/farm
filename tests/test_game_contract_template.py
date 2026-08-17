"""Automated tests for Farm Defense game contracts (T01-T07) - Endless Sandbox Edition."""

from src.capstone_contract import new_game, apply_action, is_terminal, snapshot

def test_t01_fresh_state():
    """T01: 驗證遊戲初始化狀態 (開放世界)"""
    state = new_game(seed=42)
    
    assert state["phase"] == "day"
    assert len(state["crops"]) == 0
    assert len(state["fences"]) == 0
    assert len(state["dogs"]) == 0
    assert state["money"] == 500
    assert state["day_count"] == 1
    assert state["time_left"] == 10
    assert state["status"] == "playing"
    assert not is_terminal(state)


def test_t02_normal_action_build_and_plant():
    """T02: 驗證正常行動 - 開墾農田與放置圍欄"""
    state = new_game(seed=42)
    
    # 測試種植農田
    state = apply_action(state, "plant_crop_100_100")
    assert len(state["crops"]) == 1
    assert state["money"] == 450  # 500 - 50
    
    # 測試放置圍欄
    state = apply_action(state, "build_100_110")
    assert len(state["fences"]) == 1
    assert state["money"] == 350  # 450 - 100


def test_t03_boundary_action_invalid_placement():
    """T03: 驗證邊界行為 - 重疊放置無效"""
    state = new_game(seed=42)
    
    state = apply_action(state, "plant_crop_100_100")
    # 試圖把圍欄蓋在農田上 (完全重疊)
    state = apply_action(state, "build_100_100")
    
    assert len(state["fences"]) == 0, "無效位置不應產生圍欄"
    assert "佔用" in state["last_msg"]


def _run_night(state):
    state = apply_action(state, "start_night")
    while state["phase"] == "night":
        state = apply_action(state, "night_tick")
    return state

def test_t04_survival_success_cycle():
    """T04: 驗證防禦成功 - 農田保留，獲得獎金，天數增加"""
    state = new_game(seed=42)
    state["money"] = 1000
    
    # 在 (100, 100) 種植農田
    state = apply_action(state, "plant_crop_100_100")
    
    # 完美包圍 (農田是 10x10)
    for pos in [(90,90), (100,90), (110,90), (90,110), (100,110), (110,110), (90,100), (110,100)]:
        state = apply_action(state, f"build_{pos[0]}_{pos[1]}")
        
    initial_money = state["money"]
    
    # 進入夜晚結算
    state = _run_night(state)
    
    assert len(state["crops"]) == 1, "防禦成功，農田應該保留"
    assert state["day_count"] == 2, "天數應該推進到第 2 天"
    assert state["money"] == initial_money + 200, "防禦成功應該獲得 200 獎金"
    assert state["status"] == "playing"


def test_t05_survival_failure_cycle():
    """T05: 驗證防禦失敗 - 農田被摧毀，天數增加"""
    state = new_game(seed=42)
    
    # 開墾兩個農田，全都不防禦
    state = apply_action(state, "plant_crop_100_100")
    state = apply_action(state, "plant_crop_50_50")
    
    # 進入夜晚
    state = _run_night(state)
    
    assert len(state["crops"]) == 1, "夜晚過後，其中一個未防禦的農田應該被摧毀"
    assert state["day_count"] == 2, "天數推進到第 2 天"
    assert state["status"] == "playing", "還有農田或錢，遊戲繼續"


def test_t06_game_over_condition():
    """T06: 驗證破產結束條件"""
    state = new_game(seed=42)
    
    # 開墾一個農田
    state = apply_action(state, "plant_crop_100_100")
    # 把錢花光 (模擬)
    state["money"] = 0
    
    # 進入夜晚，農田被毀
    state = _run_night(state)
    
    assert len(state["crops"]) == 0, "農田被毀"
    assert state["status"] == "lose", "沒錢也沒農田，遊戲結束"


def test_t07_stable_snapshot():
    """T07: 驗證快照的穩定性與重現性"""
    state_a = new_game(seed=99)
    state_b = new_game(seed=99)
    
    snap_a = snapshot(state_a)
    snap_b = snapshot(state_b)
    
    assert snap_a == snap_b, "相同 seed 產生的初始快照必須完全一致"
    
    # 改變狀態 B (增加一個農田)
    state_b = apply_action(state_b, "plant_crop_0_0")
    snap_b_modified = snapshot(state_b)
    
    assert snap_a != snap_b_modified, "狀態改變後，快照比對必須不一致"

def test_t08_neighbor_gift():
    """T08: 驗證鄰居禮物 - 第二天可以免費放置狗狗"""
    state = new_game(seed=42)
    state = apply_action(state, "plant_crop_100_100")
    
    # 手動修改 state 來模擬夜間結算過程，這部分應該在 night_tick 中執行
    state["phase"] = "night"
    # 直接拔除小偷路徑以模擬防禦成功
    state["thief_path"] = []
    state = apply_action(state, "night_tick")
    
    assert state["day_count"] == 2
    assert state["free_dog"] is True
    
    initial_money = state["money"]
    state = apply_action(state, "place_dog_110_110")
    
    assert len(state["dogs"]) == 1
    assert state["money"] == initial_money, "使用免費狗狗不應該扣錢"
    assert state["free_dog"] is False, "使用後免費狀態應該取消"