#!/usr/bin/env python3
"""Validate mobile-native release coverage without redefining news behaviour."""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1.0.0"
REQUIRED_MOBILE_CONTRACT_IDS = (
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
)
IMAGE_CONTRACT_IDS = frozenset((
    "MOBILE_NATIVE_IMAGE_EVIDENCE_ROUTE",
    "MOBILE_PER_STORY_VISIBLE_IMAGE_GATE",
    "DIRECT_ARTICLE_MEDIA_DELIVERY_ROUTE",
    "IMAGE_FALLBACK_EXHAUSTION_GATE",
    "IMAGE_READER_VISIBLE_DELIVERY_GATE",
    "NATIVE_MEDIA_BLOCK_DELIVERY_GATE",
    "NATIVE_MEDIA_CAPABILITY_FALLBACK",
    "QUALIFIED_IMAGE_DELIVERY_INDEPENDENT_OF_CLAIM_CRITICAL",
    "VISUAL_DELIVERY_ONLY_RECOVERY",
))
READER_CONTRACT_IDS = frozenset((
    "READER_TEMPLATE_STRUCTURE_GATE",
    "CANONICAL_TODAY_OVERVIEW_NO_OMISSION_GATE",
    "CANONICAL_THREE_PART_READER_LAYOUT_GATE",
    "MOBILE_READER_STRUCTURE_EQUIVALENT",
    "READER_INTERNAL_REPAIR_LOG_EXCLUSION_GATE",
))
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
    expected_root = {
        "schema_version", "execution_mode", "run_id", "main_sha", "window",
        "authority_snapshot", "assertions",
    }
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
    authority_by_path: dict[str, str] = {}
    for item in snapshot:
        if not isinstance(item, dict) or set(item) != {"path", "blob_sha"}:
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
    by_id: dict[str, dict[str, Any]] = {}
    base_keys = {
        "contract_id", "status", "authority_path", "authority_blob_sha",
        "evidence_refs", "checked_at",
    }
    for item in assertions:
        if not isinstance(item, dict):
            raise ValueError("gate assertion item must be an object")
        keys = set(item)
        if not base_keys.issubset(keys) or not keys.issubset(base_keys | {"applicability_rationale"}):
            raise ValueError("gate assertion fields are invalid")
        contract_id = item["contract_id"]
        if contract_id in by_id:
            raise ValueError(f"duplicate gate assertion: {contract_id}")
        if contract_id not in REQUIRED_MOBILE_CONTRACT_IDS:
            raise ValueError(f"unknown gate assertion: {contract_id}")
        status = item["status"]
        if status not in {"passed", "not_applicable", "blocked"}:
            raise ValueError(f"invalid gate assertion status: {contract_id}")
        if status == "blocked":
            raise ValueError(f"blocked mandatory contract prevents publication: {contract_id}")
        if status == "not_applicable":
            rationale = item.get("applicability_rationale")
            if not isinstance(rationale, str) or not rationale.strip():
                raise ValueError(f"not_applicable contract requires rationale: {contract_id}")
        checked_at = item["checked_at"]
        if not isinstance(checked_at, str) or not checked_at.strip():
            raise ValueError(f"contract assertion requires checked_at: {contract_id}")
        authority_path = item["authority_path"]
        if authority_by_path.get(authority_path) != item["authority_blob_sha"]:
            raise ValueError(f"contract authority binding is invalid: {contract_id}")
        refs = item["evidence_refs"]
        if (
            not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or any(not isinstance(ref, str) or ref not in allowed_evidence_refs for ref in refs)
        ):
            raise ValueError(f"contract requires current bound artifact evidence: {contract_id}")
        by_id[contract_id] = item

    missing = set(REQUIRED_MOBILE_CONTRACT_IDS).difference(by_id)
    if missing:
        raise ValueError("mandatory contract assertions are incomplete: " + ", ".join(sorted(missing)))
    if len(by_id) != len(REQUIRED_MOBILE_CONTRACT_IDS):
        raise ValueError("mandatory contract assertion count is inconsistent")

    for contract_id in IMAGE_CONTRACT_IDS:
        if image_identity not in by_id[contract_id]["evidence_refs"]:
            raise ValueError(f"image contract assertion must bind current image evidence: {contract_id}")
    for contract_id in READER_CONTRACT_IDS:
        if reader_identity not in by_id[contract_id]["evidence_refs"]:
            raise ValueError(f"reader contract assertion must bind current reader: {contract_id}")
