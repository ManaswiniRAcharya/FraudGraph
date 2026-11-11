import json
import os
import random
from datetime import date, timedelta

random.seed(42)  # same seed = same data on every machine

NUM_CUSTOMERS = 400
EXTRA_ACCOUNTS = 100
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

FIRST_NAMES = ["Asha", "Ravi", "Meera", "Karthik", "Divya", "Arjun", "Sneha", "Vikram",
               "Priya", "Rohan", "Lakshmi", "Suresh", "Anjali", "Manoj", "Kavya", "Deepak"]
LAST_NAMES = ["Rao", "Shetty", "Nair", "Hegde", "Kamath", "Bhat", "Pai", "Gowda",
              "Reddy", "Iyer", "Kulkarni", "Naik"]
CITIES = ["Mangaluru", "Udupi", "Bengaluru", "Mysuru", "Hubballi", "Belagavi"]


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


def save_json(filename, records):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Wrote {len(records)} records to {path}")


if __name__ == "__main__":
    customers = make_customers()
    accounts = make_accounts(customers)
    save_json("customers.json", customers)
    save_json("accounts.json", accounts)
