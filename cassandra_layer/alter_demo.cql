ALTER TABLE fraudgraph.alerts_by_account ADD reviewed_by text;
ALTER TABLE fraudgraph.alerts_by_account ADD review_note text;
ALTER TABLE fraudgraph.alerts_by_account DROP review_note;

UPDATE fraudgraph.alerts_by_account SET reviewed_by = 'analyst1'
  WHERE account_id = 'ACC9001' AND alert_time = '2026-11-12 14:30:00'
    AND alert_id = 22222222-2222-2222-2222-222222222222;

SELECT account_id, alert_time, rule_type, reviewed_by FROM fraudgraph.alerts_by_account;

SELECT column_name, kind, type FROM system_schema.columns
  WHERE keyspace_name = 'fraudgraph' AND table_name = 'alerts_by_account';
