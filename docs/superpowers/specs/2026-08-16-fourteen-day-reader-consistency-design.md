# 十四天清單與讀者版一致性設計 / Fourteen-Day Audit and Reader Consistency Design

## 目標 / Goal

十四天候選稽核保存逐站完整海選清單，以及 `public_value_v1` 六項大分數、總分與理由。讀者版的本輪事件集合必須精確對應稽核檔本輪所有 C 級以上候選；合併候選可共用同一事件編號，但不得失去映射。沒有合格圖片的新聞必須顯示非技術性的圖片說明。

The rolling audit stores the complete per-source shortlist with all six `public_value_v1` component scores, total score, and rationale. The current reader brief must exactly match every current-run candidate graded C or above. Merged candidates may share one reader event ID but may not lose their mapping. Events without a qualified image must show a non-technical reader explanation.

## 資料流 / Data Flow

1. `source_coverage[].ranked_items[]` stores `importance_breakdown`, `importance_score`, and `importance_reason`.
2. `manage_candidate_audit.validate` enforces exact dimension keys, configured maxima, and total equality.
3. Every C-or-above `selected` or `merged` candidate stores `selected_event_id`.
4. `publish_news_brief.candidate_errors` compares those mapped IDs with the manifest event IDs for the same latest audit run.
5. `images.omission_reason` remains backend-only; `images.reader_omission_note` is rendered as `**圖片說明：**` when `images.status=omitted`.

## 範圍界線 / Scope Boundary

The reader brief remains a precise 24-hour brief. “All C-or-above news in the fourteen-day list” means all C-or-above candidates in the audit file’s current run, not replaying prior days into today’s brief. Historical runs remain continuity evidence.

## 驗收 / Acceptance

- Six major scores exist for every ranked shortlist item and sum to the total.
- Every current-run C-or-above candidate maps to a reader event.
- The manifest has no unmatched or extra reader event.
- Every omitted-image event has the exact reader-facing image note.
- The canonical publisher remains fail-closed.

