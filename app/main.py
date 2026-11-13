import math

from flask import Flask, Response, abort, render_template, request

from app.db import get_db
from cassandra_layer import alerts_store

PAGE_SIZE = 25
KYC_STATES = ["verified", "pending", "rejected"]

app = Flask(__name__)


@app.route("/")
def index():
    db = get_db()
    stats = {
        "customers": db.customers.count_documents({}),
        "accounts": db.accounts.count_documents({}),
        "transactions": db.transactions.count_documents({}),
    }
    return render_template("index.html", stats=stats)


@app.route("/customers")
def customers():
    db = get_db()
    city = request.args.get("city", "").strip()
    kyc = request.args.get("kyc", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)

    query = {}
    if city:
        query["city"] = city
    if kyc:
        query["kyc_status"] = kyc

    total = db.customers.count_documents(query)
    pages = max(1, math.ceil(total / PAGE_SIZE))
    rows = list(
        db.customers.find(query, {"name": 1, "city": 1, "kyc_status": 1, "devices": 1})
        .sort("_id", 1)
        .skip((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )
    has_kyc = {d["_id"] for d in
               db.customers.find({"kyc_doc": {"$type": "binData"}}, {"_id": 1})}

    return render_template(
        "customers.html", rows=rows, has_kyc=has_kyc, total=total, page=page,
        pages=pages, city=city, kyc=kyc, cities=sorted(db.customers.distinct("city")),
        kyc_states=KYC_STATES)


@app.route("/customers/<cust_id>")
def customer_detail(cust_id):
    db = get_db()
    customer = db.customers.find_one({"_id": cust_id}, {"kyc_doc": 0})
    if customer is None:
        abort(404)
    accounts = list(db.accounts.find({"customer_id": cust_id}).sort("_id", 1))
    has_kyc = db.customers.count_documents(
        {"_id": cust_id, "kyc_doc": {"$type": "binData"}}) > 0

    shared = []
    for field, label in (("devices", "Device"), ("phones", "Phone"), ("ips", "IP address")):
        for value in customer.get(field, []):
            others = [o["_id"] for o in
                      db.customers.find({field: value, "_id": {"$ne": cust_id}}, {"_id": 1})
                      .sort("_id", 1)]
            if others:
                shared.append({"type": label, "value": value, "others": others})

    return render_template("customer_detail.html", c=customer, accounts=accounts,
                           has_kyc=has_kyc, shared=shared)


@app.route("/customers/<cust_id>/kyc.png")
def kyc_image(cust_id):
    doc = get_db().customers.find_one({"_id": cust_id}, {"kyc_doc": 1})
    if doc is None or not doc.get("kyc_doc"):
        abort(404)
    return Response(bytes(doc["kyc_doc"]), mimetype="image/png")


CHANNELS = ["UPI", "NEFT", "IMPS", "RTGS"]
ACCOUNT_TYPES = ["savings", "current", "salary"]


def _page_count(total):
    return max(1, math.ceil(total / PAGE_SIZE))


@app.route("/accounts")
def accounts():
    db = get_db()
    acc_type = request.args.get("type", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)
    query = {"type": acc_type} if acc_type else {}

    total = db.accounts.count_documents(query)
    rows = list(db.accounts.find(query).sort("_id", 1)
                .skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    ids = [r["_id"] for r in rows]

    def counts(field):
        return {d["_id"]: d["n"] for d in db.transactions.aggregate([
            {"$match": {field: {"$in": ids}}},
            {"$group": {"_id": "$" + field, "n": {"$sum": 1}}}])}

    return render_template(
        "accounts.html", rows=rows, sent=counts("from_acc"), received=counts("to_acc"),
        total=total, page=page, pages=_page_count(total), acc_type=acc_type,
        account_types=ACCOUNT_TYPES)


@app.route("/accounts/<acc_id>")
def account_detail(acc_id):
    db = get_db()
    account = db.accounts.find_one({"_id": acc_id})
    if account is None:
        abort(404)
    owner = db.customers.find_one({"_id": account["customer_id"]}, {"name": 1})

    def totals(field):
        result = list(db.transactions.aggregate([
            {"$match": {field: acc_id}},
            {"$group": {"_id": None, "n": {"$sum": 1}, "total": {"$sum": "$amount"}}}]))
        return result[0] if result else {"n": 0, "total": 0}

    distinct_senders = len(db.transactions.distinct("from_acc", {"to_acc": acc_id}))
    recent = list(db.transactions
                  .find({"$or": [{"from_acc": acc_id}, {"to_acc": acc_id}]})
                  .sort([("ts", -1), ("_id", 1)]).limit(50))

    return render_template(
        "account_detail.html", a=account, owner=owner, sent=totals("from_acc"),
        received=totals("to_acc"), distinct_senders=distinct_senders, recent=recent)


@app.route("/transactions")
def transactions():
    db = get_db()
    channel = request.args.get("channel", "").strip()
    account = request.args.get("account", "").strip()
    min_amount = request.args.get("min_amount", "").strip()
    page = max(request.args.get("page", 1, type=int), 1)

    query = {}
    if channel:
        query["channel"] = channel
    if account:
        query["$or"] = [{"from_acc": account}, {"to_acc": account}]
    if min_amount:
        try:
            query["amount"] = {"$gte": float(min_amount)}
        except ValueError:
            min_amount = ""

    total = db.transactions.count_documents(query)
    rows = list(db.transactions.find(query).sort([("ts", -1), ("_id", 1)])
                .skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    return render_template(
        "transactions.html", rows=rows, total=total, page=page, pages=_page_count(total),
        channel=channel, account=account, min_amount=min_amount, channels=CHANNELS)


_alert_schema_ready = False


def _alert_call(func, *args):
    """Run a Cassandra call. Returns (result, error_message) and never raises."""
    global _alert_schema_ready
    try:
        if not _alert_schema_ready:
            alerts_store.ensure_schema()
            _alert_schema_ready = True
        return func(*args), None
    except Exception as exc:
        return None, "The alert log (Cassandra) is unavailable (" + type(exc).__name__ + ")"


@app.route("/alerts")
def alerts():
    account = request.args.get("account", "").strip()
    if account:
        rows, error = _alert_call(alerts_store.get_alerts_for_account, account)
    else:
        rows, error = _alert_call(alerts_store.get_recent_alerts, 1000)
    return render_template("alerts.html", rows=rows or [], error=error, account=account)


if __name__ == "__main__":
    app.run(debug=True, port=5000)



