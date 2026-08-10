from __future__ import annotations

import json
import math
import multiprocessing
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agent_reliability_arena.transports import (
    ModelCallRequest,
    ModelCallResult,
    ModelUsage,
    RecordingTransport,
    TransportError,
    verify_transport_ledger,
)
from agent_reliability_arena.transports._ledger_lock import _exclusive_ledger_lock


FIXED_TIME = datetime(2026, 8, 9, 21, 0, tzinfo=timezone.utc)


def make_request(call_id: str) -> ModelCallRequest:
    return ModelCallRequest(
        call_id=call_id,
        condition="general",
        role="general",
        model_id="fixture-model",
        model_version="2026-08-09",
        prompt_version="concurrent-ledger-v2",
        instructions="Return a concise response.",
        input_text=f"Record {call_id}.",
        max_output_tokens=128,
        seed=1304,
        metadata={"scenario": "concurrency"},
    )


def make_result(request: ModelCallRequest) -> ModelCallResult:
    return ModelCallResult(
        call_id=request.call_id,
        request_digest=request.digest,
        provider="fixture-provider",
        response_id=f"response-{request.call_id}",
        model_id=request.model_id,
        output_text=f"recorded {request.call_id}",
        status="completed",
        latency_ms=12,
        usage=ModelUsage(input_tokens=8, output_tokens=3, total_tokens=11),
        raw_response_sha256="a" * 64,
        client_request_id=f"arena-{request.digest}",
        provider_request_id=f"provider-{request.call_id}",
        provider_processing_ms=7,
    )


class StaticTransport:
    provider = "fixture-provider"

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        return make_result(request)


class ErrorTransport:
    provider = "fixture-provider"

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        raise TransportError(
            f"expected error for {request.call_id}",
            category="fixture_error",
            retryable=False,
            client_request_id=f"arena-{request.digest}",
        )


class BarrierTransport:
    provider = "fixture-provider"

    def __init__(self, barrier: threading.Barrier) -> None:
        self.barrier = barrier

    def complete(self, request: ModelCallRequest) -> ModelCallResult:
        self.barrier.wait(timeout=10)
        return make_result(request)


