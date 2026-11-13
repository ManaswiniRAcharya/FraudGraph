import sys
from datetime import datetime, timedelta, timezone

from cassandra_layer import alerts_store

DEMO_ACCOUNT = "ACC_DEMO"


def add():
    now = datetime.now(timezone.utc)
    alerts_store.ensure_schema()
    alerts_store.save_alert({
        "account_id": DEMO_ACCOUNT, "rule_type": "FAN_IN", "risk_points": 35,
        "rules_triggered": ["FAN_IN"], "account_path": [],
        "evidence": {"distinct_senders": 23, "window_hours": 72, "note": "DEMO DATA"},
        "alert_time": now - timedelta(hours=2)})
    alerts_store.save_alert({
        "account_id": DEMO_ACCOUNT, "rule_type": "CIRCULAR", "risk_points": 40,
        "rules_triggered": ["CIRCULAR", "RAPID_CHAIN"],
        "account_path": ["ACC1", "ACC2", "ACC3", "ACC1"],
        "evidence": {"window_hours": 8, "note": "DEMO DATA"},
        "alert_time": now})
    print("Added 2 demo alerts for", DEMO_ACCOUNT)


def clear():
    alerts_store.ensure_schema()
    alerts_store.delete_alerts_for_account(DEMO_ACCOUNT)
    print("Removed demo alerts for", DEMO_ACCOUNT)


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "add":
        add()
    elif action == "clear":
        clear()
    else:
        raise SystemExit("Usage: python -m app.demo_alerts add|clear")
    alerts_store.close()
