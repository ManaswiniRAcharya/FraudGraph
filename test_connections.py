from pymongo import MongoClient
from neo4j import GraphDatabase
from cassandra.cluster import Cluster

# --- MongoDB ---
mongo = MongoClient("mongodb://localhost:27018", serverSelectionTimeoutMS=5000)
print("MongoDB  :", mongo.admin.command("ping"))
mongo.close()

# --- Neo4j ---
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "fraudgraph123"))
driver.verify_connectivity()
print("Neo4j    : connected")
driver.close()

# --- Cassandra ---
cluster = Cluster(["localhost"], port=9042)
session = cluster.connect()
row = session.execute("SELECT release_version FROM system.local").one()
print("Cassandra: version", row.release_version)
cluster.shutdown()
