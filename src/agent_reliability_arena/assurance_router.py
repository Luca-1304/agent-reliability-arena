from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence


_SCHEMA_VERSION = "assurance-router-v1"
_ATTENTION_SURFACES = frozenset(
    {
        "ci-policy",
        "dependency-supply-chain",
        "deployment-publication",
        "security-privacy",
    }
)


@dataclass(frozen=True)
class AssuranceRule:
    rule_id: str
    surfaces: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rationale: str
    exact: tuple[str, ...] = ()
    prefix: str | None = None
    contains: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()

    def matches(self, path: str) -> bool:
        if path in self.exact:
            return True
        if self.prefix is not None and (path == self.prefix.rstrip("/") or path.startswith(self.prefix)):
            return True
        if self.contains and all(fragment in path for fragment in self.contains):
            return True
        return bool(self.suffixes and path.endswith(self.suffixes))


@dataclass(frozen=True)
class PathResult:
    path: str
    rule_ids: tuple[str, ...]
    surfaces: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    rationales: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "rule_ids": list(self.rule_ids),
            "surfaces": list(self.surfaces),
            "evidence_ids": list(self.evidence_ids),
            "rationales": list(self.rationales),
        }


@dataclass(frozen=True)
class AssuranceReport:
    changed_paths: tuple[str, ...]
    touched_surfaces: tuple[str, ...]
    path_results: tuple[PathResult, ...]
    evidence_ids: tuple[str, ...]
    unknown_paths: tuple[str, ...]
    outside_reliability_trigger_surface: tuple[str, ...]
    observations: tuple[str, ...]
    attention_required: bool
    authoritative: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": _SCHEMA_VERSION,
            "changed_paths": list(self.changed_paths),
            "touched_surfaces": list(self.touched_surfaces),
            "path_results": [row.to_dict() for row in self.path_results],
            "evidence_ids": list(self.evidence_ids),
            "unknown_paths": list(self.unknown_paths),
            "outside_reliability_trigger_surface": list(
                self.outside_reliability_trigger_surface
            ),
            "observations": list(self.observations),
            "attention_required": self.attention_required,
            "authoritative": self.authoritative,
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
        ) + "\n"


_RULES: tuple[AssuranceRule, ...] = (
    AssuranceRule(
        rule_id="runtime.source",
        prefix="src/",
        surfaces=("runtime",),
        evidence_ids=("reliability.required",),
        rationale="Executable package code can change runtime behaviour.",
    ),
    AssuranceRule(
        rule_id="tests.contract",
        prefix="tests/",
        surfaces=("tests",),
        evidence_ids=("reliability.required", "tests.contract-review"),
        rationale="Test changes can strengthen or weaken the evidence contract.",
    ),
    AssuranceRule(
        rule_id="ci.workflow",
        prefix=".github/workflows/",
        surfaces=("ci-policy",),
        evidence_ids=("ci.structural-policy", "reliability.required"),
        rationale="Workflow changes can alter how merge evidence is produced.",
    ),
    AssuranceRule(
        rule_id="ci.policy",
        exact=("reliability-policy.json",),
        surfaces=("ci-policy",),
        evidence_ids=("ci.structural-policy", "reliability.required"),
        rationale="The reliability policy defines repository verification boundaries.",
    ),
    AssuranceRule(
        rule_id="ci.scripts",
        prefix="scripts/ci/",
        surfaces=("ci-policy",),
        evidence_ids=("ci.structural-policy", "reliability.required"),
        rationale="CI evidence scripts can change the meaning of verification output.",
    ),
    AssuranceRule(
        rule_id="ci.branch-protection-doc",
        exact=("docs/BRANCH_PROTECTION.md",),
        surfaces=("ci-policy",),
        evidence_ids=("ci.structural-policy",),
        rationale="Branch-protection documentation defines operational merge policy.",
    ),
    AssuranceRule(
        rule_id="privacy.security-tree",
        prefix="security/",
        surfaces=("security-privacy",),
        evidence_ids=("privacy.independent-verification", "reliability.required"),
        rationale="Security-boundary changes require independent verification.",
    ),
    AssuranceRule(
        rule_id="privacy.public-cv-verifier",
        exact=("scripts/verify_public_cv.py",),
        surfaces=("deployment-publication", "security-privacy"),
        evidence_ids=(
            "privacy.independent-verification",
            "publication.staged-verification",
            "reliability.required",
        ),
        rationale="The public-CV verifier protects a publication privacy boundary.",
    ),
    AssuranceRule(
        rule_id="publication.pages-workflow",
        exact=(".github/workflows/pages.yml",),
        surfaces=("deployment-publication",),
        evidence_ids=(
            "publication.live-independent-verification",
            "publication.staged-verification",
        ),
        rationale="The Pages workflow controls staging and public publication.",
    ),
    AssuranceRule(
        rule_id="publication.vercel-config",
        exact=("vercel.json",),
        surfaces=("deployment-publication",),
        evidence_ids=("publication.staged-verification",),
        rationale="Vercel configuration can change publication behaviour.",
    ),
    AssuranceRule(
        rule_id="publication.web-tree",
        prefix="web/",
        surfaces=("deployment-publication",),
        evidence_ids=("publication.staged-verification", "reliability.required"),
        rationale="Public web assets can change externally visible evidence.",
    ),
    AssuranceRule(
        rule_id="dependency.project-metadata",
        exact=("pyproject.toml",),
        surfaces=("dependency-supply-chain",),
        evidence_ids=("supply-chain.clean-build", "supply-chain.verification"),
        rationale="Project metadata can change packaging or dependency resolution.",
    ),
    AssuranceRule(
        rule_id="dependency.requirements",
        prefix="requirements/",
        surfaces=("dependency-supply-chain",),
        evidence_ids=("supply-chain.clean-build", "supply-chain.verification"),
        rationale="Requirement changes alter the dependency supply chain.",
    ),
    AssuranceRule(
        rule_id="evidence.release",
        prefix="release/",
        surfaces=("release-evidence",),
        evidence_ids=("release.claim-boundary-review", "reliability.required"),
        rationale="Release material participates in the public evidence boundary.",
    ),
    AssuranceRule(
        rule_id="evidence.citation",
        prefix="citation/",
        surfaces=("release-evidence",),
        evidence_ids=("release.claim-boundary-review", "reliability.required"),
        rationale="Citation material supports externally reviewable claims.",
    ),
    AssuranceRule(
        rule_id="evidence.reference-runs",
        prefix="reference_runs/",
        surfaces=("release-evidence",),
        evidence_ids=("release.claim-boundary-review", "reliability.required"),
        rationale="Reference-run material is part of the reproducible evidence record.",
    ),
    AssuranceRule(
        rule_id="docs.tree",
        prefix="docs/",
        surfaces=("documentation",),
        evidence_ids=("docs.consistency-review", "reliability.required"),
        rationale="Documentation changes can alter stated operating or evidence boundaries.",
    ),
    AssuranceRule(
        rule_id="docs.root",
        exact=("README.md", "CHANGELOG.md", "ROADMAP.md"),
        surfaces=("documentation",),
        evidence_ids=("docs.consistency-review", "reliability.required"),
        rationale="Root documentation communicates project behaviour and limits.",
    ),
)


