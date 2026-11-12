INSERT INTO fraudgraph.alerts_by_account
  (account_id, alert_time, alert_id, rule_type, risk_points, rules_triggered, account_path, evidence)
VALUES ('ACC9001', '2026-11-10 09:00:00', 11111111-1111-1111-1111-111111111111,
  'SHARED_DEVICE', 30, {'SHARED_DEVICE'}, ['ACC9001'], {'device': 'DEV900'});

INSERT INTO fraudgraph.alerts_by_account
  (account_id, alert_time, alert_id, rule_type, risk_points, rules_triggered, account_path, evidence)
VALUES ('ACC9001', '2026-11-12 14:30:00', 22222222-2222-2222-2222-222222222222,
  'CIRCULAR', 40, {'CIRCULAR'}, ['ACC9001', 'ACC9002', 'ACC9003', 'ACC9001'],
  {'window_hours': '8', 'amount_ratio': '0.94'});

INSERT INTO fraudgraph.alerts_by_account
  (account_id, alert_time, alert_id, rule_type, risk_points, rules_triggered, account_path, evidence)
VALUES ('ACC9002', '2026-11-12 14:30:00', 33333333-3333-3333-3333-333333333333,
  'CIRCULAR', 40, {'CIRCULAR'}, ['ACC9001', 'ACC9002', 'ACC9003', 'ACC9001'],
  {'window_hours': '8'});

SELECT account_id, alert_time, rule_type, risk_points, rules_triggered, account_path, evidence
  FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9001';

SELECT count(*) FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9001';

SELECT account_id, rule_type FROM fraudgraph.alerts_by_account;
