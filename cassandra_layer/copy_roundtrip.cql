COPY fraudgraph.alerts_by_account
  (account_id, alert_time, alert_id, rule_type, risk_points, rules_triggered, account_path, evidence, reviewed_by)
  TO '/tmp/alerts_export.csv' WITH HEADER = true;

SELECT count(*) FROM fraudgraph.alerts_by_account;

TRUNCATE fraudgraph.alerts_by_account;

SELECT count(*) FROM fraudgraph.alerts_by_account;

COPY fraudgraph.alerts_by_account
  (account_id, alert_time, alert_id, rule_type, risk_points, rules_triggered, account_path, evidence, reviewed_by)
  FROM '/tmp/alerts_export.csv' WITH HEADER = true;

SELECT count(*) FROM fraudgraph.alerts_by_account;

SELECT account_id, rule_type, risk_points, rules_triggered, account_path, evidence, reviewed_by
  FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9001';
