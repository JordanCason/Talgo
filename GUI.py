import sys
import main
import time
import threading
from PyQt4 import QtGui, QtCore
from selenium import webdriver
import logging

from random import randrange

from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.chrome.options import Options
from multiprocessing import Process, current_process, Queue, Value, Pipe, Manager

class Window(QtGui.QMainWindow):
    def __init__(self):
        super(Window, self).__init__()
        self.signal_q = Queue()
        self.setGeometry(50, 50, 200, 200)
        self.setWindowTitle("PyQT tuts!")
        self.setWindowIcon(QtGui.QIcon('pythonlogo.png'))
        self.home()

        test = main.trader
        test().start(signal_q=self.signal_q)

    def home(self):
        btn = QtGui.QPushButton("Open TradingView", self)
        btn.clicked.connect(self.open_tradingview)
        btn.resize(btn.minimumSizeHint())
        btn.move(0, 0)
        buy_btn = QtGui.QPushButton("buy", self)
        buy_btn.clicked.connect(self.window_buy)
        buy_btn.resize(buy_btn.minimumSizeHint())
        buy_btn.move(0, 35)
        sell_btn = QtGui.QPushButton("sell", self)
        sell_btn.clicked.connect(self.window_sell)
        sell_btn.resize(sell_btn.minimumSizeHint())
        sell_btn.move(0, 70)
        readpage_btn = QtGui.QPushButton("readpage", self)
        readpage_btn.clicked.connect(self.dump_html)
        readpage_btn.resize(readpage_btn.minimumSizeHint())
        readpage_btn.move(0, 105)
        getalert_btn = QtGui.QPushButton("findalert", self)
        getalert_btn.clicked.connect(self.start_threads)
        getalert_btn.resize(getalert_btn.minimumSizeHint())
        getalert_btn.move(0, 140)
        self.show()

    def open_tradingview(self):
        #self.driver = webdriver.Chrome('/usr/bin/chromedriver')
        #webdriver.Chrome()
        LOGGER.setLevel(logging.WARNING)
        options = webdriver.ChromeOptions()
        options.add_argument("user-data-dir=/tmp/.org.chromium.Chromium.6PgEHU/Default")  # Path to your chrome profile
        self.driver = webdriver.Chrome(executable_path="/usr/bin/chromedriver", chrome_options=options)
        self.driver.get('https://www.tradingview.com/chart/xZlrCJ3o/')

        #search_box = driver.find_element_by_name('q')
        #search_box.send_keys('ChromeDriver')
        #search_box.submit()



    def start_threads(self):
        print('in start therds')
        t1 = threading.Thread(target=self.find_alert,)
        t2 = threading.Thread(target=self.window_refresh,)
        t1.start()
        t2.start()

    def find_alert(self):
        print('Started looking for alerts')
        while True:

            try:
                if self.driver.find_elements_by_class_name("tv-alert-single-notification-dialog__message"):
                    alert = self.driver.find_element_by_class_name("tv-alert-single-notification-dialog__message").text
                if self.driver.find_elements_by_class_name("tv-gopro-dialog__section-header-title"):
                    alert = self.driver.find_element_by_class_name("tv-gopro-dialog__section-header-title-text").text
                if self.driver.find_elements_by_class_name("tv-dialog__title"):
                    alert = self.driver.find_element_by_class_name("tv-dialog__title").text
                if alert == 'buy' or alert == 'sell':
                    print('here')
                    self.signal_q.put(alert)
                    #signal = self.signal_q.get()
                    #print(signal)
                    try:
                        OKbtn = self.driver.find_element_by_class_name("tv-alert-notification-dialog__button--ok")
                        OKbtn.click()
                        alert = None
                    except Exception as e:
                        pass
                if alert == 'keepalive':
                    print('keepalive')
                    try:
                        OKbtn = self.driver.find_element_by_class_name("tv-alert-notification-dialog__button--ok")
                        OKbtn.click()
                        alert = None
                    except Exception as e:
                        pass
                if alert == 'Max devices at the same time':
                    try:
                        OKbtn = self.driver.find_element_by_class_name("i-float_left")
                        OKbtn.click()
                        alert = None
                    except Exception as e:
                        pass
                if alert == 'Alert Notifications':
                    try:
                        OKbtn = self.driver.find_element_by_class_name("js-dialog__close")
                        OKbtn.click()
                        alert = None
                    except Exception as e:
                        pass

                time.sleep(1)
            except Exception as e:
                time.sleep(1)


    def dump_html(self):
        htmlsource = self.driver.page_source
        print(htmlsource)

    def window_buy(self):
        self.signal_q.put('buy')

    def window_sell(self):
        self.signal_q.put('sell')

    def window_refresh(self):
        while True:
            try:
                time.sleep(randrange(1500, 2100))
                print('time to refresh')
                self.driver.refresh()
            except Exception as e:
                print('problem refreshing browser')
                print(e)


    def signal_handler(signal, frame):
        print('Ctrl+C captured')
        logging.info('Ctrl+C captured')
        sys.exit(0)


def run():
    app = QtGui.QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())
run()