def _wait_for_path(path: Path, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not path.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Timed out waiting for process marker: {path}")
        time.sleep(0.01)


def _process_writer(
    ledger_text: str,
    call_id: str,
    should_error: bool,
    ready_dir_text: str,
    start_marker_text: str,
) -> None:
    ledger = Path(ledger_text)
    request = make_request(call_id)
    transport = ErrorTransport() if should_error else StaticTransport()
    recorder = RecordingTransport(transport, ledger, clock=lambda: FIXED_TIME)
    Path(ready_dir_text, call_id).write_text("ready", encoding="utf-8")
    _wait_for_path(Path(start_marker_text), 20.0)
    try:
        recorder.complete(request)
    except TransportError:
        if not should_error:
            raise


def _hold_lock_process(
    ledger_text: str,
    ready_marker_text: str,
    release_marker_text: str,
) -> None:
    from agent_reliability_arena.transports._ledger_lock import _exclusive_ledger_lock as hold_lock

    with hold_lock(Path(ledger_text), timeout_seconds=5.0):
        Path(ready_marker_text).write_text("locked", encoding="utf-8")
        _wait_for_path(Path(release_marker_text), 20.0)


def _load_rows(ledger: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]


def _assert_schema2_chain(
    testcase: unittest.TestCase,
    rows: list[dict[str, object]],
) -> None:
    testcase.assertTrue(rows)
    testcase.assertEqual({row["schema_version"] for row in rows}, {"2"})
    testcase.assertIsNone(rows[0]["previous_record_digest"])
    for previous, current in zip(rows, rows[1:]):
        testcase.assertEqual(
            current["previous_record_digest"],
            previous["record_digest"],
        )


def _wait_for_ready_processes(
    ready_dir: Path,
    expected_names: set[str],
    processes: list[multiprocessing.Process],
    timeout_seconds: float,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        observed = {path.name for path in ready_dir.iterdir()}
        if observed == expected_names:
            return
        exited = [process.exitcode for process in processes if process.exitcode is not None]
        if exited:
            raise AssertionError(f"Writer exited before start marker: {exited}")
        if time.monotonic() >= deadline:
            raise AssertionError(
                f"Timed out waiting for writer readiness: expected={sorted(expected_names)} observed={sorted(observed)}"
            )
        time.sleep(0.01)


class ConcurrentTransportLedgerTests(unittest.TestCase):
    def test_recorders_created_before_writes_allocate_unique_thread_sequences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            count = 8
            recorders = [
                (
                    RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME),
                    make_request(f"thread-{index}"),
                )
                for index in range(count)
            ]
            barrier = threading.Barrier(count)
            failures: list[BaseException] = []

            def worker(recorder: RecordingTransport, request: ModelCallRequest) -> None:
                try:
                    barrier.wait(timeout=10)
                    recorder.complete(request)
                except BaseException as exc:  # captured for the parent test thread
                    failures.append(exc)

            threads = [
                threading.Thread(target=worker, args=item, daemon=True)
                for item in recorders
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)

            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(failures, [])
            rows = _load_rows(ledger)
            self.assertEqual([row["sequence"] for row in rows], list(range(1, count + 1)))
            self.assertEqual(
                {row["request"]["call_id"] for row in rows},
                {f"thread-{index}" for index in range(count)},
            )
            _assert_schema2_chain(self, rows)
            summary = verify_transport_ledger(ledger)
            self.assertEqual(summary["schema_version"], "2")
            self.assertEqual(summary["records"], count)

    def test_provider_calls_remain_parallel_while_commits_serialize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            count = 6
            provider_barrier = threading.Barrier(count)
            recorders = [
                (
                    RecordingTransport(
                        BarrierTransport(provider_barrier),
                        ledger,
                        clock=lambda: FIXED_TIME,
                    ),
                    make_request(f"provider-{index}"),
                )
                for index in range(count)
            ]
            failures: list[BaseException] = []

            def worker(recorder: RecordingTransport, request: ModelCallRequest) -> None:
                try:
                    recorder.complete(request)
                except BaseException as exc:
                    failures.append(exc)

            threads = [threading.Thread(target=worker, args=item, daemon=True) for item in recorders]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=20)

            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(failures, [])
            rows = _load_rows(ledger)
            _assert_schema2_chain(self, rows)
            self.assertEqual(verify_transport_ledger(ledger)["records"], count)

    def test_spawned_processes_write_unique_sequences_and_mixed_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "calls.jsonl"
            ready_dir = root / "ready"
            ready_dir.mkdir()
            start_marker = root / "start"
            count = 6
            expected_names = {f"process-{index}" for index in range(count)}
            context = multiprocessing.get_context("spawn")
            processes = [
                context.Process(
                    target=_process_writer,
                    args=(
                        str(ledger),
                        f"process-{index}",
                        index % 3 == 0,
                        str(ready_dir),
                        str(start_marker),
                    ),
                )
                for index in range(count)
            ]
            for process in processes:
                process.start()
            _wait_for_ready_processes(ready_dir, expected_names, processes, 30.0)
            start_marker.write_text("go", encoding="utf-8")
            for process in processes:
                process.join(timeout=30)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)
            self.assertEqual([process.exitcode for process in processes], [0] * count)

            rows = _load_rows(ledger)
            self.assertEqual([row["sequence"] for row in rows], list(range(1, count + 1)))
            self.assertEqual(
                {row["request"]["call_id"] for row in rows},
                expected_names,
            )
            _assert_schema2_chain(self, rows)
            summary = verify_transport_ledger(ledger)
            self.assertEqual(summary["schema_version"], "2")
            self.assertEqual(summary["records"], count)
            self.assertEqual(summary["results"], 4)
            self.assertEqual(summary["errors"], 2)

            follow_up = make_request("process-follow-up")
            RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME).complete(follow_up)
            rows = _load_rows(ledger)
            self.assertEqual(
                [row["sequence"] for row in rows],
                list(range(1, count + 2)),
            )
            _assert_schema2_chain(self, rows)

    def test_malformed_tail_blocks_preexisting_recorder_without_appending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            first_request = make_request("first")
            first = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            second = RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)
            first.complete(first_request)
            with ledger.open("ab") as handle:
                handle.write(b'{"partial":')
                handle.flush()
            before = ledger.read_bytes()

            with self.assertRaises(ValueError):
                second.complete(make_request("second"))

            self.assertEqual(ledger.read_bytes(), before)

    def test_public_verifier_waits_for_cooperating_writer_lock(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            request = make_request("verified")
            RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME).complete(request)
            finished = threading.Event()
            outcome: list[object] = []

            def verify() -> None:
                try:
                    outcome.append(verify_transport_ledger(ledger, lock_timeout_seconds=2.0))
                except BaseException as exc:
                    outcome.append(exc)
                finally:
                    finished.set()

            with _exclusive_ledger_lock(ledger, timeout_seconds=2.0):
                thread = threading.Thread(target=verify, daemon=True)
                thread.start()
                time.sleep(0.05)
                self.assertFalse(finished.is_set())
            thread.join(timeout=5)

            self.assertTrue(finished.is_set())
            self.assertEqual(len(outcome), 1)
            self.assertIsInstance(outcome[0], dict)
            self.assertEqual(outcome[0]["records"], 1)

    def test_cross_process_lock_timeout_leaves_ledger_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "calls.jsonl"
            request = make_request("timeout")
            RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME).complete(request)
            before = ledger.read_bytes()
            ready_marker = root / "holder-ready"
            release_marker = root / "holder-release"
            context = multiprocessing.get_context("spawn")
            holder = context.Process(
                target=_hold_lock_process,
                args=(str(ledger), str(ready_marker), str(release_marker)),
            )
            holder.start()
            _wait_for_path(ready_marker, 20.0)
            try:
                with self.assertRaises(TimeoutError):
                    verify_transport_ledger(ledger, lock_timeout_seconds=0.1)
            finally:
                release_marker.write_text("release", encoding="utf-8")
                holder.join(timeout=20)
                if holder.is_alive():
                    holder.terminate()
                    holder.join(timeout=5)
            self.assertEqual(holder.exitcode, 0)
            self.assertEqual(ledger.read_bytes(), before)

    def test_rejects_invalid_lock_timeout_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME).complete(
                make_request("timeout-validation")
            )
            invalid = (0, -1, math.inf, -math.inf, math.nan, True, "1")
            for value in invalid:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        RecordingTransport(
                            StaticTransport(),
                            ledger,
                            clock=lambda: FIXED_TIME,
                            lock_timeout_seconds=value,
                        )
                    with self.assertRaises(ValueError):
                        verify_transport_ledger(ledger, lock_timeout_seconds=value)

    def test_rejects_symlink_lock_file_when_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = root / "calls.jsonl"
            lock_target = root / "lock-target"
            lock_target.write_bytes(b"")
            lock_path = Path(str(ledger) + ".lock")
            try:
                lock_path.symlink_to(lock_target)
            except OSError as exc:
                self.skipTest(f"Symlink creation unavailable: {exc}")

            with self.assertRaisesRegex(ValueError, "lock.*symlink|symlink.*lock"):
                RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME)

    def test_persistent_lock_file_contains_no_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "calls.jsonl"
            RecordingTransport(StaticTransport(), ledger, clock=lambda: FIXED_TIME).complete(
                make_request("empty-lock")
            )
            lock_path = Path(str(ledger) + ".lock")
            self.assertTrue(lock_path.is_file())
            self.assertEqual(lock_path.read_bytes(), b"")


if __name__ == "__main__":
    unittest.main()
