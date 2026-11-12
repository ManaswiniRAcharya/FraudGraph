import os
import uuid
from datetime import datetime, timezone

from cassandra.cluster import Cluster

HOSTS = ["localhost"]
PORT = 9042
KEYSPACE = "fraudgraph"
TABLE = "alerts_by_account"

_cluster = None
_session = None
_insert_stmt = None


def get_session():
    global _cluster, _session
    if _session is None:
        _cluster = Cluster(HOSTS, port=PORT)
        _session = _cluster.connect()
    return _session


def close():
    global _cluster, _session, _insert_stmt
    if _cluster is not None:
        _cluster.shutdown()
    _cluster, _session, _insert_stmt = None, None, None


def ensure_schema():
    """Create keyspace/table from schema.cql and add reviewed_by if missing."""
    session = get_session()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.cql")
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if not ln.strip().startswith("--")]
    for stmt in "\n".join(lines).split(";"):
        if stmt.strip():
            session.execute(stmt)
    existing = {row.column_name for row in session.execute(
        "SELECT column_name FROM system_schema.columns "
        "WHERE keyspace_name = %s AND table_name = %s", (KEYSPACE, TABLE))}
    if "reviewed_by" not in existing:
        session.execute(f"ALTER TABLE {KEYSPACE}.{TABLE} ADD reviewed_by text")


def save_alert(alert):
    """Save one alert. Required keys: account_id, rule_type, risk_points.
    Optional: rules_triggered (list/set), account_path (list), evidence (dict),
    alert_time (datetime), alert_id (uuid)."""
    global _insert_stmt
    session = get_session()
    if _insert_stmt is None:
        _insert_stmt = session.prepare(
            f"INSERT INTO {KEYSPACE}.{TABLE} "
            "(account_id, alert_time, alert_id, rule_type, risk_points, "
            "rules_triggered, account_path, evidence) VALUES (?, ?, ?, ?, ?, ?, ?, ?)")
    alert_id = alert.get("alert_id") or uuid.uuid4()
    session.execute(_insert_stmt, (
        alert["account_id"],
        alert.get("alert_time") or datetime.now(timezone.utc),
        alert_id,
        alert["rule_type"],
        int(alert["risk_points"]),
        set(alert.get("rules_triggered", [])),
        list(alert.get("account_path", [])),
        {str(k): str(v) for k, v in alert.get("evidence", {}).items()},
    ))
    return alert_id


def _row_to_dict(row):
    return {
        "account_id": row.account_id,
        "alert_time": row.alert_time,
        "alert_id": row.alert_id,
        "rule_type": row.rule_type,
        "risk_points": row.risk_points,
        "rules_triggered": sorted(row.rules_triggered or []),
        "account_path": list(row.account_path or []),
        "evidence": dict(row.evidence or {}),
    }


COLUMNS = ("account_id, alert_time, alert_id, rule_type, risk_points, "
           "rules_triggered, account_path, evidence")


def get_alerts_for_account(account_id, limit=50):
    """Alerts for one account, newest first (the query this table is built for)."""
    rows = get_session().execute(
        f"SELECT {COLUMNS} FROM {KEYSPACE}.{TABLE} WHERE account_id = %s LIMIT %s",
        (account_id, limit))
    return [_row_to_dict(r) for r in rows]


def get_recent_alerts(limit=100):
    """Alerts across all accounts, newest first. Scans every partition, so it is
    fine for a demo-sized table but not a pattern for large data."""
    rows = get_session().execute(
        f"SELECT {COLUMNS} FROM {KEYSPACE}.{TABLE} LIMIT %s", (limit,))
    return sorted((_row_to_dict(r) for r in rows),
                  key=lambda a: a["alert_time"], reverse=True)


def delete_alerts_for_account(account_id):
    get_session().execute(
        f"DELETE FROM {KEYSPACE}.{TABLE} WHERE account_id = %s", (account_id,))


def clear_alerts():
    """Remove ALL alerts (use before re-running detection from scratch)."""
    get_session().execute(f"TRUNCATE {KEYSPACE}.{TABLE}")


if __name__ == "__main__":
    ensure_schema()
    test_id = "ACC_SELFTEST"
    delete_alerts_for_account(test_id)
    t1 = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 11, 12, 14, 30, tzinfo=timezone.utc)
    save_alert({"account_id": test_id, "rule_type": "SHARED_DEVICE", "risk_points": 30,
                "rules_triggered": ["SHARED_DEVICE"], "account_path": ["A1"],
                "evidence": {"device": "DEV1"}, "alert_time": t1})
    save_alert({"account_id": test_id, "rule_type": "CIRCULAR", "risk_points": 40,
                "rules_triggered": ["CIRCULAR"], "account_path": ["A1", "A2", "A3", "A1"],
                "evidence": {"window_hours": 8}, "alert_time": t2})
    alerts = get_alerts_for_account(test_id)
    for a in alerts:
        print(a)
    assert len(alerts) == 2
    assert alerts[0]["rule_type"] == "CIRCULAR", "newest alert should come first"
    assert alerts[0]["account_path"] == ["A1", "A2", "A3", "A1"]
    assert alerts[0]["evidence"] == {"window_hours": "8"}
    delete_alerts_for_account(test_id)
    assert get_alerts_for_account(test_id) == []
    print("alerts_store self-test passed")
    close()
