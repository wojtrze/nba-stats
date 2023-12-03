import pprint
from typing import List, Union, Dict
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

import requests

def get_bets_by_match_id(match_id: str) -> List[Dict[str, Union[str, int]]]:
    game_url = "https://production-superbet-offer-pl.freetls.fastly.net/matches/byId"
    params = {"matchIds": "5345270"}

    headers = {
        "authority": "production-superbet-offer-pl.freetls.fastly.net",
        "accept": "application/json, text/plain, */*",
        "accept-language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "if-none-match": 'W/"2b31c-bvT4nD83gAw8kznssTKh0vcVR04"',
        "origin": "https://superbet.pl",
        "referer": "https://superbet.pl/",
        "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    }

    response = requests.get(game_url, params=params, headers=headers)

    if response.status_code == 200:
        # Print or process the response content
        print(response.json())
        bets_for_game = response.json()['data'][0]['odds']
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
    return bets_for_game



def filter_data(data, filters):
    return [item for item in data
            if all(item.get(key) == value for key, value in filters.items())]

    pts_filter = {'bgdi': 200949}
    ast_filter = {'bgdi': 200950}
    reb_filter = {'bgdi': 200951}
    thr_filter = {'bgdi': 200992}
    stl_filter = {'bgdi': 200984}
    tov_filter = {'bgdi': 200985}

    filtered_data = filter_data(json_data, pts_filter)

    print("Filtered Data:")
    pprint.pprint(filtered_data)

