from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from core.paths import get_database_path
from core.resources import get_schema_path

SCHEMA_VERSION = 3


class DatabaseManager:
    def __init__(self, db_path: Path | None = None, logger: logging.Logger | None = None) -> None:
        self._db_path = db_path or get_database_path()
        self._logger = logger or logging.getLogger("shroudkeeper.storage")
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(self._db_path)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._initialize_schema_if_needed()
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _initialize_schema_if_needed(self) -> None:
        if self._connection is None:
            raise RuntimeError("Database connection not initialized")

        current_version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version == 0:
            self._logger.info("Applying initial database schema")
            schema_sql = get_schema_path().read_text(encoding="utf-8")
            self._connection.executescript(schema_sql)
            self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            self._connection.commit()
            self._logger.info("Database schema applied with user_version=%s", SCHEMA_VERSION)
            return

        if current_version < 2:
            self._migrate_to_v2()

        current_version = self._connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version < 3:
            self._migrate_to_v3()

    def _migrate_to_v2(self) -> None:
        if self._connection is None:
            raise RuntimeError("Database connection not initialized")

        self._logger.info("Migrating database schema to user_version=2")

        self._connection.execute("PRAGMA foreign_keys = OFF")
        self._connection.execute("BEGIN")
        self._connection.execute(
            """
            CREATE TABLE profiles_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                protocol TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                username TEXT NOT NULL,
                remote_path TEXT NOT NULL,
                passive_mode INTEGER NOT NULL DEFAULT 1,
                verify_host_key INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        rows = self._connection.execute(
            "SELECT id, name, remote_target, created_at, updated_at FROM profiles"
        ).fetchall()

        for row in rows:
            remote_target = row["remote_target"] if row["remote_target"] is not None else "/"
            self._connection.execute(
                """
                INSERT INTO profiles_v2 (
                    id,
                    name,
                    protocol,
                    host,
                    port,
                    username,
                    remote_path,
                    passive_mode,
                    verify_host_key,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    row["name"],
                    "sftp",
                    "localhost",
                    22,
                    "user",
                    str(remote_target),
                    1,
                    1,
                    row["created_at"],
                    row["updated_at"],
                ),
            )

        self._connection.execute("DROP TABLE profiles")
        self._connection.execute("ALTER TABLE profiles_v2 RENAME TO profiles")
        self._connection.execute("PRAGMA user_version = 2")
        self._connection.commit()
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._logger.info("Database schema migration to user_version=2 completed")

    def _migrate_to_v3(self) -> None:
        if self._connection is None:
            raise RuntimeError("Database connection not initialized")

        self._logger.info("Migrating database schema to user_version=3")

        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS automation_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                job_type TEXT NOT NULL,
                schedule_minute INTEGER NOT NULL,
                schedule_hour INTEGER NOT NULL,
                schedule_weekdays TEXT NOT NULL,
                profile_id INTEGER,
                remote_path TEXT,
                source_local_dir TEXT,
                upload_roll_mode TEXT NOT NULL DEFAULT 'latest',
                upload_fixed_roll INTEGER,
                keep_last_n INTEGER NOT NULL DEFAULT 10,
                last_run_at TEXT,
                last_status TEXT,
                last_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS automation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                FOREIGN KEY (job_id) REFERENCES automation_jobs(id) ON DELETE CASCADE
            );
            """
        )
        self._connection.execute("PRAGMA user_version = 3")
        self._connection.commit()
        self._logger.info("Database schema migration to user_version=3 completed")

    @property
    def connection(self) -> sqlite3.Connection:
        return self.connect()
