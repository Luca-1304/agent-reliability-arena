"""Guard private evidence paths from symlinked parent-directory redirection."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.private_pilot import _prepare_private_root
from scripts.run_private_pilot import _verify_prepared_private_output


class PrivateOutputAncestryTests(unittest.TestCase):
    def test_rejects_existing_private_directory_via_symlink_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            prepared = real / "prepared"
            prepared.mkdir(mode=0o700)
            if os.name != "nt":
                prepared.chmod(0o700)
            shortcut = root / "shortcut"
            try:
                shortcut.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Directory symlink creation is unavailable.")

            with self.assertRaisesRegex(ValueError, "symlinked parent"):
                _prepare_private_root(shortcut / "prepared")
            with self.assertRaisesRegex(ValueError, "symlinked parent"):
                _verify_prepared_private_output(shortcut / "prepared")

            # Reject before writing any sensitive artefacts.
            self.assertEqual(list(prepared.iterdir()), [])

    def test_rejects_new_private_directory_via_symlink_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real"
            real.mkdir()
            shortcut = root / "shortcut"
            try:
                shortcut.symlink_to(real, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Directory symlink creation is unavailable.")
            with self.assertRaisesRegex(ValueError, "symlinked parent"):
                _prepare_private_root(shortcut / "new-output")
            self.assertFalse((real / "new-output").exists())

    def test_prepared_normal_directory_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = root / "prepared"
            prepared.mkdir(mode=0o700)
            if os.name != "nt":
                prepared.chmod(0o700)
            self.assertEqual(_verify_prepared_private_output(prepared), prepared)
            self.assertEqual(_prepare_private_root(prepared), prepared)


if __name__ == "__main__":
    unittest.main()
