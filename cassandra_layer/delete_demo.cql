-- 1. Delete a single column value (the cell becomes null)
DELETE reviewed_by FROM fraudgraph.alerts_by_account
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

-- 2. Delete one key from a map
DELETE evidence['analyst_note'] FROM fraudgraph.alerts_by_account
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

SELECT rule_type, reviewed_by, evidence FROM fraudgraph.alerts_by_account
  WHERE account_id = 'ACC9001';

-- 3. Delete one whole row
DELETE FROM fraudgraph.alerts_by_account
  WHERE account_id = 'ACC9002' AND alert_time = '2026-11-12 16:00:00'
    AND alert_id = 44444444-4444-4444-4444-444444444444;

SELECT alert_time, rule_type FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9002';

-- 4. Delete an entire partition (all alerts of one account)
DELETE FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9002';
DELETE FROM fraudgraph.alerts_by_account WHERE account_id = 'ACC9001';

SELECT count(*) FROM fraudgraph.alerts_by_account;
