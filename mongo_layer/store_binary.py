import struct
import zlib

from bson.binary import Binary
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27018"


def make_png(rgb, width=64, height=64):
    """Build a tiny valid PNG image from scratch (a stand-in for a scanned KYC document)."""
    def chunk(tag, data):
        body = tag + data
        return (struct.pack(">I", len(data)) + body
                + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b""))


def main():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client["fraudgraph"]

    ids = [c["_id"] for c in
           db.customers.find({"kyc_status": "verified"}, {"_id": 1}).sort("_id", 1).limit(5)]
    colours = [(200, 220, 240), (240, 200, 200), (200, 240, 200), (240, 240, 180), (220, 200, 240)]

    for cust_id, colour in zip(ids, colours):
        png = make_png(colour)
        db.customers.update_one({"_id": cust_id}, {"$set": {"kyc_doc": Binary(png)}})
        print(f"Stored {len(png)} bytes for {cust_id}")

    print("binData docs :", db.customers.count_documents({"kyc_doc": {"$type": "binData"}}))
    print("null docs    :", db.customers.count_documents({"kyc_doc": None}))

    stored = db.customers.find_one({"_id": ids[0]})["kyc_doc"]
    with open("mongo_layer\\kyc_sample.png", "wb") as f:
        f.write(stored)
    print("Round trip identical:", bytes(stored) == make_png(colours[0]))
    client.close()


if __name__ == "__main__":
    main()
