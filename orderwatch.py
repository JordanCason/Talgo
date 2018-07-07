import orderbook
from multiprocessing import Process, current_process, Queue, Value, Manager, Array, Pipe
import threading
import sqlite3
import pandas as pd
from bintrees import RBTree
import logging
import signal
import gv
import authenticated_client
import math
from decimal import Decimal, ROUND_FLOOR
import public_client
import time
import datetime
import datetime as dt
import sys
import ctypes
import csv


from threading import Thread, Lock
import requests


class orderwatch:
    def __init__(self, M_bidask, signal_q, auth_user_msg_q, M_get_depth, products, authclient):
        self._bid = None
        self._ask = None
        self.now = datetime.datetime.now()
        self.start_time = Value('d', 0.0)
        self.request_interval = 0.4
        self.signal_q = signal_q
        self.products = products
        self.product_info = None
        self.authclient = authclient
        self.auth_user_msg_q = auth_user_msg_q  # queue from orderbook when loged in user gets a message on public orderbook
        self.M_get_depth = M_get_depth
        self.M_bidask = M_bidask
        self.lock = Lock()
        self.dictlist = []

    def start_threads(self, M_bidask, auth_user_msg_q, M_get_depth):
        self.account_info()
        self.M_get_depth = M_get_depth
        t1 = Thread(target=self.order, args=(M_bidask,))
        t2 = Thread(target=self.transactions, args=(auth_user_msg_q, M_bidask))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        while True:
            time.sleep(100)

    def start(self):
        time.sleep(10)
        logging.info('start orderwatch')
        print(self.M_get_depth.value)
        p1 = Process(target=self.start_threads, args=(self.M_bidask, self.auth_user_msg_q, self.M_get_depth))
        p1.start()
        #p1.join()

    def account_info(self):
        self.lock.acquire()
        try:
            account_info = self.authclient.getaccounts()
            self.product_info = self.products.split('-')
            if 'message' in account_info:
                if 'Invalid API Key' in account_info['message']:
                    print('Invalid API Key')
                    sys.exit(0)

            for i, entry in enumerate(account_info):
                if entry['currency'] == self.product_info[0]:
                    gv.profile_id = entry['profile_id']
                    print('raw crypto update balance {}'.format(entry['balance']))
                    gv.crypto_balance = Decimal(entry['balance'])
                if entry['currency'] == self.product_info[1]:
                    print('raw USD update balance {}'.format(entry['balance']))
                    gv.USD = Decimal.quantize(Decimal(entry['balance']), Decimal('0.00'), rounding=ROUND_FLOOR)
                
            #if gv.crypto_balance == Decimal(0E-8) or gv.crypto_balance == Decimal(-1E-8) or gv.crypto_balance == Decimal(0E-16):
            #    gv.crypto_balance = Decimal(0.00000000)
            #    print("here")
            print('########### wallet ###########')
            print('####    USD {0:f}          ####'.format(gv.USD)) #0:f
            print('####    ETH {0:f}    ####'.format(Decimal.quantize(Decimal(float(gv.crypto_balance)), Decimal('0.00000000'))))
            print('########### wallet ###########')
        finally:
            self.lock.release()


    def transactions(self, auth_user_msg_q, M_bidask):
        csvfile = open('stats.csv', 'a', newline='')
        csv_writer = csv.writer(csvfile, delimiter=',')
        while True:
            message = auth_user_msg_q.get()
            if 'type' in message:
                if message['type'] == 'open':
                    if len(self.dictlist) is 0:
                        self.dictlist.append([message['time'], message['type'], message['side'], str(self.M_get_depth.value), str(gv.USD), str(gv.crypto_balance), message['remaining_size'], message['price'], message['product_id'], message['order_id']])
                    else:
                        message['type'] = 'move'
                        self.dictlist.append([message['time'], message['type'], message['side'], str(self.M_get_depth.value), str(gv.USD), str(gv.crypto_balance), message['remaining_size'], message['price'], message['product_id'], message['order_id']])
            if 'type' in message:
                if message['type'] == 'match':
                    self.dictlist.append([message['time'], message['type'], message['side'], str(self.M_get_depth.value), str(gv.USD), str(gv.crypto_balance), message['size'], message['price'], message['product_id'], message['maker_order_id']])
            if 'reason' in message:
                if message['reason'] == 'canceled':
                    pass

            if message['type'] == 'match':

                ################################## BUY ##################################

                if message['side'] == 'buy':
                    print('[{}] |buy| Transaction, match made, size {}'.format(self.now.isoformat(), message['size']))



                    if gv.USD == Decimal('0.0'):
                        self.lock.acquire()
                        try:

                            gv.USD = Decimal.quantize(Decimal(((float(gv.USD) / float(M_bidask['bid'])) - float(message['size'])) * float(M_bidask['bid'])), Decimal('0.00'), rounding=ROUND_FLOOR)

                        finally:
                            self.lock.release()
                    print('[{}] |buy| Transaction, Update USD {}'.format(self.now.isoformat(), gv.USD))
                ################################## BUY ##################################
                ################################## sell #################################

                if message['side'] == 'sell':
                    print('[{}] |sell| Transaction, match made, size {}'.format(self.now.isoformat(), message['size']))
                    self.lock.acquire()
                    try:
                        gv.crypto_balance = Decimal.quantize(Decimal(float(gv.crypto_balance) - float(message['size'])), Decimal('0.00000000'), rounding=ROUND_FLOOR)
                    finally:
                        self.lock.release()
                    if gv.crypto_balance == Decimal('0E-8') or gv.crypto_balance == Decimal('-1E-8') or gv.crypto_balance == Decimal('0E-16'):
                        gv.crypto_balance = Decimal('0.00000000')
                ################################## sell #################################

            if 'reason' in message:
                if message['reason'] == 'filled':
                    gv.place_order = False
                    print('[{}] |{}| Order {}'.format(self.now.isoformat(), message['side'], gv.place_order))
                    print('#########################################################################')
                    print('####################                                 ####################')
                    print('####################         Order Complete          ####################')
                    print('####################                                 ####################')
                    print('#########################################################################')
                    self.account_info()
                    self.dictlist.append([message['time'], message['reason'], message['side'], str(self.M_get_depth.value), str(gv.USD),
                                          str(gv.crypto_balance), message['remaining_size'], message['price'],
                                          message['product_id'], message['order_id']])
                    print('########################################################################')
                    print('######################         Order Log          ######################')
                    for d in self.dictlist:
                        print(d)
                        csv_writer.writerow(d)
                    time.sleep(2)
                    print('######################         Order Log          ######################')
                    print('########################################################################')
                    print('[{}] |----| Reset Dict'.format(self.now.isoformat()))
                    self.dictlist = []
                    # how long it took to by in
                    # type: #stats
                    # depth when order what placed
                    # depth left when order done
                    # price streach for that time
                    # effective buy in price
                    # profit loss in $$$
                    # profit percentage

    def order(self, M_bidask):
        gv.place_order = True
        _bid = None
        _ask = None
        signal_data = None
        _signal_data = None
        order_placed = True
        while True:

            if not self.signal_q.empty():
                signal_data = self.signal_q.get()
                bidaskspread = M_bidask
                print('[{}] |start| Signal {}, Current spread {}>{}<{}'.format(self.now.isoformat(), signal_data, bidaskspread['bid'], Decimal.quantize(Decimal(bidaskspread['ask'] - bidaskspread['bid']), Decimal('0.00')), bidaskspread['ask']))
            if not _signal_data == signal_data or not order_placed:                                                     # reset variables on signal switch
                gv.place_order = True                                                                                   # if buy/sell signal switch, set back to false
                print('[{}] |start| Order {}'.format(self.now.isoformat(), gv.place_order))
                _signal_data = signal_data                                                                              # set the cached var to the current signal
                self.account_info()

                if signal_data == 'sell' and gv.crypto_balance <= Decimal('0.01000000'):                                  # check for minimum account balances before placing orders
                    print('[{}] |sell| Not enough crypto to sell, Order stopped'.format(self.now.isoformat()))
                    gv.place_order = False
                    print('[{}] |sell| Order {}'.format(self.now.isoformat(), gv.place_order))
                    self.authclient.cancel_all(product_id=self.products)

                if signal_data == 'buy' and gv.USD <= Decimal('1.00'):
                    print('[{}] |buy| Not enough USD to buy, Order stopped'.format(self.now.isoformat()))
                    gv.place_order = False
                    print('[{}] |buy| Order {}'.format(self.now.isoformat(), gv.place_order))
                    self.authclient.cancel_all(product_id=self.products)

            if signal_data == 'buy' and gv.place_order:
                request_time = time.time()                                                                              # starts a timer for limiting requests to server.
                if request_time - self.start_time.value > self.request_interval:                                        # if the time limit has been reached
                    local_bidask = M_bidask
                    price = Decimal.quantize(Decimal(local_bidask['ask']) - Decimal('0.01'), Decimal('0.00'))           #rounding=ROUND_FLOOR)
                    if not _bid == price:                                                                               # or maybe add if new_queue_var_for_signal_fliped or if the cached _bid and bid don't match than update position on orderbook
                        self.authclient.cancel_all(product_id=self.products)
                        size = str(Decimal.quantize(Decimal(float(gv.USD) / float(price)), Decimal('0.00000000'), rounding=ROUND_FLOOR))
                        #self.M_get_depth.value = 'bid'
                        order_response = self.authclient.buy(product_id=self.products, side='buy', type='limit',
                                                             post_only='post_only', price=str(price), size=str(size))
                        time.sleep(0.05)
                        #self.M_get_depth.value = Decimal.quantize(Decimal(self.M_get_depth.value), Decimal('0.00000000'), rounding=ROUND_FLOOR)
                        print('[{}] |buy| Order Depth {}'.format(self.now.isoformat(), self.M_get_depth.value))
                        if 'order_id' in order_response:
                            gv.order_placed = True
                            print('[{}] |buy| Order {}'.format(self.now.isoformat(), gv.place_order))
                            print('[{}] |buy| Buy Order Placed at {} for {} {} spread {} > {} < {} depth {}'.format(self.now.isoformat(), price, size, self.product_info[0], local_bidask['bid'], Decimal.quantize(Decimal(local_bidask['ask'] - local_bidask['bid']), Decimal('0.00')), local_bidask['ask'],self.M_get_depth.value))
                        if 'message' in order_response:
                            if order_response['message'] == 'Insufficient funds':
                                gv.order_placed = False
                                print('[{}] |buy| Error: Order {}'.format(self.now.isoformat(), gv.place_order))
                                print('[{}] |buy| Error: Insufficient funds'.format(self.now.isoformat()))
                                print('[{}] |buy| Error: Buy Order Placed at {} for {} {} spread {} > {} < {} depth {}'.format(self.now.isoformat(), price, size, self.product_info[0], local_bidask['bid'],
                                                                                                                        Decimal.quantize(Decimal(local_bidask['ask'] - local_bidask['bid']), Decimal('0.00')), local_bidask['ask'],
                                                                                                                        self.M_get_depth.value))
                                print('[{}] |buy| Error: current Values in the wallet USD {}, crypto {}'.format(self.now.isoformat(), gv.USD, gv.crypto_balance))
                                print('[{}] |buy| Error: Manually updating wallet to continue running')
                                self.authclient.cancel_all(product_id=self.products)
                                self.account_info()
                                print('[{}] |buy| Error: New Values in the wallet after the update USD {}, crypto {}'.format(self.now.isoformat(), gv.USD, gv.crypto_balance))
                            if 'size must be greater than' in order_response['message']:
                                gv.order_placed = False
                                print('[{}] |buy| Order {}'.format(self.now.isoformat(), gv.place_order))
                                print('[{}] |buy| {} size posted {}'.format(self.now.isoformat(), order_response, size))
                        print('[{}] |buy| server response, ({})'.format(self.now.isoformat(), order_response))
                        _bid = price                                                                                    # update the cached bid
                    self.start_time.value = time.time()                                                                 # start the timer over for next request

            if signal_data == 'sell' and gv.place_order:
                request_time = time.time()
                if request_time - self.start_time.value > self.request_interval:
                    local_bidask = M_bidask
                    price = Decimal.quantize(Decimal(local_bidask['bid']) + Decimal('0.01'), Decimal('0.00')) #, rounding=ROUND_FLOOR)
                    if not _ask == price:
                        self.authclient.cancel_all(product_id=self.products)
                        size = Decimal.quantize(Decimal(float(gv.crypto_balance)), Decimal('0.00000000'))
                        #self.M_get_depth.value = 'ask'
                        order_response = self.authclient.sell(product_id=self.products, side='sell', type='limit', post_only='post_only',
                                                              price=str(price), size=str(size))
                        time.sleep(0.05)
                        #self.M_get_depth.value = Decimal.quantize(Decimal(self.M_get_depth.value), Decimal('0.00000000'), rounding=ROUND_FLOOR)
                        USD = str(Decimal.quantize(Decimal(float(gv.USD) / float(price)), Decimal('0.00000000'), rounding=ROUND_FLOOR))
                        print('[{}] |sell| Order Depth {}'.format(self.now.isoformat(), self.M_get_depth.value))
                        if 'order_id' in order_response:
                            gv.order_placed = True
                            print('[{}] |sell| Order {}'.format(self.now.isoformat(), gv.place_order))
                            print('[{}] |sell| Sell Order Placed at {} for {} {} spread {}>{}<{} depth {}'.format(self.now.isoformat(), price, USD, self.product_info[1], local_bidask['bid'], Decimal.quantize(Decimal(local_bidask['ask'] - local_bidask['bid']), Decimal('0.00')), local_bidask['ask'], self.M_get_depth.value))
                        if 'message' in order_response:
                            if order_response['message'] == 'Insufficient funds':
                                order_placed = False
                                print('[{}] |sell| Order {}'.format(self.now.isoformat(), gv.place_order))
                                print('[{}] |sell| Insufficient funds')
                            if 'size must be greater than' in order_response['message']:
                                order_placed = False
                                print('[{}] |sell| Order {}'.format(self.now.isoformat(), gv.place_order))
                                print('[{}] |sell| {} size posted {}'.format(self.now.isoformat(), order_response, size))
                        print('[{}] |sell| server response, ({})'.format(self.now.isoformat(), order_response))
                        _ask = price
                    self.start_time.value = time.time()


















































