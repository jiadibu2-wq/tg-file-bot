"""本地存储层：所有数据（档案 + 设置）只写入本机 SQLite 文件，不联网、不上传。"""
import os
import json
import sqlite3
import threading
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL,
  gender       INTEGER NOT NULL DEFAULT 1,
  calendar     TEXT NOT NULL DEFAULT 'solar',
  year         INTEGER, month INTEGER, day INTEGER,
  hour         INTEGER, minute INTEGER,
  is_leap      INTEGER DEFAULT 0,
  longitude    REAL,
  use_true_solar INTEGER DEFAULT 0,
  note         TEXT,
  chart_json   TEXT,
  created_at   TEXT
);
CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT
);
"""


def _conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _lock, _conn() as c:
        c.executescript(SCHEMA)


# ---------------- 档案 ----------------

def list_profiles():
    with _conn() as c:
        rows = c.execute(
            "SELECT id,name,gender,calendar,year,month,day,hour,minute,"
            "is_leap,longitude,use_true_solar,note,created_at "
            "FROM profiles ORDER BY id DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_profile(pid):
    with _conn() as c:
        r = c.execute("SELECT * FROM profiles WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None


def save_profile(p):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _lock, _conn() as c:
        cur = c.execute(
            "INSERT INTO profiles(name,gender,calendar,year,month,day,hour,minute,"
            "is_leap,longitude,use_true_solar,note,chart_json,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (p.get("name") or "未命名", int(p.get("gender", 1)), p.get("calendar", "solar"),
             p.get("year"), p.get("month"), p.get("day"), p.get("hour"), p.get("minute"),
             1 if p.get("is_leap") else 0, p.get("longitude"),
             1 if p.get("use_true_solar") else 0, p.get("note"),
             json.dumps(p.get("chart"), ensure_ascii=False), now),
        )
        return cur.lastrowid


def update_profile_chart(pid, chart):
    with _lock, _conn() as c:
        c.execute("UPDATE profiles SET chart_json=? WHERE id=?",
                  (json.dumps(chart, ensure_ascii=False), pid))


def delete_profile(pid):
    with _lock, _conn() as c:
        c.execute("DELETE FROM profiles WHERE id=?", (pid,))


# ---------------- 设置 ----------------

def set_setting(key, value):
    with _lock, _conn() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                  "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def get_setting(key, default=None):
    with _conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default


DEFAULT_AI = {
    "enabled": False,
    "base_url": "",
    "api_key": "",
    "model": "",
    "temperature": 0.7,
}


def get_ai_config(mask=False):
    raw = get_setting("ai_config")
    cfg = dict(DEFAULT_AI)
    if raw:
        try:
            cfg.update(json.loads(raw))
        except Exception:
            pass
    if mask:
        key = cfg.get("api_key") or ""
        cfg["api_key"] = ("*" * max(0, len(key) - 4) + key[-4:]) if key else ""
        cfg["has_key"] = bool(key)
    return cfg


def set_ai_config(cfg):
    cur = get_ai_config(mask=False)
    # 前端回传掩码串时，保留原 key
    new_key = cfg.get("api_key")
    if new_key is None or set(new_key) <= {"*"}:
        cfg["api_key"] = cur.get("api_key", "")
    merged = dict(DEFAULT_AI)
    merged.update(cur)
    merged.update({k: v for k, v in cfg.items() if k in DEFAULT_AI})
    set_setting("ai_config", json.dumps(merged, ensure_ascii=False))
    return get_ai_config(mask=True)