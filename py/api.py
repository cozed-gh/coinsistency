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
exchange_tickers = {}

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

    default_limit = 200
    if limit is None:
        limit = default_limit

    while True:
        since = int(misc.unix_time_in_seconds(fh.read_config()['ohlcv']) * 1000)
        fetch_end = int((time.time() // 60)) * 60000 # Previous closed 1-min candle
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
        
        while True and since < fetch_end:
            try: 
                start_time = time.time()
                fetch_end = int((time.time() // 60)) * 60000 # Previous closed 1-min candle
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
                    while data_buffer[-1][0] >= fetch_end:
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

                if next_since >= fetch_end:
                    one_min_to_timeframes(path, file_path)
                    break

                since = next_since

            except Exception as e:
                print('Fetch OHLCV', exchange_id, f"{symbol}: Unable to get OHCLV data. Retrying later.")
                print('Fetch OHLCV', exchange_id, f"{e}")
                break
            time.sleep(0.25)    
        time.sleep(15)

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
        markets = fh.read_config()['markets']
        exchange_markets = []
        for market in markets:
            if market['exchange'] == exchange_id:
                exchange_markets.append(market['symbol'])
        
        keys = fh.read_config()['keys']
        exchange_assets = []
        for key in keys:
            if key['exchange'] == exchange_id:
                key_id = key['key']
                key_name = key['name']
                try:
                    account_file = f'{key_name}_{key_id}_balances.json'
                    path = os.path.join('data_storage', exchange_id, 'accounts')
                    file_path = os.path.join(path, account_file)
                    with open(file_path, 'r') as f:
                        exchange_assets = json.load(f)
                except:
                    return

        try:
            start_time = time.time()
            stables = ['USDT', 'USDC', 'USDT:USDT']
            tickers = exchange.fetch_tickers()
            exchange_tickers[exchange_id] = tickers

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

                if len(exchange_assets) > 0:
                    base, quote = ticker_symbol.split("/")
                    if base in exchange_assets and quote in stables:
                        exchange_assets[base]['usd_value'] = ticker_data['last'] * exchange_assets[base]['amount']

                    for stable in stables:
                        if stable in exchange_assets:
                            exchange_assets[stable]['usd_value'] = exchange_assets[stable]['amount']
                            with open(file_path, 'w') as f:
                                json.dump(exchange_assets, f, indent=4)
                
            end_time = time.time()
            elapsed_time = end_time - start_time
            elapsed_time_formatted = "{:.2f}".format(elapsed_time) 
            print(f'Fetched tickers from {exchange_id} ({elapsed_time_formatted}s)')

        except Exception as e:
            print(f'Fetch Tickers, {exchange_id}: Unable to fetch ticker data. Retrying later.')
            print(f'Fetch Tickers, {exchange_id}: {e}')
        time.sleep(1)

def fetch_balances(exchange_id, api_key, name):
    api_secret = None
    keys = fh.read_config()['keys']
    for key in keys:
        if key['key'] in api_key:
            api_secret = key['secret']
    exchange = getattr(ccxt, exchange_id)({
        'apiKey': api_key,
        'secret': api_secret,
    })

    account_file = f'{name}_{api_key}_balances.json'
    path = os.path.join('data_storage', exchange_id, 'accounts')
    file_path = os.path.join(path, account_file)

    while True:
        try:
            balances = exchange.fetch_balance()
            balances = balances['total']
            user_assets = {}
            for item in balances:
                asset = item
                amount = balances[item]
                user_assets[asset] = {'amount': amount}
            os.makedirs(path, exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(user_assets, f, indent=4)
        except Exception as e:
            print(f'Fetch Balances ERROR: {e}')
        
        time.sleep(10)

def create_order(api_key, type, symbol, side, amount, new_position, position_set=None):
    keys = fh.read_config()['keys']
    api_secret = None
    for key in keys:
        if api_key == key['key']:
            api_secret = key['secret']
            exchange_id = key['exchange']

    if not api_key or not api_secret:
        print(f'Cannot find "{api_key}" in your list of keys')
        return
    
    exchange = getattr(ccxt, exchange_id)({
        'apiKey': api_key,
        'secret': api_secret,
        'defaultType': 'spot'
    })

    params = {}

    try:
        order = exchange.create_order(symbol, type, side, amount, params=params)
        order_id = order['id']
        since = int(time.time() - (60 * 60 * 4)) * 1000

        order_details = fetch_order(exchange, order_id, symbol, since)

        file_name = f"{key['name']}_{key['key']}_orders.json"
        path = os.path.join('data_storage', key['exchange'], 'accounts')
        file_path = os.path.join(path, file_name)
        os.makedirs(path, exist_ok=True)
        try:
            with open(file_path, 'r+') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []

                data.append(order_details)
                f.seek(0)
                json.dump(data, f, indent=4)
                f.truncate()

                # Handle positions - Create a new position or alter an existing
                file_name = f"{key['name']}_{key['key']}_orders.json"
                path = os.path.join('data_storage', key['exchange'], 'accounts')
                file_path = os.path.join(path, file_name)
                os.makedirs(path, exist_ok=True)

                if new_position:
                    risk = 1
                    if position_set != None:
                        stoploss = position_set['stoploss']
                        risk = abs(stoploss - order_details['price']) / order_details['price']
                    position_details = {
                        'id': order_details['id'],
                        'timestamp': order_details['timestamp'],
                        'datetime': order_details['datetime'],
                        'symbol': order_details['symbol'],
                        'side': order_details['side'],
                        'entry': order_details['price'],
                        'amount': order_details['amount'],
                        'cost': order_details['cost'],
                        'fees': order_details['fees']
                    }
                    try:
                        with open(file_path, 'r+') as f:
                            try:
                                position = json.load(f)
                            except json.JSONDecodeError:
                                position = []
                    except Exception as e:
                        print(f"POSITION | Error appending to file: {e}")


        except Exception as e:
            print(f"ORDER | Error appending to file: {e}")

    except Exception as e:
        print(f"Error placing order: {e}")


def fetch_order(exchange, order_id, symbol, since):
    max_retries = 100
    tries = 0
    order_details = {}
    while True:
        tries += 1
        orders = exchange.fetch_canceled_and_closed_orders(symbol, since)
        for order in orders:
            if order['id'] == order_id:
                excluded_items = ['info', 'fees', 'trades']
                order_details = { key: value for key, value in order.items() if key not in excluded_items }
                return order_details
        
        if tries >= max_retries:
            return order_details
        
        time.sleep(3)

def build_exchange_obj(api_key):
    keys = fh.read_config()['keys']
    for key in keys:
        if api_key == key['key']:
            exchange_id = key['exchange']
            api_secret = key['secret']
            exchange = getattr(ccxt, exchange_id)({
                'apiKey': api_key,
                'secret': api_secret
            })
            return exchange
    print(f'Failed to build_exchange_obj: {api_key}')
