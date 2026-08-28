#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()

CONTRACT_IDS = [
    "RUN_INPUT_NORMALIZATION_GATE",
    "DISCOVERY_THEN_VERIFY",
    "GDELT_RESILIENT_ACQUISITION",
    "FULL_DISCOVERY_POOL_UNCAPPED",
    "REGIONAL_SUPPLEMENT_COMPLETE_MODEL_ADMISSION_GATE",
    "MOBILE_STRUCTURAL_ADMISSION_EQUIVALENT",
    "GLOBAL_SECTION_PRIMARY_DISCOVERY_GATE",
    "PIPELINE_COUNT_RECEIPT",
    "COUNT_RECEIPT_REPAIR_ONCE",
    "SEMANTIC_EVENT_LEDGER_GATE",
    "EVENT_REGION_AND_TIME_IDENTITY_GATE",
    "POLICY_GOVERNANCE_EVIDENCE_GATE",
    "PUBLIC_VALUE_V2_NORMALIZED_WEIGHTED_SCORING",
    "CATEGORY_APPROPRIATE_EVIDENCE_ROUTE",
    "TECH_SCIENCE_EVIDENCE_ROUTE",
    "CONFLICT_MULTI_SIDE_EVIDENCE_ROUTE",
    "DISASTER_OFFICIAL_STATISTICS_ROUTE",
    "OFFICIAL_SOURCE_BIAS_GUARD",
    "MEDIA_TRANSCRIPTION_IS_NOT_VERIFICATION",
    "DOMAIN_EXPERTISE_MATCH",
    "TIMELINESS_WITH_SOURCE_LIMIT_NOTE",
    "SAME_SOURCE_RECOVERY_ORDER",
    "RUN_ARTIFACT_IDENTITY_GATE",
    "FOURTEEN_DAY_AUDIT_MERGE_UNAVAILABLE",
    "CURRENT_SCHEMA_ONLY_DURABLE_AUDIT",
    "MOBILE_COMPACT_HISTORY_SCHEMA_RULE",
    "MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE",
    "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
    "DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE",
    "IMAGE_FALLBACK_EXHAUSTION_GATE",
    "IMAGE_READER_VISIBLE_DELIVERY_GATE",
    "NATIVE_MEDIA_BLOCK_DELIVERY_GATE",
    "NATIVE_MEDIA_CAPABILITY_FALLBACK",
    "QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL",
    "VISUAL_DELIVERY_ONLY_RECOVERY",
    "READER_TEMPLATE_STRUCTURE_GATE",
    "CANONICAL_TODAY_OVERVIEW_NO_OMISSION_GATE",
    "CANONICAL_THREE_PART_READER_LAYOUT_GATE",
    "MOBILE_READER_STRUCTURE_EQUIVALENT",
    "READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE",
]

IMAGE_CONTRACT_IDS = [
    "MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE",
    "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
    "DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE",
    "IMAGE_FALLBACK_EXHAUSTION_GATE",
    "IMAGE_READER_VISIBLE_DELIVERY_GATE",
    "NATIVE_MEDIA_BLOCK_DELIVERY_GATE",
    "NATIVE_MEDIA_CAPABILITY_FALLBACK",
    "QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL",
    "VISUAL_DELIVERY_ONLY_RECOVERY",
]

READER_CONTRACT_IDS = [
    "READER_TEMPLATE_STRUCTURE_GATE",
    "CANONICAL_TODAY_OVERVIEW_NO_OMISSION_GATE",
    "CANONICAL_THREE_PART_READER_LAYOUT_GATE",
    "MOBILE_READER_STRUCTURE_EQUIVALENT",
    "READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise SystemExit(
            f"{path}: expected exactly one replacement, found {count}: {old[:120]!r}"
        )
    write(path, text.replace(old, new, 1))


