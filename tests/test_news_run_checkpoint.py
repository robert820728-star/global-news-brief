import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "news_run_checkpoint.py"
SPEC = importlib.util.spec_from_file_location("news_run_checkpoint", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def make_bootstrap(root: Path):
    files = []
    for rel in MODULE.BOOTSTRAP_REQUIRED_PATHS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(("fixture:" + rel).encode("utf-8"))
        files.append({
            "path": rel,
            "source_blob_sha": MODULE.git_blob_sha1(path),
            "sha256": MODULE.sha256_file(path),
            "size": path.stat().st_size,
        })
    receipt = {
        "schema_version": MODULE.BOOTSTRAP_SCHEMA_VERSION,
        "status": "completed",
        "repository": MODULE.REPOSITORY_FULL_NAME,
        "ref": "main",
        "commit_sha": "a" * 40,
        "materialization_method": "github-connector-capsule",
        "materialization_scope": "verified-runtime-capsule",
        "workspace_root": str(root.resolve()),
        "materialized_at": "2026-08-16T00:00:00+08:00",
        "capsule": {
            "source_commit": "b" * 40,
            "manifest_blob_sha": "c" * 40,
            "manifest_sha256": "d" * 64,
            "payload_sha256": "e" * 64,
            "runtime_fingerprint": "f" * 64,
            "chunk_count": 1,
            "chunks": [{"name": "capsule.part0001.txt", "sha256": "1" * 64, "size": 8}],
        },
        "files": files,
    }
    receipt_path = root / "bootstrap-workspace.json"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    return receipt, receipt_path


class NewsRunCheckpointTests(unittest.TestCase):
    def test_bootstrap_receipt_requires_every_install_runtime_entrypoint(self):
        install = (ROOT / "INSTALL.md").read_text(encoding="utf-8")
        preflight = install.split("## 一、安裝前驗證", 1)[1].split("## 二、", 1)[0]
        expected = set(re.findall(
            r"`((?:\.agents|bootstrap|scripts|schemas|maps)/[^`]+|[^`/]+\.(?:md|json|yaml))`",
            preflight,
        ))

        self.assertTrue(expected.issubset(set(MODULE.BOOTSTRAP_REQUIRED_PATHS)))

    def test_source_scan_completion_requires_all_canonical_artifacts(self):
        self.assertEqual(
            ("source_candidates", "relevance_gate", "model_source_candidates"),
            MODULE.REQUIRED_STAGE_ARTIFACTS["source-scan"],
        )

    def test_stage_cannot_start_before_predecessor_completes(self):
        checkpoint = MODULE.create_checkpoint("run-1", "a", "b")
        with self.assertRaisesRegex(ValueError, "前一階段未完成"):
            MODULE.mark_stage(
                checkpoint, "preprocess-news-candidates", "running"
            )

    def test_stage_cannot_complete_without_running_first(self):
        checkpoint = MODULE.create_checkpoint("run-1", "a", "b")
        with self.assertRaisesRegex(ValueError, "必須先標記為 running"):
            MODULE.mark_stage(checkpoint, "source-scan", "completed")

    def test_completed_stage_requires_its_named_artifact(self):
        checkpoint = MODULE.create_checkpoint("run-1", "a", "b")
        MODULE.mark_stage(checkpoint, "source-scan", "running")
        with self.assertRaisesRegex(ValueError, "source_candidates"):
            MODULE.mark_stage(checkpoint, "source-scan", "completed")

    def test_incomplete_checkpoint_is_fail_closed(self):
        checkpoint = MODULE.create_checkpoint(
            "run-1", "2026-08-14T00:00:00+08:00", "2026-08-15T00:00:00+08:00",
            bootstrap_required=True,
        )
        errors = MODULE.validate_checkpoint(checkpoint)
        self.assertTrue(any("bootstrap" in item for item in errors))
        self.assertTrue(any("source-scan" in item for item in errors))

    def test_completed_stages_and_bound_artifacts_validate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, receipt_path = make_bootstrap(root)
            original_root = MODULE.REPO_ROOT
            MODULE.REPO_ROOT = root
            try:
                audit = root / "audit.json"
                manifest = root / "manifest.json"
                brief = root / "brief.md"
                audit.write_text("{}", encoding="utf-8")
                manifest.write_text("{}", encoding="utf-8")
                brief.write_text("brief", encoding="utf-8")
                checkpoint = MODULE.create_checkpoint(
                    "run-1",
                    "2026-08-14T00:00:00+08:00",
                    "2026-08-15T00:00:00+08:00",
                    MODULE.bootstrap_binding(receipt_path, receipt),
                    bootstrap_required=True,
                )
                for stage in MODULE.RELEASE_REQUIRED_STAGES:
                    MODULE.mark_stage(checkpoint, stage, "running")
                    artifacts = []
                    for name in MODULE.REQUIRED_STAGE_ARTIFACTS[stage]:
                        if name == "candidate_audit":
                            path = audit
                        elif name == "manifest":
                            path = manifest
                        elif name == "brief":
                            path = brief
                        else:
                            path = root / f"{stage}-{name}.json"
                            path.write_text("{}", encoding="utf-8")
                        artifacts.append(f"{name}={path}")
                    MODULE.mark_stage(checkpoint, stage, "completed", artifacts)
                self.assertEqual(MODULE.validate_checkpoint(checkpoint), [])
                self.assertEqual(
                    MODULE.verify_bound_artifact(checkpoint, "render", "brief", brief), []
                )
            finally:
                MODULE.REPO_ROOT = original_root

    def test_workspace_tamper_invalidates_bootstrap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt, receipt_path = make_bootstrap(root)
            original_root = MODULE.REPO_ROOT
            MODULE.REPO_ROOT = root
            try:
                checkpoint = MODULE.create_checkpoint(
                    "run", "a", "b", MODULE.bootstrap_binding(receipt_path, receipt),
                    bootstrap_required=True,
                )
                target = root / MODULE.BOOTSTRAP_REQUIRED_PATHS[0]
                target.write_text("changed", encoding="utf-8")
                errors = MODULE.validate_checkpoint(checkpoint, required_stages=())
                self.assertTrue(any("bootstrap" in item and "不符" in item for item in errors))
            finally:
                MODULE.REPO_ROOT = original_root

    def test_bound_artifact_change_invalidates_checkpoint_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brief.md"
            path.write_text("first", encoding="utf-8")
            checkpoint = MODULE.create_checkpoint("run", "a", "b")
            checkpoint["stage_status"]["render"] = "running"
            manifest = Path(directory) / "manifest.json"
            manifest.write_text("{}", encoding="utf-8")
            MODULE.mark_stage(
                checkpoint, "render", "completed",
                [f"brief={path}", f"manifest={manifest}"],
            )
            path.write_text("changed", encoding="utf-8")
            errors = MODULE.verify_bound_artifact(checkpoint, "render", "brief", path)
            self.assertTrue(any("雜湊不符" in item for item in errors))

    def test_render_requires_final_manifest_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            brief = Path(directory) / "brief.md"
            brief.write_text("brief", encoding="utf-8")
            checkpoint = MODULE.create_checkpoint("run", "a", "b")
            checkpoint["stage_status"]["render"] = "running"
            with self.assertRaisesRegex(ValueError, "manifest"):
                MODULE.mark_stage(
                    checkpoint, "render", "completed", [f"brief={brief}"]
                )

    def test_rewind_to_audit_preserves_discovery_and_clears_downstream(self):
        checkpoint = MODULE.create_checkpoint("run", "a", "b")
        for stage in MODULE.RELEASE_REQUIRED_STAGES:
            checkpoint["stage_status"][stage] = "completed"
            checkpoint["stage_evidence"][stage] = {"status": "completed", "artifacts": {}}
        MODULE.rewind_from_stage(
            checkpoint,
            "audit-news-candidates",
            "verification insufficient for a core claim",
        )
        self.assertEqual("completed", checkpoint["stage_status"]["select-news-events"])
        for stage in MODULE.RELEASE_REQUIRED_STAGES[3:]:
            self.assertEqual("pending", checkpoint["stage_status"][stage])
            self.assertNotIn(stage, checkpoint["stage_evidence"])
        self.assertEqual("audit-news-candidates", checkpoint["recovery"]["rewinds"][-1]["stage"])


if __name__ == "__main__":
    unittest.main()
