# nightwatch_farm 圖片搬運完成報告

## 做了什麼

把 `main` 分支 `src/assets.py` 用的真實素材包（Sprout Lands、Sunnyside World、Farm RPG 等）裡的圖片，透過新寫的 `migrate_assets.py` 腳本裁切/匯出，**取代**了 `nightwatch_farm/assets/` 底下原本 `generate_assets.py` 生成的純色扁平佔位圖，總共 64 張，已經寫回你電腦上 `nightwatch_farm/assets/` 資料夾，檔名與 `asset_loader.py` 現有的 key 規則完全對齊，**不需要改 `asset_loader.py` 或 `game_state.py` 任何一行程式碼**，遊戲下次啟動時 `AssetLoader` 就會自動讀到新圖。

## 精確匹配 vs. 替代（誠實列出，不是每個都有現成的真實素材）

我把整份素材庫全部搜過一輪（用檔名關鍵字比對 tomato/corn/eggplant/watermelon/strawberry/grape/starlight/lantern/statue/sundial/bat/boar/cat 等），結果是：

**精確匹配（15 項）：**
`radish`、`pumpkin`、`sunflower`（作物，Sunnyside 6 階段生長圖）、`windmill`（風車）、`sakura_tree`（櫻花樹，Cherry Blossom Biom 素材包）、`fountain`（噴泉，改用 Sunnyside 真實水井圖，比 main 自己「借用風車充當噴泉」的舊解法更貼切）、`enemy_bat`（蝙蝠，Dungeon Pack）、`enemy_boar`/`boss_boar`（野豬，用的正是 `main` 自己 `renderer.py` 畫野豬用的同一張豬圖）、`wooden_fence`、`scarecrow`、`watering_can`（真的是灑水壺，`main` 裡把它註冊成 `pickaxe` 只是借用同一張圖當鎬子圖示，這裡才是它原本的身分）、`guard_dog`、`enemy_thief`、`beehive`。

**沒有現成素材、用最接近的替代品（10 項，都在腳本裡用註解標了原因）：**

| nightwatch_farm 需要 | 用了什麼替代 | 為什麼 |
|---|---|---|
| `tomato`（4階段） | Sunnyside `beetroot` | 整個素材庫找不到任何番茄圖，甜菜根是外型最接近的圓形紅色根莖類 |
| `corn` | Sunnyside `wheat` | 找不到玉米圖，麥子是最接近的穀類/莖狀作物 |
| `eggplant` | Sunnyside `cabbage` | 找不到茄子圖（也找不到任何紫色系作物），高麗菜是最接近的圓形蔬菜 |
| `watermelon` | Sunnyside `cauliflower` | 找不到西瓜圖，白花椰菜是外型最接近的大顆圓形蔬菜 |
| `grape` | Sunnyside `potato` | 找不到葡萄/任何果串類圖，這個匹配度偏弱，只是矮子中選將軍 |
| `starlight`（虛構作物） | Sunnyside `parsnip` | 本來就沒有對應真實作物，選一個顏色偏淺白的防風草暫代，等你之後有更好的點子再換 |
| `strawberry` | Farm RPG 單張草莓圖示（4 階段共用同一張） | 素材庫裡草莓沒有生長階段序列，只有一張成熟圖示，`main` 本身也是這樣用的，這裡誠實地 4 階段都先放同一張 |
| `garden_bench` | Interior.png 的椅子 | 全素材庫沒有長椅，`main` 自己也是用椅子代替 |
| `apple_tree` | 「愛心果實樹」 | 沒有蘋果樹，`main` 自己也是這樣代替的 |
| `bear_trap` | 地刺陷阱動畫 | 沒有捕獸夾造型的素材，`main` 自己也是這樣代替的 |
| `soul_lantern` | 冬季篝火堆疊木柴的最終格 | 整個素材庫沒有任何燈籠/燈具類圖片 |
| `ancient_statue` | Sprout-Lands 的灰色石頭 | 整個素材庫沒有任何雕像類圖片 |
| `sundial_tower` | 樹樁圖示 | 整個素材庫沒有任何日晷/鐘塔類圖片 |
| `bird_bath` | Sunnyside 加蓋水井（藍色寶石頂） | 沒有鳥浴盆，這是外型最接近「石砌水盆」的素材 |
| `pet_house` | 一棟迷你小屋 | 沒有專門的狗屋/寵物屋素材，用最小的房屋代替 |
| `farm_cat` | 一隻小雞 | **全素材庫真的沒有任何貓的圖**，`main` 自己的「cat」也是借用同一張小雞圖 |

如果你之後找到或畫出更合適的真實圖片（尤其是 tomato/corn/eggplant/watermelon/grape/starlight 這幾個弱替代，還有貓、燈籠、雕像、日晷、鳥浴盆這幾個完全沒素材的），直接把對應檔名的 PNG 放進 `nightwatch_farm/assets/<類別>/` 覆蓋掉就行，`asset_loader.py` 不用改。

## 檔案

`migrate_assets.py`（已放在 repo 根目錄，之後想重新產生或調整某張圖可以直接改這個腳本重跑）、64 張新圖片已直接寫入你電腦上的 `nightwatch_farm/assets/`。

## 關於「以 nightwatch_farm 為核心新增功能」

圖片搬運這部分先做完了。新功能你還沒具體說要加什麼——是要把 `main`/`src/capstone_contract.py` 裡已經做好的東西（例如防禦動物、日夜循環、教學系統其中一部分）搬過去給 `nightwatch_farm` 用，還是要做全新的、`main` 沒有的東西？跟我說一聲你想先加哪個，我再開始動工。