def make_gate_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://github.com/robert820728-star/global-news-brief/schemas/mobile-gate-assertions.schema.json",
        "title": "Mobile mandatory release contract assertions",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "execution_mode",
            "run_id",
            "main_sha",
            "window",
            "authority_snapshot",
            "assertions",
        ],
        "properties": {
            "schema_version": {"const": "1.0.0"},
            "execution_mode": {"const": "mobile-native"},
            "run_id": {
                "type": "string",
                "pattern": "^gnb-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$",
            },
            "main_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
            "window": {
                "type": "object",
                "additionalProperties": False,
                "required": ["start", "end", "timezone"],
                "properties": {
                    "start": {"type": "string", "format": "date-time"},
                    "end": {"type": "string", "format": "date-time"},
                    "timezone": {"type": "string", "minLength": 1},
                },
            },
            "authority_snapshot": {
                "type": "array",
                "minItems": 4,
                "uniqueItems": True,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "blob_sha"],
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "blob_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                    },
                },
            },
            "assertions": {
                "type": "array",
                "minItems": len(CONTRACT_IDS),
                "maxItems": len(CONTRACT_IDS),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "contract_id",
                        "status",
                        "authority_path",
                        "authority_blob_sha",
                        "evidence_refs",
                        "checked_at",
                    ],
                    "properties": {
                        "contract_id": {"enum": CONTRACT_IDS},
                        "status": {"enum": ["passed", "not_applicable", "blocked"]},
                        "authority_path": {"type": "string", "minLength": 1},
                        "authority_blob_sha": {
                            "type": "string",
                            "pattern": "^[0-9a-f]{40}$",
                        },
                        "evidence_refs": {
                            "type": "array",
                            "minItems": 1,
                            "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "checked_at": {"type": "string", "format": "date-time"},
                        "applicability_rationale": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }


def make_validator_module() -> str:
    ids = "".join(f'    "{item}",\n' for item in CONTRACT_IDS)
    image_ids = "".join(f'    "{item}",\n' for item in IMAGE_CONTRACT_IDS)
    reader_ids = "".join(f'    "{item}",\n' for item in READER_CONTRACT_IDS)
    return f'''#!/usr/bin/env python3
"""Validate mobile-native release coverage without redefining news behaviour."""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"
REQUIRED_MOBILE_CONTRACT_IDS = (
{ids})
IMAGE_CONTRACT_IDS = frozenset((
{image_ids}))
READER_CONTRACT_IDS = frozenset((
{reader_ids}))
REQUIRED_AUTHORITY_PATHS = frozenset((
    "INSTALL.md",
    "mobile-chatgpt-daily-prompt.md",
    ".agents/skills/daily-news-brief/SKILL.md",
    "schemas/mobile-run-log.schema.json",
))


def _is_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def validate_gate_assertions(
    value: Any,
    *,
    record: dict[str, Any],
    allowed_evidence_refs: set[str],
    image_identity: str,
    reader_identity: str,
) -> None:
    expected_root = {{
        "schema_version", "execution_mode", "run_id", "main_sha", "window",
        "authority_snapshot", "assertions",
    }}
    if not isinstance(value, dict) or set(value) != expected_root:
        raise ValueError("bound gate assertions root is invalid")
    if value["schema_version"] != SCHEMA_VERSION:
        raise ValueError("bound gate assertions use an unsupported schema")
    if value["execution_mode"] != "mobile-native":
        raise ValueError("bound gate assertions require mobile-native execution_mode")
    if value["run_id"] != record.get("run_id") or value["main_sha"] != record.get("main_sha"):
        raise ValueError("bound gate assertions identity does not match the current run")
    if value["window"] != record.get("window"):
        raise ValueError("bound gate assertions window does not match the ledger")

    snapshot = value["authority_snapshot"]
    if not isinstance(snapshot, list):
        raise ValueError("gate assertions require authority_snapshot")
    authority_by_path: dict[str, str] = {{}}
    for item in snapshot:
        if not isinstance(item, dict) or set(item) != {{"path", "blob_sha"}}:
            raise ValueError("gate authority snapshot item is invalid")
        path = item.get("path")
        sha = item.get("blob_sha")
        if not isinstance(path, str) or not path or path in authority_by_path or not _is_sha(sha):
            raise ValueError("gate authority snapshot identity is invalid")
        authority_by_path[path] = sha
    missing_authorities = REQUIRED_AUTHORITY_PATHS.difference(authority_by_path)
    if missing_authorities:
        raise ValueError(
            "gate assertions are missing authority snapshots: "
            + ", ".join(sorted(missing_authorities))
        )

    assertions = value["assertions"]
    if not isinstance(assertions, list):
        raise ValueError("gate assertions require assertions array")
    by_id: dict[str, dict[str, Any]] = {{}}
    base_keys = {{
        "contract_id", "status", "authority_path", "authority_blob_sha",
        "evidence_refs", "checked_at",
    }}
    for item in assertions:
        if not isinstance(item, dict):
            raise ValueError("gate assertion item must be an object")
        keys = set(item)
        if not base_keys.issubset(keys) or not keys.issubset(base_keys | {{"applicability_rationale"}}):
            raise ValueError("gate assertion fields are invalid")
        contract_id = item["contract_id"]
        if contract_id in by_id:
            raise ValueError(f"duplicate gate assertion: {{contract_id}}")
        if contract_id not in REQUIRED_MOBILE_CONTRACT_IDS:
            raise ValueError(f"unknown gate assertion: {{contract_id}}")
        status = item["status"]
        if status not in {{"passed", "not_applicable", "blocked"}}:
            raise ValueError(f"invalid gate assertion status: {{contract_id}}")
        if status == "blocked":
            raise ValueError(f"blocked mandatory contract prevents publication: {{contract_id}}")
        if status == "not_applicable":
            rationale = item.get("applicability_rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                raise ValueError(f"not_applicable contract requires rationale: {{contract_id}}")
        checked_at = item["checked_at"]
        if not isinstance(checked_at, str) or not checked_at.strip():
            raise ValueError(f"contract assertion requires checked_at: {{contract_id}}")
        authority_path = item["authority_path"]
        if authority_by_path.get(authority_path) != item["authority_blob_sha"]:
            raise ValueError(f"contract authority binding is invalid: {{contract_id}}")
        refs = item["evidence_refs"]
        if (
            not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or any(not isinstance(ref, str) or ref not in allowed_evidence_refs for ref in refs)
        ):
            raise ValueError(f"contract requires current bound artifact evidence: {{contract_id}}")
        by_id[contract_id] = item

    missing = set(REQUIRED_MOBILE_CONTRACT_IDS).difference(by_id)
    if missing:
        raise ValueError("mandatory contract assertions are incomplete: " + ", ".join(sorted(missing)))
    if len(by_id) != len(REQUIRED_MOBILE_CONTRACT_IDS):
        raise ValueError("mandatory contract assertion count is inconsistent")

    for contract_id in IMAGE_CONTRACT_IDS:
        if image_identity not in by_id[contract_id]["evidence_refs"]:
            raise ValueError(f"image contract assertion must bind current image evidence: {{contract_id}}")
    for contract_id in READER_CONTRACT_IDS:
        if reader_identity not in by_id[contract_id]["evidence_refs"]:
            raise ValueError(f"reader contract assertion must bind current reader: {{contract_id}}")
'''


def patch_schema_and_runtime() -> None:
    write(
        "schemas/mobile-gate-assertions.schema.json",
        json.dumps(make_gate_schema(), ensure_ascii=False, indent=2) + "\n",
    )
    write("scripts/mobile_gate_assertions.py", make_validator_module())

    schema_path = ROOT / "schemas/mobile-run-log.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema["properties"]["schema_version"].get("const") != "1.6.0":
        raise SystemExit("unexpected mobile-run-log schema baseline")
    schema["properties"]["schema_version"]["const"] = "1.7.0"
    schema["required"].insert(
        schema["required"].index("image_evidence_artifact") + 1,
        "gate_assertions_artifact",
    )
    schema["properties"]["gate_assertions_artifact"] = {
        "oneOf": [
            {"type": "null"},
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["branch", "path", "blob_sha", "run_id", "main_sha", "window"],
                "properties": {
                    "branch": {"const": "run-logs"},
                    "path": {
                        "type": "string",
                        "pattern": "^logs/runs/gnb-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}/gate-assertions\\.json$",
                    },
                    "blob_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                    "run_id": {
                        "type": "string",
                        "pattern": "^gnb-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$",
                    },
                    "main_sha": {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                    "window": {"$ref": "#/properties/window/oneOf/1"},
                },
            },
        ]
    }
    schema_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    p = "scripts/manage_mobile_run_log.py"
    replace_once(p, "import run_identity\n", "import run_identity\nimport mobile_gate_assertions\n")
    replace_once(p, 'SCHEMA_VERSION = "1.6.0"', 'SCHEMA_VERSION = "1.7.0"')
    replace_once(
        p,
        '        "image_evidence_artifact",\n        "durable_audit_status",',
        '        "image_evidence_artifact",\n        "gate_assertions_artifact",\n        "durable_audit_status",',
    )
    replace_once(
        p,
        '        ("image_evidence_artifact", "visuals-completed", "image evidence artifact"),\n        ("reader_artifact", "reader-rendered", "reader artifact"),',
        '        ("image_evidence_artifact", "visuals-completed", "image evidence artifact"),\n        ("reader_artifact", "reader-rendered", "reader artifact"),\n        ("gate_assertions_artifact", "github-result-saved", "gate assertions artifact"),',
    )
    replace_once(
        p,
        '        if record["stage_index"] >= STAGE_INDEX["github-result-saved"]:\n            _require_artifact(\n                record,\n                "reader_artifact",\n                "logs/latest-reader.md",\n                "reader artifact",\n            )',
        '        if record["stage_index"] >= STAGE_INDEX["github-result-saved"]:\n            _require_artifact(\n                record,\n                "reader_artifact",\n                "logs/latest-reader.md",\n                "reader artifact",\n            )\n            _require_run_artifact(\n                record,\n                "gate_assertions_artifact",\n                "gate-assertions.json",\n                "gate assertions artifact",\n            )',
    )

    validator = '''\n\ndef _artifact_identity(artifact: dict[str, Any]) -> str:\n    return f"{artifact['path']}@{artifact['blob_sha']}"\n\n\ndef _validate_bound_gate_assertions(ledger_dir: Path | str, record: dict[str, Any]) -> None:\n    if record.get("execution_mode") != "mobile-native":\n        return\n    artifact = record.get("gate_assertions_artifact")\n    if not isinstance(artifact, dict):\n        return\n    path = _bound_artifact_path(Path(ledger_dir), artifact, "gate assertions")\n    if not path.is_file():\n        raise ValueError("bound gate assertions file is missing")\n    try:\n        value = json.loads(path.read_text(encoding="utf-8"))\n    except (OSError, json.JSONDecodeError) as error:\n        raise ValueError("bound gate assertions are not readable JSON") from error\n    fields = (\n        "candidate_audit_artifact", "verification_artifact", "map_decisions_artifact",\n        "image_evidence_artifact", "reader_artifact",\n    )\n    artifacts = [record.get(field) for field in fields]\n    if any(not isinstance(item, dict) for item in artifacts):\n        raise ValueError("gate assertions require all publication evidence artifacts")\n    allowed = {_artifact_identity(item) for item in artifacts}\n    mobile_gate_assertions.validate_gate_assertions(\n        value,\n        record=record,\n        allowed_evidence_refs=allowed,\n        image_identity=_artifact_identity(record["image_evidence_artifact"]),\n        reader_identity=_artifact_identity(record["reader_artifact"]),\n    )\n'''
    replace_once(
        p,
        "\n\ndef _validate_window(window: Any, label: str) -> None:",
        validator + "\n\ndef _validate_window(window: Any, label: str) -> None:",
    )
    replace_once(
        p,
        '        "image_evidence_artifact": None,\n        "durable_audit_status": "not_started",',
        '        "image_evidence_artifact": None,\n        "gate_assertions_artifact": None,\n        "durable_audit_status": "not_started",',
    )
    replace_once(
        p,
        "    image_evidence_artifact: dict[str, str] | None = None,\n    durable_audit_status: str | None = None,",
        "    image_evidence_artifact: dict[str, str] | None = None,\n    gate_assertions_artifact: dict[str, str] | None = None,\n    durable_audit_status: str | None = None,",
    )
    replace_once(
        p,
        '    if image_evidence_artifact is not None:\n        current["image_evidence_artifact"] = image_evidence_artifact\n    if durable_audit_status is not None:',
        '    if image_evidence_artifact is not None:\n        current["image_evidence_artifact"] = image_evidence_artifact\n    if gate_assertions_artifact is not None:\n        current["gate_assertions_artifact"] = gate_assertions_artifact\n    if durable_audit_status is not None:',
    )
    replace_once(
        p,
        '    if (\n        current.get("image_evidence_artifact") is not None\n        and (\n            current["stage_index"] >= STAGE_INDEX["reader-rendered"]\n            or "NATIVE_MEDIA_UNAVAILABLE" in current["capability_limitations"]\n        )\n    ):\n        _validate_bound_image_evidence(ledger_dir, current)\n    _atomic_write(current_path, current)',
        '    if (\n        current.get("image_evidence_artifact") is not None\n        and (\n            current["stage_index"] >= STAGE_INDEX["reader-rendered"]\n            or "NATIVE_MEDIA_UNAVAILABLE" in current["capability_limitations"]\n        )\n    ):\n        _validate_bound_image_evidence(ledger_dir, current)\n    if (\n        current.get("gate_assertions_artifact") is not None\n        and current["stage_index"] >= STAGE_INDEX["github-result-saved"]\n    ):\n        _validate_bound_gate_assertions(ledger_dir, current)\n    _atomic_write(current_path, current)',
    )
    replace_once(
        p,
        '    advance.add_argument("--image-evidence-artifact", type=Path)\n    advance.add_argument("--durable-audit-status",',
        '    advance.add_argument("--image-evidence-artifact", type=Path)\n    advance.add_argument("--gate-assertions-artifact", type=Path)\n    advance.add_argument("--durable-audit-status",',
    )
    replace_once(
        p,
        '            image_evidence_artifact=(\n                _read_artifact_reference(args.image_evidence_artifact)\n                if args.image_evidence_artifact else None\n            ),\n            durable_audit_status=args.durable_audit_status,',
        '            image_evidence_artifact=(\n                _read_artifact_reference(args.image_evidence_artifact)\n                if args.image_evidence_artifact else None\n            ),\n            gate_assertions_artifact=(\n                _read_artifact_reference(args.gate_assertions_artifact)\n                if args.gate_assertions_artifact else None\n            ),\n            durable_audit_status=args.durable_audit_status,',
    )
    replace_once(
        p,
        '        if (\n            result.get("image_evidence_artifact") is not None\n            and (\n                result["stage_index"] >= STAGE_INDEX["reader-rendered"]\n                or "NATIVE_MEDIA_UNAVAILABLE" in result["capability_limitations"]\n            )\n        ):\n            _validate_bound_image_evidence(args.input.parent, result)\n    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))',
        '        if (\n            result.get("image_evidence_artifact") is not None\n            and (\n                result["stage_index"] >= STAGE_INDEX["reader-rendered"]\n                or "NATIVE_MEDIA_UNAVAILABLE" in result["capability_limitations"]\n            )\n        ):\n            _validate_bound_image_evidence(args.input.parent, result)\n        if (\n            result.get("gate_assertions_artifact") is not None\n            and result["stage_index"] >= STAGE_INDEX["github-result-saved"]\n        ):\n            _validate_bound_gate_assertions(args.input.parent, result)\n    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))',
    )

    replace_once(
        "scripts/news_run_checkpoint.py",
        '    "schemas/mobile-run-log.schema.json",\n    ".agents/skills/daily-news-brief/SKILL.md",',
        '    "schemas/mobile-run-log.schema.json",\n    "schemas/mobile-gate-assertions.schema.json",\n    ".agents/skills/daily-news-brief/SKILL.md",',
    )
    replace_once(
        "scripts/news_run_checkpoint.py",
        '    "scripts/news_run_checkpoint.py",\n    "scripts/fetch_source_routes.py",',
        '    "scripts/news_run_checkpoint.py",\n    "scripts/mobile_gate_assertions.py",\n    "scripts/fetch_source_routes.py",',
    )


