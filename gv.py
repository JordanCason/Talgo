# global variables for access between threads
# locks should always be used when accessing these variables
global onbooks_limit
global lock                     # thread locking
global _asks                    # full orderbook on the ask side
global _bids                    # full orderbook on the bid side
global logger                   # for program log
global transactions_onbook      # User transactions on the orderbook ie limit orders
global market_price             # current market price
global signal                   # Values are buy and sell
global sql_to_pandas
global profile_id
global crypto_balance
global USD
global Test_USD
global Float_USD
global order_filled
global bidask
global ask_depth
global bid_depth

global place_order