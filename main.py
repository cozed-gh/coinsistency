import pandas as pd
from flask import Flask, render_template, request, jsonify, Response
import json
import threading
import queue
import os
import logging
import multiprocessing as mp
import py.background_events as be
import py.market_search as ms
import py.file_handler as fh
import py.misc as misc

app = Flask(__name__)
q = queue.Queue()
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def index():
    return render_template('index.html')

@app.get('/chart_data')
def get_chart_data():
    exchange = request.args.get('exchange')
    symbol = fh.sanitize_file_name(request.args.get('symbol'))
    timeframe = request.args.get('timeframe')
    length = int(request.args.get('length'))
    path = os.path.join('data_storage', exchange, symbol, 'ohlcv', timeframe + '.csv')
    path_open_candle = os.path.join('data_storage', exchange, symbol, 'ohlcv', 'open_candle.json')

    def load_data(q):
        try:
            candlestick_data = []
            df = pd.read_csv(path)
            df = df.iloc[-length:]
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

            candlestick_data.append({
                'time': int(open_candle['timestamp'] / 1000),
                'open': open_candle['open'],
                'high': open_candle['high'],
                'low': open_candle['low'],
                'close': open_candle['close']
            })
        
            q.put(candlestick_data)
        except:
            q.put(None)

    result_queue = queue.Queue()
    thread = threading.Thread(target=load_data, args=(result_queue,))
    thread.start()
    thread.join(timeout=5)

    candlestick_data = result_queue.get()
    if candlestick_data:
        data = { 'candlestick_data': candlestick_data }
        return json.dumps(data)
    else: 
        return json.dumps({'error': '/chart_data error'})

@app.get('/get_chart_header')
def get_chart_header():
    config = fh.read_config()
    data = config['ui']['chart']
    return jsonify(data)

@app.get('/set_chart_header')
def set_chart_header():
    exchange = request.args.get('exchange')
    symbol = request.args.get('symbol')
    timeframe = request.args.get('timeframe')
    length = request.args.get('length')
    polling_frequency = request.args.get('polling_frequency')
    data = {'chart': {'exchange': exchange, 'symbol': symbol, 'timeframe': timeframe, 'length': length, 'polling_frequency': polling_frequency}}

    try:
        fh.edit_config('ui', 'edit', data)
        return jsonify({'message': "Set chart header successfully"})
    except Exception as e:
        return jsonify({'message': e})

@app.get('/search_market')
def search_market():
    search_query = request.args.get('query')

    thread = threading.Thread(target=ms.search_market, args=(search_query, q))
    thread.start()
    thread.join()

    response = q.get()
    return jsonify(response)

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
    

if __name__ in ['__main__', 'main']:
    mp.Process(name="Backend Daemon", target=be.init, daemon=True).start()
    app.run()