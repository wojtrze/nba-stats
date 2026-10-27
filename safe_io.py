"""Writing the data files safely when the dashboards, the scheduled jobs and the scraper run at the same time.

- locked(path): an exclusive lock across processes (a `<path>.lock` file created with O_EXCL), so a read-modify-write
  (check the last saved lineup, then append; read the log, drop a game, write it back) can't interleave with
  another writer. Reentrant within a thread; a lock older than STALE_SECONDS (a crashed writer) is broken.
- atomic_write / atomic_to_csv: write a temporary file next to the target, then os.replace it, so an interrupted
  write leaves the old file whole and a reader never sees half a file.
- append_csv: locked + atomic append that keeps the saved bytes as they are and the file's column order.
"""
import os
import threading
import time
from contextlib import contextmanager
from typing import Callable, Iterator, Optional

import pandas as pd

LOCK_TIMEOUT = 60        # seconds to wait for another writer before giving up
STALE_SECONDS = 300      # a lock this old belongs to a writer that died
_held = threading.local()


def _lock_path(path: str) -> str:
    return os.path.abspath(path) + '.lock'


@contextmanager
def locked(path: str, timeout: float = LOCK_TIMEOUT) -> Iterator[None]:
    """Hold the exclusive lock of `path` (the file needn't exist). Raises TimeoutError after `timeout` seconds."""
    lock = _lock_path(path)
    held = getattr(_held, 'locks', None)
    if held is None:
        held = _held.locks = set()
    if lock in held:                     # already ours (a locked caller of a locked helper)
        yield
        return
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    start = time.monotonic()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}\n".encode())
            os.close(fd)
            break
        except (FileExistsError, PermissionError):
            # PermissionError: on Windows the lock file is being deleted by its holder right now: busy, try again
            try:
                if time.time() - os.path.getmtime(lock) > STALE_SECONDS:
                    os.remove(lock)
                    continue
            except FileNotFoundError:
                continue
            except PermissionError:
                pass
            if time.monotonic() - start > timeout:
                raise TimeoutError(f"{path} is locked by another writer ({lock})")
            time.sleep(0.05)
    held.add(lock)
    try:
        yield
    finally:
        held.discard(lock)
        for attempt in range(100):     # a waiting process may be looking at the file this instant (Windows)
            try:
                os.remove(lock)
                break
            except FileNotFoundError:
                break
            except PermissionError:
                time.sleep(0.01)


def _replace(tmp: str, path: str, attempts: int = 100):
    """os.replace, retried briefly: on Windows it fails while another process has the target open for reading."""
    for i in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05)


def atomic_write(path: str, write: Callable, mode: str = 'w', **open_args):
    """write(f) into a temporary file next to `path`, then replace `path` with it in one step."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        with open(tmp, mode, **open_args) as f:
            write(f)
            f.flush()
            os.fsync(f.fileno())
        _replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def atomic_write_text(path: str, text: str):
    atomic_write(path, lambda f: f.write(text), encoding='utf-8', newline='')


def atomic_to_csv(df: pd.DataFrame, path: str, **to_csv_args):
    """df.to_csv(path, index=False, ...) written atomically, with the line ending pandas uses for a path."""
    to_csv_args.setdefault('index', False)
    to_csv_args.setdefault('lineterminator', os.linesep)
    atomic_write(path, lambda f: df.to_csv(f, **to_csv_args), encoding='utf-8', newline='')


def append_csv(df: pd.DataFrame, path: str, columns: Optional[list] = None) -> int:
    """Append df's rows to the CSV at `path` (created with a header when missing), under its lock and atomically:
    the rows already saved are kept byte for byte. Columns follow the file's header (or `columns` for a new file);
    columns df lacks are left empty, columns the file lacks are dropped (callers that add columns rewrite the file
    under locked() themselves). Returns the rows appended."""
    if df.empty:
        return 0
    with locked(path):
        if not os.path.exists(path):
            atomic_to_csv(df.reindex(columns=columns) if columns else df, path)
            return len(df)
        header = list(pd.read_csv(path, nrows=0).columns)
        with open(path, 'rb') as f:
            saved = f.read()
        ending = '\r\n' if b'\r\n' in saved[:4096] else '\n'      # the file's own (pandas writes os.linesep)
        if saved and not saved.endswith(b'\n'):
            saved += ending.encode()
        rows = df.reindex(columns=header).to_csv(index=False, header=False, lineterminator=ending).encode('utf-8')
        atomic_write(path, lambda f: f.write(saved + rows), mode='wb')
    return len(df)
