"""
夜巡農場 (Nightwatch Farm) - 擴展單元測試與自動化模擬腳本
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from game_config import (
    GamePhase, ZoneType, CropType, CropStage, DecorationType,
    DefenseType, EnemyType, EnemyState, DogState, EventType, MAP_CONFIG
)
from game_state import GameState
from pathfinding import GridBFS


def test_dual_zones():
    print("[測試 1] 中央農田與四周景觀區劃分測試...")
    game = GameState()
    fx_min, fx_max = MAP_CONFIG["FARM_X_RANGE"]
    fy_min, fy_max = MAP_CONFIG["FARM_Y_RANGE"]
    
    # 中央為農田
    assert game.get_tile(6, 4).zone == ZoneType.FARM_ZONE
    # 四周為景觀
    assert game.get_tile(0, 0).zone == ZoneType.DECORATION_ZONE
    assert game.get_tile(17, 10).zone == ZoneType.DECORATION_ZONE
    print("  ✓ 中央農田與四周莊園景觀劃分正確！")


def test_farming_watering_harvest():
    print("[測試 2] 中央農田種植、澆水加速與收成測試...")
    game = GameState()
    initial_gold = game.gold
    
    # 在中央農田 (6, 4) 種植白蘿蔔 (10 G, 4s)
    success, msg = game.plant_crop(6, 4, CropType.WHITE_RADISH)
    assert success
    assert game.gold == initial_gold - 10
    tile = game.get_tile(6, 4)
    
    # 測試黃金水壺澆水 (5 G, +2s 進度)
    success, msg = game.water_crop(6, 4)
    assert success
    assert game.gold == initial_gold - 15
    assert tile.crop.growth_timer >= 2.0
    
    # 推進 2.5 秒，蘿蔔成熟
    game.update(2.5)
    assert tile.crop.stage == CropStage.MATURE
    
    # 收成 (+18 G)
    success, reward, msg = game.harvest_crop(6, 4)
    assert success and reward == 18
    assert game.gold == (initial_gold - 15) + 18
    print("  ✓ 種植、澆水加速與收成全數通過！")


def test_night_day_cycle_transition():
    print("[測試 3] 夜晚自動破曉切換至白天測試...")
    game = GameState()
    game._start_night()
    assert game.phase == GamePhase.NIGHT
    
    from game_config import Enemy
    game.enemies.append(Enemy(id="test_thief", enemy_type=EnemyType.THIEF, x=0.0, y=0.0))
    
    # 模擬經過完整夜晚 (18秒)
    game.update(20.0)
    assert game.phase == GamePhase.DAY, "夜晚時間結束應自動破曉切換至白天！"
    assert len(game.enemies) == 0, "白天殘餘敵人應被陽光驅散"
    print("  ✓ 日夜循環切換無卡死，破曉機制運作完美！")


def test_scarecrow_and_trap():
    print("[測試 4] 稻草人驚嚇與捕獸夾防禦測試...")
    game = GameState()
    game.gold = 500
    game.place_defense(6, 4, DefenseType.SCARECROW)
    game.place_defense(5, 4, DefenseType.BEAR_TRAP)
    game._start_night()
    
    # 小偷走近稻草人 (距離 <= 3 格)
    from game_config import Enemy
    thief = Enemy(id="t1", enemy_type=EnemyType.THIEF, x=6.5, y=4.5)
    thief.state = EnemyState.MOVING
    game.enemies.append(thief)
    
    game.update(0.1)
    assert thief.state == EnemyState.FLEEING, "小偷應被稻草人驚嚇轉為逃跑"
    print("  ✓ 稻草人驚嚇與防禦機制正常！")


def test_game_over_bankruptcy():
    print("[測試 5] 破產淘汰判定測試...")
    game = GameState()
    game.gold = 5
    for row in game.grid:
        for tile in row:
            tile.crop = None
            
    assert game.check_game_over()
    assert game.game_over
    print(f"  ✓ 破產判定正常觸發: {game.game_over_reason}")


if __name__ == "__main__":
    print("==========================================")
    print(" 🚀 執行中央農田版「夜巡農場」測試套件")
    print("==========================================")
    test_dual_zones()
    test_farming_watering_harvest()
    test_night_day_cycle_transition()
    test_scarecrow_and_trap()
    test_game_over_bankruptcy()
    print("==========================================")
    print(" 🎉 所有底層測試 100% 通過！")
    print("==========================================")
