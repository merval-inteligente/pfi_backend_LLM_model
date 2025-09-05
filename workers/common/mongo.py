import os
from pymongo import MongoClient

def get_db():
    uri = os.getenv("MONGODB_URI")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    return client.get_default_database()
