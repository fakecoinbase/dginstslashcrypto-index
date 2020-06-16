import time

import cryptoindex.API_request as api
from pymongo import MongoClient

start = time.time()

connection = MongoClient("localhost", 27017)
# creating the database called index
db = connection.index
db.rawdata.create_index([("id", -1)])
# creating the empty collection rawdata within the database index

exc_raw_collection = db.EXC_rawdata


# itbit

assets1 = ["BTC", "ETH"]
fiat1 = ["EUR", "USD"]

for Crypto in assets1:
    for Fiat in fiat1:

        api.itbit_ticker(Crypto, Fiat, exc_raw_collection)

itbit = time.time()


print("This script took: {} seconds".format(float(itbit - start)))
