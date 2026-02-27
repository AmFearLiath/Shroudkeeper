BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS profiles (
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
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    direction TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    cron_expression TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    message TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

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

COMMIT;
