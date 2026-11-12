import json
import os
import random
from datetime import date, datetime, timedelta

random.seed(42)  # same seed = same data on every machine

NUM_CUSTOMERS = 400
EXTRA_ACCOUNTS = 100
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

FIRST_NAMES = ["Asha", "Ravi", "Meera", "Karthik", "Divya", "Arjun", "Sneha", "Vikram",
               "Priya", "Rohan", "Lakshmi", "Suresh", "Anjali", "Manoj", "Kavya", "Deepak"]
LAST_NAMES = ["Rao", "Shetty", "Nair", "Hegde", "Kamath", "Bhat", "Pai", "Gowda",
              "Reddy", "Iyer", "Kulkarni", "Naik"]
CITIES = ["Mangaluru", "Udupi", "Bengaluru", "Mysuru", "Hubballi", "Belagavi"]

CHANNELS = ["UPI", "NEFT", "IMPS", "RTGS"]
CHANNEL_WEIGHTS = [60, 20, 15, 5]
NUM_NORMAL_TXNS = 2800
TXN_START = datetime(2026, 2, 1)
TXN_END = datetime(2026, 10, 31, 23, 59, 59)


def random_date(start, end):
    return start + timedelta(days=random.randint(0, (end - start).days))


def unique_phone(used):
    while True:
        phone = str(random.randint(6000000000, 9999999999))
        if phone not in used:
            used.add(phone)
            return phone


def unique_ip(used):
    while True:
        ip = f"103.{random.randint(1, 254)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        if ip not in used:
            used.add(ip)
            return ip


def make_customers():
    customers = []
    used_phones, used_ips = set(), set()
    device_no = 0
    for i in range(1, NUM_CUSTOMERS + 1):
        devices = []
        for _ in range(2 if random.random() < 0.3 else 1):
            device_no += 1
            devices.append(f"DEV{device_no:03d}")
        customers.append({
            "_id": f"CUST{i:04d}",
            "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "city": random.choice(CITIES),
            "kyc_status": random.choices(["verified", "pending", "rejected"],
                                         weights=[85, 12, 3])[0],
            "phones": [unique_phone(used_phones)],
            "devices": devices,
            "ips": [unique_ip(used_ips)],
            "kyc_doc": None,
            "created_at": random_date(date(2024, 1, 1), date(2025, 12, 31)).isoformat(),
        })
    return customers


def make_accounts(customers):
    accounts = []
    extra_owners = random.sample(customers, EXTRA_ACCOUNTS)
    for n, cust in enumerate(customers + extra_owners, start=1):
        created = date.fromisoformat(cust["created_at"])
        accounts.append({
            "_id": f"ACC{n:04d}",
            "customer_id": cust["_id"],
            "type": random.choices(["savings", "current", "salary"],
                                   weights=[70, 20, 10])[0],
            "balance": round(random.uniform(1000, 200000), 2),
            "opened_at": (created + timedelta(days=random.randint(0, 30))).isoformat(),
        })
    return accounts

def random_timestamp(start, end):
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, seconds))


def make_normal_transactions(accounts):
    acc_ids = [a["_id"] for a in accounts]
    txns = []
    for _ in range(NUM_NORMAL_TXNS):
        sender, receiver = random.sample(acc_ids, 2)
        amount = random.lognormvariate(8, 1.0)
        amount = round(min(max(amount, 100), 100000), 2)
        txns.append({
            "from_acc": sender,
            "to_acc": receiver,
            "amount": amount,
            "ts": random_timestamp(TXN_START, TXN_END).isoformat(timespec="seconds"),
            "channel": random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0],
        })
    return txns


def finalize_transactions(txns):
    txns.sort(key=lambda t: t["ts"])
    return [{"_id": f"TXN{n:06d}", **t} for n, t in enumerate(txns, start=1)]

def save_json(filename, records):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Wrote {len(records)} records to {path}")

def txn(sender, receiver, amount, ts, channel=None):
    return {
        "from_acc": sender,
        "to_acc": receiver,
        "amount": round(amount, 2),
        "ts": ts.isoformat(timespec="seconds"),
        "channel": channel or random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0],
    }


def first_account_of(customer_id, accounts):
    return next(a["_id"] for a in accounts if a["customer_id"] == customer_id)


def free_accounts(accounts, used_accounts):
    return [a["_id"] for a in accounts if a["_id"] not in used_accounts]


