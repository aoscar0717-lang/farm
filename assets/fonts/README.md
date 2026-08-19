# 中文字型掛載說明

把一個中文 `.ttf` / `.ttc` / `.otf` 字型檔放進這個資料夾即可，`advanced_nightwatch_farm-v3.py` 啟動時
會自動抓資料夾裡第一個字型檔來用，優先權比系統字型高，不需要改任何程式碼。

推薦（開源、可商用）：

- 思源黑體 Traditional Chinese (Noto Sans TC)：https://fonts.google.com/noto/specimen/Noto+Sans+TC
- 思源黑體 Simplified Chinese (Noto Sans SC)：https://fonts.google.com/noto/specimen/Noto+Sans+SC

下載後把 `.ttf` 檔直接丟進這個資料夾，重開遊戲就會生效。如果這個資料夾是空的，程式會改抓系統上已安裝的
中文字型（微軟正黑體/微軟雅黑/蘋方等），都找不到才會退回 Arial 並在終端機印警告。
