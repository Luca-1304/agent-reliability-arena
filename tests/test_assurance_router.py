from __future__ import annotations

import importlib
import json
import unittest


def _router():
    try:
        return importlib.import_module("agent_reliability_arena.assurance_router")
    except ModuleNotFoundError as exc:
        raise AssertionError("assurance router implementation is intentionally missing") from exc


class AssuranceRouterTests(unittest.TestCase):
    def classify(self, paths: list[str], triggers: list[str]):
        return _router().classify_paths(paths, triggers)

    def test_runtime_path_routes_required_reliability_evidence(self) -> None:
        report = self.classify(
            ["src/agent_reliability_arena/runner.py"],
            ["src/**"],
        )
        self.assertEqual(report.touched_surfaces, ("runtime",))
        self.assertIn("reliability.required", report.evidence_ids)
        self.assertFalse(report.attention_required)
        self.assertFalse(report.authoritative)

    def test_tests_only_change_is_not_labelled_safe(self) -> None:
        report = self.classify(["tests/test_runner.py"], ["tests/**"])
        self.assertEqual(report.touched_surfaces, ("tests",))
        self.assertIn("tests.contract-review", report.evidence_ids)
        self.assertNotIn("safe", report.to_json().casefold())

    def test_workflow_change_routes_ci_policy_and_requires_attention(self) -> None:
        report = self.classify(
            [".github/workflows/reliability-fast.yml"],
            [".github/workflows/**"],
        )
        self.assertEqual(report.touched_surfaces, ("ci-policy",))
        self.assertIn("ci.structural-policy", report.evidence_ids)
        self.assertTrue(report.attention_required)

    def test_pages_workflow_maps_to_ci_and_publication_surfaces(self) -> None:
        report = self.classify(
            [".github/workflows/pages.yml"],
            [".github/workflows/**"],
        )
        self.assertEqual(
            report.touched_surfaces,
            ("ci-policy", "deployment-publication"),
        )
        self.assertIn("publication.staged-verification", report.evidence_ids)
        self.assertIn("publication.live-independent-verification", report.evidence_ids)
        self.assertTrue(report.attention_required)

    def test_public_cv_verifier_routes_independent_privacy_evidence(self) -> None:
        report = self.classify(
            ["scripts/verify_public_cv.py"],
            ["scripts/**"],
        )
        self.assertIn("security-privacy", report.touched_surfaces)
        self.assertIn("privacy.independent-verification", report.evidence_ids)
        self.assertTrue(report.attention_required)

    def test_vercel_configuration_is_publication_and_exposes_trigger_gap(self) -> None:
        report = self.classify(["vercel.json"], ["src/**", "docs/**"])
        self.assertEqual(report.touched_surfaces, ("deployment-publication",))
        self.assertEqual(report.outside_reliability_trigger_surface, ("vercel.json",))
        self.assertTrue(report.attention_required)

    def test_dependency_metadata_routes_supply_chain_evidence(self) -> None:
        report = self.classify(["pyproject.toml"], ["pyproject.toml"])
        self.assertEqual(report.touched_surfaces, ("dependency-supply-chain",))
        self.assertIn("supply-chain.clean-build", report.evidence_ids)
        self.assertIn("supply-chain.verification", report.evidence_ids)
        self.assertTrue(report.attention_required)

    def test_release_evidence_paths_route_claim_boundary_review(self) -> None:
        report = self.classify(
            ["citation/example.json", "reference_runs/example.json", "release/manifest.json"],
            ["citation/**", "reference_runs/**", "release/**"],
        )
        self.assertEqual(report.touched_surfaces, ("release-evidence",))
        self.assertIn("release.claim-boundary-review", report.evidence_ids)

    def test_documentation_path_routes_consistency_review(self) -> None:
        report = self.classify(["README.md"], ["README.md"])
        self.assertEqual(report.touched_surfaces, ("documentation",))
        self.assertIn("docs.consistency-review", report.evidence_ids)
        self.assertFalse(report.attention_required)

    def test_branch_protection_document_is_both_documentation_and_ci_policy(self) -> None:
        report = self.classify(
            ["docs/BRANCH_PROTECTION.md"],
            ["docs/**"],
        )
        self.assertEqual(report.touched_surfaces, ("ci-policy", "documentation"))
        self.assertTrue(report.attention_required)

    def test_unknown_and_outside_trigger_path_stays_visible(self) -> None:
        report = self.classify(["ops/new-surface.txt"], ["src/**"])
        self.assertEqual(report.unknown_paths, ("ops/new-surface.txt",))
        self.assertEqual(
            report.outside_reliability_trigger_surface,
            ("ops/new-surface.txt",),
        )
        self.assertIn("manual.unknown-surface-review", report.evidence_ids)
        self.assertTrue(report.attention_required)

    def test_known_path_outside_trigger_surface_is_reported(self) -> None:
        report = self.classify(["README.md"], ["src/**"])
        self.assertEqual(report.unknown_paths, ())
        self.assertEqual(report.outside_reliability_trigger_surface, ("README.md",))
        self.assertTrue(report.attention_required)

    def test_unsupported_trigger_pattern_is_observed_not_interpreted(self) -> None:
        report = self.classify(["src/a.py"], ["src/*.py"])
        self.assertIn("unsupported_reliability_trigger_pattern:src/*.py", report.observations)
        self.assertEqual(report.outside_reliability_trigger_surface, ("src/a.py",))
        self.assertTrue(report.attention_required)

    def test_absolute_posix_path_is_rejected(self) -> None:
        module = _router()
        with self.assertRaisesRegex(ValueError, "absolute"):
            module.classify_paths(["/tmp/file.py"], ["src/**"])

    def test_absolute_windows_drive_path_is_rejected(self) -> None:
        module = _router()
        with self.assertRaisesRegex(ValueError, "absolute"):
            module.classify_paths([r"C:\repo\file.py"], ["src/**"])

    def test_traversal_path_is_rejected(self) -> None:
        module = _router()
        with self.assertRaisesRegex(ValueError, "traversal"):
            module.classify_paths(["src/../secret.txt"], ["src/**"])

    def test_separator_normalization_is_stable(self) -> None:
        report = self.classify(
            [r"src\agent_reliability_arena\runner.py"],
            ["src/**"],
        )
        self.assertEqual(
            report.changed_paths,
            ("src/agent_reliability_arena/runner.py",),
        )

    def test_duplicate_and_input_order_do_not_change_canonical_json(self) -> None:
        left = self.classify(
            ["README.md", "src/a.py", "README.md"],
            ["README.md", "src/**"],
        )
        right = self.classify(
            ["src/a.py", "README.md"],
            ["src/**", "README.md"],
        )
        self.assertEqual(left.to_json(), right.to_json())
        self.assertEqual(json.loads(left.to_json())["schema_version"], "assurance-router-v1")

    def test_empty_input_produces_deterministic_non_authoritative_report(self) -> None:
        report = self.classify([], ["src/**"])
        payload = report.to_dict()
        self.assertEqual(report.changed_paths, ())
        self.assertEqual(report.touched_surfaces, ())
        self.assertIn("empty_change_set", report.observations)
        self.assertFalse(report.attention_required)
        self.assertIs(payload["authoritative"], False)

    def test_report_exposes_per_path_rule_matches(self) -> None:
        report = self.classify(
            [".github/workflows/pages.yml", "README.md"],
            [".github/workflows/**", "README.md"],
        )
        payload = report.to_dict()
        by_path = {row["path"]: row for row in payload["path_results"]}
        self.assertGreaterEqual(len(by_path[".github/workflows/pages.yml"]["rule_ids"]), 2)
        self.assertEqual(by_path["README.md"]["surfaces"], ["documentation"])


if __name__ == "__main__":
    unittest.main()
