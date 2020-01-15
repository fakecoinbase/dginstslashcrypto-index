<p align="center">
  <img src="https://dgi.io/img/logo/dgi-logo.svg?raw=true" alt="DGI Logo"/>
</p>


## DGI Crypto-Asset Index

The DGI crypto Index is a volume-weighted index and is composed of the most relevant crypto-assets in terms of liquidity and qualitative criteria. Designed and developed by a heterogeneous group of professionals with significant experience and relevant expertise related to Financial Benchmarks, Crypto–Assets and Financial Industry, the DGI Crypto Index is intended to give to private and institutional investors a replicable tool that best represent and synthesize the Crypto-assets markets.

**Key Features:**

* use volume as a resource for weight computation
* selected exchanges based on security, real-volume and law compliance
* selected constituents on quantitative and qualitative criteria
* designed to be replicable by investors thanks to the buy and hold daily solution.

## Implementation

# Data Download

The software downloads the daily crypto-asset data in terms of trade volume and price of the 8 selected pricing sources that proved to be reliable in matter of real volumes and legal compliance: 



BitFlyer, BitStamp, Bittrex, Coinbase-Pro, Gemini, itBit, Kraken, Pooniex. The Data of these Exchanges are downloaded through the REST API of the website https://cryptowat.ch/ except for itBit's data that are downloaded through the REST API of itBit website.

Is it possible to find the functions in the utils/data_download.py file.

# Data Setup


# Index Computation