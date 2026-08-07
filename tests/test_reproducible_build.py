from __future__ import annotations

import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.ci.verify_reproducible_build import (
    ReproducibilityError,
    compare_wheels,
    normalized_wheel_manifest,
)


class ReproducibleBuildTests(unittest.TestCase):
    def _write_wheel(
        self,
        path: Path,
        *,
        source: bytes = b"VALUE = 1\n",
        timestamp: tuple[int, int, int, int, int, int] = (2024, 1, 1, 0, 0, 0),
        member_order: tuple[str, ...] | None = None,
    ) -> None:
        files = {
            "pkg/__init__.py": source,
            "pkg-1.0.dist-info/METADATA": b"Metadata-Version: 2.1\nName: pkg\nVersion: 1.0\n",
            "pkg-1.0.dist-info/WHEEL": b"Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
            "pkg-1.0.dist-info/entry_points.txt": b"[console_scripts]\npkg=pkg:main\n",
        }
        order = member_order or tuple(files)
        record_rows = [[name, "", ""] for name in sorted(files)] + [["pkg-1.0.dist-info/RECORD", "", ""]]
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerows(record_rows)
        files["pkg-1.0.dist-info/RECORD"] = buffer.getvalue().encode("utf-8")
        order = tuple(name for name in order if name in files) + tuple(
            name for name in files if name not in order
        )
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in order:
                info = zipfile.ZipInfo(name, date_time=timestamp)
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, files[name])

    def test_zip_timestamp_and_member_order_do_not_change_normalized_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.whl"
            second = root / "second.whl"
            self._write_wheel(first, timestamp=(2024, 1, 1, 0, 0, 0))
            self._write_wheel(
                second,
                timestamp=(2026, 8, 7, 12, 0, 0),
                member_order=(
                    "pkg-1.0.dist-info/WHEEL",
                    "pkg/__init__.py",
                    "pkg-1.0.dist-info/entry_points.txt",
                    "pkg-1.0.dist-info/METADATA",
                ),
            )
            self.assertEqual(normalized_wheel_manifest(first), normalized_wheel_manifest(second))
            self.assertTrue(compare_wheels(first, second).equal)

    def test_changed_package_byte_is_reported_by_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "first.whl"
            second = root / "second.whl"
            self._write_wheel(first, source=b"VALUE = 1\n")
            self._write_wheel(second, source=b"VALUE = 2\n")
            result = compare_wheels(first, second)
            self.assertFalse(result.equal)
            self.assertIn("pkg/__init__.py", result.diff)

    def test_absolute_or_traversal_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "bad.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("../escape.py", b"bad")
            with self.assertRaisesRegex(ReproducibilityError, "unsafe wheel member"):
                normalized_wheel_manifest(wheel)

    def test_duplicate_member_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "duplicate.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("pkg/a.py", b"one")
                archive.writestr("pkg/a.py", b"two")
            with self.assertRaisesRegex(ReproducibilityError, "duplicate wheel member"):
                normalized_wheel_manifest(wheel)

    def test_symlink_member_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "symlink.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                info = zipfile.ZipInfo("pkg/link")
                info.create_system = 3
                info.external_attr = 0o120777 << 16
                archive.writestr(info, b"target")
            with self.assertRaisesRegex(ReproducibilityError, "symlink"):
                normalized_wheel_manifest(wheel)

    def test_record_row_order_is_semantically_normalized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wheel = root / "record.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("pkg/a.py", b"a")
                archive.writestr(
                    "pkg-1.0.dist-info/RECORD",
                    "pkg-1.0.dist-info/RECORD,,\npkg/a.py,,\n",
                )
            manifest = normalized_wheel_manifest(wheel)
            record = manifest["pkg-1.0.dist-info/RECORD"]
            self.assertEqual(record["kind"], "record")
            self.assertEqual(record["rows"], [["pkg-1.0.dist-info/RECORD", "", ""], ["pkg/a.py", "", ""]])


if __name__ == "__main__":
    unittest.main()
