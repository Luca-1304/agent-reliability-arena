from __future__ import annotations

import errno
import math
import os
import stat
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl


_DEFAULT_RETRY_SECONDS = 0.01
_THREAD_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_BUSY_ERRNOS = {
    errno.EACCES,
    errno.EAGAIN,
    getattr(errno, "EDEADLK", errno.EACCES),
}


def _validate_lock_timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("'lock_timeout_seconds' must be a positive finite number.")
    timeout = float(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("'lock_timeout_seconds' must be a positive finite number.")
    return timeout


def _lock_path_for(ledger_path: Path) -> Path:
    path = Path(ledger_path)
    return path.with_name(path.name + ".lock")


def validate_ledger_lock_path(ledger_path: Path) -> Path:
    lock_path = _lock_path_for(Path(ledger_path))
    parent = lock_path.parent
    if not parent.exists() or not parent.is_dir():
        raise ValueError(
            f"Ledger lock parent directory does not exist or is not a directory: {parent}"
        )
    if lock_path.is_symlink():
        raise ValueError(f"Ledger lock path must not be a symlink: {lock_path}")
    if lock_path.exists() and not lock_path.is_file():
        raise ValueError(f"Ledger lock path must be a regular file: {lock_path}")
    return lock_path


def _thread_lock_for(lock_path: Path) -> threading.Lock:
    key = os.path.normcase(os.path.abspath(os.fspath(lock_path)))
    with _THREAD_LOCKS_GUARD:
        existing = _THREAD_LOCKS.get(key)
        if existing is None:
            existing = threading.Lock()
            _THREAD_LOCKS[key] = existing
        return existing


def _open_lock_file(lock_path: Path) -> int:
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        if lock_path.is_symlink():
            raise ValueError(f"Ledger lock path must not be a symlink: {lock_path}") from exc
        raise

    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"Ledger lock path must be a regular file: {lock_path}")

        current = os.stat(lock_path, follow_symlinks=False)
        if stat.S_ISLNK(current.st_mode):
            raise ValueError(f"Ledger lock path must not be a symlink: {lock_path}")
        if not stat.S_ISREG(current.st_mode):
            raise ValueError(f"Ledger lock path must be a regular file: {lock_path}")

        opened_inode = getattr(opened, "st_ino", 0)
        current_inode = getattr(current, "st_ino", 0)
        opened_device = getattr(opened, "st_dev", 0)
        current_device = getattr(current, "st_dev", 0)
        if opened_inode and current_inode and (
            opened_inode != current_inode or opened_device != current_device
        ):
            raise ValueError(f"Ledger lock path changed while opening: {lock_path}")

        if opened.st_size < 1:
            os.lseek(descriptor, 0, os.SEEK_SET)
            written = os.write(descriptor, b"\0")
            if written != 1:
                raise OSError("Could not initialise ledger lock byte.")
            os.fsync(descriptor)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _wait_or_timeout(deadline: float, lock_path: Path) -> None:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError(f"Timed out acquiring ledger lock: {lock_path}")
    time.sleep(min(_DEFAULT_RETRY_SECONDS, remaining))


def _acquire_process_lock(descriptor: int, lock_path: Path, deadline: float) -> None:
    while True:
        try:
            if os.name == "nt":
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except OSError as exc:
            if exc.errno not in _BUSY_ERRNOS:
                raise
            _wait_or_timeout(deadline, lock_path)


def _release_process_lock(descriptor: int) -> None:
    if os.name == "nt":
        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        fcntl.flock(descriptor, fcntl.LOCK_UN)


@contextmanager
def _exclusive_ledger_lock(
    ledger_path: Path,
    *,
    timeout_seconds: float,
) -> Iterator[None]:
    timeout = _validate_lock_timeout(timeout_seconds)
    lock_path = validate_ledger_lock_path(Path(ledger_path))
    deadline = time.monotonic() + timeout
    thread_lock = _thread_lock_for(lock_path)
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not thread_lock.acquire(timeout=remaining):
        raise TimeoutError(f"Timed out acquiring ledger lock: {lock_path}")

    descriptor: int | None = None
    process_locked = False
    try:
        # Validate again after the in-process wait so a changed lock path is not trusted.
        lock_path = validate_ledger_lock_path(Path(ledger_path))
        descriptor = _open_lock_file(lock_path)
        _acquire_process_lock(descriptor, lock_path, deadline)
        process_locked = True
        yield
    finally:
        try:
            if descriptor is not None and process_locked:
                _release_process_lock(descriptor)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            thread_lock.release()
