import ccxt
import os
import json
import pandas as pd
import numpy as np
import time
import py.file_handler as fh
import py.misc as misc
import threading

lock = threading.Lock()

def fetch_markets():
    path = "data_storage"
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, "all_markets.json")

    symbols = []
    new_markets = {}
    exchanges = ccxt.exchanges
    for exchange_name in exchanges:
        exchange = getattr(ccxt, exchange_name)()
        try:
            markets = exchange.fetch_markets()
            print(f'Fetched markets successfully from {exchange_name}')
        except Exception as e:
            print(f'Could not fetch markets from {exchange_name}: {e}')
        
        for market in markets:
            symbols.append(market['symbol'])

        # Add symbols for the exchange to the new_markets dictionary
        new_markets[exchange_name] = [market['symbol'] for market in markets]

    with open(file_path, "w") as f:
        json.dump(new_markets, f, indent=4)


def fetch_ohlcv(exchange_id, symbol, limit=None):
    market = fh.sanitize_file_name(symbol)
    path = os.path.join('data_storage', exchange_id, market, 'ohlcv')
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, "1min.csv")
    file_path_open = os.path.join(path, "open_candle.json")

    api_key = None
    api_secret = None
    exchange = getattr(ccxt, exchange_id)({
        'apiKey': api_key,
        'secret': api_secret,
    })

    last_minute = 0
    current_minute = int(time.time() // 60)

    while True:
        current_minute = int(time.time() // 60)
        if current_minute != last_minute:
            last_minute = current_minute

            default_limit = 200
            if limit is None:
                limit = default_limit

            since = int(misc.unix_time_in_seconds(fh.read_config()['ohlcv']) * 1000)

            try:
                existing_data = pd.read_csv(file_path)
            except FileNotFoundError:
                # If the file doesn't exist, create it with an empty DataFrame
                existing_data = pd.DataFrame()
                existing_data.to_csv(file_path, index=False)

            if existing_data.size > 0:
                start_fresh = False
                since = int(existing_data['timestamp'].max() + 60000)
            else:
                start_fresh = True

            headers = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            data_buffer = []
            data_buffer_limit = 10000
            counter = 0
            while True:
                try: 
                    start_time = time.time()
                    fetch_end = int((time.time() * 1000) // 60000) * 60000 - 60000 # Last closed 1-min candle
                    ohlcv_data = exchange.fetch_ohlcv(symbol, '1m', int(since), int(limit))
                    end_time = time.time()
                    elapsed_time = end_time - start_time
                    elapsed_time_formatted = "{:.2f}".format(elapsed_time) 
                    print(f'Fetched OHLCVs for {exchange_id} | {symbol} ({elapsed_time_formatted}s)')
                    data_buffer.extend(ohlcv_data)
                    counter += len(ohlcv_data)

                    last_point = ohlcv_data[-1][0]
                    next_since = last_point + 60000

                    if start_fresh:
                        first_point = ohlcv_data[0][0]
                        if first_point > since:
                            markets = fh.read_config('markets')
                            for i in range(len(markets)):
                                if markets[i]['exchange'] == exchange_id and markets[i]['symbol'] == symbol:
                                    markets[i]['since'] = since
                            fh.edit_config('markets', markets)
                        df = pd.DataFrame(data_buffer, columns=headers)
                        df.to_csv(file_path, index=False)

                        data_buffer = []
                        counter = 0
                        start_fresh = False

                    if counter >= data_buffer_limit or last_point >= fetch_end:
                        while data_buffer[-1][0] > fetch_end:
                            try: 
                                with open(file_path_open, 'r') as f:
                                    open_candle = json.load(f)

                                    open_df = [data_buffer[-1]]
                                    open_df = pd.DataFrame(open_df, columns=headers)
                                    #open_df.index = ['1min']
                                    open_candle['1min'] = open_df.to_dict(orient='records')[0]
                                    data_buffer.pop()

                                with lock:
                                    with open(file_path_open, 'w') as f:
                                        json.dump(open_candle, f, indent=4)
                            except:
                                open_df = [data_buffer[-1]]
                                open_df = pd.DataFrame(open_df, columns=headers)
                                open_df.index = ['1min']
                                open_df.to_json(file_path_open, orient='index', indent=4)
                                data_buffer.pop()

                        df = pd.DataFrame(data_buffer)
                        with open(file_path, 'a', newline='') as f:
                            df.to_csv(f, header=False, index=False)

                        data_buffer = []
                        counter = 0

                    if next_since > fetch_end:
                        one_min_to_timeframes(path, file_path)
                        break

                    since = next_since

                except Exception as e:
                    print('Fetch OHLCV', exchange_id, f"{symbol}: Unable to get OHCLV data. Retrying later.")
                    print('Fetch OHLCV', exchange_id, f"{e}")
                    break
        time.sleep(1)

def one_min_to_timeframes(path, file_path):
    timeframes = ['2min', '3min', '5min', '10min', '15min', '20min', '30min', '1h', '2h', '3h', '4h', '6h', '8h', '12h', '1D', '2D', '3D']
    df_1min = pd.read_csv(file_path)
    df_1min_begin = int(df_1min['timestamp'].min())
    df_1min['timestamp'] = pd.to_datetime(df_1min['timestamp'], unit='ms')
    df_1min.set_index('timestamp', inplace=True)

    open_candle_file_path = os.path.join(path, 'open_candle.json')
    try:
        with lock:
            with open(open_candle_file_path, 'r') as f:
                open_candle = json.load(f)
    except FileNotFoundError:
        open_candle = {}

    for timeframe in timeframes:
        first_timestamp = 0
        last_timestamp = 0
        closed_data_file_path = os.path.join(path, timeframe + '.csv')
        try:
            closed_data = pd.read_csv(closed_data_file_path)
            if closed_data.size != 0:
                first_timestamp = int(closed_data['timestamp'].min())
                last_timestamp = int(closed_data['timestamp'].max())
        except:
            closed_data = pd.DataFrame()

        timeframe_delta = pd.to_timedelta(timeframe)
        multiplier = timeframe_delta.total_seconds() // 60
        timeframe_begin = int(df_1min_begin + (multiplier * 60000))

        if first_timestamp != timeframe_begin:
            resampled_df = df_1min.resample(timeframe, label='right').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
            resampled_df['resampled_time'] = resampled_df.index
            resampled_df['timestamp'] = resampled_df['resampled_time'].astype(np.int64) // 1000000
            resampled_df = resampled_df.drop('resampled_time', axis=1)
            resampled_df.set_index('timestamp', inplace=True)
            open_df = resampled_df.iloc[-1:].reset_index()
            resampled_df = resampled_df.iloc[:-1]

            os.makedirs(path, exist_ok=True)
            resampled_df.to_csv(closed_data_file_path)
            open_candle[timeframe] = open_df.to_dict(orient='records')[0]

        else:
            new_data_df = df_1min[(df_1min.index.astype(np.int64) // 1000000) >= last_timestamp]

            resampled_df = new_data_df.resample(timeframe, label='right').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'})
            resampled_df['resampled_time'] = resampled_df.index
            resampled_df['timestamp'] = resampled_df['resampled_time'].astype(np.int64) // 1000000
            resampled_df = resampled_df.drop('resampled_time', axis=1)
            resampled_df.set_index('timestamp', inplace=True)
            open_df = resampled_df.iloc[-1:].reset_index()
            resampled_df = resampled_df.iloc[:-1]

            os.makedirs(path, exist_ok=True) 
            resampled_df.to_csv(closed_data_file_path, mode='a', header=False)
            open_candle[timeframe] = open_df.to_dict(orient='records')[0]
        
    with lock:
        with open(open_candle_file_path, 'w') as f:
            json.dump(open_candle, f, indent=4)

def fetch_tickers(exchange_id):
    api_key = None
    api_secret = None
    exchange = getattr(ccxt, exchange_id)({
        'apiKey': api_key,
        'secret': api_secret,
    })

    path = os.path.join('data_storage', exchange_id)

    while True:
        config = fh.read_config()
        markets = config['markets']
        exchange_markets = []
        for market in markets:
            if market['exchange'] == exchange_id:
                exchange_markets.append(market['symbol'])

        try:
            start_time = time.time()
            tickers = exchange.fetch_tickers()

            for ticker_symbol, ticker_data in tickers.items():
                if ticker_symbol in exchange_markets:
                    sanitized_symbol = fh.sanitize_file_name(ticker_symbol)
                    ohlcv_path = os.path.join(path, sanitized_symbol, 'ohlcv')
                    open_candle = fh.read_json(ohlcv_path, 'open_candle.json')

                    for item in open_candle:
                        high = open_candle[item]['high']
                        low = open_candle[item]['low']
                        last = ticker_data['last']
                        if last > high:
                            open_candle[item]['high'] = last
                        if last < low:
                            open_candle[item]['low'] = last
                        open_candle[item]['close'] = last
                        
                    with lock:
                        with open(os.path.join(ohlcv_path, 'open_candle.json'), 'w') as f:
                            json.dump(open_candle, f, indent=4)
                
            end_time = time.time()
            elapsed_time = end_time - start_time
            elapsed_time_formatted = "{:.2f}".format(elapsed_time) 
            print(f'Fetched tickers from {exchange_id} ({elapsed_time_formatted}s)')

        except Exception as e:
            print(f'Fetch Tickers, {exchange_id}: Unable to fetch ticker data. Retrying later.')
            print(f'Fetch Tickers, {exchange_id}: {e}')
        time.sleep(2)