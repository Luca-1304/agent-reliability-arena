from __future__ import annotations

import copy
import difflib
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


class DeterminismError(ValueError):
    """Raised when a determinism rule is invalid or unsafe to apply."""


@dataclass(frozen=True)
class ComparisonResult:
    equal: bool
    left_digest: str
    right_digest: str
    diff: str


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(data: bytes) -> bytes:
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeterminismError(f"input is not valid UTF-8 JSON: {exc}") from exc
    return _json_bytes(payload)


def _json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _encode_pointer_token(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _decode_pointer_token(token: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(token):
        if token[index] != "~":
            output.append(token[index])
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise DeterminismError(f"invalid JSON pointer escape in token: {token!r}")
        output.append("~" if token[index + 1] == "0" else "/")
        index += 2
    return "".join(output)


def _pointer_tokens(pointer: str) -> tuple[str, ...]:
    if not pointer.startswith("/"):
        raise DeterminismError(f"ignored pointer must start with '/': {pointer!r}")
    return tuple(_decode_pointer_token(token) for token in pointer[1:].split("/"))


def _remove_pointer(payload: object, pointer: str) -> None:
    tokens = _pointer_tokens(pointer)
    if not tokens:
        raise DeterminismError("root JSON pointer cannot be ignored")
    current = payload
    for token in tokens[:-1]:
        if isinstance(current, dict):
            if token not in current:
                raise DeterminismError(f"ignored pointer does not exist: {pointer}")
            current = current[token]
        elif isinstance(current, list):
            try:
                index = int(token)
            except ValueError as exc:
                raise DeterminismError(f"ignored pointer does not exist: {pointer}") from exc
            if index < 0 or index >= len(current):
                raise DeterminismError(f"ignored pointer does not exist: {pointer}")
            current = current[index]
        else:
            raise DeterminismError(f"ignored pointer does not exist: {pointer}")
    final = tokens[-1]
    if isinstance(current, dict):
        if final not in current:
            raise DeterminismError(f"ignored pointer does not exist: {pointer}")
        del current[final]
        return
    if isinstance(current, list):
        try:
            index = int(final)
        except ValueError as exc:
            raise DeterminismError(f"ignored pointer does not exist: {pointer}") from exc
        if index < 0 or index >= len(current):
            raise DeterminismError(f"ignored pointer does not exist: {pointer}")
        del current[index]
        return
    raise DeterminismError(f"ignored pointer does not exist: {pointer}")


def _diff(left: bytes, right: bytes, *, left_name: str = "left", right_name: str = "right") -> str:
    left_lines = left.decode("utf-8", "replace").splitlines(keepends=True)
    right_lines = right.decode("utf-8", "replace").splitlines(keepends=True)
    return "".join(difflib.unified_diff(left_lines, right_lines, fromfile=left_name, tofile=right_name))


def _difference_pointers(left: object, right: object, *, pointer: str = "") -> list[str]:
    if type(left) is not type(right):
        return [pointer or "/"]
    if isinstance(left, dict):
        pointers: list[str] = []
        for key in sorted(set(left) | set(right), key=str):
            child = f"{pointer}/{_encode_pointer_token(str(key))}"
            if key not in left or key not in right:
                pointers.append(child)
            else:
                pointers.extend(_difference_pointers(left[key], right[key], pointer=child))
        return pointers
    if isinstance(left, list):
        pointers = []
        for index in range(max(len(left), len(right))):
            child = f"{pointer}/{index}"
            if index >= len(left) or index >= len(right):
                pointers.append(child)
            else:
                pointers.extend(_difference_pointers(left[index], right[index], pointer=child))
        return pointers
    return [] if left == right else [pointer or "/"]


def compare_json_values(left: object, right: object, *, ignored_pointers: Sequence[str]) -> ComparisonResult:
    normalized_left = copy.deepcopy(left)
    normalized_right = copy.deepcopy(right)
    for pointer in ignored_pointers:
        _remove_pointer(normalized_left, pointer)
        _remove_pointer(normalized_right, pointer)
    left_bytes = _json_bytes(normalized_left)
    right_bytes = _json_bytes(normalized_right)
    if left_bytes == right_bytes:
        return ComparisonResult(True, _sha256(left_bytes), _sha256(right_bytes), "")
    pointers = _difference_pointers(normalized_left, normalized_right)
    pointer_summary = "changed_json_pointers:\n" + "".join(f"- {pointer}\n" for pointer in pointers)
    return ComparisonResult(
        False,
        _sha256(left_bytes),
        _sha256(right_bytes),
        pointer_summary + _diff(left_bytes, right_bytes),
    )


def _resolve_json_pointer(payload: object, pointer: str) -> object:
    current = payload
    for token in _pointer_tokens(pointer):
        if isinstance(current, dict):
            if token not in current:
                raise DeterminismError(f"invariant pointer does not exist: {pointer}")
            current = current[token]
        elif isinstance(current, list):
            try:
                index = int(token)
            except ValueError as exc:
                raise DeterminismError(f"invariant pointer does not exist: {pointer}") from exc
            if index < 0 or index >= len(current):
                raise DeterminismError(f"invariant pointer does not exist: {pointer}")
            current = current[index]
        else:
            raise DeterminismError(f"invariant pointer does not exist: {pointer}")
    return current


def compare_outputs(left: Path, right: Path, rule: Mapping[str, object]) -> ComparisonResult:
    determinism_class = str(rule.get("class", ""))
    data_format = str(rule.get("format", ""))
    if determinism_class not in {"byte", "semantic", "bounded"}:
        raise DeterminismError(f"unsupported determinism class: {determinism_class!r}")
    left_bytes = left.read_bytes()
    right_bytes = right.read_bytes()
    if determinism_class == "byte":
        equal = left_bytes == right_bytes
        return ComparisonResult(equal, _sha256(left_bytes), _sha256(right_bytes), "" if equal else "byte content differs")
    if data_format != "json":
        raise DeterminismError(
            f"{determinism_class} comparison does not support format {data_format!r}; use the format-specific specialist"
        )
    try:
        left_payload = json.loads(left_bytes.decode("utf-8"))
        right_payload = json.loads(right_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DeterminismError(f"semantic JSON input is invalid: {exc}") from exc
    if determinism_class == "semantic":
        ignored = rule.get("ignore_json_pointers", [])
        if not isinstance(ignored, list) or any(not isinstance(value, str) for value in ignored):
            raise DeterminismError("ignore_json_pointers must be an array of strings")
        return compare_json_values(left_payload, right_payload, ignored_pointers=tuple(ignored))
    invariants = rule.get("invariants")
    if not isinstance(invariants, list) or not invariants:
        raise DeterminismError("bounded determinism requires explicit invariants")
    if any(not isinstance(value, str) for value in invariants):
        raise DeterminismError("bounded invariants must be JSON pointers")
    left_subset = {pointer: _resolve_json_pointer(left_payload, pointer) for pointer in invariants}
    right_subset = {pointer: _resolve_json_pointer(right_payload, pointer) for pointer in invariants}
    return compare_json_values(left_subset, right_subset, ignored_pointers=())