def patch_docs() -> None:
    p = "mobile-chatgpt-daily-prompt.md"
    text = read(p)
    retired = "`MOBILE_PER_STORY_VISIBLE_IMAGE_GATE`（取代整份層級的 `MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE`）"
    if text.count(retired) != 1:
        raise SystemExit("retired mobile image gate marker baseline mismatch")
    text = text.replace(retired, "`MOBILE_PER_STORY_VISIBLE_IMAGE_GATE`", 1)
    anchor = "## Same-source recovery order\n"
    if text.count(anchor) != 1:
        raise SystemExit("same-source section anchor mismatch")
    registry = "\n".join(f"- `{item}`" for item in CONTRACT_IDS)
    coverage = f'''## Mandatory mobile release contract coverage\n\n`MANDATORY_GATE_EXECUTION_ASSERTION`\n\nmobile-native 在把本輪 Reader 保存為正式 GitHub 結果（`github-result-saved`）前，必須建立並持久化 `logs/runs/<run_id>/gate-assertions.json`，再把其 Git blob 綁定到 `logs/current.json.gate_assertions_artifact`。這份 artifact 只證明本輪對 release-critical contracts 已逐項判定並有現行 artifact 證據，**不是第二份新聞規則**；實際行為仍只以 `INSTALL.md` 的權責順序與各 contract 所在權責文件為準。\n\n`MOBILE_MANDATORY_GATE_REGISTRY`：本輪 release coverage 固定包含下列 contract IDs；`schemas/mobile-gate-assertions.schema.json`、`scripts/mobile_gate_assertions.py` 與 `scripts/manage_mobile_run_log.py` 必須與此清單完全一致。缺項、重複、未知 ID、無現行 evidence 或任何 `blocked` 都不得保存正式 Reader，也不得進入完成狀態：\n\n{registry}\n\n每筆 assertion 必須保存 `contract_id`、`status`、`authority_path`、`authority_blob_sha`、`evidence_refs` 與 `checked_at`。只有規則本身具有條件適用性且本輪確實不適用時才可用 `not_applicable`，並必填 `applicability_rationale`；「沒有工具」、「看起來不需要」、「已閱讀」或單純 `passed=true` 都不算證據。`authority_snapshot` 至少綁定本輪固定 `main_sha` 下的 `INSTALL.md`、`mobile-chatgpt-daily-prompt.md`、`.agents/skills/daily-news-brief/SKILL.md` 與 `schemas/mobile-run-log.schema.json` Git blob SHA。\n\n`evidence_refs` 只能引用本輪已綁定的 candidate audit、verification、map decisions、image evidence 或 Reader Git blob identity。所有圖片 contracts 都必須直接引用同一 run 的 `image-evidence.json@<blob_sha>`；因此「來源確實沒有合格圖片才可省略」不得被重新解讀成「圖片為 optional」。Reader 結構 contracts 必須直接引用本輪 `logs/latest-reader.md@<blob_sha>`。若 selected event 缺逐則 image evidence、四層搜尋尚未依規則窮盡、找到合格圖片卻未完成可見交付、Reader 結構未通過，或 evidence 與本輪 identity 不一致，release receipt 都不得通過。\n\n`CONVERSATION_READER_BYTE_IDENTITY_GATE` 屬於正式 Reader 已保存後的最後對話交付邊界，不能在 `github-result-saved` 前假裝已有客戶端回執，因此不納入此 pre-handoff receipt；它仍由下方既有 delivery contract 約束，且沒有外部回執時不得宣稱 `client_confirmed`。\n\n'''
    text = text.replace(anchor, coverage + anchor, 1)
    stale = "正常只維護 `logs/current.json`、`logs/previous.json`、`logs/latest-candidate-audit.json` 與 `logs/latest-reader.md`，不得寫入 `main`，也不得逐新聞或逐工具呼叫建立紀錄。"
    replacement = "正常只維護 `logs/current.json`、`logs/previous.json`、`logs/latest-candidate-audit.json`、`logs/latest-reader.md`，以及本輪 `logs/runs/<run_id>/` 下由 stage 契約明確要求的 candidate audit、verification、map decisions、image evidence 與 gate assertions；不得寫入 `main`，也不得逐新聞或逐工具呼叫另造紀錄。"
    if text.count(stale) != 1:
        raise SystemExit("mobile durable-write paragraph baseline mismatch")
    text = text.replace(stale, replacement, 1)
    write(p, text)

    p = "INSTALL.md"
    text = read(p)
    old = "- `schemas/mobile-run-log.schema.json`\n\n### 核心工具與地圖資產"
    if text.count(old) != 1:
        raise SystemExit("INSTALL schema list anchor mismatch")
    text = text.replace(
        old,
        "- `schemas/mobile-run-log.schema.json`\n- `schemas/mobile-gate-assertions.schema.json`\n\n### 核心工具與地圖資產",
        1,
    )
    old = "- `scripts/manage_mobile_run_log.py`\n- `schemas/mobile-run-log.schema.json`\n- `mobile-chatgpt-start-prompt.md`"
    if text.count(old) != 1:
        raise SystemExit("INSTALL mobile support anchor mismatch")
    text = text.replace(
        old,
        "- `scripts/manage_mobile_run_log.py`\n- `scripts/mobile_gate_assertions.py`\n- `schemas/mobile-run-log.schema.json`\n- `schemas/mobile-gate-assertions.schema.json`\n- `mobile-chatgpt-start-prompt.md`",
        1,
    )
    recovery_anchor = "## 七、局部恢復指令\n"
    if text.count(recovery_anchor) != 1:
        raise SystemExit("INSTALL recovery anchor mismatch")
    install_gate = '''### Mandatory mobile release gate assertion\n\n`MANDATORY_GATE_EXECUTION_ASSERTION`：mobile-native 在 `github-result-saved` 前必須以本輪固定 `main_sha` 的權責文件與本輪 artifacts 建立 `logs/runs/<run_id>/gate-assertions.json`，並將其 Git blob 綁定至 `gate_assertions_artifact`。這是 release coverage receipt，不是第二份規則；contract 清單以 `mobile-chatgpt-daily-prompt.md` 的 `MOBILE_MANDATORY_GATE_REGISTRY` 為人類可讀權威，schema 與 runtime validator 必須與該清單完全一致。\n\n- receipt 必須綁定同一 `run_id`、`main_sha`、精確 24 小時 `window` 與權責文件 Git blob SHA；不得引用前一輪或快取 authority snapshot。\n- 每個 registry contract 都必須逐項 `passed`，或只在規則本身具條件適用性且本輪有證據不適用時寫 `not_applicable`；缺項、重複、未知、無現行 artifact evidence 或 `blocked` 一律不得保存正式 Reader。\n- 圖片 contracts 的 `evidence_refs` 必須直接綁定本輪 `image-evidence.json@<blob_sha>`，Reader 結構 contracts 必須直接綁定本輪 `logs/latest-reader.md@<blob_sha>`。模型只說「已讀取／已遵守」不是 evidence。\n- `NATIVE_MEDIA_UNAVAILABLE` 仍依既有規則停在 `running + visuals-completed`；這種尚未能進 Reader 發布的 run 不要求偽造 release receipt。視覺恢復後才建立／更新 receipt。\n- `CONVERSATION_READER_BYTE_IDENTITY_GATE` 保留在真正對話交付邊界，不因 pre-handoff receipt 而提前宣稱已完成。\n- full-runtime 不使用 mobile gate receipt；其 completion 仍由 bootstrap receipt、checkpoint、manifest、stage validators、publisher 與 release receipt 驗證。\n\n'''
    text = text.replace(recovery_anchor, install_gate + recovery_anchor, 1)
    stage11 = "| 11 final authority 與 render | collect stage 已 completed／依 profile 合法 omission | full-runtime 首次執行 `validate_news_brief.py manifest` 到 `OK`，由 manifest 渲染 reader 並執行 brief validator；mobile-native 由 run-scoped selected events 與已驗證事實渲染 reader，再執行既有 `MOBILE_READER_STRUCTURE_EQUIVALENT` |"
    if text.count(stage11) != 1:
        raise SystemExit("INSTALL stage 11 baseline mismatch")
    text = text.replace(
        stage11,
        "| 11 final authority 與 render | collect stage 已 completed／依 profile 合法 omission | full-runtime 首次執行 `validate_news_brief.py manifest` 到 `OK`，由 manifest 渲染 reader 並執行 brief validator；mobile-native 由 run-scoped selected events 與已驗證事實渲染 reader，執行 `MOBILE_READER_STRUCTURE_EQUIVALENT`；正式保存 Reader 前建立並驗證 `gate-assertions.json`，`MANDATORY_GATE_EXECUTION_ASSERTION` 未通過不得進 `github-result-saved` |",
        1,
    )
    test_anchor = "- map decision、chart decision 與每則 image check 均已執行；full-runtime 下載失敗有截圖備援證據，mobile-native 有文章直接媒體 URL、原生圖片／圖片卡及後續來源嘗試結果。"
    if text.count(test_anchor) != 1:
        raise SystemExit("INSTALL first-test anchor mismatch")
    text = text.replace(
        test_anchor,
        test_anchor
        + "\n- mobile-native 在正式保存 Reader 前已保存並綁定 `gate-assertions.json`；registry 無缺項、重複、未知、blocked 或非本輪 evidence，圖片 assertions 綁定本輪 image-evidence blob，Reader assertions 綁定本輪 Reader blob。",
        1,
    )
    write(p, text)

    replace_once(
        ".agents/skills/daily-news-brief/SKILL.md",
        "並在進入 `selection-verified`／`visuals-completed`／`reader-rendered`／`github-result-saved` 前依序綁定 candidate audit／verification／map+image／Reader。不得建立 mobile checkpoint 或 manifest。",
        "並在進入 `selection-verified`／`visuals-completed`／`reader-rendered`／`github-result-saved` 前依序綁定 candidate audit／verification／map+image／Reader+gate assertions。正式保存 Reader 前須通過 `MANDATORY_GATE_EXECUTION_ASSERTION`；不得以模型自我宣告替代本輪 artifact evidence。不得建立 mobile checkpoint 或 manifest。",
    )

    p = ".agents/skills/recover-news-run/SKILL.md"
    text = read(p)
    old = "進入各邊界前讀回並核對現有 Git blob binding：`selection-verified` 需要 candidate audit、`visuals-completed` 需要 verification、`reader-rendered` 需要 map decisions 與 image evidence、`github-result-saved` 需要 Reader。"
    if text.count(old) != 1:
        raise SystemExit("recover artifact-boundary baseline mismatch")
    text = text.replace(
        old,
        "進入各邊界前讀回並核對現有 Git blob binding：`selection-verified` 需要 candidate audit、`visuals-completed` 需要 verification、`reader-rendered` 需要 map decisions 與 image evidence、`github-result-saved` 需要 Reader 與 gate assertions。gate assertions 缺失、blocked 或 evidence binding 失敗時只恢復真正缺少的 release evidence，不得重跑已完成 discovery、評分或驗證。",
        1,
    )
    old = "mobile-native 則要求 run-scoped audit 的 selected ids 與 Reader 守恆、上述 artifact boundaries 已綁定、沒有 unresolved recovery target，才可進 `delivery-handoff`。"
    if text.count(old) != 1:
        raise SystemExit("recover delivery-boundary baseline mismatch")
    text = text.replace(
        old,
        "mobile-native 則要求 run-scoped audit 的 selected ids 與 Reader 守恆、上述 artifact boundaries（含已驗證 `gate_assertions_artifact`）已綁定、沒有 unresolved recovery target，才可進 `delivery-handoff`。",
        1,
    )
    write(p, text)

    p = "news-brief-settings.md"
    text = read(p)
    anchor = "full-runtime 的 post-selection event exchange 必須遵守 `schemas/news-event-manifest.schema.json`；mobile-native 以 run-scoped candidate audit 的 selected events 與既有 mobile evidence／ledger contracts 為 publication authority，不建立或冒充通過 full-runtime manifest。"
    if text.count(anchor) != 1:
        raise SystemExit("settings mode-boundary baseline mismatch")
    text = text.replace(
        anchor,
        anchor
        + " mobile-native 正式保存 Reader 前另依 `MANDATORY_GATE_EXECUTION_ASSERTION` 綁定本輪 release coverage receipt；receipt 只能引用本輪已綁定 artifacts，且不得覆寫各權責文件的行為內容。",
        1,
    )
    write(p, text)

    write(
        "mobile-chatgpt-start-prompt.md",
        '''# 手機 ChatGPT 相容啟動指令\n\n本檔只提供舊書籤／舊連結的相容導引，**不是另一個安裝入口，也不是 Scheduled Task 規則來源**。目前唯一安裝入口與排程 prompt 權威是 repository 當下最新 `INSTALL.md`。\n\n若從手機一般 ChatGPT 開始，直接貼：\n\n```text\n請使用以下 GitHub 專案建立我的每日新聞簡報：\nhttps://github.com/robert820728-star/global-news-brief\n\n請先完整閱讀當下最新 main 的 INSTALL.md，並以 INSTALL.md 作為唯一安裝與執行入口；依其中的 Scheduled Task 排程指令唯一契約建立排程。不要把本檔、mobile-chatgpt-daily-prompt.md 或任何圖片／驗證細節複製成第二份 task prompt。每次觸發都 fresh resolve 最新 main，執行進度、成功結果或最早不可恢復 blocker 只回覆到建立此排程的目前對話，不得另開新對話。\n```\n\n排程時間、時區、區域與監控類型若已由使用者指定就直接沿用；未指定時由 `INSTALL.md` 的現行規則處理。mobile-native 的 discovery、評分、驗證、圖片、release gate assertions、Reader、恢復與持久化契約均由每次觸發時的最新 `INSTALL.md` 及其權責文件取得，本檔不複製那些規則，避免版本漂移。\n''',
    )

    p = "README.md"
    text = read(p)
    start = text.index("## 手機 ChatGPT 基礎排程\n")
    end = text.index("\n## 快速安裝\n", start)
    mobile = '''## 手機 ChatGPT 基礎排程\n\n`INSTALL.md` 是唯一安裝入口。一般手機 ChatGPT／Scheduled Task 也先從 `INSTALL.md` 開始，由它在每次實際觸發時依 capability routing 選擇 `mobile-native` 或 `full-runtime`，再讀取對應權責文件；不得把 `mobile-chatgpt-daily-prompt.md`、圖片規則或其他執行細節複製成第二份 Scheduled Task prompt。`mobile-chatgpt-start-prompt.md` 只保留給舊書籤作相容導引。\n\nmobile-native 仍必須完成 discovery、語意事件、Public Value V2 評分、驗證、逐則圖片 evidence 與 canonical reader；正式保存 Reader 前另以 `MANDATORY_GATE_EXECUTION_ASSERTION` 保存 run-scoped release coverage receipt。來源確實沒有合格圖片時才可依權責規則省略；已確認合格圖片但交付失敗時仍停在同一 run 的視覺恢復。執行進度與成功結果只回覆到建立該排程的原 ChatGPT 對話，不另開結果對話。\n'''
    text = text[:start] + mobile + text[end:]
    text = text.replace(
        "完成後，每次排程都會重新讀取 repo 最新規則，並以獨立結果對話輸出當日新聞。",
        "完成後，每次排程都會重新讀取 repo 最新規則，並把當輪進度、成功結果或最早不可恢復 blocker 回覆到建立該排程的原對話。",
    )
    text = text.replace(
        "- `mobile-chatgpt-start-prompt.md`：手機一般 ChatGPT 建立低消耗排程的貼上指令\n- `mobile-chatgpt-daily-prompt.md`：手機排程每輪重新讀取的基礎新聞規則",
        "- `mobile-chatgpt-start-prompt.md`：舊手機入口的相容導引；重新導向唯一安裝入口 `INSTALL.md`\n- `mobile-chatgpt-daily-prompt.md`：由 `INSTALL.md` 導向的 mobile-native 詳細每日執行契約",
    )
    write(p, text)

    p = "VERSION-RECORD.md"
    text = read(p)
    heading = "# Version Record / 版本紀錄\n\n"
    if not text.startswith(heading):
        raise SystemExit("version record heading mismatch")
    entry = '''## v0.6.0-rc.22 — Mandatory mobile release gate assertion / Mobile 必要 Release Gate 執行證明\n\n- Reason / 建立原因：Scheduled Task 的 launcher 刻意只 fresh-resolve 最新 `INSTALL.md`，避免把圖片、驗證或評分規則複製成第二份 prompt；但 mobile-native 仍可能因模型漏讀、錯誤摘要或把「窮盡後可省略」曲解成「optional」而在文字上自稱完成。既有 image-evidence validator 已能檢查逐則圖片與 fallback 守恆，缺少的是跨權責 contract 的 release coverage 證明。\n- Approach / 作法：新增 `gate-assertions.json`、`schemas/mobile-gate-assertions.schema.json` 與 `scripts/mobile_gate_assertions.py`，由既有 `manage_mobile_run_log.py` 在 `github-result-saved` 發布邊界強制驗證。receipt 綁定同一 run/main/window、權責文件 blob、以及本輪 candidate audit／verification／map／image／Reader blobs；圖片 contracts 必須引用本輪 image evidence，Reader 結構 contracts 必須引用本輪 Reader。把 gate 放在 publish boundary 而不是 render 前，是為了避免 Reader 尚未存在時要求證明 Reader 結構的循環依賴。\n- Non-goals / 不修改：不把圖片或其他執行規則複製進 Scheduled Task prompt，不新增第二套新聞行為權威，不改 discovery routes、Public Value V2、C 級門檻、圖片四層 fallback、`NATIVE_MEDIA_UNAVAILABLE` 視覺恢復語義或 full-runtime completion state machine。`CONVERSATION_READER_BYTE_IDENTITY_GATE` 仍留在真正對話 delivery 邊界，不用 pre-handoff receipt 假裝已有客戶端回執。\n- Validation / 驗證：registry／schema／runtime constants 必須完全一致；ledger regressions 拒絕缺 receipt、blocked／缺項／重複／未知 contract、非本輪 artifact evidence、圖片 assertion 未綁 image evidence、Reader assertion 未綁 Reader。active-surface residue tests 禁止退役圖片 gate、舊直接 mobile 規則入口與「獨立結果對話」。bootstrap required paths 與 deterministic capsule 同步包含新 schema/helper；focused tests、完整 repository suite、capsule verification、feature final audit 與 main CI 均為 release gate。\n- Result / 結果：Source candidate until focused/full regression, capsule verification, final repository-wide conflict/residue audit and remote main CI all pass.\n\n'''
    write(p, heading + entry + text[len(heading) :])


