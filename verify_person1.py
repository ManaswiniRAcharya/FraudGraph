import json
import os
import subprocess
import sys

from neo4j import GraphDatabase
from pymongo.errors import DuplicateKeyError

from app.db import get_db
from cassandra_layer import alerts_store
from graph_layer import load_graph

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "data_generator", "output")

results = []


def read_json(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def check(name, condition, detail=""):
    results.append(bool(condition))
    note = f"   [{detail}]" if detail and not condition else ""
    print(("PASS  " if condition else "FAIL  ") + name + note)


def section(title, func):
    print(f"\n== {title} ==")
    try:
        func()
    except Exception as exc:
        check(f"{title}: finished without an error", False, f"{type(exc).__name__}: {exc}")


def files():
    for name in ("customers.json", "accounts.json", "transactions.json", "ground_truth.json"):
        check(f"generator output {name} exists", os.path.exists(os.path.join(OUT, name)))
    for rel in ("docker-compose.yml", "cassandra_layer/schema.cql",
                "cassandra_layer/alerts_store.py", "mongo_layer/setup_mongo.py",
                "graph_layer/load_graph.py", "app/main.py"):
        check(f"{rel} exists", os.path.exists(os.path.join(ROOT, rel)))

    with open(os.path.join(ROOT, "requirements.txt"), "rb") as f:
        raw = f.read()
    low = raw.lower()
    check("requirements.txt is plain text, not UTF-16",
          b"\x00" not in raw and not raw.startswith(b"\xff\xfe"))
    for pkg in (b"flask==", b"pymongo==", b"neo4j==", b"cassandra-driver=="):
        check(f"requirements.txt pins {pkg[:-2].decode()}", pkg in low)

    proc = subprocess.run(["git", "show", "HEAD:requirements.txt"], cwd=ROOT,
                          capture_output=True)
    check("committed requirements.txt is readable text with Flask pinned",
          proc.returncode == 0 and b"\x00" not in proc.stdout
          and b"flask==" in proc.stdout.lower())


def mongo():
    db = get_db()
    gt = read_json("ground_truth.json")

    n_customers = db.customers.count_documents({})
    n_accounts = db.accounts.count_documents({})
    n_txns = db.transactions.count_documents({})
    expected_txns = len(read_json("transactions.json"))
    check("MongoDB holds 400 customers and 500 accounts",
          (n_customers, n_accounts) == (400, 500), f"{n_customers}/{n_accounts}")
    check("transaction count matches transactions.json", n_txns == expected_txns,
          f"{n_txns} vs {expected_txns}")

    indexes = {i["name"] for i in db.transactions.list_indexes()}
    check("transaction indexes exist (from_acc, to_acc, ts)",
          {"from_acc_1", "to_acc_1", "ts_1"} <= indexes, str(indexes))
    check("5 customers have a binary KYC document",
          db.customers.count_documents({"kyc_doc": {"$type": "binData"}}) == 5)

    try:
        db.customers.insert_one({"_id": "CUST0001", "name": "duplicate"})
    except DuplicateKeyError:
        check("duplicate _id is rejected", True)
    else:
        check("duplicate _id is rejected", False)
        db.customers.delete_one({"_id": "CUST0001", "name": "duplicate"})

    acc_ids = [a["_id"] for a in db.accounts.find({}, {"_id": 1})]
    cust_ids = [c["_id"] for c in db.customers.find({}, {"_id": 1})]
    check("every account belongs to an existing customer",
          db.accounts.count_documents({"customer_id": {"$nin": cust_ids}}) == 0)
    check("every transaction connects two existing accounts",
          db.transactions.count_documents(
              {"$or": [{"from_acc": {"$nin": acc_ids}}, {"to_acc": {"$nin": acc_ids}}]}) == 0)
    check("no account sends money to itself",
          db.transactions.count_documents({"$expr": {"$eq": ["$from_acc", "$to_acc"]}}) == 0)

    fields = {"device": "devices", "ip": "ips", "phone": "phones"}

    def holders(shared):
        return [sorted(d["_id"] for d in db.customers.find({fields[k]: v}, {"_id": 1}))
                for k, v in shared.items()]

    check("planted shared-identifier rings are present in MongoDB",
          all(h == sorted(r["customers"])
              for r in gt["shared_identifier_rings"] for h in holders(r["shared"])))
    check("decoy households are present in MongoDB",
          all(h == sorted(r["customers"])
              for r in gt["decoy_households"] for h in holders(r["shared"])))

    check("every planted fan-in target received from all its planted senders",
          all(set(f["senders"]) <= set(db.transactions.distinct("from_acc", {"to_acc": f["target"]}))
              for f in gt["fan_in"]))

    def edge(a, b):
        return db.transactions.count_documents({"from_acc": a, "to_acc": b}) > 0

    check("every planted cycle has all its transfers",
          all(edge(c["accounts"][i], c["accounts"][(i + 1) % len(c["accounts"])])
              for c in gt["circular_flows"] for i in range(len(c["accounts"]))))
    check("every planted rapid chain has all its transfers",
          all(edge(c["accounts"][i], c["accounts"][i + 1])
              for c in gt["rapid_chains"] for i in range(len(c["accounts"]) - 1)))
    check("ground truth lists 20 suspicious accounts and 2 decoy households",
          len(gt["suspicious_accounts"]) == 20 and len(gt["decoy_households"]) == 2)


def neo4j_graph():
    gt = read_json("ground_truth.json")
    device = gt["shared_identifier_rings"][0]["shared"]["device"]
    n_txns = get_db().transactions.count_documents({})
    driver = GraphDatabase.driver(load_graph.NEO4J_URI, auth=load_graph.NEO4J_AUTH)
    try:
        driver.verify_connectivity()
        with driver.session() as s:
            def one(query, **params):
                return s.run(query, **params).single()[0]

            check("Neo4j holds 400 Customer and 500 Account nodes",
                  one("MATCH (n:Customer) RETURN count(n)") == 400
                  and one("MATCH (n:Account) RETURN count(n)") == 500)
            check("Neo4j SENT relationships equal the MongoDB transaction count",
                  one("MATCH ()-[r:SENT]->() RETURN count(r)") == n_txns)
            check("5 uniqueness constraints exist", len(s.run("SHOW CONSTRAINTS").data()) == 5)
            check("the planted shared device is used by 4 customers in the graph",
                  one("MATCH (:Device {id: $d})<-[:USES_DEVICE]-(c:Customer) RETURN count(c)",
                      d=device) == 4)
    finally:
        driver.close()


def cassandra():
    alerts_store.ensure_schema()
    session = alerts_store.get_session()
    columns = {r.column_name for r in session.execute(
        "SELECT column_name FROM system_schema.columns "
        "WHERE keyspace_name = 'fraudgraph' AND table_name = 'alerts_by_account'")}
    expected = {"account_id", "alert_time", "alert_id", "rule_type", "risk_points",
                "rules_triggered", "account_path", "evidence", "reviewed_by"}
    check("alerts table has the 9 expected columns", columns == expected, str(columns ^ expected))

    account = "ACC_VERIFY"
    alerts_store.delete_alerts_for_account(account)
    alerts_store.save_alert({
        "account_id": account, "rule_type": "CIRCULAR", "risk_points": 40,
        "rules_triggered": ["CIRCULAR"], "account_path": ["A1", "A2", "A1"],
        "evidence": {"window_hours": 8}})
    got = alerts_store.get_alerts_for_account(account)
    check("alert round trip keeps the set, list and map",
          len(got) == 1 and got[0]["rules_triggered"] == ["CIRCULAR"]
          and got[0]["account_path"] == ["A1", "A2", "A1"]
          and got[0]["evidence"] == {"window_hours": "8"})
    alerts_store.delete_alerts_for_account(account)
    check("the verification alert was removed",
          alerts_store.get_alerts_for_account(account) == [])

    leftovers = {r.account_id for r in session.execute(
        "SELECT DISTINCT account_id FROM fraudgraph.alerts_by_account")
        if r.account_id.startswith("ACC_")}
    check("no leftover demo or test alerts", not leftovers, str(leftovers))
    alerts_store.close()


def web():
    proc = subprocess.run([sys.executable, "-m", "app.check_pages"], cwd=ROOT,
                          capture_output=True, text=True)
    passed = sum(1 for line in proc.stdout.splitlines() if line.startswith("PASS"))
    check("all 18 Flask page checks pass", proc.returncode == 0 and passed == 18,
          f"{passed} passed, exit code {proc.returncode}")


if __name__ == "__main__":
    section("Project files and dependencies", files)
    section("MongoDB (source of truth)", mongo)
    section("Neo4j (graph copy)", neo4j_graph)
    section("Cassandra (alert log)", cassandra)
    section("Flask pages", web)

    passed = sum(results)
    print(f"\n{passed} of {len(results)} checks passed.")
    if passed != len(results):
        raise SystemExit("PERSON 1 VERIFICATION FAILED. Fix the FAIL lines above.")
    print("PERSON 1 VERIFICATION PASSED.")
