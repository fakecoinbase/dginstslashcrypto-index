import requests
from requests import get
from datetime import *
import pandas as pd
import numpy as np
from time import sleep

from pymongo import MongoClient

# this file cointains all the API calls for each pricing source. Every script call the api,
# downloads the data and stores them in mongoDB.

connection = MongoClient('localhost', 27017)
#creating the database called index
db = connection.index
db.rawdata.create_index([ ("id", -1) ])
#creating the empty collection rawdata within the database index
exc_raw_collection = db.EXC_rawdata

# function takes as input Start Date, End Date (both string in mm-dd-yyyy format) and delta (numeric)
# then creates an object containing multiple couples of date in ISO format with "delta"  days between them
# for a total length defined by start date and end date. If the last delta is bigger than end date, then 
# end date is taken as last date of the object

def date_gen_isoformat(Start_Date, End_Date, delta):
     
    # converting string to date format
    start = datetime.strptime(Start_Date,'%m-%d-%Y') 
    stop = datetime.strptime(End_Date,'%m-%d-%Y') 
    # define delta as days
    delta = timedelta(days=delta)

    pace = start
    if Start_Date != End_Date:

        while (pace < stop):

            end = pace + delta

            if end > stop:
                end = stop

            yield (str(pace.isoformat()), str(end.isoformat()))
            pace = end + timedelta(days = 1)

    # if start date == end date, then a couple containing the same date is returned
    else:
        
        yield (str(start.isoformat()), str(stop.isoformat()))



# function takes as input Start Date, End Date (both string in mm-dd-yyyy format) and delta (numeric)
# then creates an object containing multiple couples of date in TIMESTAMP format with "delta"  days between them
# for a total length defined by start date and end date. If the last delta is bigger than end date, then 
# end date is taken as last date of the object

def date_gen_timestamp(Start_Date, End_Date, delta):

    # converting string to date format
    start = datetime.strptime(Start_Date,'%m-%d-%Y') 
    stop = datetime.strptime(End_Date,'%m-%d-%Y') 
    # define delta as days
    delta = timedelta(days=delta)

    pace = start
    if Start_Date != End_Date:

        while (pace < stop):

            end = pace + delta
            if end > stop:

                end = stop

            yield (str(pace.timestamp()), str(end.timestamp()))
            pace = end + timedelta(days = 1)
    
    # if start date == end date, then a couple containing the same date is returned
    else:

        yield (str(start.isoformat()), str(stop.isoformat()))

#create the daily timestamp at midnigh UTC

def today_ts():

    today = datetime.now().strftime('%Y-%m-%d-%H')
    today_TS = int(datetime.strptime(today,'%Y-%m-%d-%H').timestamp())


    return str(today_TS)


#####################################################################################################
################################ COINBASE - PRO #####################################################
#####################################################################################################

# REST API request for coinbase-pro exchange. 
# It requires:
# crypto Pair = crypto-fiat (ex: BTC - USD)
# start date = ISO 8601
# end date = ISO 8601
# granularity = in seconds. Ex 86400 = 1 day
# this api gives back 300 responses max for each request.

#-------------------------------------------------------------------------------------------------------

# function that given Crypto (ex. BTC), Fiat (ex. USD), start DAte and End Date 
# retrieve the Historical Series from start date to End Date of the definend Crypto + Fiat
# on the Coinbase Pro Exchange
# the output will be displayed in three columns containing: 'Time' in timestamp format,
# 'Close Price' in "Fiat" currency, 'Crypto Volume' in "Crypto" amount

