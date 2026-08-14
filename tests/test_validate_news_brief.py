import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_news_brief", ROOT / "scripts" / "validate_news_brief.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


def valid_manifest():
    note = VALIDATOR.SINGLE_SOURCE_NOTE
    return {
        "schema_version": "1.1.0",
        "run": {
            "generated_at": "2026-08-14T06:00:00+08:00",
            "timezone": "Asia/Taipei",
            "window_start": "2026-08-13T06:00:00+08:00",
            "window_end": "2026-08-14T06:00:00+08:00",
            "language": "繁體中文",
        },
        "sections": [{"code": "TWN", "name": "台灣", "order": 1}],
        "stage_status": {
            "select-news-events": "completed",
            "verify-news-events": "completed",
            "build-news-maps": "completed",
            "build-news-charts": "completed",
            "collect-news-images": "completed",
            "recover-news-run": "completed",
            "render": "completed",
            "validate": "completed",
        },
        "recovery": {
            "status": "completed",
            "max_attempts_per_target": 3,
            "attempts": [],
            "unresolved_targets": [],
        },
        "events": [
            {
                "event_id": "TWN-01",
                "primary_section": "TWN",
                "title": "測試事件",
                "grade": "B",
                "selection": {
                    "dedup_key": "test-event",
                    "category": "公共安全",
                    "impact_scope": "台灣",
                    "reason": "具有公共影響",
                    "candidate_urls": ["https://example.com/news"],
                    "news_time": "2026-08-14T05:30:00+08:00",
                    "event_time": "2026-08-14T05:00:00+08:00",
                },
                "verification": {
                    "status": "completed",
                    "finding": "single_reliable_source",
                    "search_performed": True,
                    "independent_source_count": 1,
                    "sources": [
                        {
                            "source_id": "src-1",
                            "name": "官方來源",
                            "url": "https://example.com/source",
                            "role": "官方",
                            "producer": "官方機構",
                            "independence_group": "official-agency",
                            "published_at": "2026-08-14T05:30:00+08:00",
                            "accessed_at": "2026-08-14T06:00:00+08:00",
                            "evidence_type": "supports",
                            "claim_ids": ["claim-1"],
                            "limitations": [],
                        }
                    ],
                    "claims": [
                        {
                            "claim_id": "claim-1",
                            "text": "事件發生",
                            "status": "supported",
                            "source_ids": ["src-1"],
                        }
                    ],
                    "uncertainties": ["缺少其他獨立來源"],
                    "source_limit_note": note,
                    "positions": [],
                    "reader_wording": "據官方來源指出。",
                    "verified_at": "2026-08-14T06:00:00+08:00",
                },
                "map": {
                    "required": True,
                    "status": "ready",
                    "rationale": "位置有助理解",
                    "assets": [
                        {
                            "path": "sandbox:/tmp/map.png",
                            "caption": "地圖一：事件位置，依來源資料整理。",
                            "source_urls": ["https://example.com/source"],
                            "visual_checked": True,
                            "width": 1200,
                            "height": 900,
                        }
                    ],
                    "omission_reason": None,
                },
                "charts": {
                    "required": False,
                    "status": "not_required",
                    "rationale": "本事件不需要數據比較圖表",
                    "assets": [],
                    "omission_reason": None,
                },
                "images": {
                    "required": True,
                    "status": "ready",
                    "source_checks": [
                        {
                            "source_url": "https://example.com/source",
                            "checked": True,
                            "usable_image_found": True,
                            "attempts": 1,
                            "outcome": "attached",
                        }
                    ],
                    "assets": [
                        {
                            "path": "sandbox:/tmp/image.png",
                            "caption": "圖一：官方資訊圖（來源：官方來源）。",
                            "source_name": "官方來源",
                            "source_url": "https://example.com/source",
                            "kind": "official_information",
                            "published_at": "2026-08-14T05:30:00+08:00",
                            "visual_checked": True,
                            "time_checked": True,
                            "width": 1000,
                            "height": 800,
                        }
                    ],
                    "omission_reason": None,
                },
                "detail": {
                    "overview_time": "8/14 05:30",
                    "time": "新聞時間：8/14 05:30；事件時間：8/14 05:00。",
                    "event_details": "據官方來源指出，事件已發生。",
                    "positions": [],
                    "analysis": "事件具有公共影響，但仍缺少獨立來源。",
                    "follow_up": "追蹤是否出現其他獨立來源。",
                },
            }
        ],
        "final_status": "ready",
    }