def patch_tests() -> None:
    p = "tests/test_manage_mobile_run_log.py"
    text = read(p)
    old = '    def mobile_artifacts(self):\n        self.write_candidate_audit(["GLB-01"])\n        self.write_image_evidence(self.delivered_image_event())\n        return {'
    if text.count(old) != 1:
        raise SystemExit("mobile_artifacts baseline mismatch")
    text = text.replace(
        old,
        '    def mobile_artifacts(self):\n        self.write_candidate_audit(["GLB-01"])\n        self.write_image_evidence(self.delivered_image_event())\n        self.write_gate_assertions()\n        return {',
        1,
    )
    old = '            "github-result-saved": {\n                "reader_artifact": artifact_reference(\n                    "logs/latest-reader.md", "b" * 40\n                )\n            },'
    if text.count(old) != 1:
        raise SystemExit("github-result artifact baseline mismatch")
    text = text.replace(
        old,
        '            "github-result-saved": {\n                "reader_artifact": artifact_reference(\n                    "logs/latest-reader.md", "b" * 40\n                ),\n                "gate_assertions_artifact": artifact_reference(\n                    f"logs/runs/{RUN_1}/gate-assertions.json", "c" * 40\n                ),\n            },',
        1,
    )
    helper_anchor = '    def write_candidate_audit(self, selected_event_ids):\n'
    if text.count(helper_anchor) != 1:
        raise SystemExit("test helper anchor mismatch")
    helper = '''    def write_gate_assertions(self, *, blocked=None, omit=None, image_ref=None, reader_ref=None):\n        path = self.ledger_dir / "logs" / "runs" / RUN_1 / "gate-assertions.json"\n        path.parent.mkdir(parents=True, exist_ok=True)\n        authorities = {\n            "INSTALL.md": "1" * 40,\n            "mobile-chatgpt-daily-prompt.md": "2" * 40,\n            ".agents/skills/daily-news-brief/SKILL.md": "3" * 40,\n            "schemas/mobile-run-log.schema.json": "4" * 40,\n        }\n        audit_ref = f"logs/runs/{RUN_1}/candidate-audit.json@{'a' * 40}"\n        image_ref = image_ref or f"logs/runs/{RUN_1}/image-evidence.json@{'d' * 40}"\n        reader_ref = reader_ref or f"logs/latest-reader.md@{'b' * 40}"\n        assertions = []\n        for contract_id in self.module.mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS:\n            if contract_id == omit:\n                continue\n            refs = [audit_ref]\n            if contract_id in self.module.mobile_gate_assertions.IMAGE_CONTRACT_IDS:\n                refs = [image_ref]\n            elif contract_id in self.module.mobile_gate_assertions.READER_CONTRACT_IDS:\n                refs = [reader_ref]\n            assertions.append({\n                "contract_id": contract_id,\n                "status": "blocked" if contract_id == blocked else "passed",\n                "authority_path": "mobile-chatgpt-daily-prompt.md",\n                "authority_blob_sha": authorities["mobile-chatgpt-daily-prompt.md"],\n                "evidence_refs": refs,\n                "checked_at": "2026-08-17T22:35:00Z",\n            })\n        path.write_text(json.dumps({\n            "schema_version": "1.0.0",\n            "execution_mode": "mobile-native",\n            "run_id": RUN_1,\n            "main_sha": MAIN_SHA,\n            "window": RUN_WINDOW,\n            "authority_snapshot": [\n                {"path": key, "blob_sha": value} for key, value in authorities.items()\n            ],\n            "assertions": assertions,\n        }), encoding="utf-8")\n        return path\n\n'''
    text = text.replace(helper_anchor, helper + helper_anchor, 1)
    old = '        self.assertIsNone(current["image_evidence_artifact"])\n        self.assertEqual(current["durable_audit_status"], "not_started")'
    if text.count(old) != 1:
        raise SystemExit("prepare assertion baseline mismatch")
    text = text.replace(
        old,
        '        self.assertIsNone(current["image_evidence_artifact"])\n        self.assertIsNone(current["gate_assertions_artifact"])\n        self.assertEqual(current["durable_audit_status"], "not_started")',
        1,
    )
    anchor = '    def test_mobile_native_requires_reader_before_github_result_saved(self):\n'
    if text.count(anchor) != 1:
        raise SystemExit("mobile regression insertion anchor mismatch")
    regressions = '''    def test_mobile_native_requires_gate_assertions_before_github_result_saved(self):\n        self.module.prepare_run(\n            self.ledger_dir, run_id=RUN_1, scheduled_for="2026-08-18T06:00:00+08:00",\n            updated_at="2026-08-17T21:58:00Z", execution_mode="mobile-native"\n        )\n        artifacts = self.mobile_artifacts()\n        self.advance_to("reader-rendered", stage_kwargs=artifacts)\n        kwargs = dict(artifacts["github-result-saved"])\n        kwargs.pop("gate_assertions_artifact")\n        with self.assertRaisesRegex(ValueError, "gate assertions artifact"):\n            self.module.advance_run(\n                self.ledger_dir, run_id=RUN_1, stage="github-result-saved",\n                updated_at="2026-08-17T22:40:00Z", **kwargs\n            )\n\n    def test_mobile_native_rejects_blocked_contract_assertion(self):\n        self.module.prepare_run(\n            self.ledger_dir, run_id=RUN_1, scheduled_for="2026-08-18T06:00:00+08:00",\n            updated_at="2026-08-17T21:58:00Z", execution_mode="mobile-native"\n        )\n        artifacts = self.mobile_artifacts()\n        self.write_gate_assertions(blocked="DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE")\n        self.advance_to("reader-rendered", stage_kwargs=artifacts)\n        with self.assertRaisesRegex(ValueError, "blocked mandatory contract"):\n            self.module.advance_run(\n                self.ledger_dir, run_id=RUN_1, stage="github-result-saved",\n                updated_at="2026-08-17T22:40:00Z", **artifacts["github-result-saved"]\n            )\n\n    def test_mobile_native_rejects_missing_contract_assertion(self):\n        self.module.prepare_run(\n            self.ledger_dir, run_id=RUN_1, scheduled_for="2026-08-18T06:00:00+08:00",\n            updated_at="2026-08-17T21:58:00Z", execution_mode="mobile-native"\n        )\n        artifacts = self.mobile_artifacts()\n        self.write_gate_assertions(omit="IMAGE_FALLBACK_EXHAUSTION_GATE")\n        self.advance_to("reader-rendered", stage_kwargs=artifacts)\n        with self.assertRaisesRegex(ValueError, "mandatory contract assertions are incomplete"):\n            self.module.advance_run(\n                self.ledger_dir, run_id=RUN_1, stage="github-result-saved",\n                updated_at="2026-08-17T22:40:00Z", **artifacts["github-result-saved"]\n            )\n\n    def test_mobile_native_rejects_image_contract_not_bound_to_current_image_evidence(self):\n        self.module.prepare_run(\n            self.ledger_dir, run_id=RUN_1, scheduled_for="2026-08-18T06:00:00+08:00",\n            updated_at="2026-08-17T21:58:00Z", execution_mode="mobile-native"\n        )\n        artifacts = self.mobile_artifacts()\n        self.write_gate_assertions(image_ref=f"logs/latest-reader.md@{'b' * 40}")\n        self.advance_to("reader-rendered", stage_kwargs=artifacts)\n        with self.assertRaisesRegex(ValueError, "image contract assertion"):\n            self.module.advance_run(\n                self.ledger_dir, run_id=RUN_1, stage="github-result-saved",\n                updated_at="2026-08-17T22:40:00Z", **artifacts["github-result-saved"]\n            )\n\n'''
    text = text.replace(anchor, regressions + anchor, 1)
    write(p, text)

    contract_test = '''import json\nimport re\nimport sys\nimport unittest\nfrom pathlib import Path\n\nROOT = Path(__file__).resolve().parents[1]\nSCRIPTS = ROOT / "scripts"\nif str(SCRIPTS) not in sys.path:\n    sys.path.insert(0, str(SCRIPTS))\nimport mobile_gate_assertions\n\nclass MobileGateAssertionsContractTests(unittest.TestCase):\n    def test_registry_matches_schema_runtime_and_mobile_prompt(self):\n        schema = json.loads((ROOT / "schemas/mobile-gate-assertions.schema.json").read_text(encoding="utf-8"))\n        schema_ids = schema["properties"]["assertions"]["items"]["properties"]["contract_id"]["enum"]\n        prompt = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")\n        block = prompt.split("`MOBILE_MANDATORY_GATE_REGISTRY`", 1)[1].split("每筆 assertion", 1)[0]\n        prompt_ids = re.findall(r"^- `([A-Z0-9_]+)`$", block, re.MULTILINE)\n        self.assertEqual(list(mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS), schema_ids)\n        self.assertEqual(list(mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS), prompt_ids)\n        self.assertEqual(len(prompt_ids), len(set(prompt_ids)))\n        for contract_id in mobile_gate_assertions.REQUIRED_MOBILE_CONTRACT_IDS:\n            self.assertIn(f"`{contract_id}`", prompt)\n        for required in (\n            "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",\n            "DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE",\n            "IMAGE_FALLBACK_EXHAUSTION_GATE",\n            "IMAGE_READER_VISIBLE_DELIVERY_GATE",\n            "NATIVE_MEDIA_BLOCK_DELIVERY_GATE",\n            "QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL",\n            "VISUAL_DELIVERY_ONLY_RECOVERY",\n        ):\n            self.assertIn(required, mobile_gate_assertions.IMAGE_CONTRACT_IDS)\n\n    def test_active_authorities_require_release_assertion(self):\n        for relative in (\n            "INSTALL.md", "mobile-chatgpt-daily-prompt.md", "news-brief-settings.md",\n            ".agents/skills/daily-news-brief/SKILL.md", ".agents/skills/recover-news-run/SKILL.md",\n        ):\n            self.assertIn("MANDATORY_GATE_EXECUTION_ASSERTION", (ROOT / relative).read_text(encoding="utf-8"), relative)\n        schema = json.loads((ROOT / "schemas/mobile-run-log.schema.json").read_text(encoding="utf-8"))\n        self.assertEqual("1.7.0", schema["properties"]["schema_version"]["const"] )\n        self.assertIn("gate_assertions_artifact", schema["required"])\n\n    def test_active_surfaces_have_no_retired_mobile_gate_or_alternate_result_conversation(self):\n        paths = [\n            ROOT / "INSTALL.md", ROOT / "README.md", ROOT / "mobile-chatgpt-start-prompt.md",\n            ROOT / "mobile-chatgpt-daily-prompt.md", ROOT / "daily-schedule-prompt.md", ROOT / "news-brief-settings.md",\n        ]\n        paths.extend((ROOT / ".agents/skills").rglob("*.md"))\n        forbidden = (\n            "MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE",\n            "以獨立結果對話輸出當日新聞",\n            "GitHub 規則來源：https://github.com/robert820728-star/global-news-brief/blob/main/mobile-chatgpt-daily-prompt.md",\n        )\n        hits = []\n        for path in paths:\n            body = path.read_text(encoding="utf-8")\n            for phrase in forbidden:\n                if phrase in body:\n                    hits.append(f"{path.relative_to(ROOT)}: {phrase}")\n        self.assertEqual([], hits)\n\n    def test_start_prompt_is_compatibility_redirect_only(self):\n        text = (ROOT / "mobile-chatgpt-start-prompt.md").read_text(encoding="utf-8")\n        self.assertIn("唯一安裝入口", text)\n        self.assertIn("INSTALL.md", text)\n        self.assertIn("不要把本檔", text)\n        self.assertNotIn("最低驗收不可省略", text)\n        self.assertNotIn("不要使用 Thinking 或 Pro", text)\n\n    def test_post_handoff_byte_identity_gate_is_not_falsely_preasserted(self):\n        prompt = (ROOT / "mobile-chatgpt-daily-prompt.md").read_text(encoding="utf-8")\n        block = prompt.split("`MOBILE_MANDATORY_GATE_REGISTRY`", 1)[1].split("每筆 assertion", 1)[0]\n        self.assertNotIn("CONVERSATION_READER_BYTE_IDENTITY_GATE", block)\n        self.assertIn("CONVERSATION_READER_BYTE_IDENTITY_GATE", prompt)\n\nif __name__ == "__main__":\n    unittest.main()\n'''
    write("tests/test_mobile_gate_assertions_contract.py", contract_test)

    p = "tests/test_no_obsolete_contracts.py"
    text = read(p)
    anchor = "    def test_active_execution_contracts_have_no_retired_relevance_or_recovery_prose(self):\n"
    if text.count(anchor) != 1:
        raise SystemExit("no-obsolete insertion anchor mismatch")
    method = '''    def test_active_execution_contracts_have_no_retired_mobile_image_gate(self):\n        paths = [\n            ROOT / "INSTALL.md", ROOT / "README.md", ROOT / "mobile-chatgpt-start-prompt.md",\n            ROOT / "mobile-chatgpt-daily-prompt.md", ROOT / "daily-schedule-prompt.md", ROOT / "news-brief-settings.md",\n        ]\n        paths.extend((ROOT / ".agents" / "skills").rglob("*.md"))\n        retired = "MOBILE_" + "B_OR_HIGHER_VISIBLE_IMAGE_GATE"\n        hits = [str(path.relative_to(ROOT)) for path in paths if retired in path.read_text(encoding="utf-8")]\n        self.assertEqual([], hits)\n\n'''
    text = text.replace(anchor, method + anchor, 1)
    write(p, text)