def Coinbase_API(Crypto, Fiat, Start_Date, End_Date = None, granularity = '86400'):

    Crypto = Crypto.upper()
    Fiat = Fiat.upper()

    if End_Date == None:
        End_Date = datetime.now().strftime('%m-%d-%Y')
   
    date_object = date_gen_isoformat(Start_Date, End_Date, 49)
    df = np.array([])
    header = ['Time', 'low', 'high', 'open', 'Close Price', 'Crypto Volume']

    for asset in Crypto:

        for fiat in Fiat:
            
            for start,stop in date_object:

                entrypoint = 'https://api.pro.coinbase.com/products/'
                key = asset+"-"+fiat+"/candles?start="+start+"&end="+stop+"&granularity="+granularity
                request_url = entrypoint + key

                response = requests.get(request_url)
                sleep(0.25)

                response = response.json()

                if df.size == 0 :
                    df = np.array(response)
                else:
                    df = np.row_stack((df, response))
                
               
    #non dovrebbe essere all'interno del ciclo?
    Coinbase_df = pd.DataFrame(df, columns=header)        
    Coinbase_df = Coinbase_df.drop(columns = ['open', 'high', 'low'])      

    return Coinbase_df    

#########################################################################################
#########################################################################################

def coinbase_ticker( Crypto, Fiat, collection):

    asset = Crypto.upper()
    fiat = Fiat.upper()
    
    entrypoint = 'https://api.pro.coinbase.com/products'
    key = '/' + asset + '-'+ fiat +'/ticker'
    #print(key)
    request_url = entrypoint + key
    response = requests.get(request_url)
    response = response.json()
    #print(response)
    try:
    
        r = response
        Pair = asset + fiat
        print(Pair)
        exchange = 'coinbase-pro'
        time = today_ts()
        date = datetime.now()
        ticker_time = r['time']
        price = r['price']
        volume = r['volume'] 
        size = r['size']
        bid = r['bid']
        ask = r['ask']
        traded_id = r['trade_id']

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time': time, 'date' : date, 'ticker_time' : ticker_time, 'Close Price' : price, 'Crypto Volume' : volume, 
                    'size': size, 'bid': bid, 'ask' : ask, 'traded_id' : traded_id}

        
        collection.insert_one(rawdata)

    except:
        print('none_coinbase')
    
     

    return 

#####################################################################################################
################################      KRAKEN    #####################################################
#####################################################################################################

# The REST API OHLC endpoint only provides a limited amount of historical data, specifically
# 720 data points of the requested interval.
# unfortunally the since option seems to not work. so here the date_gen fuction is useless

#-------------------------------------------------------------------------------------------------------

# function that given Crypto (ex. BTC), Fiat (ex. USD), start DAte and End Date 
# retrieve the Historical Series from start date to End Date of the definend Crypto + Fiat
# on the Kraken Exchange. "interval" is set on default as 1440 minutes that is equal to a day
# the output will be displayed in three columns containing: 'Time' in timestamp format,
# 'Close Price' in "Fiat" currency, 'Crypto Volume' in "Crypto" amount

def kraken_API(Start_Date, End_Date, Crypto, Fiat, interval  = '1440'):

    df = np.array([])
    header = ['Time', 'open', 'high', 'low', 'Crypto Price', 'vwap', 'Crypto Volume', 'count']

    for asset in Crypto:

        for fiat in Fiat:
            
            entrypoint = 'https://api.kraken.com/0/public/OHLC?'
            key = 'Pair='+asset+fiat+'&interval='+interval
            request_url = entrypoint + key

            response = requests.get(request_url)
            sleep(0.25)

            response = response.json()

            if df.size == 0 :
                df = np.array(response)
            else:
                df = np.row_stack((df, response))
            
            

    Kraken_df = pd.DataFrame(df, columns=header)        
    Kraken_df = Kraken_df.drop(columns = ['open', 'high', 'low', 'vwap', 'count'])      

    return Kraken_df 



########################################## kraken ticker

