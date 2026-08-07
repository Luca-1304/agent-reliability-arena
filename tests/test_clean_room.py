from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts.ci.verify_clean_room import (
    CleanRoomError,
    assert_package_outside_workspace,
    build_clean_room_environment,
)


class CleanRoomTests(unittest.TestCase):
    def test_environment_removes_workspace_and_provider_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            clean_root = root / "clean"
            workspace.mkdir()
            base = {
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": f"{workspace}/src",
                "VIRTUAL_ENV": f"{workspace}/.venv",
                "PIP_CACHE_DIR": f"{workspace}/cache",
                "OPENAI_API_KEY": "not-real",
                "CUSTOM_SECRET": "not-real",
                "HOME": f"{workspace}/home",
                "LANG": "en_GB.UTF-8",
            }
            env = build_clean_room_environment(base=base, workspace=workspace, root=clean_root)
            joined = "\n".join(f"{key}={value}" for key, value in env.items())
            self.assertNotIn(str(workspace), joined)
            self.assertNotIn("PYTHONPATH", env)
            self.assertNotIn("VIRTUAL_ENV", env)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("CUSTOM_SECRET", env)
            self.assertEqual(env["TZ"], "UTC")
            self.assertEqual(env["LC_ALL"], "C.UTF-8")
            self.assertEqual(env["LANG"], "C.UTF-8")
            self.assertEqual(env["PYTHONHASHSEED"], "0")
            self.assertTrue(Path(env["HOME"]).is_relative_to(clean_root))
            self.assertTrue(Path(env["PIP_CACHE_DIR"]).is_relative_to(clean_root))

    def test_path_is_preserved_only_when_it_does_not_reference_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            workspace.mkdir()
            env = build_clean_room_environment(
                base={"PATH": f"/usr/bin:{workspace}/bin:/bin"},
                workspace=workspace,
                root=root / "clean",
            )
            self.assertEqual(env["PATH"], os.pathsep.join(["/usr/bin", "/bin"]))

    def test_package_resolving_inside_workspace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            module = workspace / "src" / "agent_reliability_arena" / "__init__.py"
            module.parent.mkdir(parents=True)
            module.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(CleanRoomError, "resolved inside workspace"):
                assert_package_outside_workspace(module, workspace)

    def test_package_resolving_outside_workspace_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "repo"
            installed = root / "clean" / "venv" / "site-packages" / "agent_reliability_arena" / "__init__.py"
            workspace.mkdir()
            installed.parent.mkdir(parents=True)
            installed.write_text("", encoding="utf-8")
            assert_package_outside_workspace(installed, workspace)


if __name__ == "__main__":
    unittest.main()
