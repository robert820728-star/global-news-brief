import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_map_decisions", ROOT / "scripts" / "validate_map_decisions.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VALIDATOR)


def event(title, category, impact_scope, reason, required, status, rationale):
    return {
        "event_id": "AUS-05",
        "title": title,
        "selection": {
            "category": category,
            "impact_scope": impact_scope,
            "reason": reason,
        },
        "verification": {"claims": []},
        "detail": {"event_details": "", "analysis": ""},
        "map": {
            "required": required,
            "status": status,
            "rationale": rationale,
            "assets": [],
            "omission_reason": None,
        },
    }


def manifest(item):
    return {
        "events": [item],
        "stage_status": {"build-news-maps": "completed"},
        "final_status": "ready",
    }


class MapDecisionValidatorTests(unittest.TestCase):
    def test_great_barrier_reef_whale_migration_cannot_silently_skip_map(self):
        item = event(
            "大堡礁疑似違規鯨豚互動增加",
            "海洋保育",
            "大堡礁海洋公園與昆士蘭東岸座頭鯨遷徙帶",
            "鯨豚互動通報增加",
            False,
            "not_required",
            "只是統計新聞，不需要地圖",
        )
        errors = VALIDATOR.validate(manifest(item))
        self.assertTrue(any("疑似漏判" in error for error in errors))

    def test_spatial_event_passes_when_map_is_required(self):
        item = event(
            "大堡礁疑似違規鯨豚互動增加",
            "海洋保育",
            "大堡礁海洋公園與座頭鯨遷徙帶",
            "遷徙帶有助理解事件",
            True,
            "ready",
            "大堡礁範圍與座頭鯨遷徙帶有助理解事件空間關係",
        )
        self.assertEqual([], VALIDATOR.validate(manifest(item)))

    def test_incidental_location_can_be_not_required_with_specific_reason(self):
        item = event(
            "科技公司公布季度財報",
            "企業財報",
            "澳洲",
            "公司公布季度營收",
            False,
            "not_required",
            "公司所在地僅為澳洲，位置僅為所在地且不影響理解，事件沒有空間關係或地理範圍差異。",
        )
        self.assertEqual([], VALIDATOR.validate(manifest(item)))

    def test_pending_map_decision_blocks_completed_stage(self):
        item = event(
            "測試事件", "公共政策", "澳洲", "政策公布", False, "pending", ""
        )
        errors = VALIDATOR.validate(manifest(item))
        self.assertTrue(any("仍為 pending" in error for error in errors))
        self.assertTrue(any("不得 completed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