######## old order for buy just incase price stops working after i change local_bidask['bid'] to bid_place_floored

#order_response = self.authclient.buy(product_id=self.products, side='buy', type='limit', post_only='post_only', price=str(bid_place_floored), size=str(Decimal.quantize(Decimal(float(gv.USD) / float(local_bidask['bid'])), Decimal('0.00000000'),  rounding=ROUND_FLOOR)))







#            if 'reason' in message:
#                if message['reason'] == 'filled':
#                    #print(' ')
#                    #print('filled message = ({})'.format(message))
#                    #print('Transaction, USD test,  Order has been ({}), USD = ({}),                ETH = ({}), Order flag set False, price({}), remaining({})'.format(message['reason'], gv.Test_USD, gv.crypto_balance, message['price'], message['remaining_size']))
#                    #print('Transaction, USD Float, Order has been ({}), USD = ({}), ETH = ({}), Order flag set False, price({}), remaining({})'.format(message['reason'], gv.Float_USD, gv.crypto_balance,  message['price'], message['remaining_size']))
#                    #print('Transaction, USD USD,   Order has been ({}), USD = ({}),                ETH = ({}), Order flag set False, price({}), remaining({})'.format(message['reason'], gv.USD, gv.crypto_balance, message['price'], message['remaining_size']))
#                    #print(' ')









