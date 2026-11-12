from neo4j import GraphDatabase
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27018"
MONGO_DB = "fraudgraph"
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "fraudgraph123")
BATCH_SIZE = 500

CONSTRAINTS = [
    "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (n:Customer) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (n:Account) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (n:Device) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT phone_id IF NOT EXISTS FOR (n:Phone) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ip_id IF NOT EXISTS FOR (n:IP) REQUIRE n.id IS UNIQUE",
]

Q_CUSTOMERS = """
UNWIND $rows AS r
CREATE (:Customer {id: r.id, name: r.name, city: r.city,
                   kyc_status: r.kyc_status, created_at: r.created_at})
"""

Q_ACCOUNTS = """
UNWIND $rows AS r
MATCH (c:Customer {id: r.customer_id})
CREATE (c)-[:OWNS]->(:Account {id: r.id, type: r.type, balance: r.balance,
                               opened_at: r.opened_at})
"""

Q_SENT = """
UNWIND $rows AS r
MATCH (a:Account {id: r.from_acc}), (b:Account {id: r.to_acc})
CREATE (a)-[:SENT {txn_id: r.id, amount: r.amount, ts: r.ts, channel: r.channel}]->(b)
"""


def q_identifier(label, rel):
    return f"""
UNWIND $rows AS r
MATCH (c:Customer {{id: r.cust}})
MERGE (n:{label} {{id: r.value}})
MERGE (c)-[:{rel}]->(n)
"""


def read_mongo():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[MONGO_DB]
    customers = list(db.customers.find({}, {"kyc_doc": 0}))
    accounts = list(db.accounts.find({}))
    transactions = list(db.transactions.find({}).sort("ts", 1))
    client.close()
    return customers, accounts, transactions


def identifier_rows(customers, field):
    rows = []
    for c in customers:
        for value in dict.fromkeys(c.get(field, [])):
            rows.append({"cust": c["_id"], "value": value})
    return rows


def _write_batch(tx, query, rows):
    tx.run(query, rows=rows).consume()


def run_batches(driver, query, rows):
    with driver.session() as session:
        for i in range(0, len(rows), BATCH_SIZE):
            session.execute_write(_write_batch, query, rows[i:i + BATCH_SIZE])


def main():
    customers, accounts, transactions = read_mongo()
    print(f"Read from MongoDB: {len(customers)} customers, "
          f"{len(accounts)} accounts, {len(transactions)} transactions")

    customer_rows = [{"id": c["_id"], "name": c["name"], "city": c["city"],
                      "kyc_status": c["kyc_status"], "created_at": c["created_at"]}
                     for c in customers]
    account_rows = [{"id": a["_id"], "customer_id": a["customer_id"], "type": a["type"],
                     "balance": a["balance"], "opened_at": a["opened_at"]}
                    for a in accounts]
    txn_rows = [{"id": t["_id"], "from_acc": t["from_acc"], "to_acc": t["to_acc"],
                 "amount": t["amount"], "ts": t["ts"], "channel": t["channel"]}
                for t in transactions]
    dev_rows = identifier_rows(customers, "devices")
    phone_rows = identifier_rows(customers, "phones")
    ip_rows = identifier_rows(customers, "ips")

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    driver.verify_connectivity()

    print("Wiping the existing graph and creating constraints...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n").consume()
        for stmt in CONSTRAINTS:
            session.run(stmt).consume()

    print("Loading customers, accounts, identifiers, transactions...")
    run_batches(driver, Q_CUSTOMERS, customer_rows)
    run_batches(driver, Q_ACCOUNTS, account_rows)
    run_batches(driver, q_identifier("Device", "USES_DEVICE"), dev_rows)
    run_batches(driver, q_identifier("Phone", "HAS_PHONE"), phone_rows)
    run_batches(driver, q_identifier("IP", "LOGGED_FROM"), ip_rows)
    run_batches(driver, Q_SENT, txn_rows)

    checks = [
        ("Customer nodes", len(customers), "MATCH (n:Customer) RETURN count(n)"),
        ("Account nodes", len(accounts), "MATCH (n:Account) RETURN count(n)"),
        ("OWNS relationships", len(accounts), "MATCH ()-[r:OWNS]->() RETURN count(r)"),
        ("Device nodes", len({r["value"] for r in dev_rows}), "MATCH (n:Device) RETURN count(n)"),
        ("USES_DEVICE rels", len(dev_rows), "MATCH ()-[r:USES_DEVICE]->() RETURN count(r)"),
        ("Phone nodes", len({r["value"] for r in phone_rows}), "MATCH (n:Phone) RETURN count(n)"),
        ("HAS_PHONE rels", len(phone_rows), "MATCH ()-[r:HAS_PHONE]->() RETURN count(r)"),
        ("IP nodes", len({r["value"] for r in ip_rows}), "MATCH (n:IP) RETURN count(n)"),
        ("LOGGED_FROM rels", len(ip_rows), "MATCH ()-[r:LOGGED_FROM]->() RETURN count(r)"),
        ("SENT relationships", len(transactions), "MATCH ()-[r:SENT]->() RETURN count(r)"),
    ]

    print("\nVerification (expected from MongoDB vs found in Neo4j):")
    ok = True
    with driver.session() as session:
        for label, expected, query in checks:
            found = session.run(query).single()[0]
            status = "OK" if found == expected else "MISMATCH"
            ok = ok and found == expected
            print(f"  {label:<20} expected {expected:<6} found {found:<6} {status}")
        exp_sum = round(sum(t["amount"] for t in transactions), 2)
        got_sum = round(session.run(
            "MATCH ()-[r:SENT]->() RETURN sum(r.amount)").single()[0], 2)
        sum_ok = abs(exp_sum - got_sum) < 0.01
        ok = ok and sum_ok
        print(f"  {'Total SENT amount':<20} expected {exp_sum:<10} found {got_sum:<10} "
              f"{'OK' if sum_ok else 'MISMATCH'}")
    driver.close()

    if not ok:
        raise SystemExit("Graph does not match MongoDB. Do not continue until this is fixed.")
    print("\nGraph load verified.")


if __name__ == "__main__":
    main()
