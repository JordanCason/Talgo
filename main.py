import time
import sys
from PyQt4 import QtGui, QtCore
import orderbook
import orderwatch
import threading
import sqlite3
import pandas as pd
from bintrees import RBTree
import logging
import signal
import gv  # Global Variables
import authenticated_client
import public_client
import time
import sys
from selenium.webdriver.remote.remote_connection import LOGGER
from multiprocessing import Process, current_process, Queue, Value, Pipe, Manager
import ctypes


##  real account
API_KEY = ''
API_SECRET = ''
API_PASS = ''
API_URL = ''
WSS_URL = ''
products = 'ETH-USD'



class trader:

    def start(self, signal_q):
        authclient = authenticated_client.AuthenticatedClient(key=API_KEY, b64secret=API_SECRET, passphrase=API_PASS, api_url=API_URL)
        logging.basicConfig(filename='websock2.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s')
        lock = threading.Lock()
        gv.lock = threading.Lock()
        gv._asks = RBTree()
        gv._bids = RBTree()
        gv.logger = logging.getLogger(__name__)
        gv.transactions_onbook = []
        gv.market_price = None
        gv.sql_to_pandas = None
        gv.USD = None
        gv.crypto_balance = None
        signal_q = signal_q
        # bid_ask_q = Queue()
        M_get_depth = Queue()
        auth_user_msg_q = Queue()
        manager = Manager()
        M_bidask = manager.dict(({}))
        M_get_depth = manager.Value(ctypes.c_char_p, 'None')
        # print(M_bidask['bid'])



        logging.info('Start of Program')
        order_book = orderbook.OrderBook(API_KEY=API_KEY, API_SECRET=API_SECRET, API_PASS=API_PASS, API_URL=API_URL,
                                         WSS_URL=WSS_URL, products=products, M_bidask=M_bidask, authclient=authclient,
                                         auth_user_msg_q=auth_user_msg_q, M_get_depth=M_get_depth)
        order_book.start()
        print('started orderbook')
        orderwatch2 = orderwatch.orderwatch(M_bidask=M_bidask, signal_q=signal_q,
                                            auth_user_msg_q=auth_user_msg_q, M_get_depth=M_get_depth, products=products, authclient=authclient)
        orderwatch2.start()
        print('started orderwatch')










    #def run():
    #    app = QtGui.QApplication(sys.argv)
    #    GUI = Window()
    #    sys.exit(app.exec_())
    #
    #run()


