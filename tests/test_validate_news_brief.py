import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
RUN_ID = "gnb-20260817T102800Z-6a82b2e0"
MAIN_SHA = "0123456789abcdef0123456789abcdef01234567"
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
            "run_id": RUN_ID,
            "main_sha": MAIN_SHA,
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
                "title": "測試地震事件",
                "grade": "B",
                "selection": {
                    "dedup_key": "test-event",
                    "category": "地震與海嘯",
                    "impact_scope": "台灣",
                    "reason": "地震造成公共安全影響",
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
                            "style_id": "yellow-admin-v2",
                            "style_reference": "maps/style.json",
                            "generator": "scripts/render_base_maps.py",
                            "source_urls": ["https://example.com/source"],
                            "visual_checked": True,
                            "width": 1200,
                            "height": 900,
                            "place_labels": ["測試地點"],
                            "canvas_scope": "full_section",
                            "base_map": "maps/generated/taiwan-counties-yellow-v2.png",
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
                            "checked_at": "2026-08-14T06:00:00+08:00",
                            "inspection_method": "browser",
                            "evidence_path": "sandbox:/tmp/source-check.png",
                            "detected_image_urls": ["https://example.com/image.png"],
                            "usable_image_found": True,
                            "attempts": 1,
                            "outcome": "attached",
                            "failure_detail": None,
                        }
                    ],
                    "professional_visual_required": True,
                    "professional_visual_status": "ready",
                    "professional_source_checks": [
                        {
                            "source_url": "https://example.com/source",
                            "checked": True,
                            "checked_at": "2026-08-14T06:00:00+08:00",
                            "inspection_method": "browser",
                            "evidence_path": "sandbox:/tmp/professional-check.png",
                            "detected_image_urls": ["https://example.com/image.png"],
                            "usable_image_found": True,
                            "attempts": 1,
                            "outcome": "attached",
                            "failure_detail": None,
                        }
                    ],
                    "professional_omission_reason": None,
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
                    "event_details": "據官方來源指出，地震事件已發生。",
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

執行編號：{RUN_ID}
程式版本：{MAIN_SHA}
正式發布：是

本期共 1 則新聞：台灣 1 則。

## 今日總覽

### 台灣

| 編號 | 時間 | 事件 | 等級 |
|---|---|---|---|
| TWN-01 | 8/14 05:30 | 測試地震事件 | B |

## 逐條詳報

### TWN-01. 測試地震事件 - B

**時間：**新聞時間：8/14 05:30；事件時間：8/14 05:00。

