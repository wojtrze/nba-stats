import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import pprint
from typing import List, Union, Dict

from selenium.common import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import logging


import driver_manager
from selenium.webdriver.common.by import By

import requests

from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_sb_games_ids_from_page(url) -> List[str]:
    driver_manager.install_chromedriver()
    with webdriver.Chrome() as driver:
        driver.get(url)
        try:
            # accept_button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            # accept_button.click()

            accept_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "onetrust-accept-btn-handler")))
            accept_button.click()
            logger.info("Clicked on 'Akceptuję wszystkie' button.")
        except NoSuchElementException:
            logger.info("'Akceptuję wszystkie' button not found on the page.")

        time.sleep(12)
        elements = driver.find_elements(By.CLASS_NAME, 'event-row-container')
        # Extract and print the ID of each element

        elements = [element.get_attribute('id').replace("event-", "") for element in elements]
        # Close the WebDriver
        driver.quit()
        logger.info(f"{len(elements)} game(s) found on superbet")
    return elements


def get_bets_by_game_id(match_id: str) -> List[Dict[str, Union[str, int]]]:
    game_url = "https://production-superbet-offer-pl.freetls.fastly.net/matches/byId"
    params = {"matchIds": match_id}

    headers = {
        "authority": "production-superbet-offer-pl.freetls.fastly.net",
        "accept": "application/json, text/plain, */*",
        "accept-language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        # "if-none-match": 'W/"2b31c-bvT4nD83gAw8kznssTKh0vcVR04"',
        "origin": "https://superbet.pl",
        "referer": "https://superbet.pl/",
        "sec-ch-ua": '"Google Chrome";v="119", "Chromium";v="119", "Not?A_Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    headers["user-agent"] = UserAgent().random

    response = requests.get(game_url, params=params, headers=headers)
    if response.status_code == 200:
        # Print or process the response content
        # print(response.json())
        bets_for_game = response.json()['data'][0]['odds']
    else:
        logger.info(f"Failed to fetch data. Status code: {response.status_code}")
    return bets_for_game


def filter_data(data, bet_type):
    return [item for item in data
            if all(item.get(key) == value for key, value in bet_type.items())]


def main():
    games_ids = get_sb_games_ids_from_page("https://superbet.pl/zaklady-bukmacherskie/koszykowka/usa/usa-nba/wszystko")

    for id in games_ids:
        json_data = get_bets_by_game_id(id)

        bet_type = {
            'pts': {'bgdi': 200949},
            'ast': {'bgdi': 200950},
            'reb': {'bgdi': 200951},
            'thr': {'bgdi': 200992},
            'stl': {'bgdi': 200984},
            'tov': {'bgdi': 200985}
        }

        filtered_data = filter_data(json_data, bet_type['pts'])

        logger.info("Filtered Data:")
        logger.info(filtered_data)
        time.sleep(1)


if __name__ == '__main__':
    main()
