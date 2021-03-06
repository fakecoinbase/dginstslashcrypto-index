# #############################################################################
# The file completes the historical series of Cryptocurrencies market data
# stored on MongoDB
# The main rules for the manipulation of raw data are the followings:
# - if a certain Crypto-Fiat pair does not start at the beginning of the
#   period but later, the script will put a series of zeros from the start
#   period until the actual beginning of the series (homogenize_series)
# - if a certain Crypto-Fiat pair stopped to trade at a certain point, the
#   script will put a series of zeros starting from the last traded value
#   until today (homogenize_dead_series)
# - if a certain data is missing in a certain date the file will compute
#   a value to insert using all the values displayed, for the same Crypto-Fiat
#   pair, in the other exchanges.
# - if, trying to fix a series as described above, the code find out that just
#   one exchange has the values for the wanted Crypto-Fiat pair, the file will
#   put a 0-values array for all the missing date
# Once the data is manipulated and the series has been homogeneized, the script
# put the historical series on MongoDB in the collection "CW_cleandata"
# ############################################################################

# standard library import
import time
from datetime import datetime, timezone

# third party import
import numpy as np

# local import
# import cryptoindex.data_setup as data_setup
# import cryptoindex.mongo_setup as mongo
from cryptoindex.data_setup import (CW_series_fix_missing, date_gen,
                                    homogenize_dead_series, homogenize_series,
                                    make_unique)
from cryptoindex.mongo_setup import (
    query_mongo, mongo_coll, mongo_coll_drop,
    mongo_indexing, mongo_upload)
from cryptoindex.config import (
    START_DATE, DAY_IN_SEC, MONGO_DICT,
    PAIR_ARRAY, CRYPTO_ASSET, EXCHANGES, DB_NAME)

start = time.time()
# ################ initial settings #######################


# define today date as timestamp
today_str = datetime.now().strftime("%Y-%m-%d")
today = datetime.strptime(today_str, "%Y-%m-%d")
today_TS = int(today.replace(tzinfo=timezone.utc).timestamp())
y_TS = today_TS - DAY_IN_SEC

# define the variable containing all the date from start_date to today.
# the date are displayed as timestamp and each day refers to 12:00 am UTC
reference_date_vector = date_gen(START_DATE)


# #################### setup MongoDB connection ################

mongo_coll_drop("cw_hist_s")

mongo_indexing()

collection_dict_upload = mongo_coll()

# ################ download raw data freom MngoDB #################

raw_matrix = query_mongo(DB_NAME, MONGO_DICT.get("coll_cw_raw"))
raw_matrix = raw_matrix.loc[raw_matrix.Time != 0]
raw_matrix = raw_matrix.drop(columns=["Low", "High", "Open"])

# ################ remove potential duplicate values ##############

tot_matrix = make_unique(raw_matrix)

# ################ fixing the "Pair Volume" information ###########


# tot_matrix['str_t'] = [str(t) for t in tot_matrix['Time']]
tot_matrix['key'] = tot_matrix['Exchange'] + '&' + \
    tot_matrix['Pair']
# correct the "Crypto Volume" information for the date 2017-04-28 and
# 2017-04-29 using the previous day value
m_27_04 = tot_matrix.loc[tot_matrix.Time
                         == 1493251200, ['key', 'Crypto Volume']]

m_28_04 = tot_matrix.loc[tot_matrix.Time == 1493337600]
m_29_04 = tot_matrix.loc[tot_matrix.Time == 1493424000]
for k in m_27_04['key']:

    prev_vol = np.array(m_27_04.loc[m_27_04.key == k, "Crypto Volume"])
    m_28_04.loc[m_28_04.key == k, "Crypto Volume"] = prev_vol
    m_29_04.loc[m_29_04.key == k, "Crypto Volume"] = prev_vol

tot_matrix = tot_matrix.loc[tot_matrix.Time != 1493337600]
tot_matrix = tot_matrix.loc[tot_matrix.Time != 1493424000]

tot_matrix = tot_matrix.append(m_28_04)
tot_matrix = tot_matrix.append(m_29_04)
tot_matrix = tot_matrix.sort_values(by=['Time'])
tot_matrix = tot_matrix.drop(columns=['key'])

for Crypto in CRYPTO_ASSET:

    ccy_pair_array = []

    for i in PAIR_ARRAY:

        ccy_pair_array.append(Crypto.lower() + i)

    for exchange in EXCHANGES:

        for cp in ccy_pair_array:

            mat = tot_matrix.loc[tot_matrix["Exchange"] == exchange]
            mat = mat.loc[mat["Pair"] == cp]
            # checking if the matrix is not empty
            if mat.shape[0] > 1:

                if exchange == "bittrex" and cp == "btcusdt":

                    sub_vol = np.array(
                        mat.loc[mat.Time == 1544486400, "Crypto Volume"])
                    mat.loc[mat.Time == 1544572800, "Crypto Volume"] = sub_vol
                    mat.loc[mat.Time == 1544659200, "Crypto Volume"] = sub_vol

                mat["Pair Volume"] = mat["Close Price"] * mat["Crypto Volume"]

            # put the manipulated data on MongoDB
            try:

                mongo_upload(mat, "collection_cw_vol_check")

            except TypeError:
                pass

end = time.time()

print("This script took: {} seconds".format(float(end - start)))

# ############## fixing historical series main part ##############
start = time.time()

tot_matrix = query_mongo(DB_NAME, MONGO_DICT.get("coll_vol_chk"))


for Crypto in CRYPTO_ASSET:

    print(Crypto)
    ccy_pair_array = []

    for i in PAIR_ARRAY:

        ccy_pair_array.append(Crypto.lower() + i)

    for exchange in EXCHANGES:

        ex_matrix = tot_matrix.loc[tot_matrix["Exchange"] == exchange]
        print(exchange)
        for cp in ccy_pair_array:

            print(cp)
            crypto = cp[:3]
            pair = cp[3:]

            cp_matrix = ex_matrix.loc[ex_matrix["Pair"] == cp]
            cp_matrix = cp_matrix.drop(columns=["Exchange", "Pair"])
            # checking if the matrix is not empty
            if cp_matrix.shape[0] > 1:

                # check if the historical series start at the same date as
                # the start date if not fill the dataframe with zero values
                cp_matrix = homogenize_series(
                    cp_matrix, reference_date_vector
                )

                # check if the series stopped at certain point in
                # the past, if yes fill with zero
                cp_matrix = homogenize_dead_series(
                    cp_matrix, reference_date_vector
                )

                # checking if the matrix has missing data and if ever fixing it
                if cp_matrix.shape[0] != reference_date_vector.size:

                    print("fixing")
                    cp_matrix = CW_series_fix_missing(
                        cp_matrix,
                        exchange,
                        cp,
                        reference_date_vector,
                        DB_NAME,
                        MONGO_DICT.get("coll_vol_chk"),
                    )

                # ######## part that transform the timestamped date into string

                new_date = np.array([])
                for element in cp_matrix["Time"]:

                    element = str(element)
                    new_date = np.append(new_date, element)

                cp_matrix["Time"] = new_date
                # ############################################################

                # add exchange and currency_pair column
                cp_matrix["Exchange"] = exchange
                cp_matrix["Pair"] = cp
                # put the manipulated data on MongoDB
                mongo_upload(cp_matrix, "collection_cw_clean")


# #######################################################################

end = time.time()

print("This script took: {} seconds".format(float(end - start)))
