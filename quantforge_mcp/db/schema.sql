PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS ohlcv (
    symbol      TEXT    NOT NULL,
    date        TEXT    NOT NULL,
    interval    TEXT    NOT NULL DEFAULT '1d',
    open        REAL    NOT NULL,
    high        REAL    NOT NULL,
    low         REAL    NOT NULL,
    close       REAL    NOT NULL,
    volume      REAL    NOT NULL,
    source      TEXT    NOT NULL DEFAULT 'yfinance',
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (symbol, date, interval)
);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_date ON ohlcv (symbol, date);

CREATE TABLE IF NOT EXISTS data_fetch_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    start_date  TEXT    NOT NULL,
    end_date    TEXT    NOT NULL,
    interval    TEXT    NOT NULL DEFAULT '1d',
    rows_added  INTEGER NOT NULL DEFAULT 0,
    source      TEXT    NOT NULL,
    fetched_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT    PRIMARY KEY,
    status          TEXT    NOT NULL DEFAULT 'pending',
    job_type        TEXT    NOT NULL,
    config_json     TEXT    NOT NULL,
    strategy_code   TEXT,
    error_message   TEXT,
    summary_json    TEXT,
    created_at      TEXT    NOT NULL,
    finished_at     TEXT
);

CREATE TABLE IF NOT EXISTS artifacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT    NOT NULL REFERENCES jobs(job_id),
    kind        TEXT    NOT NULL,
    path        TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
