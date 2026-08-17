"""Automated tests for Farm Defense game contracts - Updated Sandbox Edition."""

from src.capstone_contract import new_game, apply_action

def test_fresh_state():
    """T01: 驗證遊戲初始化狀態"""
    state = new_game(seed=42)
    
    assert state["phase"] == "day"
    assert len(state["crops"]) == 0
    assert len(state["fences"]) == 0
    assert len(state["dogs"]) == 0
    assert state["money"] == 500
    assert state["day_count"] == 1
    assert state["time_left"] == 120
    assert state["status"] == "playing"


def test_day_actions_build_and_plant():
    """T02: 驗證使用工具開墾與種植"""
    state = new_game(seed=42)
    
    # 使用鋤頭開墾農田
    state = apply_action(state, "use_hoe_10_10")
    assert len(state["building_tasks"]) == 1
    assert state["building_tasks"][0]["type"] == "farmland"
    
    # 推進時間完成開墾 (進度 2)
    for _ in range(3):
        state = apply_action(state, "tick")
        
    assert len(state["farmland"]) == 1
    
    # 在農田上種植蘿蔔
    state = apply_action(state, "plant_crop_radish_10_10")
    assert len(state["building_tasks"]) == 1
    assert state["building_tasks"][0]["type"] == "crop"
    assert state["money"] == 470  # 500 - 30
    
    # 推進時間完成種植 (進度 3)
    for _ in range(4):
        state = apply_action(state, "tick")
        
    assert len(state["crops"]) == 1
    assert state["crops"][0] == (10, 10)


def test_invalid_placement():
    """T03: 驗證無法封死農田的邊界邏輯"""
    state = new_game(seed=42)
    state["wood"] = 10
    
    # 放置農田
    state["crops"].append((10, 10))
    
    # 用圍欄完全包圍農田 (10,10)
    positions = [(0,0), (10,0), (20,0), (0,10), (20,10), (0,20), (10,20)]
    for pos in positions:
        state = apply_action(state, f"build_fence_{pos[0]}_{pos[1]}")
    
    # 推進時間完成建造
    for _ in range(5):
        state = apply_action(state, "tick")
    assert len(state["fences"]) == 7
    
    # 嘗試放置最後一塊
    state = apply_action(state, "build_fence_20_20")
    # 應該會失敗，因為這會封死農田
    assert "封死" in state.get("last_msg", "")


def test_night_phase_and_thief_spawn():
    """T04: 驗證黑夜階段與小偷生成"""
    state = new_game(seed=42)
    
    # 放一個農田作為目標，否則小偷不會尋路
    state["crops"].append((10, 10))
    
    # 直接進入夜晚
    state = apply_action(state, "start_night")
    assert state["phase"] == "night"
    
    # 推進時間讓小偷生成 (第一隻小偷需要 30 tick)
    for _ in range(35):
        state = apply_action(state, "night_tick")
        
    # 第一隻小偷應該已經生成
    assert state["thieves_spawned"] > 0
    assert state["thief_pos"] is not None


def test_harvesting_and_selling():
    """T05: 驗證收割系統與品質"""
    state = new_game(seed=42)
    
    # 手動建立一個成熟的蘿蔔
    pos = (10, 10)
    state["crops"].append(pos)
    state["crop_data"][pos] = {
        "type": "radish", 
        "stage": 1, 
        "max_stage": 1,
        "fertilized": False,
        "growth_timer": 0
    }
    
    # 使用鐮刀收割
    state = apply_action(state, "use_scythe_10_10")
    
    assert len(state["crops"]) == 0
    # 檢查是否有蘿蔔進入背包
    inv = state["inventory"]["radish"]
    total_harvested = inv["normal"] + inv["rare"] + inv["epic"] + inv["legendary"]
    assert total_harvested == 1


def test_game_over_rent():
    """T06: 驗證破產結束條件"""
    state = new_game(seed=42)
    
    # 將錢歸零
    state["money"] = 0
    
    # 進入夜晚
    state = apply_action(state, "start_night")
    
    # 推進直到進入白天或結束
    # 夜晚長度通常為60秒，每秒30 ticks
    for _ in range(2000):
        state = apply_action(state, "tick")
        if state["phase"] == "day" or state["status"] == "game_over":
            break
            
    assert state["status"] == "game_over"
    assert state["money"] < 0
