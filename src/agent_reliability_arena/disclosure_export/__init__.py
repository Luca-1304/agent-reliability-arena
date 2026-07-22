"""Public disclosure-export API with a narrow scanner compatibility fix.

The implementation remains in the adjacent single-file module while this branch
validates the schema. This facade permits prohibited private-field names only as
keys of the exact redaction declaration; every other public location continues
to use the fail-closed scanner.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


_IMPLEMENTATION_NAME = "agent_reliability_arena._disclosure_export_implementation"
_IMPLEMENTATION_PATH = Path(__file__).resolve().parents[1] / "disclosure_export.py"


def _load_implementation() -> ModuleType:
    existing = sys.modules.get(_IMPLEMENTATION_NAME)
    if existing is not None:
        return existing
    specification = importlib.util.spec_from_file_location(
        _IMPLEMENTATION_NAME,
        _IMPLEMENTATION_PATH,
    )
    if specification is None or specification.loader is None:
        raise ImportError("Unable to load the disclosure-export implementation.")
    module = importlib.util.module_from_spec(specification)
    sys.modules[_IMPLEMENTATION_NAME] = module
    specification.loader.exec_module(module)
    return module


_implementation = _load_implementation()
_original_scan = _implementation._scan_public


def _scan_public(value: object, path: str = "export") -> None:
    if path == "export.redaction_record":
        if not isinstance(value, dict):
            raise ValueError("The public redaction record must be a JSON object.")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("The public redaction record contains a non-string key.")
            _implementation._safe_text(key, "redaction record key")
            _scan_public(item, f"{path}.{key}")
        return
    _original_scan(value, path)


_implementation._scan_public = _scan_public

PriceSource = _implementation.PriceSource
build_disclosure_safe_empirical_export = _implementation.build_disclosure_safe_empirical_export
verify_disclosure_safe_empirical_export = _implementation.verify_disclosure_safe_empirical_export
write_disclosure_safe_empirical_export = _implementation.write_disclosure_safe_empirical_export
write_private_evidence_index = _implementation.write_private_evidence_index

__all__ = [
    "PriceSource",
    "build_disclosure_safe_empirical_export",
    "verify_disclosure_safe_empirical_export",
    "write_disclosure_safe_empirical_export",
    "write_private_evidence_index",
]