def valid_brief():
    note = VALIDATOR.SINGLE_SOURCE_NOTE
    return f"""2026/08/14 每日新聞

## 今日總覽

### 台灣版

| 編號 | 時間 | 事件 | 等級 |
|---|---|---|---|
| TWN-01 | 8/14 05:30 | 測試事件 | B |

## 逐條詳報

### TWN-01. 測試事件 - B

**時間：**新聞時間：8/14 05:30；事件時間：8/14 05:00。

**來源：**[官方來源](https://example.com/source)。{note}

**地圖：**

![地圖一](sandbox:/tmp/map.png)

地圖一：事件位置，依來源資料整理。

**圖片：**

![圖一](sandbox:/tmp/image.png)

圖一：官方資訊圖（來源：官方來源）。

**事件細節：**據官方來源指出，事件已發生。

**分析：**事件具有公共影響，但仍缺少獨立來源。

## 後續觀察

- TWN-01：追蹤是否出現其他獨立來源。
"""


class ValidatorTests(unittest.TestCase):
    def test_valid_manifest_and_brief(self):
        manifest = valid_manifest()
        self.assertEqual([], VALIDATOR.validate_manifest_data(manifest))
        self.assertEqual([], VALIDATOR.validate_brief_text(manifest, valid_brief()))

    def test_single_source_does_not_change_grade(self):
        manifest = valid_manifest()
        self.assertEqual("B", manifest["events"][0]["grade"])
        self.assertEqual([], VALIDATOR.validate_manifest_data(manifest))

    def test_stage_guard_catches_map_stage_deleting_images(self):
        before = valid_manifest()
        after = copy.deepcopy(before)
        after["events"][0]["map"]["rationale"] = "更新定位理由"
        after["events"][0]["images"]["assets"] = []
        errors = VALIDATOR.validate_stage_data(before, after, "build-news-maps")
        self.assertTrue(any("越權修改 TWN-01.images" in error for error in errors))

    def test_brief_catches_missing_image(self):
        text = valid_brief().replace("sandbox:/tmp/image.png", "sandbox:/tmp/other.png")
        errors = VALIDATOR.validate_brief_text(valid_manifest(), text)
        self.assertTrue(any("漏放圖片附件" in error for error in errors))

    def test_ready_manifest_blocks_omitted_image_when_source_has_one(self):
        manifest = valid_manifest()
        manifest["events"][0]["images"]["status"] = "omitted"
        manifest["events"][0]["images"]["assets"] = []
        manifest["events"][0]["images"]["omission_reason"] = "取得失敗"
        manifest["events"][0]["images"]["source_checks"][0]["outcome"] = "acquisition_failed"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("未附上合格附件前不得完成簡報" in error for error in errors))

    def test_ready_chart_does_not_replace_required_source_image(self):
        manifest = valid_manifest()
        manifest["events"][0]["charts"] = {
            "required": True,
            "status": "ready",
            "rationale": "比較兩個統計值",
            "assets": [{
                "path": "sandbox:/tmp/chart.png",
                "caption": "資料圖表一：本簡報依官方資料製作。",
                "source_names": ["官方來源"],
                "source_urls": ["https://example.com/source"],
                "chart_type": "bar",
                "data_points": 2,
                "visual_checked": True,
                "data_checked": True,
                "width": 1200,
                "height": 800,
            }],
            "omission_reason": None,
        }
        manifest["events"][0]["images"]["status"] = "omitted"
        manifest["events"][0]["images"]["assets"] = []
        manifest["events"][0]["images"]["omission_reason"] = "取得失敗"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("未附上合格附件前不得完成簡報" in error for error in errors))

    def test_b_grade_requires_all_source_pages_checked(self):
        manifest = valid_manifest()
        manifest["events"][0]["images"]["source_checks"] = []
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("缺少來源頁圖片檢查紀錄" in error for error in errors))

    def test_ready_manifest_requires_completed_recovery(self):
        manifest = valid_manifest()
        manifest["recovery"]["status"] = "recovering"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("recovery.status 必須 completed" in error for error in errors))

    def test_recovery_attempts_are_sequential_and_bounded(self):
        manifest = valid_manifest()
        manifest["recovery"]["attempts"] = [
            {
                "target_stage": "collect-news-images",
                "event_id": "TWN-01",
                "attempt": 2,
                "started_at": "2026-08-14T06:00:00+08:00",
                "ended_at": "2026-08-14T06:01:00+08:00",
                "outcome": "failed",
                "error_code": "timeout",
                "message": "逾時",
            }
        ]
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("attempt 應為 1" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
