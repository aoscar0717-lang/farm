"""
夜巡農場 (Nightwatch Farm) - 相容用啟動入口

`python src/main.py` 過去是舊版農場防禦遊戲（src/capstone_contract.py 那一套）
的啟動指令。舊遊戲已經整個搬進 archive_old_capstone_game/src/ 保留，nightwatch_farm
升級成了主專案，這個檔案的唯一用途，是讓「python src/main.py」這個習慣的指令
繼續可以用，而且啟動的是新遊戲，不會噴錯或啟動到舊遊戲。跟根目錄的 main.py
是完全一樣的入口，兩個指令挑一個習慣的用就好。
"""
import sys
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import importlib
module = importlib.import_module("advanced_nightwatch_farm-v3")

if __name__ == "__main__":
    app = module.NightwatchFarmApp()
    app.run()
