from __future__ import annotations

import contextlib
import hashlib
import hmac
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_reliability_arena.repeated_receipt import write_detached_witness_receipt
from agent_reliability_arena.repeated_receipt_auth import (
    AUTH_ALGORITHM,
    AUTH_KEY_ENV,
    AUTH_SCHEMA,
    main as auth_main,
    verify_detached_receipt_auth,
    write_detached_receipt_auth,
)
from agent_reliability_arena.repeated_witness import append_completed_trial_witness
from test_repeated_receipt import make_experiment, make_receipt_parent
from test_repeated_witness import PLAN_DIGEST, PREFLIGHT_DIGEST, make_trial


KEY = bytes(range(32))
WRONG_KEY = bytes(reversed(range(32)))
AUTH_KEYS = {"schema_version", "algorithm", "receipt_digest", "key_id", "auth_tag"}
_KEY_ID_DOMAIN = b"arena-repeated-receipt-auth-key-id-v1\x00"
_AUTH_DOMAIN = b"arena-repeated-receipt-auth-v1\x00"


def expected_key_id(key: bytes) -> str:
    return hashlib.sha256(_KEY_ID_DOMAIN + key).hexdigest()


def expected_tag(key: bytes, receipt_digest: str) -> str:
    return hmac.new(key, _AUTH_DOMAIN + bytes.fromhex(receipt_digest), hashlib.sha256).hexdigest()


def create_receipt(base: Path, root: Path, name: str = "checkpoint.json") -> Path:
    parent = make_receipt_parent(base)
    path = parent / name
    write_detached_witness_receipt(root, path)
    return path


def auth_parent(base: Path) -> Path:
    path = base / "auth"
    path.mkdir()
    return path


