from bintrees import RBTree
from decimal import Decimal
#from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException


from multiprocessing import Process, current_process, Lock, Value, Manager, Queue
import pickle
import datetime as dt
import requests
import json
import base64
import hmac
import hashlib
import time
import sqlite3
import signal
import sys
import logging
#import threading
import gv
import authenticated_client
import public_client
import pandas as pd
import os

class OrderBook:

    def __init__(self, API_KEY, API_SECRET, API_PASS, API_URL, WSS_URL, products, M_bidask,
                 auth_user_msg_q, M_get_depth, authclient, message_type="subscribe", auth=True, level=True):
        self.authclient = authclient
        self.WSS_URL = WSS_URL
        self.API_URL = API_URL
        self.products = products
        self.type = message_type
        self.stop = False
        self.ws = None
        self.thread = None
        self.lock = Lock()
        self.auth = auth
        self.API_KEY = API_KEY
        self.API_SECRET = API_SECRET
        self.API_PASS = API_PASS
        self._sequence = -1
        self._bid = None
        self._ask = None
        self._bid_depth = None
        self._ask_depth = None
        self.price = None
        self.level = level
        self.pd_data_set = None
        self.buyop = 0
        self.sellop = 0
        self._bid = None
        self._ask = None
        self.M_bidask = M_bidask
        self.auth_user_msg_q = auth_user_msg_q
        self.M_get_depth = M_get_depth
        self.count01 = 0
        self.manager = Manager()


    def start(self):
        logging.info('start called')
        self.on_open()
        self.process = Process(target=self._go, args=(self.M_bidask, self.M_get_depth))
        self.process.start()

    def _go(self, M_bidask, M_get_depth):
        self.stop = False
        self._sequence = -1
        self.M_get_depth = M_get_depth
        self._connect()
        self._listen(M_bidask)


    def _connect(self):
        logging.info('_connect called')
        if self.WSS_URL[-1] == "/":
            self.WSS_URL = self.WSS_URL[:-1]  # If url ends in a "/" strip it
        sub_params = {'type': 'subscribe', 'product_ids': [self.products]}
        if self.auth:
            timestamp = str(time.time())
            message = timestamp + 'GET' + '/users/self'
            message = message.encode('ascii')
            hmac_key = base64.b64decode(self.API_SECRET)
            signature = hmac.new(hmac_key, message, hashlib.sha256)
            digest = signature.digest()
            signature_b64 = base64.b64encode(digest).decode('utf-8').rstrip('\n')
            sub_params['signature'] = signature_b64
            sub_params['key'] = self.API_KEY
            sub_params['passphrase'] = self.API_PASS
            sub_params['timestamp'] = timestamp
        self.ws = create_connection(self.WSS_URL)
        self.ws.send(json.dumps(sub_params))

        if self.level:
            sub_params = {"type": "subscribe", "product_ids": [self.products], "channels": ["matches"]}
            self.ws.send(json.dumps(sub_params))

    def _listen(self, M_bidask):
        self.M_bidask2 = M_bidask  # setting self.p1_w2 within this process so as to not confuse with self.p1_w. they are the came Pipe object
        logging.info('_listen called')
        while not self.stop:
            try:
                msg = self.ws.recv()
            except Exception as e:

                print('exception 1')
                gv.logger.exception(e)
                gv.logger.info('sleeping for 5 seconds and running _connect()')
                self.close()
                time.sleep(5)
                self._go(self.M_bidask, self.M_get_depth)
            else:
                if msg:
                    msg = json.loads(msg)
                    self.on_message(msg)

    def on_message(self, message):
        try:
            if 'user_id' in message:
                self.auth_user_msg_q.put(message)
            if 'sequence' not in message:
                return
            sequence = message['sequence']
            if self._sequence == -1:
                self._asks = RBTree()
                self._bids = RBTree()
                res = self.get_product_order_book(level=3)
                for bid in res['bids']:
                    self.add({
                        'id': bid[2],
                        'side': 'buy',
                        'price': Decimal(bid[0]),
                        'size': Decimal(bid[1])
                    })
                for ask in res['asks']:
                    self.add({
                        'id': ask[2],
                        'side': 'sell',
                        'price': Decimal(ask[0]),
                        'size': Decimal(ask[1])
                    })
                self._sequence = res['sequence']

            if sequence <= self._sequence:
                # ignore older messages (e.g. before order book initialization from getProductOrderBook)
                return
            elif sequence > self._sequence + 1:
                print('Error: messages missing ({} - {}). Re-initializing websocket.'.format(sequence, self._sequence))
                self.close()
                time.sleep(5)
                self._go(self.M_bidask, self.M_get_depth)
                return



            msg_type = message['type']
            if msg_type == 'open':
                self.add(message)
            elif msg_type == 'done' and 'price' in message:
                self.remove(message)
            elif msg_type == 'match':
                self.match(message)
            elif msg_type == 'change':
                self.change(message)
            self._sequence = sequence

            bid = self.get_bid()  # Update Multiprocessing.Value variables with the new bid and ask
            ask = self.get_ask()
            if self.M_get_depth.value == 'bid':
                bids = self.get_bids(bid)
                bid_depth = sum([b['size'] for b in bids])
                self.M_get_depth.value = bid_depth
            if self.M_get_depth.value == 'ask':
                asks = self.get_asks(ask)
                ask_depth = sum([a['size'] for a in asks])
                self.M_get_depth.value = ask_depth

            if not self._bid == bid or not self._ask == ask:
                # lock these vars
                self.M_bidask2['bid'] = float(bid)
                self.M_bidask2['ask'] = float(ask)
                self._bid = bid
                self._ask = ask

        except Exception as e:
            print(e)
            print('exception 2')
            gv.logger.exception(e)
            self.close()
            time.sleep(5)
            self._go(self.M_bidask, self.M_get_depth)


        # bids = self.get_bids(bid)
        # bid_depth = sum([b['size'] for b in bids])
        # asks = self.get_asks(ask)
        # ask_depth = sum([a['size'] for a in asks])
        # print('bid: %f @ %f - ask: %f @ %f' % (bid_depth, bid, ask_depth, ask))

    def on_error(self, e):
        self._sequence.value = -1
        print('on_error called')
        self.close()
        self._go(self.M_bidask, self.M_get_depth)

    def close(self):
        logging.info('close called')
        if not self.stop:

            print('in not self.stop')
            self.on_close()
            self.stop = True
            #self.process.join()
            try:
                if self.ws:
                    print('if self.ws')
                    self.ws.close()
            except WebSocketConnectionClosedException as e:
                gv.logger.debug(e)

    def add(self, order):
        order = {
            'id': order.get('order_id') or order['id'],
            'side': order['side'],
            'price': Decimal(order['price']),
            'size': Decimal(order.get('size') or order['remaining_size'])
        }
        if order['side'] == 'buy':
            bids = self.get_bids(order['price'])
            if bids is None:
                bids = [order]
            else:
                bids.append(order)
            self.set_bids(order['price'], bids)
        else:
            asks = self.get_asks(order['price'])
            if asks is None:
                asks = [order]
            else:
                asks.append(order)
            self.set_asks(order['price'], asks)

    def remove(self, order):                                                  # order is the instance of one message receded from the websockit
        price = Decimal(order['price'])                                       # get the price from the order and saves it as a decimal in variable price
        if order['side'] == 'buy':                                            # if its a buy order continue
            bids = self.get_bids(price)                                       # returns all the bids at specified (price) from orderbook, geting ready to compare with current order.
            if bids is not None:                                              # bids being None does not happen often
                bidslist = [o for o in bids if o['id'] != order['order_id']]  # creates a list minus the current order to be removed
                if len(bidslist) > 0:                                         # when bidslist still contains items in its list send list and price to set_bids
                    self.set_bids(price, bidslist)
                else:
                    self.remove_bids(price)                                   # when bidslist returns nothing in its list send price to remove_bids(price) to be removed from orderbook.
        else:
            asks = self.get_asks(price)                                       # same as the first part of this function except on the ask side
            if asks is not None:
                asks = [o for o in asks if o['id'] != order['order_id']]
                if len(asks) > 0:
                    self.set_asks(price, asks)
                else:
                    self.remove_asks(price)

                                                                # An order was matched so it needs to be removed from our orderbook \
                                                                # and keep the remaining
    def match(self, order):                                     # order is the instance of one message receded from the websockit
        size = Decimal(order['size'])                           # order size how many ETH or BTC etc..
        price = Decimal(order['price'])
        if order['side'] == 'buy':                              # if the order is a buy order \
            bids = self.get_bids(price)                         # returns all the bids at specified (price) from orderbook \
            if not bids:                                        # if there are no orders at this price on the bid/buy side than just return
                return
            assert bids[0]['id'] == order['maker_order_id']     # if condition returns False trigger an error
                                                                # this is taking the trade id of the order on our orderbook and comparing \
                                                                # it to the market makers order id to varify the data.
                                                                # this should always return True if it returns false are market data \
                                                                # we have saved is incorrect
            if bids[0]['size'] == size:                         # The first order on our books at this pirce is bids[0] and if the size \
                                                                # of that order matches the incoming match order then we need to remove \
                                                                # the order from our books at this price
                                                                # we use bids[0] because the market works on a first come first serve \
                                                                # and bids[0] has been here the longest
                self.set_bids(price, bids[1:])                  # excludes the first order in the list and sets the remaining \
                                                                # back in the orderbook list
            else:
                bids[0]['size'] -= size                         # subtract size of current trade from the position held on the orderbook "bids[0]"
                self.set_bids(price, bids)
        else:                                                   # same as above for the match function but on the ask/sell side
            asks = self.get_asks(price)
            if not asks:
                return
            assert asks[0]['id'] == order['maker_order_id']
            if asks[0]['size'] == size:
                self.set_asks(price, asks[1:])
            else:
                asks[0]['size'] -= size
                self.set_asks(price, asks)

    def change(self, order):
        try:
            new_size = Decimal(order['new_size'])
        except KeyError as e:
            gv.logger.debug(e)
            return
        price = Decimal(order['price'])
        if order['side'] == 'buy':
            bids = self.get_bids(price)
            if bids is None or not any(o['id'] == order['order_id'] for o in bids):
                return
            index = [b['id'] for b in bids].index(order['order_id'])
            bids[index]['size'] = new_size
            self.set_bids(price, bids)
        else:
            asks = self.get_asks(price)
            if asks is None or not any(o['id'] == order['order_id'] for o in asks):
                return
            index = [a['id'] for a in asks].index(order['order_id'])
            asks[index]['size'] = new_size
            self.set_asks(price, asks)
        tree = self._asks if order['side'] == 'sell' else self._bids
        node = tree.get(price)
        if node is None or not any(o['id'] == order['order_id'] for o in node):
            return

    def get_ask(self):
        return self._asks.min_key()

    def get_asks(self, price):
        return self._asks.get(price)

    def remove_asks(self, price):
        self._asks.remove(price)

    def set_asks(self, price, asks):
        self._asks.insert(price, asks)

    def get_bid(self):
        return self._bids.max_key()

    def get_bids(self, price):
        return self._bids.get(price)

    def remove_bids(self, price):
        self._bids.remove(price)

    def set_bids(self, price, bids):
        self._bids.insert(price, bids)

    # _bids is the is the binary data structure of the entire buy side of the overbook
    # this function is returning every order from the buy side with a specific price
    # get is a funcntion of an RBTree data structure

    def get_product_order_book(self, level):
        params = {'level': level}
        r = requests.get(self.API_URL + '/products/{}/book'.format(self.products), params=params, timeout=30)
        return r.json()

    def on_open(self):
        print("-- Subscribed! --\n")

    def on_close(self):
        print("\n-- Socket Closed --")

    def bid_ask_spread(self):
        lock.acquire()
        try:
            bid = self.get_bid()
            ask = self.get_ask()
            print((bid - ask) * -1)
        except Exception as e:
            gv.logger.debug(e)
        finally:
            lock.release()

    #def bid_ask(self):
    #    try:
    #        bid = self.get_bid()
    #        bids = self.get_bids(bid)
    #        ask = self.get_ask()
    #        asks = self.get_asks(ask)
