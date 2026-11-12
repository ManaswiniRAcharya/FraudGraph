import load_mongo
import store_binary

if __name__ == "__main__":
    print("== Step 1: loading JSON into MongoDB ==")
    load_mongo.main()
    print("== Step 2: attaching binary KYC documents ==")
    store_binary.main()
