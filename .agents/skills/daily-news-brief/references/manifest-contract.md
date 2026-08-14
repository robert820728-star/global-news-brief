# 事件資料交接契約

## 原則

事件資料是所有技能的唯一交接物。每個技能只補充自己的欄位，不得重建整個物件。最終資料必須符合 repo 根目錄的 `schemas/news-event-manifest.schema.json`，目前版本固定為 `1.0.0`。

## 欄位所有權

| 技能 | 可修改欄位 |
|---|---|
| daily-news-brief | run、sections、stage_status、final_status |
| select-news-events | event_id、primary_section、title、grade、selection |
| verify-news-events | verification |
| build-news-maps | map |
| collect-news-images | images |

`detail` 由主控依 selection 與 verification 組裝；子技能不得直接重寫最終文章。

地圖與圖片附件都必須保存實際寬高及視覺驗收結果。網址只能放在來源欄；讀者可見附件路徑必須是絕對本地路徑或 `sandbox:/` 絕對路徑。

## 事件最小結構

```json
{
  "event_id": "TWN-01",
  "primary_section": "TWN",
  "title": "事件名稱",
  "grade": "A",
  "selection": {},
  "verification": {},
  "map": {},
  "images": {},
  "detail": {}
}
```

## 階段快照

每個技能執行前保存目前事件資料；執行後比較：

- 驗證階段只允許 `verification` 改變。
- 地圖階段只允許 `map` 改變。
- 圖片階段只允許 `images` 改變。
- 發現越權變更時，還原非本技能欄位並重做該階段。

可用下列命令檢查：

```bash
python3 scripts/validate_news_brief.py stage \
  --stage build-news-maps \
  --before /path/to/before.json \
  --after /path/to/after.json
```

## 省略與失敗

- 地圖或圖片不適用時使用 `status: not_required`。
- 應嘗試但來源無圖或重試失敗時使用 `status: omitted` 並保存後台原因。
- 後台原因不得出現在讀者版。
- `verification.finding: single_reliable_source` 不得觸發自動降級或刪除。
