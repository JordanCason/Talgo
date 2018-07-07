import json, hmac, hashlib, time, requests, base64
from requests.auth import AuthBase


class CoinbaseExchangeAuth(AuthBase):
    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def __call__(self, request):
        timestamp = str(time.time())
        message = timestamp + request.method + request.path_url + (request.body or '')
        hmac_key = base64.b64decode(self.secret_key)
        signature = hmac.new(hmac_key, message.encode('utf-8'), hashlib.sha256)
        digest = signature.digest()
        signature_b64 = base64.b64encode(digest).decode('utf-8').rstrip('\n')

        request.headers.update({
            'CB-ACCESS-SIGN': signature_b64,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        })
        return request

# Get accounts
def getaccounts():
    r = requests.get(api_url + '/accounts', auth=auth)
    print(r.json())



# Place an order
#  limit orders: A sell order can be filled at the specified price per bitcoin or a higher price per bitcoin
#  and a buy order can be filled at the specified price or a lower price depending on market conditions
def placeorder():
    order = {
        'size': 1.0,  # amount of coins to buy or sell
        'price': 2500,  # price in USD for the coin
        'type': 'limit',  # [Optional] limit, market, or stop
        'side': 'sell',  # buy or sell
        'product_id': 'BTC-USD',
    }
    r = requests.post(api_url + '/orders', json=order, auth=auth)
    print(r.json())

# get a product
def get_product():
    product = {
            "id": "BTC-USD",
            "base_currency": "BTC",
            "quote_currency": "USD",
            "base_min_size": "0.01",
            "base_max_size": "10000.00",
            "quote_increment": "0.01"
        }
    r = requests.get(api_url + '/products', auth=auth)
    print(r.json())

def get_currencies():
    currencies = [{
        "id": "BTC",
        "name": "Bitcoin",
        "min_size": "0.00000001"
    }, {
        "id": "USD",
        "name": "United States Dollar",
        "min_size": "0.01000000"
    }]
    r = requests.post(api_url + '/currencies', json=currencies, auth=auth)
    print(r.json())

def GET_orderbook():
    r = requests.get(api_url + '/products/ETH-USD/book?level=2', auth=auth)
    #parsed = json.loads(r)
    #print(json.dumps(parsed, sort_keys=True))
    pp_json(r.json())

def print_json(json_thing, sort=True, indents=4):
    if type(json_thing) is str:
        print(json.dumps(json.loads(json_thing), sort_keys=sort, indent=indents))
    else:
        print(json.dumps(json_thing, sort_keys=sort, indent=indents))
    return None

auth = CoinbaseExchangeAuth(API_KEY, API_SECRET, API_PASS)
getaccounts()