**來源：**[官方來源](https://example.com/source)。{note}

**地圖：**

![地圖一](sandbox:/tmp/map.png)

地圖一：事件位置，依來源資料整理。

**圖片：**

![圖一](sandbox:/tmp/image.png)

圖一：官方資訊圖（來源：官方來源）。

**事件細節：**據官方來源指出，地震事件已發生。

**分析：**事件具有公共影響，但仍缺少獨立來源。

## 後續觀察

- TWN-01：追蹤是否出現其他獨立來源。
"""


class ValidatorTests(unittest.TestCase):
    def test_manifest_requires_canonical_run_identity(self):
        manifest = valid_manifest()
        manifest["run"].pop("run_id")
        manifest["run"]["main_sha"] = "not-a-sha"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("run.run_id" in error for error in errors))
        self.assertTrue(any("run.main_sha" in error for error in errors))

    def test_reader_rejects_mismatched_run_id(self):
        text = valid_brief().replace(RUN_ID, "gnb-20260817T102800Z-deadbeef", 1)
        errors = VALIDATOR.validate_brief_text(valid_manifest(), text)
        self.assertTrue(any("執行編號" in error for error in errors))

    def test_reader_rejects_nonfinal_delivery_marker(self):
        text = valid_brief().replace("正式發布：是", "正式發布：否", 1)
        errors = VALIDATOR.validate_brief_text(valid_manifest(), text)
        self.assertTrue(any("正式發布" in error for error in errors))

    def test_premature_final_manifest_command_is_deferred_without_failing_run(self):
        manifest = valid_manifest()
        manifest["stage_status"]["collect-news-images"] = "pending"
        manifest["final_status"] = "draft"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = VALIDATOR.main(["manifest", "--input", str(path)])

        self.assertEqual(0, exit_code)
        self.assertIn("DEFERRED", output.getvalue())
        self.assertNotIn("OK", output.getvalue())

    def test_crlf_event_separators_are_accepted(self):
        manifest = valid_manifest()
        second = copy.deepcopy(manifest["events"][0])
        second["event_id"] = "TWN-02"
        second["title"] = "第二則測試事件"
        second["selection"]["dedup_key"] = "test-event-2"
        manifest["events"].append(second)
        brief = valid_brief()
        brief = brief.replace(
            "本期共 1 則新聞：台灣 1 則。",
            "本期共 2 則新聞：台灣 2 則。",
        ).replace(
            "| TWN-01 | 8/14 05:30 | 測試地震事件 | B |",
            "| TWN-01 | 8/14 05:30 | 測試地震事件 | B |\n"
            "| TWN-02 | 8/14 05:30 | 第二則測試事件 | B |",
        )
        first_detail, follow_up = brief.split("## 後續觀察", 1)
        second_detail = first_detail[first_detail.index("### TWN-01."):]
        second_detail = second_detail.replace("TWN-01", "TWN-02").replace(
            "測試地震事件", "第二則測試事件"
        )
        brief = first_detail.rstrip() + "\n\n---\n\n" + second_detail.rstrip() + (
            "\n\n## 後續觀察" + follow_up.replace(
                "- TWN-01：追蹤是否出現其他獨立來源。",
                "- TWN-01：追蹤是否出現其他獨立來源。\n"
                "- TWN-02：追蹤是否出現其他獨立來源。",
            )
        )
        crlf_brief = brief.replace("\n", "\r\n")
        self.assertEqual([], VALIDATOR.validate_brief_text(manifest, crlf_brief))

    def test_valid_manifest_and_brief(self):
        manifest = valid_manifest()
        self.assertEqual([], VALIDATOR.validate_manifest_data(manifest))
        self.assertEqual([], VALIDATOR.validate_brief_text(manifest, valid_brief()))

    def test_single_source_does_not_change_grade(self):
        manifest = valid_manifest()
        self.assertEqual("B", manifest["events"][0]["grade"])
        self.assertEqual([], VALIDATOR.validate_manifest_data(manifest))

    def test_brief_requires_manifest_derived_news_count_summary(self):
        errors = VALIDATOR.validate_brief_text(
            valid_manifest(), valid_brief().replace("本期共 1 則新聞：台灣 1 則。\n\n", "")
        )
        self.assertTrue(any("本期新聞總數" in error for error in errors))

    def test_map_requires_named_place_labels(self):
        manifest = valid_manifest()
        manifest["events"][0]["map"]["assets"][0]["place_labels"] = ["1"]
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("純數字" in error for error in errors))

    def test_traditional_chinese_output_rejects_english_only_map_label(self):
        manifest = valid_manifest()
        manifest["events"][0]["map"]["assets"][0]["place_labels"] = ["Venezuela"]
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("必須符合輸出語言繁體中文" in error for error in errors))

    def test_map_rejects_redundant_canvas_caption(self):
        manifest = valid_manifest()
        manifest["events"][0]["map"]["assets"][0]["caption"] = "地圖一：完整世界行政界線底圖；標記1為測試地點。"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("不得重複說明" in error for error in errors))
        self.assertTrue(any("不得以標記1" in error for error in errors))

    def test_blue_or_noncanonical_map_style_is_rejected(self):
        manifest = valid_manifest()
        manifest["events"][0]["map"]["assets"][0]["style_id"] = "blue-default"
        manifest["events"][0]["map"]["assets"][0]["generator"] = "platform-map"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("yellow-admin-v2" in error for error in errors))
        self.assertTrue(any("canonical renderer" in error for error in errors))

    def test_twn_map_rejects_local_zoom(self):
        manifest = valid_manifest()
        asset = manifest["events"][0]["map"]["assets"][0]
        asset["canvas_scope"] = "regional_detail"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("禁止裁切或局部放大" in error for error in errors))

    def test_glb_map_requires_complete_world_basemap(self):
        manifest = valid_manifest()
        manifest["sections"][0] = {"code": "GLB", "name": "世界", "order": 1}
        event = manifest["events"][0]
        event["event_id"] = "GLB-01"
        event["primary_section"] = "GLB"
        asset = event["map"]["assets"][0]
        asset["canvas_scope"] = "full_section"
        asset["base_map"] = "maps/generated/sections/JPN-base.png"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("禁止裁切或局部放大" in error for error in errors))
        self.assertTrue(any("canonical 完整板塊底圖" in error for error in errors))

    def test_stage_guard_catches_map_stage_deleting_images(self):
        before = valid_manifest()
        after = copy.deepcopy(before)
        after["events"][0]["map"]["rationale"] = "更新定位理由"
        after["events"][0]["images"]["assets"] = []
        errors = VALIDATOR.validate_stage_data(before, after, "build-news-maps")
        self.assertTrue(any("越權修改 TWN-01.images" in error for error in errors))

    def test_brief_rejects_gallery_or_dynamic_image_group(self):
        text = valid_brief().replace(
            "![圖一](sandbox:/tmp/image.png)",
            'genui{"async_image_group":{"query":"test"}}',
        )
        errors = VALIDATOR.validate_brief_text(valid_manifest(), text)
        self.assertTrue(any("禁止的圖廊、疊圖或動態元件" in error for error in errors))

    def test_reader_times_reject_timezone_suffixes_after_user_timezone_conversion(self):
        for suffix in ("UTC", "GMT", "+08:00", "Asia/Taipei"):
            with self.subTest(suffix=suffix):
                manifest = valid_manifest()
                manifest["events"][0]["detail"]["overview_time"] = f"8/14 05:30 {suffix}"
                manifest["events"][0]["detail"]["time"] = (
                    f"新聞時間：8/14 05:30 {suffix}；事件時間：8/14 05:00。"
                )
                text = valid_brief().replace("8/14 05:30", f"8/14 05:30 {suffix}")
                errors = VALIDATOR.validate_brief_text(manifest, text)
                self.assertTrue(
                    any("使用者時區" in error and "時區標記" in error for error in errors),
                    errors,
                )

    def test_overview_rejects_cross_section_mixed_table(self):
        text = valid_brief().replace(
            "## 逐條詳報",
            "### 中國\n\n| 編號 | 時間 | 事件 | 等級 |\n|---|---|---|---|\n| TWN-01 | 8/14 05:30 | 測試事件 | B |\n\n## 逐條詳報",
        )
        errors = VALIDATOR.validate_brief_text(valid_manifest(), text)
        self.assertTrue(any("獨立標題與表格" in error for error in errors))
        self.assertTrue(any("錯誤板塊" in error for error in errors))

    def test_brief_requires_numbered_markdown_attachment(self):
        text = valid_brief().replace(
            "![圖一](sandbox:/tmp/image.png)",
            "![官方圖片](sandbox:/tmp/image.png)",
        )
        errors = VALIDATOR.validate_brief_text(valid_manifest(), text)
        self.assertTrue(any("逐張使用 Markdown 並依序標示圖一" in error for error in errors))

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
                "labels": ["原預測", "最新預測"],
                "numeric_values": [9.64, 11.05],
                "unit": "%",
                "chart_purpose": "comparison",
                "highlight_reason": None,
                "x_axis_label": "預測版本",
                "y_axis_label": "經濟成長率（%）",
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

    def test_text_card_cannot_pass_as_chart(self):
        manifest = valid_manifest()
        manifest["events"][0]["charts"] = {
            "required": True,
            "status": "ready",
            "rationale": "比較雙方立場",
            "assets": [{
                "path": "sandbox:/tmp/text-card.png",
                "caption": "雙方立場摘要。",
                "source_names": ["可靠來源"],
                "source_urls": ["https://example.com/source"],
                "chart_type": "bar",
                "data_points": 2,
                "labels": ["俄羅斯", "烏克蘭及盟友"],
                "numeric_values": [],
                "unit": "",
                "chart_purpose": "comparison",
                "highlight_reason": None,
                "x_axis_label": "立場",
                "y_axis_label": "",
                "visual_checked": True,
                "data_checked": True,
                "width": 1200,
                "height": 800,
            }],
            "omission_reason": None,
        }
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("至少一個實際繪製的具體數值" in error for error in errors))

    def test_two_point_line_chart_is_rejected(self):
        manifest = valid_manifest()
        manifest["events"][0]["charts"] = {
            "required": True,
            "status": "ready",
            "rationale": "比較前後預測",
            "assets": [{
                "path": "sandbox:/tmp/two-point-line.png",
                "caption": "前後預測比較。",
                "source_names": ["官方來源"],
                "source_urls": ["https://example.com/source"],
                "chart_type": "line",
                "data_points": 2,
                "labels": ["原預測", "最新預測"],
                "numeric_values": [9.64, 11.05],
                "unit": "%",
                "chart_purpose": "trend",
                "highlight_reason": None,
                "x_axis_label": "預測版本",
                "y_axis_label": "經濟成長率（%）",
                "visual_checked": True,
                "data_checked": True,
                "width": 1200,
                "height": 800,
            }],
            "omission_reason": None,
        }
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("折線圖至少需要三個時間點" in error for error in errors))

    def test_single_verified_metric_card_is_allowed(self):
        manifest = valid_manifest()
        manifest["events"][0]["charts"] = {
            "required": True,
            "status": "ready",
            "rationale": "凸顯核心傷亡數字",
            "assets": [{
                "path": "sandbox:/tmp/metric-card.png",
                "caption": "資料卡一：本簡報依官方資料製作。",
                "source_names": ["官方來源"],
                "source_urls": ["https://example.com/source"],
                "chart_type": "metric_card",
                "chart_purpose": "single_metric",
                "data_points": 1,
                "labels": ["受傷人數"],
                "numeric_values": [36],
                "unit": "人",
                "highlight_reason": "此為事件最重要的公共安全規模指標",
                "x_axis_label": None,
                "y_axis_label": None,
                "visual_checked": True,
                "data_checked": True,
                "width": 1200,
                "height": 800,
            }],
            "omission_reason": None,
        }
        self.assertEqual([], VALIDATOR.validate_manifest_data(manifest))

    def test_b_grade_requires_all_source_pages_checked(self):
        manifest = valid_manifest()
        manifest["events"][0]["images"]["source_checks"] = []
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("缺少來源頁圖片檢查紀錄" in error for error in errors))

    def test_c_plus_still_requires_all_source_pages_checked(self):
        manifest = valid_manifest()
        event = manifest["events"][0]
        event["grade"] = "C+"
        event["images"]["required"] = False
        event["images"]["status"] = "not_required"
        event["images"]["source_checks"] = []
        event["images"]["assets"] = []
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("所有入選事件都必須啟用來源圖片檢查" in error for error in errors))
        self.assertTrue(any("缺少來源頁圖片檢查紀錄" in error for error in errors))

    def test_oil_spill_requires_professional_visual_by_event_type(self):
        manifest = valid_manifest()
        event = manifest["events"][0]
        event["title"] = "阿曼外海大型漏油"
        event["selection"]["category"] = "海洋污染"
        event["detail"]["event_details"] = "油污擴散至保護區。"
        event["images"]["professional_visual_required"] = False
        event["images"]["professional_visual_status"] = "not_required"
        event["images"]["professional_source_checks"] = []
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("必須依事件類型判定為 true" in error for error in errors))

    def test_no_usable_image_requires_inspection_evidence_and_reason(self):
        manifest = valid_manifest()
        check = manifest["events"][0]["images"]["source_checks"][0]
        check["usable_image_found"] = False
        check["outcome"] = "no_usable_image"
        check["detected_image_urls"] = []
        check["evidence_path"] = None
        check["failure_detail"] = None
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("缺少附件路徑" in error for error in errors))
        self.assertTrue(any("必須保存具體判定理由" in error for error in errors))

    def test_reader_brief_requires_explanation_when_event_has_no_image(self):
        manifest = valid_manifest()
        images = manifest["events"][0]["images"]
        for check in images["source_checks"] + images["professional_source_checks"]:
            check["usable_image_found"] = False
            check["outcome"] = "no_usable_image"
            check["detected_image_urls"] = []
            check["failure_detail"] = "來源頁已完整檢查，未提供與本事件相符的可用圖片。"
        images["status"] = "omitted"
        images["assets"] = []
        images["omission_reason"] = "所有已驗證來源頁均無可用圖片。"
        images["professional_visual_status"] = "not_available"
        images["professional_omission_reason"] = "官方與專業來源均未提供同期圖資。"
        images["reader_omission_note"] = "已檢查本則新聞的可靠來源，未找到可確認為本事件且適合刊載的圖片。"
        brief = valid_brief().replace(
            "**圖片：**\n\n![圖一](sandbox:/tmp/image.png)\n\n圖一：官方資訊圖（來源：官方來源）。\n\n",
            "",
        )
        errors = VALIDATOR.validate_brief_text(manifest, brief)
        self.assertTrue(any("圖片說明" in error for error in errors))


    def test_chart_attachment_cannot_replace_or_duplicate_image(self):
        manifest = valid_manifest()
        manifest["events"][0]["charts"] = {
            "required": True, "status": "ready", "rationale": "數值比較",
            "assets": [{
                "path": "sandbox:/tmp/image.png", "caption": "資料圖表一：比較。",
                "source_names": ["官方來源"], "source_urls": ["https://example.com/source"],
                "chart_type": "bar", "chart_purpose": "comparison", "data_points": 2,
                "labels": ["甲", "乙"], "numeric_values": [1, 2], "unit": "人",
                "highlight_reason": None, "x_axis_label": "類別", "y_axis_label": "人數",
                "visual_checked": True, "data_checked": True, "width": 800, "height": 600,
            }], "omission_reason": None,
        }
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("同一附件同時出現在資料圖表與圖片" in error for error in errors))

    def test_professional_visual_cannot_be_replaced_by_news_photo(self):
        manifest = valid_manifest()
        manifest["events"][0]["images"]["assets"][0]["kind"] = "news_photo"
        errors = VALIDATOR.validate_manifest_data(manifest)
        self.assertTrue(any("合格專業資訊圖" in error for error in errors))

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
