# va messo check con CW clean del giorno prima. prendo tutti le key formtae
# da crypto-fiat-exchange e faccio il check sui dati del giorno.
# se ci sono dati nuovi vediamo il da farsi
# se mancano dati (seri morta) lo individuo e metto 0

# standard library import
import time
from datetime import datetime

# third party import
from pymongo import MongoClient
import pandas as pd
import numpy as np

# local import
import cryptoindex.data_setup as data_setup
import cryptoindex.mongo_setup as mongo


# ############# INITIAL SETTINGS ################################

pair_array = ['gbp', 'usd', 'cad', 'jpy', 'eur', 'usdt', 'usdc']
# pair complete = ['gbp', 'usd', 'cad', 'jpy', 'eur', 'usdt', 'usdc']
Crypto_Asset = ['BTC', 'ETH', 'XRP', 'LTC', 'BCH',
                'EOS', 'ETC', 'ZEC', 'ADA', 'XLM', 'XMR', 'BSV']
# crypto complete [ 'BTC', 'ETH', 'XRP', 'LTC', 'BCH', 'EOS',
# 'ETC', 'ZEC', 'ADA', 'XLM', 'XMR', 'BSV']
Exchanges = ['coinbase-pro', 'poloniex', 'bitstamp',
             'gemini', 'bittrex', 'kraken', 'bitflyer']
# exchange complete = [ 'coinbase-pro', 'poloniex', 'bitstamp',
# 'gemini', 'bittrex', 'kraken', 'bitflyer']

# #################### setup mongo connection ##################

# connecting to mongo in local
connection = MongoClient('localhost', 27017)
# creating the database called index
db = connection.index

# naming the existing collections as a variable
collection_clean = db.cleandata
collection_volume = db.volume_checked_data

# defining the database name and the collection name where to look for data
database = "index"
collection_raw = "CW_rawdata"
collection_clean_check = "CW_cleandata"
collection_volume_check = "volume_checked_data"

# ############################ missing days check #############################

# this section allows to check if CW_clean data comtains the new values of the
# day. the check is based on a 5-days period and allows
# set start_period
Start_Period = '01-01-2016'
# set today
today = datetime.now().strftime('%Y-%m-%d')
today_TS = int(datetime.strptime(today, '%Y-%m-%d').timestamp()) + 3600*2
yesterday_TS = today_TS - 86400
two_before_TS = yesterday_TS - 86400

# defining the array containing all the date from start_period until today
date_complete_int = data_setup.timestamp_gen(Start_Period)
# converting the timestamp format date into string
date_complete = [str(single_date) for single_date in date_complete_int]

# searching only the last five days
last_five_days = date_complete[(len(date_complete) - 5): len(date_complete)]

# defining the MongoDB path where to look for the rates
query = {'Exchange': "coinbase-pro", 'Pair': "ethusd"}

# retrieving data from MongoDB 'index' and 'ecb_raw' collection
matrix = mongo.query_mongo(database, collection_clean_check, query)

# checking the time column
date_list = np.array(matrix["Time"])
last_five_days_mongo = date_list[(len(date_list) - 5): len(date_list)]

# finding the date to download as difference between complete array of date and
# date now stored on MongoDB
date_to_add = data_setup.Diff(last_five_days, last_five_days_mongo)
print(date_to_add)

if date_to_add != []:

    if len(date_to_add) > 1:

        date_to_add.sort()
        start_date = data_setup.timestamp_to_human(
            [date_to_add[0]], date_format='%m-%d-%Y')
        start_date = start_date[0]
        end_date = data_setup.timestamp_to_human(
            [date_to_add[len(date_to_add)-1]], date_format='%m-%d-%Y')
        end_date = end_date[0]

    else:

        start_date = datetime.fromtimestamp(int(date_to_add[0]))
        start_date = start_date.strftime('%m-%d-%Y')
        end_date = start_date

    relative_reference_vector = data_setup.timestamp_gen(
        start_date, end_date, EoD='N')

    # creating a date array of support that allows to manage the one-day
    # missing data
    if start_date == end_date:

        day_before = int(relative_reference_vector[0]) - 86400
        support_date_array = np.array([day_before])
        support_date_array = np.append(
            support_date_array, int(relative_reference_vector[0]))


# ################### fixing the "Pair Volume" information #################

db = 'index'
collection_raw = "CW_rawdata"
q_dict = {'Time': yesterday_TS}

daily_matrix = mongo.query_mongo2(db, collection_raw, q_dict)
daily_matrix = daily_matrix.loc[daily_matrix.Time != 0]
daily_matrix = daily_matrix.drop(columns=['Low', 'High', 'Open'])

for Crypto in Crypto_Asset:

    currencypair_array = []

    for i in pair_array:

        currencypair_array.append(Crypto.lower() + i)

    for exchange in Exchanges:

        for cp in currencypair_array:

            matrix = daily_matrix.loc[daily_matrix['Exchange'] == exchange]
            matrix = matrix.loc[matrix['Pair'] == cp]
            # checking if the matrix is not empty
            if matrix.shape[0] > 1:

                matrix['Pair Volume'] = matrix['Close Price'] * \
                    matrix['Crypto Volume']

            # put the manipulated data on MongoDB
            try:

                data = matrix.to_dict(orient='records')
                collection_volume.insert_many(data)

            except TypeError:
                pass

