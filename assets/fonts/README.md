# 中文字型掛載說明

`NotoSansTC-GameSubset.otf` 已經放在這個資料夾裡了，`advanced_nightwatch_farm-v3.py` 啟動時會
自動抓資料夾裡的字型檔來用（優先權比系統字型高），不需要再另外下載或設定，中文應該已經正常顯示，
不會再出現「□」豆腐塊。

這個檔案是思源黑體 Traditional Chinese (Noto Sans CJK TC) 的**精簡子集**——只保留了目前遊戲原始碼
裡實際用到的約 1000 個字元（含全部中文字、標點、英數），所以只有 600KB 左右，不是完整 16MB 的
思源黑體全字集。

**如果之後新增的 UI 文字用到子集裡沒有的新字**，那個字一樣會變成「□」。這時候把這個檔案直接換成
完整版思源黑體即可解決（不用改程式碼，檔名不同也沒關係，程式只認資料夾裡的第一個字型檔）：

- 思源黑體 Traditional Chinese (Noto Sans TC)：https://fonts.google.com/noto/specimen/Noto+Sans+TC

如果這個資料夾是空的，程式會改抓系統上已安裝的中文字型（微軟正黑體/微軟雅黑/蘋方等），都找不到才會
退回 Arial 並在終端機印警告。
