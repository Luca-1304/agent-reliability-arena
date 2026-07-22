from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "showcase" / "publication-manifest.json"


class ShowcaseHashInventoryTests(unittest.TestCase):
    def test_manifest_hashes_match_exact_public_files(self) -> None:
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected = {row["path"]: row["sha256"] for row in raw["files"]}
        actual = {
            relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            for relative in sorted(expected)
        }
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
