import os
import json
from flask import request, jsonify
import re

def search_market(query, q):
    file_path = os.path.join('data_storage', 'all_markets.json')
    all_markets = json.load(open(file_path, 'r'))

    pattern1 = re.compile(r'.*'.join(query.split()), re.IGNORECASE)
    pattern2 = re.compile(rf".*{query}.*", re.IGNORECASE)

    matching_markets = []
    for exchange_name, markets in all_markets.items():
        for i in range(len(markets)):
            combined_string1 = f"{exchange_name} {markets[i]}"
            combined_string2 = f"{markets[i]} {exchange_name}"
            if pattern1.match(combined_string1) or pattern2.match(combined_string1) or pattern1.match(combined_string2) or pattern2.match(combined_string2):
                matching_markets.append((exchange_name, markets[i]))
    
    matching_markets.sort(key=lambda x: (x[0], x[1]))

    return q.put(matching_markets)