"""
夜巡農場 (Nightwatch Farm) - 遊戲啟動入口
執行此腳本即可啟動夜巡農場。
"""

import sys
import os

# 將當前資料夾加入 Python 模組搜尋路徑，確保無論從何處執行都能正確 import
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import importlib
module = importlib.import_module("advanced_nightwatch_farm-v3")

if __name__ == "__main__":
    app = module.NightwatchFarmApp()
    app.run()
