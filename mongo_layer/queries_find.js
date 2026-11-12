print("--- 1. COUNT customers by kyc_status");
print("verified:", db.customers.countDocuments({kyc_status: "verified"}));
print("pending :", db.customers.countDocuments({kyc_status: "pending"}));
print("rejected:", db.customers.countDocuments({kyc_status: "rejected"}));

print("--- 2. FIND with filter and projection (3 customers in Mysuru)");
printjson(db.customers.find({city: "Mysuru"}, {name: 1, city: 1}).limit(3).toArray());

print("--- 3. NULL handling on kyc_doc");
print("kyc_doc == null        :", db.customers.countDocuments({kyc_doc: null}));
print("kyc_doc missing        :", db.customers.countDocuments({kyc_doc: {$exists: false}}));
print("kyc_doc has type null  :", db.customers.countDocuments({kyc_doc: {$type: "null"}}));
print("kyc_doc not null       :", db.customers.countDocuments({kyc_doc: {$ne: null}}));

print("--- 4. SORT + LIMIT: 5 largest transactions");
printjson(db.transactions.find({}, {from_acc: 1, to_acc: 1, amount: 1})
  .sort({amount: -1, _id: 1}).limit(5).toArray());

print("--- 5. SKIP: the next 5 (ranks 6 to 10)");
printjson(db.transactions.find({}, {from_acc: 1, to_acc: 1, amount: 1})
  .sort({amount: -1, _id: 1}).skip(5).limit(5).toArray());

print("--- 6. ARRAYS");
print("customers with 2+ devices :", db.customers.countDocuments({"devices.1": {$exists: true}}));
print("customers with 2 phones   :", db.customers.countDocuments({phones: {$size: 2}}));
print("customers with 2 IPs      :", db.customers.countDocuments({ips: {$size: 2}}));