def final_static_stop_loss() -> None:
    active_roots = [
        "INSTALL.md",
        "README.md",
        "mobile-chatgpt-start-prompt.md",
        "mobile-chatgpt-daily-prompt.md",
        "daily-schedule-prompt.md",
        "news-brief-settings.md",
        ".agents/skills",
        "schemas",
        "scripts",
    ]
    forbidden = (
        "MOBILE_B_OR_HIGHER_VISIBLE_IMAGE_GATE",
        "以獨立結果對話輸出當日新聞",
        "GitHub 規則來源：https://github.com/robert820728-star/global-news-brief/blob/main/mobile-chatgpt-daily-prompt.md",
    )
    hits: list[str] = []
    for root_name in active_roots:
        root = ROOT / root_name
        candidates = [root] if root.is_file() else [item for item in root.rglob("*") if item.is_file()]
        for candidate in candidates:
            if candidate.suffix.lower() not in {".md", ".json", ".py", ".yaml", ".yml"}:
                continue
            body = candidate.read_text(encoding="utf-8")
            for phrase in forbidden:
                if phrase in body:
                    hits.append(f"{candidate.relative_to(ROOT)}: {phrase}")
    if hits:
        raise SystemExit("active contract residue:\n" + "\n".join(hits))

    prompt = read("mobile-chatgpt-daily-prompt.md")
    for contract_id in CONTRACT_IDS:
        if f"`{contract_id}`" not in prompt:
            raise SystemExit(f"registry contract is not present in mobile authority: {contract_id}")


def main() -> None:
    patch_schema_and_runtime()
    patch_docs()
    patch_tests()
    final_static_stop_loss()
    SELF.unlink()


if __name__ == "__main__":
    main()
