"""Session executor wiring for startup coordinators."""

import gc
import socket
import threading
import time
import weakref

import pytest
from django.db.backends.signals import connection_created
from django.db.utils import OperationalError

from hpcperfstats.dbload.lib import sync_timedb_session_executor as se
from hpcperfstats.dbload.lib.sync_timedb_session_executor import (
  SyncTimedbThreadPool,
)
from hpcperfstats.dbload.lib.sync_timedb_startup_archive_scan import (
  StartupArchiveScanCoordinator,
)


class _FakeRaw:
  """psycopg-like connection exposing a real socket fd."""

  def __init__(self, sock):
    self._sock = sock
    self.closed = False

  def fileno(self):
    return self._sock.fileno()

  def close(self):
    self.closed = True


class _FakeWrapper:
  """Django DatabaseWrapper stand-in holding one raw connection."""

  vendor = "sqlite"
  alias = "default"

  def __init__(self, raw):
    self.connection = raw


def test_terminate_shuts_abandoned_task_backend_socket(monkeypatch):
  """terminate() must EOF a stuck task's backend so Postgres frees the slot."""
  ours, peer = socket.socketpair()
  peer.settimeout(5)
  wrapper = _FakeWrapper(_FakeRaw(ours))
  monkeypatch.setattr(se, "_thread_django_wrappers", lambda: [wrapper])
  monkeypatch.setattr(se.connections, "close_all", lambda: None)
  started = threading.Event()
  release = threading.Event()
  idents = []

  def stuck():
    idents.append(threading.get_ident())
    started.set()
    release.wait(timeout=5)

  pool = SyncTimedbThreadPool(max_workers=1, thread_role="ingest-pool")
  try:
    pool.apply_async(stuck)
    assert started.wait(timeout=5)
    pool.terminate()
    assert peer.recv(1) == b""
    assert idents[0] in se._ABANDONED_THREAD_IDENTS
  finally:
    release.set()
    pool.join()
    ours.close()
    peer.close()
  assert idents[0] not in se._ABANDONED_THREAD_IDENTS
  assert pool._task_connections == {}


def test_join_after_terminate_does_not_wait_for_stuck_worker():
  """terminate() then join() must not hang on workers stuck in native/long sleep."""
  release = threading.Event()

  def stuck() -> None:
    release.wait(timeout=3600)

  pool = SyncTimedbThreadPool(max_workers=1, thread_role="ingest-pool")
  try:
    pool.apply_async(stuck)
    time.sleep(0.1)
    pool.terminate()
    t0 = time.monotonic()
    pool.join()
    assert (time.monotonic() - t0) < 2.0
  finally:
    release.set()


def test_completed_task_is_never_abandoned(monkeypatch):
  """Normal completion unregisters the task; later terminate touches nothing."""
  ours, peer = socket.socketpair()
  wrapper = _FakeWrapper(_FakeRaw(ours))
  monkeypatch.setattr(se, "_thread_django_wrappers", lambda: [wrapper])
  monkeypatch.setattr(se.connections, "close_all", lambda: None)
  pool = SyncTimedbThreadPool(max_workers=1, thread_role="ingest-pool")
  try:
    assert pool.apply_async(lambda: 7).get(timeout=5) == 7
    pool.terminate()
    pool.join()
    assert pool._task_connections == {}
    peer.setblocking(False)
    with pytest.raises(BlockingIOError):
      peer.recv(1)
  finally:
    ours.close()
    peer.close()


def test_abandoned_thread_reconnect_is_refused_and_closed():
  """connection_created in an abandoned thread closes the new backend."""
  raw = _FakeRaw(None)
  wrapper = _FakeWrapper(raw)
  ident = threading.get_ident()
  with se._ABANDONED_LOCK:
    se._ABANDONED_THREAD_IDENTS.add(ident)
  try:
    with pytest.raises(OperationalError, match="terminated"):
      connection_created.send(sender=None, connection=wrapper)
  finally:
    with se._ABANDONED_LOCK:
      se._ABANDONED_THREAD_IDENTS.discard(ident)
  assert raw.closed is True
  assert wrapper.connection is None
  other = _FakeWrapper(_FakeRaw(None))
  connection_created.send(sender=None, connection=other)
  assert other.connection is not None


