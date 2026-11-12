UPDATE fraudgraph.alerts_by_account SET risk_points = 55
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

UPDATE fraudgraph.alerts_by_account SET rules_triggered = rules_triggered + {'SHARED_DEVICE'}
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

UPDATE fraudgraph.alerts_by_account SET account_path = account_path + ['ACC9004']
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

UPDATE fraudgraph.alerts_by_account SET evidence['analyst_note'] = 'checked manually'
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

UPDATE fraudgraph.alerts_by_account SET rule_type = 'FAN_IN', risk_points = 35
  WHERE account_id = 'ACC9002' AND alert_time = '2026-11-12 16:00:00'
    AND alert_id = 44444444-4444-4444-4444-444444444444;

SELECT risk_points, rules_triggered, account_path, evidence
  FROM fraudgraph.alerts_by_account
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00';

SELECT alert_time, rule_type, risk_points, rules_triggered
  FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9002';
