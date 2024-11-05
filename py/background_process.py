import threading
import time
import py.file_handler as fh
import py.api as api
import py.trading as trading

threads = []
all_tickers = {}

def fetch_ohlcv_thread():
    global threads
    markets = fh.read_config()['markets']
    for market in markets:
        exchange = market['exchange']
        symbol = market['symbol']
        thread_name = f'Fetch OHLCV | {exchange} - {symbol}'
        if thread_name not in [thread.name for thread in threads]:
            print(f'Starting {thread_name}')
            thread = threading.Thread(name=thread_name, target=api.fetch_ohlcv, args=(exchange, symbol, '500',))
            thread.start()
            threads.append(thread)

def fetch_tickers_thread():
    global threads, all_tickers
    markets = fh.read_config()['markets']
    keys = fh.read_config()['keys']

    exchanges = []
    for market in markets:
        if market['exchange'] not in exchanges:
            exchanges.append(market['exchange'])
    for key in keys:
        if key['exchange'] not in exchanges:
            exchanges.append(key['exchange'])

    for exchange in exchanges:
        thread_name = f'Fetch Tickers | {exchange}'
        if thread_name not in [thread.name for thread in threads]:
            print(f'Starting {thread_name}')
            ticker_thread = threading.Thread(name=thread_name, target=api.fetch_tickers, args=(exchange, all_tickers,))
            ticker_thread.start()
            threads.append(ticker_thread)

def fetch_balance_thread():
    global threads
    keys = fh.read_config()['keys']
    for key in keys:
        exchange = key['exchange']
        api_key = key['key']
        key_name = key['name']
        thread_name = f'Fetch Balances | {exchange} - {api_key}'
        if thread_name not in [thread.name for thread in threads]:
            print(f'Starting {thread_name}')
            ohlcv_thread = threading.Thread(name=thread_name, target=api.fetch_balances, args=(exchange, api_key, key_name))
            ohlcv_thread.start()
            threads.append(ohlcv_thread)

def account_bot_thread():
    global threads
    keys = fh.read_config()['keys']
    for key in keys:
        exchange = key['exchange']
        api_key = key['key']
        thread_name = f'Account Bot | {exchange} - {api_key}'
        if thread_name not in [thread.name for thread in threads]:
            print(f'Starting {thread_name}')
            trading_thread = threading.Thread(name=thread_name, target=trading.account_bot_loop, args=(key,))
            trading_thread.start()
            threads.append(trading_thread)

def threads_control():
    global threads
    while True:
        fetch_ohlcv_thread()
        fetch_tickers_thread()
        fetch_balance_thread()
        #account_bot_thread()

        markets = fh.read_config()['markets']
        exchanges_tickers = []
        exchanges_ohlcvs = []
        for market in markets:
            if market['exchange'] not in exchanges_tickers:
                exchanges_tickers.append(f"Fetch Tickers | {market['exchange']}")
            exchanges_ohlcvs.append(f"Fetch OHLCV | {market['exchange']} - {market['symbol']}")

        if threads:
            for i, thread in enumerate(threads):
                if thread.name in exchanges_tickers or thread.name in exchanges_ohlcvs:
                    continue
                if not thread.is_alive():
                    print(f'Removing dead thread: {thread.name}')
                    threads.pop(i)
        time.sleep(5)

def init():
    #threading.Thread(name="Time Loop", target=time_loop).start()
    threading.Thread(name="Threads Control", target=threads_control).start()
    #api.create_order('bybit', 'TPNoASzaE4U9TN0eVv', 'market', 'BTC/USDT', 'buy', '0.00005', True)