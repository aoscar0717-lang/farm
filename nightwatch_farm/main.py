"""
夜巡農場 (Nightwatch Farm) - 獨立模組啟動入口
"""

import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

import importlib
module = importlib.import_module("advanced_nightwatch_farm-v3")

if __name__ == "__main__":
    app = module.NightwatchFarmApp()
    app.run()
