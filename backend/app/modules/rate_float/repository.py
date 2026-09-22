"""rate_float repository: persist per-loan rate float events and validate them."""
from datetime import datetime, timezone

DDL = """
CREATE TABLE IF NOT EXISTS rate_float_events(
    id INTEGER PRIMARY KEY,
    loan_id INTEGER NOT NULL,
    effective_period INTEGER NOT NULL,
    new_annual_rate REAL NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    note TEXT DEFAULT '',
    created_at TEXT,
    updated_at TEXT
);
"""


class RateFloatError(ValueError):
    """Validation or conflict failure on a rate float event."""


def ensure_table(conn):
    conn.executescript(DDL)
    conn.commit()


def _now():
    return datetime.now(timezone.utc).isoformat()


def list_events(conn, loan_id, enabled_only=False):
    sql = "SELECT * FROM rate_float_events WHERE loan_id=?"
    args = [loan_id]
    if enabled_only:
        sql += " AND enabled=1"
    sql += " ORDER BY effective_period, id"
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def get_event(conn, event_id):
    row = conn.execute("SELECT * FROM rate_float_events WHERE id=?", (event_id,)).fetchone()
    return dict(row) if row else None


def _validate(loan_months, effective_period, new_annual_rate):
    p = int(effective_period)
    if p <= 1 or p > int(loan_months):
        raise RateFloatError(f"生效期须大于 1 且小于等于贷款总期数 {loan_months}，收到 {p}")
    r = float(new_annual_rate)
    if r < 0:
        raise RateFloatError(f"新年利率不得为负，收到 {r}")
    return p, r


def _check_conflict(conn, loan_id, effective_period, exclude_id=None):
    sql = "SELECT id FROM rate_float_events WHERE loan_id=? AND effective_period=? AND enabled=1"
    args = [loan_id, effective_period]
    if exclude_id is not None:
        sql += " AND id<>?"
        args.append(exclude_id)
    clash = conn.execute(sql, args).fetchone()
    if clash:
        other = clash["id"]
        if exclude_id is None:
            raise RateFloatError(
                f"生效期 {effective_period} 冲突：已启用事件 #{other} 与本次新建事件生效期相同")
        raise RateFloatError(
            f"生效期 {effective_period} 冲突：事件 #{other} 与事件 #{exclude_id} 同为启用且生效期相同")


def create_event(conn, loan_id, loan_months, effective_period, new_annual_rate, note=""):
    p, r = _validate(loan_months, effective_period, new_annual_rate)
    _check_conflict(conn, loan_id, p)
    now = _now()
    cur = conn.execute(
        "INSERT INTO rate_float_events(loan_id,effective_period,new_annual_rate,enabled,note,created_at,updated_at)"
        " VALUES (?,?,?,1,?,?,?)",
        (loan_id, p, r, note or "", now, now))
    conn.commit()
    return get_event(conn, int(cur.lastrowid))


def update_event(conn, event_id, loan_months, effective_period=None, new_annual_rate=None, note=None):
    ev = get_event(conn, event_id)
    if not ev:
        raise RateFloatError(f"事件 #{event_id} 不存在")
    p = effective_period if effective_period is not None else ev["effective_period"]
    r = new_annual_rate if new_annual_rate is not None else ev["new_annual_rate"]
    p, r = _validate(loan_months, p, r)
    if ev["enabled"]:
        _check_conflict(conn, ev["loan_id"], p, exclude_id=event_id)
    conn.execute(
        "UPDATE rate_float_events SET effective_period=?, new_annual_rate=?, note=?, updated_at=? WHERE id=?",
        (p, r, ev["note"] if note is None else note, _now(), event_id))
    conn.commit()
    return get_event(conn, event_id)


def disable_event(conn, event_id):
    ev = get_event(conn, event_id)
    if not ev:
        raise RateFloatError(f"事件 #{event_id} 不存在")
    conn.execute("UPDATE rate_float_events SET enabled=0, updated_at=? WHERE id=?", (_now(), event_id))
    conn.commit()
    return get_event(conn, event_id)