#
    #        bid_depth = sum([b['size'] for b in bids])              # If there are no changes to the bid-ask spread \
    #        ask_depth = sum([a['size'] for a in asks])              # since the last update, no need to print
#
    #                                                                # if we end up logging a type error we may need to \
    #                                                                # lock the rbtree(_bid and _ask)
    #        if gv._bid == bid and gv._ask == ask and self._bid_depth == bid_depth and self._ask_depth == ask_depth:
    #            pass
    #        else:                                                   # If there are differences, update the cache
    #            gv._bid = bid
    #            gv._ask = ask
    #            self._bid_depth = bid_depth
    #            self._ask_depth = ask_depth
    #            print('{}\tbid: {:.3f} @ {:.2f}\task: {:.3f} @ {:.2f}'.format(dt.datetime.now(), bid_depth, bid, ask_depth, ask))
    #    except Exception as e:
    #        gv.logger.debug(e)

    def user_orders_on_book(self):
        self.lock.acquire()
        try:
            print('user orders on book {}'.format(gv.transactions_onbook))
        finally:
            self.lock.release()

    def test2(self):
        return 'test'



    def market_price(self):
        self.lock.acquire()
        try:
            if gv.market_price is not None:
                print('match {}'.format(gv.market_price))
                pass

        finally:
            self.lock.release()










  #df = df.set_index('index', inplace=True)
            #df['time'] = pd.to_datetime(df['time'])
            ##df.set_index('time', inplace=True)
            #df['price'] = pd.to_numeric(df['price'])
            #print('price {}'.format(message['price']))
            #d1 = gv.sql_to_pandas
            #d2 = gv.sql_to_pandas
            #df.reset_index(inplace=True)
            #gv.sql_to_pandas.reset_index(inplace=True)
            #print(df)
