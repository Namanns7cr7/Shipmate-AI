"""
sqlite_store — ONE connection manager + location policy for every ShipMate
sqlite store (inflight registry, report history, OAuth state).

Before this, three modules each hand-rolled their own sqlite plumbing with
three different lifecycles, PRAGMA sets, and locations:

  • inflight_registry._conn     — per-thread cache; WAL + busy_timeout +
                                  foreign_keys; /tmp/shipmate_inflight.db
  • report_store._conn          — per-thread (path-aware) cache; WAL +
                                  busy_timeout; /tmp/shipmate_reports.db
  • github_auth_service._get_conn — open/close PER CALL; WAL only, no
                                  busy_timeout; oauth_state.db NEXT TO THE
                                  MODULE (inside the source tree!)

"Where does state live, and does it survive a restart?" had three answers.
This module is the single answer:

  • connect(name) returns a connection cached per (thread, resolved-path) with
    the SAME PRAGMAs everywhere — WAL, busy_timeout=5000, foreign_keys=ON, and
    a sqlite3.Row row_factory.
  • ONE location policy: SHIPMATE_STORE_DIR (default /tmp) is the base dir and
    each store is a file under it. A per-store LEGACY env override
    (SHIPMATE_INFLIGHT_DB / SHIPMATE_REPORTS_DB / OAUTH_STATE_DB) still wins
    when set — read at CALL TIME so a test fixture that points it at a tmp path
    keeps working without import-order games.
  • register(...) records a store's filename + legacy env + DDL. init_all()
    (called from the FastAPI lifespan) applies every registered schema eagerly.
    connect() ALSO applies the store's schema on first open, so a store still
    works when init_all() never ran (CLI scripts, ad-hoc tests).

The three stores keep their own public functions, signatures, and table names
— this unifies only the plumbing beneath them.
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger("shipmate.sqlite_store")

# Default base directory for every store. /tmp matches the convention the two
# newer stores already used; the OAuth store moves here too (it previously sat
# inside the source tree, which is the inconsistency this refactor closes).
_DEFAULT_STORE_DIR = "/tmp"


def store_dir() -> str:
    """Resolve the base directory for all stores. Read at call time so a test
    that sets SHIPMATE_STORE_DIR before the first DB touch is honoured."""
    d = os.getenv("SHIPMATE_STORE_DIR", _DEFAULT_STORE_DIR)
    try:
        os.makedirs(d, exist_ok=True)
    except OSError as e:  # pragma: no cover - defensive (e.g. read-only fs)
        logger.warning("sqlite_store: could not create store dir %s: %s", d, e)
    return d


@dataclass
class _StoreSpec:
    name: str
    filename: str     # default file under store_dir()
    legacy_env: str   # per-store env override, wins when set (back-compat)
    schema: str       # DDL applied idempotently (CREATE ... IF NOT EXISTS)


_REGISTRY: Dict[str, _StoreSpec] = {}
_thread_local = threading.local()


def register(name: str, *, filename: str, legacy_env: str, schema: str) -> None:
    """Register a store's location + DDL. Idempotent; safe to call at import."""
    _REGISTRY[name] = _StoreSpec(
        name=name, filename=filename, legacy_env=legacy_env, schema=schema,
    )


def db_path(name: str) -> str:
    """Resolve a store's file path. The per-store legacy env override wins
    (read at call time); otherwise store_dir()/filename."""
    spec = _REGISTRY.get(name)
    if spec is None:
        raise KeyError(f"sqlite_store: unknown store {name!r} (call register first)")
    override = os.getenv(spec.legacy_env)
    if override:
        return override
    return os.path.join(store_dir(), spec.filename)


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")


def connect(name: str) -> sqlite3.Connection:
    """Return a per-(thread, resolved-path) cached connection for store `name`,
    with shared PRAGMAs and the store's schema applied on first open.

    check_same_thread=False because FastAPI runs blocking handlers on a worker
    threadpool — a connection may legitimately move threads. We keep one
    connection PER thread via the cache below, so it's never shared
    simultaneously. The cache is path-aware: if the resolved path changes
    (a test repoints the legacy env var), we open a fresh connection rather
    than serve a stale handle to the old file."""
    cache: Dict[str, tuple] = getattr(_thread_local, "conns", None)
    if cache is None:
        cache = {}
        _thread_local.conns = cache

    path = db_path(name)
    cached = cache.get(name)
    if cached is not None and cached[0] == path:
        return cached[1]
    if cached is not None:
        # Path changed under us (test isolation) — close the stale handle.
        try:
            cached[1].close()
        except Exception:
            pass

    conn = sqlite3.connect(path, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    spec = _REGISTRY[name]
    conn.executescript(spec.schema)
    conn.commit()
    cache[name] = (path, conn)
    return conn


def init_schema(name: str) -> None:
    """Eager-create one store's tables (side-effect of opening it)."""
    connect(name)


def init_all() -> None:
    """Eager-create every registered store's tables. Called from the FastAPI
    lifespan startup so the first request doesn't pay the create cost."""
    for name in list(_REGISTRY):
        try:
            connect(name)
        except Exception as e:  # pragma: no cover - startup best-effort
            logger.warning("sqlite_store: init_all failed for %s: %s", name, e)
    logger.info("sqlite_store: initialized %d store(s) under %s",
                len(_REGISTRY), store_dir())


def close_all() -> None:
    """Close this thread's cached connections. For test teardown / shutdown."""
    cache: Dict[str, tuple] = getattr(_thread_local, "conns", None)
    if not cache:
        return
    for _name, (_path, conn) in list(cache.items()):
        try:
            conn.close()
        except Exception:
            pass
    cache.clear()