def kraken_ticker (Crypto, Fiat, collection):
    
    asset = Crypto.lower()
    fiat = Fiat.lower()

    if asset == 'btc':

        asset = 'xbt'


    entrypoint = 'https://api.kraken.com/0/public/Ticker?pair='
    key = asset+fiat
    #print(key)
    request_url = entrypoint + key
    print(request_url)
    response = requests.get(request_url)

    response = response.json()
    print(response)
    try:
        asset = asset.upper()
        fiat = fiat.upper()
        Pair = 'X' + asset + 'Z' + fiat
        exchange = 'kraken'
        if fiat == 'USDT' or fiat == 'USDC' or fiat == 'CHF' or asset == 'ADA' or asset == 'EOS' or asset == 'BCH' or (asset == 'XRP' and fiat == 'GBP') or (asset == 'LTC' and fiat == 'GBP'):
            Pair = asset + fiat
        r = response['result'][Pair]
        Pair = asset + fiat
        print(Pair)
        time = today_ts()
        date = datetime.now()
        price = r['c'][0]
        crypto_volume = r['v'][1]

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time': time, 'date' : date, 'Close Price' : price, 
                    'Crypto Volume' : crypto_volume}

        collection.insert_one(rawdata)



    except:
        print('none_kraken')
            
        return 






#####################################################################################################
################################     BITTREX    #####################################################
#####################################################################################################

# https://bittrex.github.io/api/v3 api actually not working for historical data

def bittrex_ticker (Crypto, Fiat, collection):

    asset = Crypto.lower()
    fiat = Fiat.lower()
    entrypoint = 'https://api.bittrex.com/api/v1.1/public/getmarketsummary?market='
    key = fiat + '-' + asset 
    request_url = entrypoint + key

    response = requests.get(request_url)

    response = response.json() 

    try:
        r = response["result"][0]
        Pair = asset.upper() + fiat.upper()
        exchange = 'bittrex'
        time = today_ts()
        date = datetime.now()
        ticker_time = r['TimeStamp']
        price = r["Last"]
        volume = r['Volume']
        basevolume = r['BaseVolume'] 
        high = r['High']
        low = r['Low']
        openbuyorders = r['OpenBuyOrders']
        opensellorders = r['OpenSellOrders']
        prevday = r['PrevDay']

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time': time, 'date' : date, 'ticker_time' : ticker_time, 'Close Price':price, 'Crypto Volume': volume, 'Pair Volume': basevolume,  'high' : high, 'low': low, 'openbuyorders' : openbuyorders,'opensellorders' : opensellorders, 'prevday' : prevday }


        collection.insert_one(rawdata)

    except:
        print('none_bittrex')



    return 





#####################################################################################################
################################    POLONIEX    #####################################################
#####################################################################################################

# function that given Crypto (ex. BTC), Fiat (ex. USD), start DAte and End Date 
# retrieve the Historical Series from start date to End Date of the definend Crypto + Fiat
# on the Poloniex Exchange
# the output will be displayed in three columns containing: 'Time' in timestamp format,
# 'Close Price' in "Fiat" currency, 'Crypto Volume' in "Crypto" amount

def Poloniex_API(Start_Date, End_Date, Crypto, Fiat, period = '86400'):

    if End_Date == None:
        End_Date = datetime.now().strftime('%m-%d-%Y')
   
    date_object = date_gen_timestamp(Start_Date, End_Date, 49)
    df = np.array([])
    header = ['Time', 'open', 'high', 'low', 'Crypto Price', 'Crypto Volume', 'volume_usd', 'vwap']

    for asset in Crypto:

        for fiat in Fiat:
            
            for start,stop in date_object:

                entrypoint = 'https://poloniex.com/public?command=returnChartData&currencyPair='
                key = asset + '_' + fiat + '&start=' + start + '&end=' + stop + '&period=' + period
                request_url = entrypoint + key

                response = requests.get(request_url)
                sleep(0.25)

                response = response.json()

                if df.size == 0:

                    df = np.array(response)

                else:

                    df = np.row_stack((df, response))
                
               

    Poloniex_df = pd.DataFrame(df, columns=header)        
    Poloniex_df = Poloniex_df.drop(columns = ['open', 'high', 'low', 'vwap', 'volume usd'])      

    return Poloniex_df 


###################################################### poloniex_ticker

