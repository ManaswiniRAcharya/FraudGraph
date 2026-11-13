from app.main import app
from cassandra_layer import alerts_store

client = app.test_client()
failures = []


def check(name, condition):
    print(("PASS  " if condition else "FAIL  ") + name)
    if not condition:
        failures.append(name)


def check_customer_pages():
    r = client.get("/")
    check("home page loads", r.status_code == 200 and b"Customers" in r.data)

    r = client.get("/customers")
    check("customer list loads", r.status_code == 200 and b"CUST0001" in r.data)

    r = client.get("/customers?city=Mysuru")
    check("city filter keeps Mysuru customers", b"CUST0003" in r.data)
    check("city filter drops other cities",
          r.status_code == 200 and b"CUST0001" not in r.data)

    r = client.get("/customers/CUST0228")
    check("ring member shows shared device",
          r.status_code == 200 and b"DEV372" in r.data and b"CUST0271" in r.data)

    r = client.get("/customers/CUST0001/kyc.png")
    check("KYC image is a real PNG",
          r.status_code == 200 and r.mimetype == "image/png"
          and r.data[:8] == b"\x89PNG\r\n\x1a\n")
    check("customer without KYC image gives 404",
          client.get("/customers/CUST0006/kyc.png").status_code == 404)
    check("unknown customer gives 404", client.get("/customers/NOPE").status_code == 404)


def check_account_and_transaction_pages():
    r = client.get("/accounts")
    check("account list loads", r.status_code == 200 and b"ACC0001" in r.data)

    r = client.get("/accounts/ACC0414")
    check("ACC0414 shows 23 distinct senders",
          r.status_code == 200 and b'<div class="num">23</div>' in r.data)
    check("unknown account gives 404", client.get("/accounts/NOPE").status_code == 404)

    r = client.get("/transactions")
    check("transaction list loads", r.status_code == 200 and b"TXN" in r.data)

    r = client.get("/transactions?min_amount=90000")
    check("amount filter finds exactly the two 90k+ transactions",
          r.status_code == 200 and b"TXN000137" in r.data and b"TXN000448" in r.data
          and b"TXN000449" not in r.data)

    r = client.get("/transactions?channel=RTGS")
    check("RTGS count matches the MongoDB aggregation (133)",
          r.status_code == 200 and b"133 transactions" in r.data)

    check("bad amount input does not crash",
          client.get("/transactions?min_amount=abc").status_code == 200)


def check_alert_pages():
    """Uses its own throwaway account and always removes what it created."""
    test_account = "ACC_PAGETEST"
    try:
        alerts_store.ensure_schema()
        alerts_store.save_alert({
            "account_id": test_account, "rule_type": "CIRCULAR", "risk_points": 40,
            "rules_triggered": ["CIRCULAR"], "account_path": ["A1", "A2", "A1"],
            "evidence": {"marker": "pagetest-7f3a"}})

        r = client.get("/alerts")
        check("alerts page lists a fresh alert",
              r.status_code == 200 and b"pagetest-7f3a" in r.data)

        r = client.get("/alerts?account=" + test_account)
        check("alerts page filters by account",
              r.status_code == 200 and b"pagetest-7f3a" in r.data and b"CIRCULAR" in r.data)

        r = client.get("/alerts?account=ACC_NO_ALERTS")
        check("account with no alerts shows the empty message",
              r.status_code == 200 and b"No alerts" in r.data)
    finally:
        try:
            alerts_store.delete_alerts_for_account(test_account)
            alerts_store.close()
        except Exception:
            pass


if __name__ == "__main__":
    check_customer_pages()
    check_account_and_transaction_pages()
    check_alert_pages()
    if failures:
        raise SystemExit(f"{len(failures)} check(s) failed")
    print("All page checks passed.")
