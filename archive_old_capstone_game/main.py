from src.capstone_contract import new_game, apply_action, is_terminal

def print_board(state):
    print("\n" + "="*20)
    print(f"階段: {state['phase'].upper()} | 狀態: {state['status']}")
    print(f"系統訊息: {state['last_msg']}")
    print("-" * 20)
    
    for y in range(5):
        row = ""
        for x in range(5):
            pos = (x, y)
            if pos == state["thief_pos"]:
                row += "🥷 " # 小偷
            elif pos in state.get("crops", []):
                row += "🌱 " # 農作物
            elif pos in state["fences"]:
                row += "🚧 " # 圍欄
            else:
                row += "⬜ " # 空地
        print(row)
    print("="*20 + "\n")

def play():
    state = new_game()
    print("🌾 歡迎來到保衛農場 (純文字測試版) 🌾")
    
    while not is_terminal(state):
        print_board(state)
        print("可選行動:")
        print("1. 放置圍欄 (格式: build_X_Y，例如 build_1_2)")
        print("2. 點擊小偷 (格式: click_X_Y，例如 click_0_0)")
        print("3. 結束白天，進入夜晚 (輸入: start_night)")
        
        action = input("請輸入行動指令: ").strip()
        if action:
            state = apply_action(state, action)
            
    # 遊戲結束
    print_board(state)

if __name__ == "__main__":
    play()