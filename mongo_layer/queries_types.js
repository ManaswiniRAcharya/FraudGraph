print("--- Customer CUST0001 (has a KYC image)");
printjson(db.customers.aggregate([{$match: {_id: "CUST0001"}}, {$project: {
  name: {$type: "$name"}, phones: {$type: "$phones"},
  kyc_doc: {$type: "$kyc_doc"}, created_at: {$type: "$created_at"}}}]).toArray());
print("--- Customer CUST0006 (no KYC image)");
printjson(db.customers.aggregate([{$match: {_id: "CUST0006"}}, {$project: {
  kyc_doc: {$type: "$kyc_doc"}}}]).toArray());
print("--- A transaction");
printjson(db.transactions.aggregate([{$limit: 1}, {$project: {
  amount: {$type: "$amount"}, ts: {$type: "$ts"}, from_acc: {$type: "$from_acc"}}}]).toArray());
