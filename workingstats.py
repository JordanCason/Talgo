import sqlite3
import pandas as pd
import logging
import math
from decimal import Decimal, ROUND_FLOOR
import time
import datetime as dt
import sys
import csv

# sell_trade_time, The time it took to sell currency
# buy_trade_time, the time it took to buy currency
# sell_price_diff, time it took to sell currency
# buy_price_diff, time it took to buy currency


class stats:
    def __init__(self):
        self.statslist = dict()



    def splitlist(self):
        count = 0
        buylist = []
        selllist = []
        with open('statsmatch.csv') as f:
            data = [{k: str(v) for k, v in row.items()} for row in csv.DictReader(f, skipinitialspace=True)]
            print(len(data))
            time.sleep(3)
        while not count == len(data) - 1:
            #print(count)
            buylist = list()
            selllist = list()
            while 'buy' in data[count]['side'] and count < len(data) - 1:
                buylist.append(data[count])
                count = count + 1
                print(data[count])
            while 'sell' in data[count]['side'] and count < len(data) - 1:
                selllist.append(data[count])
                count = count + 1
                print(data[count])
            if len(buylist) is 0 or len(selllist) is 0:  # makes sure we start off stats with a buy signal
                buylist = []
                selllist = []
            else:
                stime = self.start_end(buylist)
                etime = self.start_end(selllist)
                self.statslist.update(stime)
                self.statslist.update(etime)
                bt = self.time_diff(buylist)
                st = self.time_diff(selllist)
                self.statslist.update(bt)
                self.statslist.update(st)
                bp = self.price_diff(buylist)
                sp = self.price_diff(selllist)
                self.statslist.update(bp)
                self.statslist.update(sp)
                #print(self.statslist)
                #time.sleep(3)


    def start_end(self, ordlist):
        d = {}
        if ordlist[0]['type'] == 'open' and ordlist[-1]['type'] == 'filled':
            startime = dt.datetime.strptime(ordlist[-0]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            endtime = dt.datetime.strptime(ordlist[-1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            d = {'{}_start'.format(ordlist[0]['side']): startime.isoformat(), '{}_end'.format(ordlist[0]['side']): endtime.isoformat()}
        return d

    def time_diff(self, ordlist):
        d = {}
        if ordlist[0]['type'] == 'open' and ordlist[-1]['type'] == 'filled':
            startime = dt.datetime.strptime(ordlist[-0]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            endtime = dt.datetime.strptime(ordlist[-1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            trade_time = endtime - startime
            d = {'{}_trade_time'.format(ordlist[0]['side']): str(trade_time)}
        return d

    def price_diff(self, ordlist):
        d = {}
        if ordlist[0]['type'] == 'open' and ordlist[-1]['type'] == 'filled':
            trade_diff = Decimal.quantize(Decimal(ordlist[-1]['price']), Decimal('0.00')) - Decimal.quantize(Decimal(ordlist[0]['price']), Decimal('0.00'))
            d = {'{}_price_diff'.format(ordlist[0]['side']): str(trade_diff)}
        return d

    def affective_price(self):
        """
        This is the price that we have affectively bought into or out of the market
        add up all the matched orders market price and davide by the amount of orders
        """

    def value_USD(self):
        """
        This is the USD value after order has been filled.
        Add up all the matched order sizes and multiply by the affective_price
        """

    def value_crypto(self):
        """
        This is the crypto value after order has been filled.
        Add up all the matched order sizes
        """



        # print(self.statslist)




        #d = {}
        #if ordlist[0]['type'] == 'open' and ordlist[-1]['type'] == 'filled':
        #    print('{}                   {}            {}          {}       {}'.format(ordlist[0]['time'], ordlist[0]['type'], ordlist[0]['crypto'], ordlist[0]['usd'], ordlist[0]['price']))
        #    print('{}                   {}        {}   {}          {}'.format(ordlist[-1]['time'], ordlist[-1]['type'], ordlist[-1]['crypto'], ordlist[-1]['usd'], ordlist[-1]['price']))
        #    startime = dt.datetime.strptime(ordlist[-0]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        #    endtime = dt.datetime.strptime(ordlist[-1]['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
        #    trade_time = endtime - startime
        #    d = {'trade_time': str(trade_time)}
        #time.sleep(3)
        #self.statslist.append(d)
        ## print(self.statslist)

testing = stats()
testing.splitlist()





