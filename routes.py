import py.market_search as ms
import py.file_handler as fh
import py.api as api
import time
import json
import os
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, Response

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.get('/chart_data')
async def get_chart_data():
    exchange = request.args.get('exchange')
    symbol = fh.sanitize_file_name(request.args.get('symbol'))
    timeframe = request.args.get('timeframe')
    length = int(request.args.get('length'))
    path = os.path.join('data_storage', exchange, symbol, 'ohlcv', timeframe + '.csv')
    path_open_candle = os.path.join('data_storage', exchange, symbol, 'ohlcv', 'open_candle.json')

    async def load_data():
        try:
            start_time = time.time()
            candlestick_data = []
            df = pd.read_csv(path)
            df = df.iloc[-length + 1:]
            for row in df.itertuples():
                timestamp = int(row[1] / 1000)
                open_price = row[2]
                high_price = row[3]
                low_price = row[4]
                close_price = row[5]

                candlestick_data.append({
                    'time': timestamp,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price
                })

            with open(path_open_candle, 'r') as f:
                open_candle = json.load(f)[timeframe]
            open_timestamp = int(open_candle['timestamp'] / 1000)
            last_candlestick_timestamp = candlestick_data[-1]['time']
            append_open = open_timestamp >= last_candlestick_timestamp
            if append_open:
                candlestick_data.append({
                    'time': int(open_candle['timestamp'] / 1000),
                    'open': open_candle['open'],
                    'high': open_candle['high'],
                    'low': open_candle['low'],
                    'close': open_candle['close']
                })
            end_time = time.time()
            elapsed_time = end_time - start_time
            elapsed_time_formatted = "{:.4f}".format(elapsed_time) 
            print(f'Loaded {len(candlestick_data)} data points in {elapsed_time_formatted}s (Length: {length})')

            return candlestick_data
        except Exception as e:
            print(e)
            return None

    candlestick_data = await load_data()
    if candlestick_data:
        data = { 'candlestick_data': candlestick_data }
        return json.dumps(data)
    else: 
        return json.dumps({'error': '/chart_data error'})

@app.get('/get_chart_length')
def get_chart_length():
    exchange = request.args.get('exchange')
    symbol = fh.sanitize_file_name(request.args.get('symbol'))
    timeframe = request.args.get('timeframe')
    path = os.path.join('data_storage', exchange, symbol, 'ohlcv', timeframe + '.csv')
    data_length = len(pd.read_csv(path))
    
    return json.dumps({'length': data_length})

@app.get('/get_chart_defaults')
def get_chart_defaults():
    config = fh.read_config()
    data = config['ui']['chart']
    return jsonify(data)

@app.get('/set_chart_defaults')
def set_chart_defaults():
    exchange = request.args.get('exchange')
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe')
    data = {'chart': {'exchange': exchange, 'symbol': symbol, 'timeframe': timeframe}}

    try:
        fh.edit_config('ui', 'edit', data)
        return jsonify({'message': "Set chart header successfully"})
    except Exception as e:
        return jsonify({'message': e})

@app.get('/search_market')
async def search_market():
    search_query = request.args.get('query')
    result = await ms.search_market(search_query, None)

    return jsonify(result)

@app.get('/add_market')
def add_market():
    exchange = request.args.get('exchange')
    symbol = request.args.get('symbol')

    data = {'exchange': exchange, 'symbol': symbol}
    try:
        message = fh.edit_config('markets', 'add', data)
        return jsonify({'message': f'{symbol} ({exchange}) {message}'})
    except Exception as e:
        return jsonify({'message': e})


@app.get('/remove_market')
def remove_market():
    exchange = request.args.get('exchange')
    symbol = request.args.get('symbol')

    data = {'exchange': exchange, 'symbol': symbol}
    try:
        message = fh.edit_config('markets', 'remove', data)
        return jsonify({'message': f'{symbol} ({exchange}) {message}'})
    except Exception as e:
        return jsonify({'message': e})
    
@app.get('/set_ohlcv')
def set_ohlcv():
    ohlcv_date = request.args.get('ohlcv-since')

    timestamp = ohlcv_date

    try: 
        fh.edit_config('ohlcv', 'edit', timestamp)
        return jsonify({'message': f'OHLCV set to {ohlcv_date}'})
    except Exception as e:
        return jsonify({'message': e})
    
@app.get('/load_config')
def load_config():
    config = fh.read_config()
    return jsonify(config)

@app.get('/create_order')
def create_order():
    key = request.args.get('key')
    type = request.args.get('type')
    symbol = request.args.get('symbol')
    side = request.args.get('side')
    amount = request.args.get('amount')

    api.create_order(key, type, symbol, side, amount, True)
    