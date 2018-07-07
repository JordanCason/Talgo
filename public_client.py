import requests


class PublicClient(object):
    def __init__(self, api_url='https://api.gdax.com'):
        self.url = api_url.rstrip('/')

    def get_products(self):

        r = requests.get(self.url + '/products', timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_product_order_book(self, product_id, level=1):
        params = {'level': level}
        r = requests.get(self.url + '/products/{}/book'
                         .format(product_id), params=params, timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_product_ticker(self, product_id):
        r = requests.get(self.url + '/products/{}/ticker'
                         .format(product_id), timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_product_trades(self, product_id):
        r = requests.get(self.url + '/products/{}/trades'.format(product_id), timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_product_historic_rates(self, product_id, start=None, end=None,
                                   granularity=None):
        params = {}
        if start is not None:
            params['start'] = start
        if end is not None:
            params['end'] = end
        if granularity is not None:
            params['granularity'] = granularity
        r = requests.get(self.url + '/products/{}/candles'
                         .format(product_id), params=params, timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_product_24hr_stats(self, product_id):
        r = requests.get(self.url + '/products/{}/stats'.format(product_id), timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_currencies(self):

        r = requests.get(self.url + '/currencies', timeout=30)
        # r.raise_for_status()
        return r.json()

    def get_time(self):
        r = requests.get(self.url + '/time', timeout=30)
        # r.raise_for_status()
        return r.json()