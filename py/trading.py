import py.file_handler as fh
import py.api as api
import time
import os
import json

def account_bot_loop(key):
    #exchange_id = key['exchange']
    api_key = key['key']

    exchange = api.build_exchange_obj(api_key)
    while True:
        #check positions
        #check signals
        #check orders
        #update balance every 15s
        time.sleep(0.5)


def calculate_risk(account=None):
    keys = fh.read_config()['keys']
    positions = {}
    balances = {}
    if account is None:
        for key in keys:
            exchange_id = key['exchange']
            key_id = key['key']
            key_name = key['name']
            exchange_assets = {}
            exchange_positions = {}
            try:
                account_file = f'{key_name}_{key_id}_balances.json'
                account_path = os.path.join('data_storage', exchange_id, 'accounts')
                account_file_path = os.path.join(account_path, account_file)
                with open(account_file_path, 'r') as f:
                    exchange_assets = json.load(f)

                position_file = f'{key_name}_{key_id}_positions.json'
                position_path = os.path.join('data_storage', exchange_id, 'accounts')
                position_file_path = os.path.join(position_path, position_file)
                with open(position_file_path, 'r') as f:
                    exchange_positions = json.load(f)

            except:
                continue

            stables = ['USDT', 'USDC']
            sum_usd_value = 0.0
            sum_stable_value = 0.0
            risk = 0.0
            for item in exchange_assets:
                balances[item] += exchange_assets[item]['usd_value']
                sum_usd_value += exchange_assets[item]['usd_value']
                if item in stables:
                    sum_stable_value += exchange_assets[item]['usd_value']

            for item in exchange_positions:
                p = exchange_positions[item]
                stoploss_range = p['entry'] - p['stoploss']
                stoploss_percent = stoploss_range // p['entry']
                risk_usd = p['amount'] * stoploss_percent

                balances[item] -= (p['amount'] - risk_usd)

            if sum_usd_value != 0:
                risk = 1 - (sum_stable_value // sum_usd_value)

            return risk
        
def new_position():
    #create_order
    #create_position
    return