def poloniex_ticker (Crypto, Fiat, collection):
    
    asset = Crypto.upper()
    stbc = Fiat.upper()
    Pair = stbc+'_'+asset
    entrypoint = 'https://poloniex.com/public?command=returnTicker'
    request_url = entrypoint
    response = requests.get(request_url)
    response = response.json()
    

    try:
        response_short = response[Pair]
        r = response_short
        time = today_ts()
        date = datetime.now()
        price = r['last']
        exchange = 'poloniex'
        lowestAsk = r['lowestAsk'] 
        highestBid = r['highestBid']
        percentChange = r['percentChange']
        base_volume = r['baseVolume']
        crypto_volume = r['quoteVolume']
        isFrozen =  r['isFrozen']
        high24hr = r['high24hr']
        low24hr = r['low24hr']

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time': time, 'date': date, 'Close Price': price, 'lowestAsk': lowestAsk,
                    'highestBid': highestBid, 'percentChange' : percentChange,
                    'Pair Volume': base_volume, 'Crypto Volume' : crypto_volume, 'isFrozen' : isFrozen,
                    'high24hr' : high24hr, 'low24hr' : low24hr }

        
        
        collection.insert_one(rawdata)

    except:
        print('none_poloniex')
                    
    return 



#####################################################################################################
################################      ITBIT     #####################################################
#####################################################################################################

# https://www.itbit.com/api api actually not working for historical data 

#instead of BTC here the call is with XBT

def itbit_ticker (Crypto, Fiat, collection):
            
    asset = Crypto.upper()
    fiat = Fiat.upper()

    if asset == 'BTC':
        asset = 'XBT'

    entrypoint = 'https://api.itbit.com/v1/markets/'
    key = asset + fiat + '/ticker'
    request_url = entrypoint + key
    response = requests.get(request_url)
    response = response.json()


    if asset == 'XBT':
        asset = 'BTC'

    try:
        r = response 
        Pair = asset + fiat
        exchange = 'itbit'
        time = today_ts()
        date = datetime.now()
        price = r['lastPrice']
        volume = r['volume24h']
        volumeToday = r['volumeToday'] 
        high24h = r['high24h']
        low24h = r['low24h']
        highToday = r['highToday']
        lowToday = r['lowToday']
        openToday = r['openToday']
        vwapToday = r['vwapToday']
        vwap24h = r['vwap24h']
    

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time':time, 'date' : date, 'Close Price' : price, 'Crypto Volume' : volume, 
                    'volumeToday' : volumeToday,  'high24h' : high24h, 'low24h': low24h, 
                    'highToday' : highToday, 'lowToday' : lowToday, 'openToday' : openToday,
                    'vwapToday' : vwapToday, 'vwap24h' : vwap24h }


        

        collection.insert_one(rawdata)

    except :
        
        print('none_itbit')

    return  


#####################################################################################################
################################    BITFLYER    #####################################################
#####################################################################################################

# https://lightning.bitflyer.com/docs?lang=en api actually not working for historical data 



def bitflyer_ticker(Crypto, Fiat, collection):

    asset = Crypto.upper()
    fiat = Fiat.upper()
    entrypoint = 'https://api.bitflyer.com/v1/'
    key = 'getticker?product_code=' + asset + '_' + fiat
    request_url = entrypoint + key

    response = requests.get(request_url)
    response = response.json() 

    try:
        
        r = response
        Pair = asset + fiat
        exchange = 'bitflyer'
        time = today_ts()
        date = datetime.now()
        ticker_time = r['timestamp']
        price = r['ltp']
        volume = r['volume']
        volume_by_product = r['volume_by_product'] 
        best_bid = r['best_bid']
        best_ask = r['best_ask']
        best_bid_size = r['best_bid_size']
        best_ask_size = r['best_ask_size']
        total_bid_depth = r['total_bid_depth']

        

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time':time, 'date' : date, 'ticker_time' : ticker_time, 'Crypto Volume' : volume, 'Close Price': price, 'volume_by_product': volume_by_product, 
                    'best_bid': best_bid,  'best_ask' : best_ask, 'best_bid_size': best_bid_size, 
                    'best_ask_size': best_ask_size, 'total_bid_depth': total_bid_depth}

        
        collection.insert_one(rawdata)        
    except:
        print('none bitflyer')
    

    return 


