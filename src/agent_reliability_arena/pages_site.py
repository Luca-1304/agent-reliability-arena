from __future__ import annotations

import re
from pathlib import Path

from .launch_package import verify_launch_package
from .showcase_release import verify_showcase_release


_SOURCE_TO_TARGET = {
    "web/app.js": "app.js",
    "web/data/fixture-v1.json": "data/fixture-v1.json",
    "web/index.html": "index.html",
    "web/styles.css": "styles.css",
}
_EXPECTED_STAGED_FILES = {
    ".nojekyll",
    "app.js",
    "data/fixture-v1.json",
    "index.html",
    "styles.css",
}
_TITLE = re.compile(r"<title>(?P<title>[^<]+)</title>", re.IGNORECASE)


class PagesSiteError(ValueError):
    """Raised when the static Pages artifact cannot be staged safely."""


def _real_directory(path: Path, label: str) -> Path:
    candidate = Path(path)
    if not candidate.exists() or not candidate.is_dir() or candidate.is_symlink():
        raise PagesSiteError(f"{label} must be an existing real directory: {candidate}")
    return candidate.resolve()


def _source_file(repository_root: Path, relative: str) -> Path:
    source = repository_root / relative
    if source.is_symlink():
        raise PagesSiteError(f"Pages source must not be a symlink: {relative}")
    if not source.exists() or not source.is_file():
        raise PagesSiteError(f"Required Pages source is missing: {relative}")
    resolved = source.resolve(strict=True)
    if repository_root != resolved and repository_root not in resolved.parents:
        raise PagesSiteError(f"Pages source escapes repository root: {relative}")
    return source


def stage_pages_site(root: Path, destination: Path) -> dict[str, object]:
    """Verify and stage the exact disclosure-safe static Pages artifact."""

    repository_root = _real_directory(Path(root), "Repository root")
    output = Path(destination)
    if output.exists() or output.is_symlink():
        raise PagesSiteError(f"Pages destination must not already exist: {output}")

    showcase = verify_showcase_release(repository_root)
    launch = verify_launch_package(repository_root)

    sources = {
        relative: _source_file(repository_root, relative)
        for relative in _SOURCE_TO_TARGET
    }

    output.mkdir(parents=True, exist_ok=False)
    for relative, target_relative in _SOURCE_TO_TARGET.items():
        target = output / target_relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(sources[relative].read_bytes())
    (output / ".nojekyll").write_bytes(b"")

    staged = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    }
    if staged != _EXPECTED_STAGED_FILES:
        raise PagesSiteError(
            "Pages staging produced an unexpected file set: "
            f"{sorted(staged)}"
        )
    if any(path.is_symlink() for path in output.rglob("*")):
        raise PagesSiteError("Pages staging produced a prohibited symlink.")

    index_text = (output / "index.html").read_text(encoding="utf-8")
    title_match = _TITLE.search(index_text)
    if title_match is None:
        raise PagesSiteError("Pages index is missing a document title.")

    return {
        "files_staged": len(staged),
        "staged_files": sorted(staged),
        "site_title": title_match.group("title").strip(),
        "showcase_version": showcase["showcase_version"],
        "showcase_manifest_digest": showcase["manifest_digest"],
        "launch_package_version": launch["package_version"],
        "launch_manifest_digest": launch["manifest_digest"],
        "provider_called": False,
        "comparative_claim_permitted": False,
    }
