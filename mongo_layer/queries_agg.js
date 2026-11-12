print("--- 1. Top 5 senders by total amount sent");
printjson(db.transactions.aggregate([
  {$group: {_id: "$from_acc", total_sent: {$sum: "$amount"}, txn_count: {$sum: 1}}},
  {$project: {total_sent: {$round: ["$total_sent", 2]}, txn_count: 1}},
  {$sort: {total_sent: -1}},
  {$limit: 5}
]).toArray());

print("--- 2. Per channel: count, average, maximum");
printjson(db.transactions.aggregate([
  {$group: {_id: "$channel", txns: {$sum: 1}, avg_amount: {$avg: "$amount"}, max_amount: {$max: "$amount"}}},
  {$project: {txns: 1, avg_amount: {$round: ["$avg_amount", 0]}, max_amount: 1}},
  {$sort: {txns: -1}}
]).toArray());

print("--- 3. Monthly transaction volume");
printjson(db.transactions.aggregate([
  {$group: {_id: {$dateToString: {format: "%Y-%m", date: "$ts"}}, txns: {$sum: 1}, volume: {$sum: "$amount"}}},
  {$project: {txns: 1, volume: {$round: ["$volume", 0]}}},
  {$sort: {_id: 1}}
]).toArray());

print("--- 4. Top 5 accounts by number of DISTINCT senders");
printjson(db.transactions.aggregate([
  {$group: {_id: "$to_acc", senders: {$addToSet: "$from_acc"}}},
  {$project: {distinct_senders: {$size: "$senders"}}},
  {$sort: {distinct_senders: -1}},
  {$limit: 5}
]).toArray());

print("--- 5. Identifiers used by more than one customer");
["devices", "phones", "ips"].forEach(function (field) {
  print(field + ":");
  printjson(db.customers.aggregate([
    {$unwind: "$" + field},
    {$group: {_id: "$" + field, customers: {$push: "$_id"}, n: {$sum: 1}}},
    {$match: {n: {$gt: 1}}}
  ]).toArray());
});