def normalize_path(path: str) -> str:
    if not isinstance(path, str) or path == "":
        raise ValueError("changed path must be a non-empty string")
    value = path.replace("\\", "/")
    if value.startswith("/") or value.startswith("//"):
        raise ValueError(f"absolute path is not permitted: {path}")
    if len(value) >= 3 and value[1] == ":" and value[2] == "/":
        raise ValueError(f"absolute path is not permitted: {path}")
    parts: list[str] = []
    for part in value.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError(f"path traversal is not permitted: {path}")
        parts.append(part)
    if not parts:
        raise ValueError("changed path must resolve to a repository-relative path")
    return "/".join(parts)


def _normalize_trigger_pattern(pattern: str) -> str:
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("reliability trigger pattern must be a non-empty string")
    return pattern.strip().replace("\\", "/")


def _supported_trigger(pattern: str) -> bool:
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return bool(base) and not any(token in base for token in "*?[")
    return not any(token in pattern for token in "*?[")


def _trigger_matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        base = pattern[:-3].rstrip("/")
        return path == base or path.startswith(base + "/")
    return path == pattern


def classify_paths(
    paths: Sequence[str],
    trigger_patterns: Sequence[str],
) -> AssuranceReport:
    changed_paths = tuple(sorted({normalize_path(path) for path in paths}))
    normalized_triggers = tuple(
        sorted({_normalize_trigger_pattern(pattern) for pattern in trigger_patterns})
    )
    supported_triggers = tuple(
        pattern for pattern in normalized_triggers if _supported_trigger(pattern)
    )
    unsupported_triggers = tuple(
        pattern for pattern in normalized_triggers if pattern not in supported_triggers
    )

    observations: set[str] = {
        f"unsupported_reliability_trigger_pattern:{pattern}"
        for pattern in unsupported_triggers
    }
    if not changed_paths:
        observations.add("empty_change_set")

    path_results: list[PathResult] = []
    touched_surfaces: set[str] = set()
    evidence_ids: set[str] = set()
    unknown_paths: list[str] = []
    outside_trigger: list[str] = []

    for path in changed_paths:
        matched = tuple(rule for rule in _RULES if rule.matches(path))
        rule_ids = tuple(sorted(rule.rule_id for rule in matched))
        surfaces = tuple(sorted({surface for rule in matched for surface in rule.surfaces}))
        row_evidence = tuple(
            sorted({evidence for rule in matched for evidence in rule.evidence_ids})
        )
        rationales = tuple(sorted({rule.rationale for rule in matched}))

        if not matched:
            unknown_paths.append(path)
            row_evidence = ("manual.unknown-surface-review",)

        if not any(_trigger_matches(path, pattern) for pattern in supported_triggers):
            outside_trigger.append(path)

        touched_surfaces.update(surfaces)
        evidence_ids.update(row_evidence)
        path_results.append(
            PathResult(
                path=path,
                rule_ids=rule_ids,
                surfaces=surfaces,
                evidence_ids=row_evidence,
                rationales=rationales,
            )
        )

    attention_required = bool(
        unknown_paths
        or outside_trigger
        or (_ATTENTION_SURFACES & touched_surfaces)
    )

    return AssuranceReport(
        changed_paths=changed_paths,
        touched_surfaces=tuple(sorted(touched_surfaces)),
        path_results=tuple(path_results),
        evidence_ids=tuple(sorted(evidence_ids)),
        unknown_paths=tuple(sorted(unknown_paths)),
        outside_reliability_trigger_surface=tuple(sorted(outside_trigger)),
        observations=tuple(sorted(observations)),
        attention_required=attention_required,
    )