def plant_shared_rings(customers, accounts, used_customers, used_accounts, txns):
    rings = []
    for kind, size in [("device", 4), ("ip_and_phone", 3)]:
        pool = [c for c in customers if c["_id"] not in used_customers]
        members = random.sample(pool, size)
        lead = members[0]
        if kind == "device":
            shared = {"device": lead["devices"][0]}
            for m in members[1:]:
                m["devices"].append(shared["device"])
        else:
            shared = {"ip": lead["ips"][0], "phone": lead["phones"][0]}
            for m in members[1:]:
                m["ips"].append(shared["ip"])
                m["phones"].append(shared["phone"])
        used_customers.update(m["_id"] for m in members)
        ring_accounts = [first_account_of(m["_id"], accounts) for m in members]
        used_accounts.update(ring_accounts)
        for acc in ring_accounts[1:]:
            ts = random_timestamp(TXN_START, TXN_END)
            txns.append(txn(acc, ring_accounts[0], random.uniform(3000, 15000), ts))
        rings.append({
            "shared": shared,
            "customers": [m["_id"] for m in members],
            "accounts": ring_accounts,
        })
    return rings


def plant_cycles(accounts, used_accounts, txns):
    cycles = []
    for length in (3, 4):
        members = random.sample(free_accounts(accounts, used_accounts), length)
        used_accounts.update(members)
        amount = random.uniform(40000, 90000)
        ts = random_timestamp(TXN_START, TXN_END - timedelta(days=3))
        for i in range(length):
            txns.append(txn(members[i], members[(i + 1) % length], amount, ts))
            amount *= 0.98
            ts += timedelta(hours=random.randint(1, 8))
        cycles.append({"length": length, "accounts": members})
    return cycles


def plant_fan_in(accounts, used_accounts, txns):
    result = []
    for _ in range(2):
        target = random.choice(free_accounts(accounts, used_accounts))
        used_accounts.add(target)
        senders = random.sample(free_accounts(accounts, used_accounts),
                                random.randint(15, 20))
        start = random_timestamp(TXN_START, TXN_END - timedelta(days=4))
        for s in senders:
            ts = start + timedelta(seconds=random.randint(0, 72 * 3600))
            txns.append(txn(s, target, random.uniform(2000, 9000), ts))
        result.append({"target": target, "senders": senders})
    return result


def plant_rapid_chain(accounts, used_accounts, txns):
    members = random.sample(free_accounts(accounts, used_accounts), 4)
    used_accounts.update(members)
    amount = random.uniform(60000, 95000)
    ts = random_timestamp(TXN_START, TXN_END - timedelta(days=2))
    for i in range(3):
        txns.append(txn(members[i], members[i + 1], amount, ts))
        amount *= 0.97
        ts += timedelta(hours=random.randint(1, 6))
    return [{"accounts": members}]

def plant_decoys(customers, accounts, used_accounts, used_customers):
    suspicious_owners = {a["customer_id"] for a in accounts
                         if a["_id"] in used_accounts}
    pool = [c for c in customers
            if c["_id"] not in used_customers and c["_id"] not in suspicious_owners]
    households = []
    for share_device in (False, True):
        a, b = random.sample(pool, 2)
        pool = [c for c in pool if c["_id"] not in (a["_id"], b["_id"])]
        b["ips"].append(a["ips"][0])
        shared = {"ip": a["ips"][0]}
        if share_device:
            b["devices"].append(a["devices"][0])
            shared["device"] = a["devices"][0]
        households.append({"shared": shared, "customers": [a["_id"], b["_id"]]})
    return households

def plant_fraud(customers, accounts, txns):
    used_customers, used_accounts = set(), set()
    ground_truth = {
        "shared_identifier_rings": plant_shared_rings(
            customers, accounts, used_customers, used_accounts, txns),
        "circular_flows": plant_cycles(accounts, used_accounts, txns),
        "fan_in": plant_fan_in(accounts, used_accounts, txns),
        "rapid_chains": plant_rapid_chain(accounts, used_accounts, txns),
    }
    ground_truth["decoy_households"] = plant_decoys(
        customers, accounts, used_accounts, used_customers)
    ground_truth["suspicious_accounts"] = sorted(used_accounts)
    return ground_truth


def save_ground_truth(ground_truth):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "ground_truth.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Wrote ground truth ({len(ground_truth['suspicious_accounts'])} "
          f"suspicious accounts) to {path}")

if __name__ == "__main__":
    customers = make_customers()
    accounts = make_accounts(customers)
    transactions = make_normal_transactions(accounts)
    ground_truth = plant_fraud(customers, accounts, transactions)
    transactions = finalize_transactions(transactions)
    save_json("customers.json", customers)
    save_json("accounts.json", accounts)
    save_json("transactions.json", transactions)
    save_ground_truth(ground_truth)