# ############################################################################
# ########### DEAD AND NEW CRYPTO-FIAT MANAGEMENT ############################

collection_volume_check = "volume_checked_data"
collection_logic_key = 'exchange_pair_key'
q_dict = {'Time': yesterday_TS}

# downloading from MongoDB the matrix with the daily values and the
# matrix containing the exchange-pair logic values
daily_matrix = mongo.query_mongo2(db, collection_volume_check, q_dict)
logic_key = mongo.query_mongo2(db, collection_logic_key)

# creating the exchange-pair couples key for the daily matrix
daily_matrix['key'] = daily_matrix['Exchange'] + '&' + daily_matrix['Pair']
# ########## adding the dead series to the daily values ##################

# selecting only the exchange-pair couples present in the historical series
key_present = logic_key.loc[logic_key.logic_value == 1]
key_present = key_present.drop(columns=['logic_value'])
# applying a left join between the prresent keys matrix and the daily
# matrix, this operation returns a matrix containing all the keys in
# "key_present" and, if some keys are missing in "daily_matrix" put NaN
merged = pd.merge(key_present, daily_matrix, on='key', how='left')
# assigning some columns values and substituting NaN with 0
# in the "merged" df
merged['Time'] = yesterday_TS
split_val = merged['key'].str.split('&', expand=True)
merged['Exchange'] = split_val[0]
merged['Pair'] = split_val[1]
merged.fillna(0, inplace=True)

# ########## checking potential new exchange-pair couple ##################

key_absent = logic_key.loc[logic_key.logic_value == 0]
key_absent.drop(columns=['logic_value'])

merg_absent = pd.merge(key_absent, daily_matrix, on='key', how='left')
merg_absent.fillna('NaN', inplace=True)
new_key = merg_absent.loc[merg_absent['Close Price'] != 'NaN']

if new_key.empty is False:

    print('Message: New exchange-pair couple(s) found.')
    new_key_list = new_key['key']
    print(new_key_list)

    for key in new_key_list:

        # updating the logic matrix of exchange-pair couple
        logic_key.loc[logic_key.key == key, 'logic value'] = 1

        # create the historical series of the new couple(s)
        # composed by zeros
        splited_key = key.split('&')
        key_hist_df = pd.DataFrame(date_complete, columns='Time')
        key_hist_df['Close Price'] = 0
        key_hist_df['Pair Volume'] = 0
        key_hist_df['Crypto Volume'] = 0
        key_hist_df['Exchange'] = splited_key[0]
        key_hist_df['Pair'] = splited_key[1]

        # inserting the today value of the new couple(s)
        new_price = new_key.loc[new_key.key == key, 'Close Price']
        new_p_vol = new_key.loc[new_key.key == key, 'Pair Volume']
        new_c_vol = new_key.loc[new_key.key == key, 'Crypto Volume']
        key_hist_df.loc[key_hist_df.Time ==
                        yesterday_TS, 'Close Price'] = new_price
        key_hist_df.loc[key_hist_df.Time ==
                        yesterday_TS, 'Pair Volume'] = new_p_vol
        key_hist_df.loc[key_hist_df.Time ==
                        yesterday_TS, 'Crypto Volume'] = new_c_vol

        # upload the dataframe on MongoDB collection "CW_cleandata"
        data = key_hist_df.to_dict(orient='records')
        collection_clean.insert_many(data)

else:
    pass

# ###########################################################################
# ######################## MISSING DATA FIXING ##############################

database = "index"
collection_clean_check = "CW_cleandata"
q_dict = {'Time': str(two_before_TS)}
# downloading from MongoDB the matrix referring to the previuos day
day_before_matrix = mongo.query_mongo2(db, collection_clean_check, q_dict)
print(day_before_matrix)
# add the "key" column
day_before_matrix['key'] = day_before_matrix['Exchange'] + \
    '&' + day_before_matrix['Pair']

# looping through all the daily keys looking for potential missing value
for key_val in day_before_matrix['key']:

    new_val = merged.loc[merged.key == key_val]

    # if the new 'Close Price' referred to a certain key is 0 the script
    # check the previous day value: if is == 0 then pass, if is != 0
    # the values related to the selected key needs to be corrected
    # ###### IF A EXC-PAIR DIES AT A CERTAIN POINT, THE SCRIPT
    # CHANGES THE VALUES. MIGHT BE WRONG #######################
    if new_val['Close Price'] == 0:

        d_before_val = day_before_matrix.loc[day_before_matrix.key == key_val]

        if d_before_val['Close Price'] != 0:

            price_var = data_setup.daily_fix_missing(
                new_val, merged, day_before_matrix)

            # applying the weighted variation to the day before 'Close Price'
            new_price = (1 + price_var) * d_before_val['Close Price']
            # changing the 'Close Price' value using the new computed price
            merged.loc[merged.key == key_val, 'Close Price'] = new_price

        else:
            pass

    else:
        pass


# put the manipulated data on MongoDB
merged.drop(columns=['key'])
data = merged.to_dict(orient='records')
collection_clean.insert_many(data)