#####################################################################################################
################################     GEMINI     #####################################################
#####################################################################################################

# returns data just starting from 1 year back


def Gemini_API(Start_Date, End_Date, Crypto, Fiat, time_frame = '1day'):

    if End_Date == None:
        End_Date = datetime.now().strftime('%m-%d-%Y')
   
    df = np.array([])

    header = ['Time', 'low', 'high', 'open', 'Close Price', 'Crypto Volume']

    for asset in Crypto:

        for fiat in Fiat:
            
            entrypoint = 'https://api.gemini.com/v2'
            key = '/candles/'+asset+fiat+'/'+time_frame
            request_url = entrypoint + key

            response = requests.get(request_url)
            sleep(0.25)

            response = response.json()

            if df.size == 0 :

                df = np.array(response)
            else:

                df = np.row_stack((df, response))
                
               
    Gemini_df = pd.DataFrame(df, columns=header)        
    Gemini_df = Gemini_df.drop(columns = ['open', 'high', 'low'])      

    return Gemini_df    

    #####################################################################################################
    ################################ GEMINI - TICKER ####################################################
    #####################################################################################################

def gemini_ticker(Crypto, Fiat, collection):


    asset = Crypto.lower()
    fiat = Fiat.lower()
    entrypoint = 'https://api.gemini.com/v1/pubticker/'
    key = asset + fiat
    request_url = entrypoint + key

    response = requests.get(request_url)
    response = response.json()

    try:
        asset = asset.upper()
        fiat = fiat.upper()
        r = response
        Pair = asset + fiat
        exchange = 'gemini'
        time = today_ts()
        date = datetime.now()
        ticker_time = r['volume']['timestamp']
        price = r['last']
        asset = asset.upper()
        volume = r['volume'][asset]
        bid = r['bid']
        ask = r['ask']
        
        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time': time, 'date' : date, 'ticker_time' : ticker_time, 'Close Price': price, 'Crypto Volume': volume, 'bid': bid,
                    'ask' : ask}
    
        collection.insert_one(rawdata)
    except :
        print('none_gemini')
    
    return
            
            


    # bitstamp_df = pd.DataFrame(response, columns=header)        
    # bitstamp_df = bitstamp_df.drop(columns = ['open', 'high', 'low', 'vwap', 'volume usd'])      




    #####################################################################################################
    ################################    BITSTAMP    #####################################################
    #####################################################################################################

    # https://www.bitstamp.net/api/ api actually not working for historical data 


def bitstamp_ticker(Crypto, Fiat, collection):

    asset = Crypto.lower()
    fiat = Fiat.lower()
    entrypoint = 'https://www.bitstamp.net/api/v2/ticker/'
    key = asset + fiat
    request_url = entrypoint + key

    response = requests.get(request_url)

    

    try:
        response = response.json()
        r = response
        Pair = asset.upper() + fiat.upper()
        exchange = 'bistamp'
        time = today_ts()
        date = datetime.now()
        ticker_time = r['timestamp']
        price = r['last']
        volume = r['volume']
        high = r['high'] 
        low = r['low']
        bid = r['bid']
        ask = r['ask']
        vwap = r['vwap']
        Open = r['open']
        

        rawdata = {'Pair' : Pair, 'Exchange': exchange, 'Time':time, 'date' : date, 'ticker_time' : ticker_time, 'Close Price':price, 'Crypto Volume':volume, 'high':high,
                        'low' : low, 'bid': bid, 'ask':ask, 'vwap': vwap, 'open' : Open}

        
        collection.insert_one(rawdata)  
                
    except:
        print('none_bitstamp')

    return 