# {'message': 'Order size is too small. Minimum size is 0.01'}


# buy and sell on the avrage of open close, buying starts off at small open/close diff while moving up that diff is much larger start to sell when the diff goes back down

                    #    print('signal data {}'.format(signal_data))
                    ########### only for testing REMOVE #########
                    # if gv.place_order == False and signal_data == 'buy':
                    #    signal_data = 'sell'
                    #    gv.place_order = True
                    # if gv.place_order == False and signal_data == 'sell':
                    #    signal_data = 'buy'
                    #    gv.place_order = True
                    ########### only for testing REMOVE #########



#bid_ask_q = Queue()
#signal_q = Queue()
#bid_ask_q.put((5, 10))
#test = orderwatch(bid_ask_q, signal_q)
#test.start()

#print('ETH avalible {}'.format(str(format(float(gv.USD) / float(bid), '.9f'))))
#print('ETH avalible {}'.format(format(str(float(333.564563457456) / float(22.2345234563246))), '.9f'))


                    #if not _bid == Decimal(M_bidask['bid']):  # if the cached _bid and bid don't match than update position on orderbook
                    #    print('{} == {}'.format(type(_bid), type(Decimal(M_bidask['ask']))))
                    #    print('{} == {}'.format(_bid, M_bidask['ask']))