#
            #print(gv.sql_to_pandas)




        #Exception in thread Thread-1:
        #Traceback (most recent call last):
        #  File "/usr/lib/python3.5/threading.py", line 914, in _bootstrap_inner
        #    self.run()
        #  File "/usr/lib/python3.5/threading.py", line 862, in run
        #    self._target(*self._args, **self._kwargs)
        #  File "/home/nonya/PycharmProjects/gdax/reorg/orderbook.py", line 59, in _go
        #    self._listen()
        #  File "/home/nonya/PycharmProjects/gdax/reorg/orderbook.py", line 102, in _listen
        #    self.on_message(msg)
        #  File "/home/nonya/PycharmProjects/gdax/reorg/orderbook.py", line 169, in on_message
        #    self._listen()
        #  File "/home/nonya/PycharmProjects/gdax/reorg/orderbook.py", line 102, in _listen
        #    self.on_message(msg)
        #  File "/home/nonya/PycharmProjects/gdax/reorg/orderbook.py", line 194, in on_message
        #    self.match(message)                             # The match function should check for the remaining bid or asks and, \
        #  File "/home/nonya/PycharmProjects/gdax/reorg/orderbook.py", line 285, in match
        #    assert bids[0]['id'] == order['maker_order_id']     # if condition returns False trigger an error
        #AssertionError
