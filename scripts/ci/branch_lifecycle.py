from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_POLICY_SCHEMA = "branch-lifecycle-policy-v1"
_PROVENANCE_SCHEMA = "branch-lifecycle-provenance-v1"
_POLICY_KEYS = {
    "schema_version",
    "default_branch",
    "remote",
    "destructive_actions_supported",
    "release_archive_prefixes",
    "temporary_review_prefixes",
    "explicit_retained_branches",
}
_PROVENANCE_KEYS = {"schema_version", "branches"}
_PROVENANCE_RECORD_KEYS = {
    "pr_state",
    "superseded_by",
    "retain_as_evidence",
    "retention_reason",
    "note",
}
_PR_STATES = {"open", "merged", "closed_unmerged", "none", "unknown"}
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class BranchLifecyclePolicyError(ValueError):
    """Raised when lifecycle policy/provenance cannot be trusted."""


@dataclass(frozen=True)
class BranchLifecyclePolicy:
    schema_version: str
    default_branch: str
    remote: str
    destructive_actions_supported: bool
    release_archive_prefixes: tuple[str, ...]
    temporary_review_prefixes: tuple[str, ...]
    explicit_retained_branches: Mapping[str, str]


@dataclass(frozen=True)
class BranchProvenance:
    pr_state: str
    superseded_by: int | None
    retain_as_evidence: bool
    retention_reason: str | None
    note: str | None


@dataclass(frozen=True)
class BranchGitEvidence:
    branch: str
    tip_sha: str
    default_tip_sha: str
    ancestor_of_default: bool
    ahead: int
    behind: int


@dataclass(frozen=True)
class BranchLifecycleRow:
    branch: str
    tip_sha: str
    default_tip_sha: str
    ancestor_of_default: bool
    ahead: int
    behind: int
    lifecycle_class: str
    reasons: tuple[str, ...]
    deletion_authorized: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "branch": self.branch,
            "tip_sha": self.tip_sha,
            "default_tip_sha": self.default_tip_sha,
            "ancestor_of_default": self.ancestor_of_default,
            "ahead": self.ahead,
            "behind": self.behind,
            "lifecycle_class": self.lifecycle_class,
            "reasons": list(self.reasons),
            "deletion_authorized": False,
        }


@dataclass(frozen=True)
class BranchLifecycleReport:
    schema_version: str
    remote: str
    default_branch: str
    default_tip_sha: str
    destructive_actions_supported: bool
    branches: tuple[BranchLifecycleRow, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "remote": self.remote,
            "default_branch": self.default_branch,
            "default_tip_sha": self.default_tip_sha,
            "destructive_actions_supported": False,
            "branch_count": len(self.branches),
            "branches": [row.to_dict() for row in self.branches],
        }


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BranchLifecyclePolicyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            payload = json.load(handle, object_pairs_hook=_object_without_duplicates)
    except BranchLifecyclePolicyError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise BranchLifecyclePolicyError(
            f"could not load lifecycle JSON: {type(exc).__name__}"
        ) from exc
    if not isinstance(payload, dict):
        raise BranchLifecyclePolicyError("lifecycle JSON root must be an object")
    return payload


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], *, label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise BranchLifecyclePolicyError(
            f"{label} keys must be exact; missing={sorted(expected - actual)!r} "
            f"unknown={sorted(actual - expected)!r}"
        )


