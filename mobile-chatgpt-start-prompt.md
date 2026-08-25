# 手機 ChatGPT 起始指令

先在手機 ChatGPT 的模型選單選擇 **Instant**。若可設定，關閉自動切換到 Thinking。不要使用 Thinking 或 Pro。

接著把下方整段貼到一般 ChatGPT 對話：

```text
請建立一個 ChatGPT Scheduled Task，名稱為「每日新聞」。

排程：每天 06:00，時區 Asia/Taipei；建立後立即執行一次。
執行模式：維持目前的 Instant，不切換到 Thinking 或 Pro。
GitHub 規則來源：https://github.com/robert820728-star/global-news-brief/blob/main/mobile-chatgpt-daily-prompt.md
監控區域：台灣、中國、全球
加重類型：無

每次執行前重新讀取上述 GitHub 檔案，依其中「手機 ChatGPT 基礎每日新聞規則」完成本輪更新。使用此排程對話可取得的網頁搜尋、已連接 app 與前次執行記憶；不要要求本機檔案、命令列或程式執行環境。

使用已連接且具此 repository 寫入權限的 GitHub app。每輪搜尋前先接手 `run-logs` 分支的持久執行紀錄；讀者版完成後先保存到該分支，再嘗試輸出到本對話。不得把「後端已開始交付」誤稱為「手機畫面已確認收到」。

最低驗收不可省略：本輪 24 小時 run-scoped candidate audit、每筆六項大評分、本輪所有 C 級以上新聞進入讀者版，以及每則新聞的同圖低解析圖片、同一張原圖或圖片說明。十四天 continuity cache 能安全合併時才更新；無法合併時保留舊檔並延後，不得阻擋當日 reader。不得為了縮小檔案換成另一張圖，不得用圖片網址／原網站連結代替圖片，也不得因無法縮圖而讓整份新聞失敗。

若本輪無法讀取 GitHub 規則或無法搜尋新聞，請明確回報失敗原因，不得用模型記憶虛構新聞或宣稱已更新。
```
