import threading
import time
import py.file_handler as fh
import py.api as api

threads = []

def init():
    threading.Thread(name="Time Loop", target=time_loop).start()
    threading.Thread(name="Check Threads", target=check_threads).start()

def time_loop():
    global threads

    last_second = 0
    last_ten_second = 0
    last_minute = 0
    last_five_minute = 0
    last_day = 0
    while True:
        current_second = int(time.time())
        current_ten_second = int(time.time() / 10)
        current_minute = int(time.time() / 60)
        current_five_minute = int(time.time() / 60 / 5)
        current_day = int(time.time() / 60 / 60 / 24)

        if last_second != current_second:
            last_second = current_second
            fetch_tickers_thread()

        if last_ten_second != current_ten_second:
            last_ten_second = current_ten_second

        if last_minute != current_minute:
            last_minute = current_minute
            fetch_ohlcv_thread()
        
        if last_five_minute != current_five_minute:
            last_five_minute = current_five_minute
        
        if last_day != current_day:
            last_day = current_day
            #markets_thread = threading.Thread(name="Fetch Markets", target=api.fetch_markets)
            #markets_thread.start()
            #threads.append(markets_thread)
            
        time.sleep(0.2)

def fetch_ohlcv_thread():
    global threads
    markets = fh.read_config()['markets']
    for market in markets:
        exchange = market['exchange']
        symbol = market['symbol']
        thread_name = f'Fetch OHLCV | {exchange} - {symbol}'
        if thread_name not in [thread.name for thread in threads]:
            print(f'Starting {thread_name}')
            ohlcv_thread = threading.Thread(name=thread_name, target=api.fetch_ohlcv, args=(exchange, symbol, '500',))
            ohlcv_thread.start()
            threads.append(ohlcv_thread)

def fetch_tickers_thread():
    global threads
    markets = fh.read_config()['markets']
    #keys = fh.read_config()['keys']

    exchanges = []
    for market in markets:
        if market['exchange'] not in exchanges:
            exchanges.append(market['exchange'])
    #for key in keys:
    #    if key['exchange'] not in exchanges:
    #        exchanges.append(key['exchange'])

    for exchange in exchanges:
        thread_name = f'Fetch Tickers | {exchange}'
        if thread_name not in [thread.name for thread in threads]:
            print(f'Starting {thread_name}')
            ticker_thread = threading.Thread(name=thread_name, target=api.fetch_tickers, args=(exchange,))
            ticker_thread.start()
            threads.append(ticker_thread)

def check_threads():
    global threads
    while True:
        markets = fh.read_config()['markets']
        exchanges_tickers = []
        exchanges_ohlcvs = []
        for market in markets:
            if market['exchange'] not in exchanges_tickers:
                exchanges_tickers.append(f"Fetch Tickers | {market['exchange']}")
            exchanges_ohlcvs.append(f"Fetch OHLCV | {market['exchange']} - {market['symbol']}")

        while threads:
            for i, thread in enumerate(threads):
                if thread.name in exchanges_tickers or thread.name in exchanges_ohlcvs:
                    continue
                if not thread.is_alive():
                    print(f'Removing dead thread: {thread.name}')
                    threads.pop(i)
            time.sleep(10)