def test_startup_archive_scan_coordinator_construct(tmp_path):
  coord = StartupArchiveScanCoordinator(
    archive_data_dir=str(tmp_path / "archive"),
    host_name_ext=".hpc",
    tgz_archive_dir=str(tmp_path / "daily"),
    log_fn=lambda *_a, **_k: None,
  )
  assert coord.get_snapshot() is None


def test_titled_thread_pool_closes_all_thread_local_connections_after_task(
  monkeypatch,
):
  """Worker finally must call connections.close_all(), not only close_old."""
  calls = []
  monkeypatch.setattr(
    "hpcperfstats.dbload.lib.sync_timedb_session_executor.connections.close_all",
    lambda: calls.append("close_all"),
  )
  pool = SyncTimedbThreadPool(
    max_workers=1,
    thread_role="metrics-pool",
    process_title="update_metrics.py",
  )
  try:
    assert pool.apply_async(lambda: 1).get(timeout=5) == 1
    assert pool.imap_unordered(lambda x: x, [2]).next(timeout=5) == 2
  finally:
    pool.terminate()
    pool.join()
  assert calls.count("close_all") >= 2


def test_titled_thread_pool_imap_unordered_supports_timeout_and_completion_order():
  pool = SyncTimedbThreadPool(
    max_workers=2,
    thread_role="metrics-pool",
    process_title="update_metrics.py",
  )

  def delayed(item):
    delay, value = item
    time.sleep(delay)
    return value

  iterator = pool.imap_unordered(
    delayed,
    [(0.05, "slow"), (0.0, "fast")],
    chunksize=1,
  )
  assert iterator.next(timeout=0.5) == "fast"
  assert iterator.next(timeout=0.5) == "slow"
  with pytest.raises(StopIteration):
    next(iterator)
  pool.close()
  pool.join()


def test_titled_thread_pool_exposes_bounded_worker_count():
  pool = SyncTimedbThreadPool(
    max_workers=3,
    thread_role="metrics-pool",
    process_title="update_metrics.py",
  )
  try:
    assert pool._processes == 3
    assert pool.is_active is True
  finally:
    pool.terminate()
    pool.join()


def test_titled_thread_pool_imap_keeps_only_worker_width_submitted():
  """Lazy submission bounds shared-heap Futures and input payloads."""
  gate = threading.Event()
  produced = []
  pool = SyncTimedbThreadPool(
    max_workers=2,
    thread_role="metrics-pool",
    process_title="update_metrics.py",
  )

  def items():
    for item in range(10):
      produced.append(item)
      yield item

  def blocked(item):
    gate.wait(timeout=1)
    return item

  try:
    iterator = pool.imap_unordered(blocked, items())
    assert produced == [0, 1]
    gate.set()
    assert iterator.next(timeout=1) in {0, 1}
    assert produced == [0, 1, 2]
  finally:
    gate.set()
    pool.terminate()
    pool.join()


def test_titled_thread_pool_imap_close_releases_unsubmitted_inputs():
  """Closing a stalled iterator must release its unsubmitted source."""
  gate = threading.Event()
  pool = SyncTimedbThreadPool(
    max_workers=1,
    thread_role="metrics-pool",
    process_title="update_metrics.py",
  )

  class Payload:
    pass

  retained = Payload()
  retained_ref = weakref.ref(retained)
  items = [object(), retained]

  def blocked(item):
    del item
    gate.wait(timeout=1)

  try:
    iterator = pool.imap_unordered(blocked, items)
    del items, retained
    iterator.close()
    gc.collect()
    assert retained_ref() is None
  finally:
    gate.set()
    pool.terminate()
    pool.join()


def test_titled_thread_pool_imap_worker_error_does_not_submit_next_input():
  """A terminal Future error must close the source before refill."""
  produced = []
  pool = SyncTimedbThreadPool(
    max_workers=1,
    thread_role="metrics-pool",
    process_title="update_metrics.py",
  )

  def items():
    for item in range(2):
      produced.append(item)
      yield item

  def fail(item):
    raise ValueError(str(item))

  try:
    iterator = pool.imap_unordered(fail, items())
    with pytest.raises(ValueError, match="0"):
      iterator.next(timeout=1)
    assert produced == [0]
  finally:
    pool.terminate()
    pool.join()