class AuthenticatedDetachedReceiptTests(unittest.TestCase):
    def test_create_auth_envelope_commits_verified_receipt_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"

            envelope = write_detached_receipt_auth(root, receipt_path, auth_path, KEY)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

            self.assertEqual(set(envelope), AUTH_KEYS)
            self.assertEqual(envelope["schema_version"], AUTH_SCHEMA)
            self.assertEqual(envelope["algorithm"], AUTH_ALGORITHM)
            self.assertEqual(envelope["receipt_digest"], receipt["receipt_digest"])
            self.assertEqual(envelope["key_id"], expected_key_id(KEY))
            self.assertEqual(envelope["auth_tag"], expected_tag(KEY, receipt["receipt_digest"]))
            self.assertEqual(json.loads(auth_path.read_text(encoding="utf-8")), envelope)

    def test_auth_verifies_now_and_after_later_witness_appends(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"
            envelope = write_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            immediate = verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)
            self.assertEqual(immediate["status"], "verified")
            self.assertEqual(immediate["receipt_digest"], envelope["receipt_digest"])
            self.assertEqual(immediate["key_id"], expected_key_id(KEY))
            self.assertFalse(immediate["later_records_present"])

            for index in (2, 3):
                trial_id = f"trial-{index:04d}"
                make_trial(root, trial_id, f"call-{index}")
                append_completed_trial_witness(root, trial_id, PLAN_DIGEST, PREFLIGHT_DIGEST)

            later = verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)
            self.assertEqual(later["status"], "verified")
            self.assertTrue(later["later_records_present"])
            self.assertEqual(later["receipt_digest"], envelope["receipt_digest"])

    def test_rejects_wrong_or_invalid_python_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"
            write_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            with self.assertRaisesRegex(ValueError, "authentication key"):
                verify_detached_receipt_auth(root, receipt_path, auth_path, WRONG_KEY)

            for bad in (b"short", b"x" * 31, b"x" * 33, "x" * 32, bytearray(32)):
                with self.subTest(bad_type=type(bad).__name__, bad_length=len(bad)):
                    with self.assertRaisesRegex(ValueError, "32-byte"):
                        verify_detached_receipt_auth(root, receipt_path, auth_path, bad)  # type: ignore[arg-type]

    def test_create_rejects_inside_root_existing_and_symlink_auth_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)

            with self.assertRaisesRegex(ValueError, "outside"):
                write_detached_receipt_auth(root, receipt_path, root / "auth.json", KEY)

            parent = auth_parent(base)
            existing = parent / "existing.json"
            existing.write_text("occupied\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "new|exist"):
                write_detached_receipt_auth(root, receipt_path, existing, KEY)

            target = parent / "target.json"
            target.write_text("target\n", encoding="utf-8")
            link = parent / "link.json"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"Symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "symlink"):
                write_detached_receipt_auth(root, receipt_path, link, KEY)

    def test_create_rejects_parent_symlink_resolving_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            inside = root / "auth-dir"
            inside.mkdir()
            alias = base / "auth-alias"
            try:
                alias.symlink_to(inside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"Directory symlink creation unavailable: {exc}")
            with self.assertRaisesRegex(ValueError, "outside"):
                write_detached_receipt_auth(root, receipt_path, alias / "auth.json", KEY)

    def test_rejects_envelope_shape_algorithm_key_id_and_tag_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"
            original = write_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            unknown = dict(original)
            unknown["unexpected"] = True
            auth_path.write_text(json.dumps(unknown) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "shape"):
                verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            auth_path.write_text(
                '{"schema_version":"x","schema_version":"y"}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate"):
                verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            auth_path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON"):
                verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            for field, value, pattern in (
                ("algorithm", "sha256", "algorithm"),
                ("key_id", "f" * 64, "authentication key"),
                ("auth_tag", "f" * 64, "authentication tag"),
                ("receipt_digest", "f" * 64, "receipt digest"),
            ):
                tampered = dict(original)
                tampered[field] = value
                auth_path.write_text(json.dumps(tampered) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, pattern):
                    verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)

    def test_authenticated_envelope_rejects_replaced_root_and_receipt_without_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1, call_prefix="original")
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"
            old_auth = write_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            shutil.rmtree(root)
            root = make_experiment(base, 1, call_prefix="replacement")
            receipt_path.unlink()
            write_detached_witness_receipt(root, receipt_path)
            replacement = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertNotEqual(replacement["receipt_digest"], old_auth["receipt_digest"])

            forged = dict(old_auth)
            forged["receipt_digest"] = replacement["receipt_digest"]
            auth_path.write_text(json.dumps(forged) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "authentication tag|receipt digest"):
                verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)

    def test_underlying_receipt_corruption_still_fails_before_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "checkpoint.auth.json"
            write_detached_receipt_auth(root, receipt_path, auth_path, KEY)

            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["last_trial_id"] = "trial-9999"
            receipt_path.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_detached_receipt_auth(root, receipt_path, auth_path, KEY)

    def test_module_cli_uses_environment_key_without_echoing_secret(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = make_experiment(base, 1)
            receipt_path = create_receipt(base, root)
            auth_path = auth_parent(base) / "cli.auth.json"
            key_hex = KEY.hex()

            with mock.patch.dict(os.environ, {AUTH_KEY_ENV: key_hex}, clear=False):
                create_out = io.StringIO()
                with contextlib.redirect_stdout(create_out):
                    auth_main(
                        [
                            "create",
                            "--experiment-root",
                            str(root),
                            "--receipt",
                            str(receipt_path),
                            "--auth",
                            str(auth_path),
                        ]
                    )
                created = json.loads(create_out.getvalue())
                self.assertEqual(created["schema_version"], AUTH_SCHEMA)

                verify_out = io.StringIO()
                with contextlib.redirect_stdout(verify_out):
                    auth_main(
                        [
                            "verify",
                            "--experiment-root",
                            str(root),
                            "--receipt",
                            str(receipt_path),
                            "--auth",
                            str(auth_path),
                        ]
                    )
                verified = json.loads(verify_out.getvalue())
                self.assertEqual(verified["status"], "verified")

            secret = "ab" * 31
            error_out = io.StringIO()
            with mock.patch.dict(os.environ, {AUTH_KEY_ENV: secret}, clear=False):
                with contextlib.redirect_stderr(error_out):
                    with self.assertRaises(SystemExit):
                        auth_main(
                            [
                                "verify",
                                "--experiment-root",
                                str(root),
                                "--receipt",
                                str(receipt_path),
                                "--auth",
                                str(auth_path),
                            ]
                        )
            self.assertNotIn(secret, error_out.getvalue())

            error_out = io.StringIO()
            with mock.patch.dict(os.environ, {}, clear=True):
                with contextlib.redirect_stderr(error_out):
                    with self.assertRaises(SystemExit):
                        auth_main(
                            [
                                "verify",
                                "--experiment-root",
                                str(root),
                                "--receipt",
                                str(receipt_path),
                                "--auth",
                                str(auth_path),
                            ]
                        )
            self.assertIn(AUTH_KEY_ENV, error_out.getvalue())


if __name__ == "__main__":
    unittest.main()
