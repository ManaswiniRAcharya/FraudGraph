# FraudGraph

Fraud-ring and AML detection using a polyglot NoSQL design for the course NoSQL Database (CS3214-1).

| Database | Role |
|---|---|
| MongoDB | Master data: customers, accounts, transactions (source of truth) |
| Neo4j | Graph copy of the data, used for fraud-pattern queries (rebuildable) |
| Cassandra | Alert log written by the detection code |

## Quick start (Windows PowerShell, from the project root)

1. Start the databases and wait about a minute for Cassandra:

        docker compose up -d
        docker compose ps

   If an image download fails with an EOF error, pull it from the mirror and tag it, for example:
   `docker pull mirror.gcr.io/library/mongo:7` then `docker tag mirror.gcr.io/library/mongo:7 mongo:7`.

2. Create the Python environment:

        python -m venv venv
        .\venv\Scripts\Activate.ps1
        pip install -r requirements.txt

3. Load the data:

        python mongo_layer\setup_mongo.py
        python graph_layer\load_graph.py

4. Check everything (Person 1 deliverables):

        python verify_person1.py

5. Run the web app and open http://127.0.0.1:5000

        python -m app.main

Always run commands from the project root. After any restart, repeat step 1 first.

## Ports

| Service | Host port | Note |
|---|---|---|
| MongoDB | 27018 | Not 27017, which a local Windows MongoDB service may already use |
| Neo4j | 7474 (browser), 7687 (code) | Login neo4j / fraudgraph123 |
| Cassandra | 9042 | |
| Flask | 5000 | |

## Folders

| Folder | Contents |
|---|---|
| data_generator | Synthetic data with planted fraud, written to data_generator/output |
| mongo_layer | MongoDB load, binary KYC documents, query scripts |
| graph_layer | MongoDB to Neo4j loader with built-in verification |
| cassandra_layer | CQL schema, demo scripts, and alerts_store.py |
| app | Flask web app and page checks |

## Person 1 modules

| Module | What it does | Syllabus topics shown |
|---|---|---|
| data_generator/generate_data.py | 400 customers, 500 accounts, 2847 transactions, planted rings, cycles, fan-in, chain, and innocent decoy households | Dataset design |
| mongo_layer/load_mongo.py, store_binary.py, setup_mongo.py | Load, indexes, binary KYC images | Unique key, indexes, binary data, JSON documents |
| mongo_layer/queries_find.js | count, find, null handling, sort, limit, skip, arrays | Unit II query language |
| mongo_layer/queries_agg.js, queries_types.js | Aggregation pipelines, BSON types | Aggregate functions, data types, MapReduce analogue |
| cassandra_layer/*.cql | Keyspace, table, CRUD, set/list/map, ALTER, COPY, DELETE | Unit III |
| cassandra_layer/alerts_store.py | Python interface for saving and reading alerts | Cassandra from an application |
| graph_layer/load_graph.py | Builds the Neo4j graph and verifies it against MongoDB | Graph NoSQL, polyglot persistence |
| app/ | Customers, accounts, transactions and alerts pages | Document queries in an application |

## Interfaces for Person 2

- IDs are fixed across all databases: CUST0001, ACC0001, DEV001, TXN000001.
- Neo4j model: (Customer)-[:OWNS]->(Account), (Customer)-[:USES_DEVICE]->(Device), (Customer)-[:HAS_PHONE]->(Phone), (Customer)-[:LOGGED_FROM]->(IP), (Account)-[:SENT {txn_id, amount, ts, channel}]->(Account).
- Neo4j timestamps are local date-times with no timezone, matching the MongoDB values. Compare them with each other, never with a timezone-aware "now".
- Rebuild the graph any time with python graph_layer\load_graph.py.
- Save alerts with cassandra_layer.alerts_store.save_alert(...). Required keys: account_id, rule_type, risk_points. Optional: rules_triggered, account_path, evidence, alert_time.
- python -m app.demo_alerts add|clear shows or removes two fake alerts on the Alerts page.

## Known limitations

- The data is synthetic, and planted transactions use larger amounts than normal ones, so an amount threshold must not be used as a detection rule.
- Only Cassandra's schema and replication settings are configured for a single node. Sharding and replication are explained, not demonstrated.
- MongoDB mapReduce is deprecated, so the MapReduce topic is shown with aggregation pipelines.
- The binary KYC documents are 64x64 stand-in images. Real scans larger than 16 MB would need GridFS, which is not implemented.
- The alerts page without a filter scans every Cassandra partition (up to 1000 rows). That suits this dataset, not a large one.

## Person 2 section

To be completed by Person 2: detection queries, risk scoring, fraud pages.
