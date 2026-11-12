-- Keyspace: the Cassandra equivalent of a database
CREATE KEYSPACE IF NOT EXISTS fraudgraph
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

-- Table: one partition per account, rows sorted newest-first inside it
CREATE TABLE IF NOT EXISTS fraudgraph.alerts_by_account (
  account_id      text,
  alert_time      timestamp,
  alert_id        uuid,
  rule_type       text,
  risk_points     int,
  rules_triggered set<text>,
  account_path    list<text>,
  evidence        map<text, text>,
  PRIMARY KEY ((account_id), alert_time, alert_id)
) WITH CLUSTERING ORDER BY (alert_time DESC, alert_id ASC);
