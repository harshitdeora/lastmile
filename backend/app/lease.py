"""Prevent accidental multi-worker startup against a shared private-state volume."""

from pathlib import Path
import os


def acquire_process_lease():
    folder = Path(os.getenv("PRIVATE_STATE_DIR", ".private"))
    folder.mkdir(parents=True, exist_ok=True)
    handle = (folder / "worker.lock").open("a+b")
    handle.write(b"0")
    handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise RuntimeError(
            "LastMile supports one backend worker only. Stop the other worker or use its API."
        ) from exc
    return handle
