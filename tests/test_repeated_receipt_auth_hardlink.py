from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from agent_reliability_arena.repeated_receipt_auth import (
    verify_detached_receipt_auth,
    write_detached_receipt_auth,
)
from test_repeated_receipt_auth import KEY, auth_parent, create_receipt
from test_repeated_receipt import make_experiment


class AuthEnvelopeHardlinkTests(unittest.TestCase):
    def test_verify_rejects_auth_envelope_with_multiple_hard_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"
            write_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            linked = base / "linked-auth.json"
            try:
                os.link(auth_path, linked)
            except OSError as exc:
                self.skipTest(f"Hard-link creation unavailable: {exc}")

            self.assertGreater(auth_path.stat().st_nlink, 1)
            with self.assertRaisesRegex(ValueError, "hard link"):
                verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)


if __name__ == "__main__":
    unittest.main()