def _clean_name(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise BranchLifecyclePolicyError(f"{label} must be a non-empty trimmed string")
    if "\x00" in value:
        raise BranchLifecyclePolicyError(f"{label} contains a prohibited NUL byte")
    return value


def _prefixes(value: Any, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise BranchLifecyclePolicyError(f"{label} must be a list")
    result: list[str] = []
    for item in value:
        prefix = _clean_name(item, label=label)
        if prefix in result:
            raise BranchLifecyclePolicyError(f"{label} contains duplicate prefix {prefix!r}")
        result.append(prefix)
    return tuple(result)


def load_branch_lifecycle_policy(path: Path) -> BranchLifecyclePolicy:
    raw = _read_json(path)
    _require_exact_keys(raw, _POLICY_KEYS, label="branch lifecycle policy")
    if raw["schema_version"] != _POLICY_SCHEMA:
        raise BranchLifecyclePolicyError(f"schema_version must be {_POLICY_SCHEMA!r}")
    if raw["destructive_actions_supported"] is not False:
        raise BranchLifecyclePolicyError("destructive_actions_supported must remain false")

    default_branch = _clean_name(raw["default_branch"], label="default_branch")
    remote = _clean_name(raw["remote"], label="remote")
    release_prefixes = _prefixes(raw["release_archive_prefixes"], label="release_archive_prefixes")
    temporary_prefixes = _prefixes(raw["temporary_review_prefixes"], label="temporary_review_prefixes")

    raw_retained = raw["explicit_retained_branches"]
    if not isinstance(raw_retained, dict):
        raise BranchLifecyclePolicyError("explicit_retained_branches must be an object")
    retained: dict[str, str] = {}
    for branch, reason in raw_retained.items():
        branch_name = _clean_name(branch, label="retained branch")
        reason_text = _clean_name(reason, label=f"retention reason for {branch_name}")
        retained[branch_name] = reason_text

    return BranchLifecyclePolicy(
        schema_version=_POLICY_SCHEMA,
        default_branch=default_branch,
        remote=remote,
        destructive_actions_supported=False,
        release_archive_prefixes=release_prefixes,
        temporary_review_prefixes=temporary_prefixes,
        explicit_retained_branches=dict(sorted(retained.items())),
    )


def load_branch_provenance(
    path: Path,
    *,
    known_branches: set[str],
) -> dict[str, BranchProvenance]:
    raw = _read_json(path)
    _require_exact_keys(raw, _PROVENANCE_KEYS, label="branch provenance")
    if raw["schema_version"] != _PROVENANCE_SCHEMA:
        raise BranchLifecyclePolicyError(f"provenance schema_version must be {_PROVENANCE_SCHEMA!r}")
    raw_branches = raw["branches"]
    if not isinstance(raw_branches, dict):
        raise BranchLifecyclePolicyError("provenance branches must be an object")

    result: dict[str, BranchProvenance] = {}
    for raw_branch, raw_record in raw_branches.items():
        branch = _clean_name(raw_branch, label="provenance branch")
        if branch not in known_branches:
            raise BranchLifecyclePolicyError(f"provenance references unknown branch {branch!r}")
        if not isinstance(raw_record, dict):
            raise BranchLifecyclePolicyError(f"provenance record for {branch!r} must be an object")
        _require_exact_keys(raw_record, _PROVENANCE_RECORD_KEYS, label=f"provenance {branch}")

        state = raw_record["pr_state"]
        if state not in _PR_STATES:
            raise BranchLifecyclePolicyError(f"unsupported pr_state for {branch!r}: {state!r}")

        superseded = raw_record["superseded_by"]
        if superseded is not None and (
            not isinstance(superseded, int) or isinstance(superseded, bool) or superseded < 1
        ):
            raise BranchLifecyclePolicyError(f"superseded_by for {branch!r} must be null or positive integer")

        retain = raw_record["retain_as_evidence"]
        if not isinstance(retain, bool):
            raise BranchLifecyclePolicyError(f"retain_as_evidence for {branch!r} must be boolean")

        retention_reason = raw_record["retention_reason"]
        if retention_reason is not None:
            retention_reason = _clean_name(
                retention_reason,
                label=f"retention_reason for {branch}",
            )
        if retain and retention_reason is None:
            raise BranchLifecyclePolicyError(
                f"retained evidence branch {branch!r} requires retention_reason"
            )
        if not retain and retention_reason is not None:
            raise BranchLifecyclePolicyError(
                f"non-retained branch {branch!r} must not carry retention_reason"
            )

        note = raw_record["note"]
        if note is not None:
            note = _clean_name(note, label=f"note for {branch}")

        result[branch] = BranchProvenance(
            pr_state=state,
            superseded_by=superseded,
            retain_as_evidence=retain,
            retention_reason=retention_reason,
            note=note,
        )
    return dict(sorted(result.items()))


def classify_branch(
    evidence: BranchGitEvidence,
    policy: BranchLifecyclePolicy,
    provenance: BranchProvenance | None,
) -> BranchLifecycleRow:
    if not _SHA_RE.fullmatch(evidence.tip_sha) or not _SHA_RE.fullmatch(evidence.default_tip_sha):
        raise BranchLifecyclePolicyError(f"invalid Git SHA evidence for {evidence.branch!r}")
    if evidence.ahead < 0 or evidence.behind < 0:
        raise BranchLifecyclePolicyError(f"negative ahead/behind count for {evidence.branch!r}")

    reasons: list[str] = []
    if evidence.branch in policy.explicit_retained_branches:
        reasons.append(policy.explicit_retained_branches[evidence.branch])
        lifecycle_class = "historical-evidence-retain"
    elif provenance is not None and provenance.retain_as_evidence:
        reasons.append(provenance.retention_reason or "Explicit historical evidence retention")
        lifecycle_class = "historical-evidence-retain"
    elif provenance is not None and provenance.pr_state == "open":
        reasons.append("Provenance records an open pull request or active review.")
        lifecycle_class = "active"
    elif any(evidence.branch.startswith(prefix) for prefix in policy.release_archive_prefixes):
        reasons.append("Branch matches reviewed release/archive retention policy.")
        lifecycle_class = "release-archive-retain"
    elif provenance is not None and (
        provenance.pr_state == "merged" or provenance.superseded_by is not None
    ):
        reasons.append("Provenance records merged or superseded work; review only, no deletion authority.")
        lifecycle_class = "merged-superseded-candidate"
    elif any(evidence.branch.startswith(prefix) for prefix in policy.temporary_review_prefixes):
        reasons.append("Temporary/ref-sync prefix marks this branch for lifecycle review only.")
        lifecycle_class = "temporary-obsolete-candidate"
    elif evidence.ancestor_of_default:
        reasons.append("Branch tip is an ancestor of the default branch.")
        lifecycle_class = "merged-superseded-candidate"
    else:
        reasons.append("Git ancestry/provenance is insufficient for a stronger lifecycle conclusion.")
        lifecycle_class = "uncertain"

    if provenance is not None and provenance.note:
        reasons.append(provenance.note)

    return BranchLifecycleRow(
        branch=evidence.branch,
        tip_sha=evidence.tip_sha,
        default_tip_sha=evidence.default_tip_sha,
        ancestor_of_default=evidence.ancestor_of_default,
        ahead=evidence.ahead,
        behind=evidence.behind,
        lifecycle_class=lifecycle_class,
        reasons=tuple(reasons),
        deletion_authorized=False,
    )


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise BranchLifecyclePolicyError("git executable is required") from exc
    if check and completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise BranchLifecyclePolicyError(f"git command failed: {detail}")
    return completed


def _resolve(repo: Path, ref: str) -> str:
    value = _git(repo, "rev-parse", f"{ref}^{{commit}}").stdout.strip()
    if not _SHA_RE.fullmatch(value):
        raise BranchLifecyclePolicyError(f"Git ref did not resolve to a full commit SHA: {ref}")
    return value


def collect_remote_branch_evidence(
    repo: Path,
    policy: BranchLifecyclePolicy,
) -> tuple[str, tuple[BranchGitEvidence, ...]]:
    root = Path(repo).resolve()
    inside = _git(root, "rev-parse", "--is-inside-work-tree").stdout.strip()
    if inside != "true":
        raise BranchLifecyclePolicyError(f"not a Git work tree: {root}")

    prefix = f"refs/remotes/{policy.remote}/"
    default_ref = prefix + policy.default_branch
    default_tip = _resolve(root, default_ref)
    refs = _git(
        root,
        "for-each-ref",
        "--format=%(refname)",
        f"refs/remotes/{policy.remote}",
    ).stdout.splitlines()

    evidence_rows: list[BranchGitEvidence] = []
    for ref in sorted(refs):
        if ref in {f"refs/remotes/{policy.remote}/HEAD", default_ref}:
            continue
        if not ref.startswith(prefix):
            continue
        branch = ref[len(prefix) :]
        if not branch:
            continue
        tip = _resolve(root, ref)
        ancestor_check = _git(
            root,
            "merge-base",
            "--is-ancestor",
            tip,
            default_tip,
            check=False,
        )
        if ancestor_check.returncode not in {0, 1}:
            raise BranchLifecyclePolicyError(
                f"could not compare ancestry for {branch!r}: {ancestor_check.stderr.strip()}"
            )
        counts = _git(
            root,
            "rev-list",
            "--left-right",
            "--count",
            f"{default_tip}...{tip}",
        ).stdout.split()
        if len(counts) != 2 or not all(item.isdigit() for item in counts):
            raise BranchLifecyclePolicyError(f"invalid ahead/behind evidence for {branch!r}")
        behind, ahead = (int(counts[0]), int(counts[1]))
        evidence_rows.append(
            BranchGitEvidence(
                branch=branch,
                tip_sha=tip,
                default_tip_sha=default_tip,
                ancestor_of_default=ancestor_check.returncode == 0,
                ahead=ahead,
                behind=behind,
            )
        )
    return default_tip, tuple(evidence_rows)


def classify_remote_branches(
    repo: Path,
    policy: BranchLifecyclePolicy,
    provenance: Mapping[str, BranchProvenance] | None = None,
) -> BranchLifecycleReport:
    default_tip, evidence_rows = collect_remote_branch_evidence(repo, policy)
    known = {row.branch for row in evidence_rows}
    provenance_map = dict(provenance or {})
    unknown = sorted(set(provenance_map) - known)
    if unknown:
        raise BranchLifecyclePolicyError(f"provenance contains unknown remote branches: {unknown!r}")

    rows = tuple(
        classify_branch(evidence, policy, provenance_map.get(evidence.branch))
        for evidence in evidence_rows
    )
    return BranchLifecycleReport(
        schema_version="branch-lifecycle-report-v1",
        remote=policy.remote,
        default_branch=policy.default_branch,
        default_tip_sha=default_tip,
        destructive_actions_supported=False,
        branches=rows,
    )