#
                    #    self.authclient.cancel_all(product_id=self.products)  # Cancel all open orders
                    #    local_bidask = M_bidask
#
                    #    print('########################### Start Buy ###########################')
                    #    print('1, bid ask spread {}'.format(local_bidask))
                    #    ################# figure bid placement #################
                    #    bid_place_test = Decimal.quantize(Decimal(local_bidask['ask']) - Decimal(0.01), Decimal('0.00'))  # place bid directly under the ask to try and place first on the orderbook
                    #    bid_place_float = float(float(local_bidask['ask'])) - float(0.01)
                    #    bid_place_Floored = Decimal.quantize(Decimal(local_bidask['ask']) - Decimal(0.01), Decimal('0.00'), rounding=ROUND_FLOOR)
                    #    ################# figure bid placement #################
#
                    #    ################# Post request data #################
                    #    print(' ')
                    #    print('2, Post Request Test    = (price={},     size={})))))'.format(str(bid_place_test), (Decimal.quantize(Decimal(float(gv.USD) / float(local_bidask['bid'])), Decimal('0.00000000')))))
                    #    print('2, Post Request float   = (price={},     size={})))))'.format(str(float(bid_place_float)), (float(gv.USD) / float(local_bidask['bid']))))
                    #    print('2, Post Request floored = (price={},     size={})))))'.format(str(bid_place_Floored), (Decimal.quantize(Decimal(float(gv.USD) / float(local_bidask['bid'])), Decimal('0.00000000'), rounding=ROUND_FLOOR))))
                    #    ################# Post request data #################
                    #    print(' ')
                    #    print('3, Order response {}'.format(self.authclient.buy(product_id=self.products, side='buy', type='limit', post_only='post_only', price=str(bid_place_Floored),
                    #                                                            size=str(Decimal.quantize(Decimal(float(gv.USD) / float(local_bidask['bid'])), Decimal('0.00000000'), rounding=ROUND_FLOOR)))))
                    #    print('4, Post Request Check should be the same as #3 float = (price={}, size={})))))'.format(str(float(bid_place_float)), (float(gv.USD) / float(local_bidask['bid']))))
                    #    print('5, right after buy {}'.format(M_bidask))
                    #    print('########################### End Buy ###########################')
                    #    print('{} = {}'.format(_bid, bid_place_Floored))
                    #    _bid = bid_place_Floored  # update the cached bid
                    #self.start_time.value = time.time()  # start the timer over for next request