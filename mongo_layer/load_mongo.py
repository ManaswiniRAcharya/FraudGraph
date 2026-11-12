import json
import os
from datetime import datetime

from pymongo import ASCENDING, MongoClient

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data_generator", "output")
MONGO_URI = "mongodb://localhost:27018"
DB_NAME = "fraudgraph"


def load_json(filename):
    with open(os.path.join(DATA_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


def main():
    customers = load_json("customers.json")
    accounts = load_json("accounts.json")
    transactions = load_json("transactions.json")

    for c in customers:
        c["created_at"] = datetime.fromisoformat(c["created_at"])
    for a in accounts:
        a["opened_at"] = datetime.fromisoformat(a["opened_at"])
    for t in transactions:
        t["ts"] = datetime.fromisoformat(t["ts"])

    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]

    for name in ("customers", "accounts", "transactions"):
        db.drop_collection(name)

    db.customers.insert_many(customers)
    db.accounts.insert_many(accounts)
    db.transactions.insert_many(transactions)

    db.accounts.create_index([("customer_id", ASCENDING)])
    db.transactions.create_index([("from_acc", ASCENDING)])
    db.transactions.create_index([("to_acc", ASCENDING)])
    db.transactions.create_index([("ts", ASCENDING)])

    print("customers   :", db.customers.count_documents({}))
    print("accounts    :", db.accounts.count_documents({}))
    print("transactions:", db.transactions.count_documents({}))
    client.close()


if __name__ == "__main__":
    main()
