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
    # 四周為景觀（右下角座標從實際網格尺寸算，不寫死數字——網格大小
    # 之後再調整也不會讓這個測試莫名其妙爆掉）
    assert game.get_tile(0, 0).zone == ZoneType.DECORATION_ZONE
    assert game.get_tile(game.width - 1, game.height - 1).zone == ZoneType.DECORATION_ZONE
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
    
    # 模擬經過完整夜晚 (18秒)。注意：dt=20 這麼大的一次 update() 除了
    # 觸發破曉之外，途中 _update_night_spawning() 也會依配置正常生怪，
    # 所以場上最終殘留的敵人數量不保證只有一開始手動加的那隻，測試
    # 只驗證「破曉當下的行為」，不假設確切數量。
    game.update(20.0)
    assert game.phase == GamePhase.DAY, "夜晚時間結束應自動破曉切換至白天！"
    # 【AI 行為升級：白天的恐懼與逃跑機制】破曉不再讓殘餘敵人直接消失
    # （len(enemies)==0），而是強制轉成 FLEEING 狀態、逃往地圖邊界，
    # 移動到邊界格才會被真正移除，不是瞬間清空。
    assert len(game.enemies) >= 1, "破曉當下應轉為逃跑，不是立刻消失"
    assert all(e.state == EnemyState.FLEEING for e in game.enemies), "破曉當下場上所有敵人都應強制進入 FLEEING 狀態"
    # 手動加的那隻敵人一開始就站在 (0, 0)——本身已經是地圖邊界——
    # _set_enemy_flee_path() 算出的目標就是原地，DAY 階段的 update()
    # 現在也會繼續呼叫 _update_enemies()，下一次呼叫就會判定牠已經在
    # 邊界上並真正移除，驗證「移動到地圖邊界才移除」這條規則確實有
    # 生效，不是永遠留在場上。
    game.update(0.1)
    assert not any(e.id == "test_thief" for e in game.enemies), "站在地圖邊界的逃跑敵人應在白天被真正移除"
    print("  ✓ 日夜循環切換無卡死，破曉驅散改為合理的逃跑機制運作完美！")


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
    print("[測試 5] 破產判定已取消測試...")
    # 【使用者要求：取消「金錢過少判定失敗」機制】原本這裡測試「持金
    # 過低 + 農田無作物」會觸發強制破產淘汰；使用者要求取消這個機制
    # 之後，改成驗證同樣的極端窮困情境「不會」再被判定成遊戲結束，
    # check_game_over() 應該回傳 False，玩家可以繼續遊戲。
    game = GameState()
    game.gold = 5
    for row in game.grid:
        for tile in row:
            tile.crop = None

    assert not game.check_game_over(), "金錢過少+無作物不應再被判定為遊戲失敗"
    assert not game.game_over, "取消破產機制後，遊戲不應被強制結束"
    print("  ✓ 金錢過少不再強制判定失敗，玩家可以繼續遊戲！")


def test_starting_gold_and_fence_durability():
    print("[測試 6] 初始金幣 300 與圍籬破壞機制測試...")
    game = GameState()
    assert game.gold == 300, "初始金錢應為 300 G！"
    
    # 在 (6, 4) 種植蘿蔔，並在四周建造木柵阻隔
    game.plant_crop(6, 4, CropType.WHITE_RADISH)
    for fx, fy in [(5, 4), (7, 4), (6, 3), (6, 5)]:
        game.place_defense(fx, fy, DefenseType.WOODEN_FENCE)
    fence_tile = game.get_tile(5, 4)
    assert fence_tile.defense is not None
    assert fence_tile.defense.hp == 80.0

    
    # 進入夜晚測試破壞
    game._start_night()
    
    # 建立一隻野豬從 (4, 4) 出發攻擊 (6, 4) 作物
    from game_config import Enemy
    boar = Enemy(id="b1", enemy_type=EnemyType.WILD_BOAR, x=4.0, y=4.0)
    game._assign_enemy_target_and_path(boar)
    game.enemies.append(boar)
    
    # 推進 1 秒 (20 幀 x 0.05s)
    for _ in range(20):
        game.update(0.05)
    assert fence_tile.defense.hp < 80.0, "野豬應對阻擋中的木柵造成持續破壞！"
    
    # 再推進 1.5 秒 (30 幀 x 0.05s)，木柵應被徹底衝破
    for _ in range(30):
        game.update(0.05)
    assert fence_tile.defense is None, "木柵耐久歸零後應被衝破並消失！"
    print("  ✓ 初始金幣 300 與圍籬破壞機制測試全數通過！")



def test_shovel_demolish_and_refund():
    print("[測試 7] 鐵鏟剷除作物與拆除防禦退款測試...")
    game = GameState()
    
    # 測試剷除作物
    game.plant_crop(6, 4, CropType.WHITE_RADISH)
    assert game.get_tile(6, 4).crop is not None
    success, msg, refund = game.demolish_tile(6, 4)
    assert success and refund == 0
    assert game.get_tile(6, 4).crop is None
    
    # 測試拆除木柵（【遊戲平衡與 UI/UX 體驗大優化】原價 15 調降至 5，
    # 退還 80% = 4）
    gold_before = game.gold
    game.place_defense(6, 4, DefenseType.WOODEN_FENCE)
    assert game.gold == gold_before - 5
    success, msg, refund = game.demolish_tile(6, 4)
    assert success and refund == 4
    assert game.gold == gold_before - 5 + 4
    assert game.get_tile(6, 4).defense is None
    print("  ✓ 鐵鏟剷除作物與拆除設施退款機制全數通過！")


if __name__ == "__main__":
    print("==========================================")
    print(" 🚀 執行中央農田版「夜巡農場」測試套件")
    print("==========================================")
    test_dual_zones()
    test_farming_watering_harvest()
    test_night_day_cycle_transition()
    test_scarecrow_and_trap()
    test_game_over_bankruptcy()
    test_starting_gold_and_fence_durability()
    test_shovel_demolish_and_refund()
    print("==========================================")
    print(" 🎉 所有底層測試 100% 通過！")
    print("==========================================")


