# 舊版遊戲封存說明

這個資料夾保存的是「夜巡農場 (nightwatch_farm)」升級為主專案之前，舊的 `src/capstone_contract.py`
農場防禦遊戲的完整內容（含 `src/`、`tests/`、原本的根目錄 `main.py`、課程相關的舊版素材包
`assets/`，以及 `migrate_assets.py` 這個一次性的圖片搬運腳本）。

不是被刪除，只是被搬到這裡保留歷史記錄——整個 git 歷史（`git log --follow`）仍然找得到每一個檔案
之前的所有 commit。如果之後想找回舊遊戲的某個功能或素材，直接來這裡翻，或用
`git log --follow -- archive_old_capstone_game/src/xxx.py` 查它改動過的完整歷史。

`migrate_assets.py` 曾經讀取這裡的 `assets/` 作為素材來源，裁切匯出成
`nightwatch_farm`（現在的根目錄）`assets/{crops,decorations,defenses,characters}/` 底下的 64 張真實
素材圖——這件事已經做完了，腳本目前的路徑設定不會再對現在的專案結構生效，純粹留作紀錄。
