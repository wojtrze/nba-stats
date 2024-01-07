from datetime import datetime
import requests
import time
from typing import List, Union, Dict
from selenium.common import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from fake_useragent import UserAgent
import logging
import driver_manager
from selenium.webdriver.common.by import By
from selenium import webdriver

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SUPERBET_URL = "https://superbet.pl/zaklady-bukmacherskie/koszykowka/usa/usa-nba/wszystko"


def get_sb_games_info_from_page(url):
    driver_manager.install_chromedriver()
    with webdriver.Chrome() as driver:
        driver.get(url)
        try:
            accept_button = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "onetrust-accept-btn-handler")))
            accept_button.click()
            logger.info("Clicked on 'Akceptuję wszystkie' button.")
        except NoSuchElementException:
            logger.info("'Akceptuję wszystkie' button not found on the page.")

        time.sleep(6)
        #WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'event-row-container')))

        game_elements = driver.find_elements(By.CLASS_NAME, 'event-row-container')
        logger.info(f"{len(game_elements)} game events were found on {url}")
        games_info = []
        current_datetime = datetime.now()
        for el in game_elements:
            game_info = extract_game_info(current_datetime, el)
            games_info.append(game_info)

        logger.info(f"{len(games_info)} game(s) found on superbet")

        driver.quit()
        return games_info


def extract_game_info(current_datetime, el):
    game_info = {"superbet_event_id": el.get_attribute("id").replace("event-", ""),
                 "event_time": el.find_element(By.CLASS_NAME, "event-time").text.strip(),
                 "home": el.find_element(By.XPATH, ".//*[@class='event-competitor__name e2e-event-team1-name']").text.strip(),
                 "away": el.find_element(By.XPATH, ".//*[@class='event-competitor__name e2e-event-team2-name']").text.strip(),
                 "odds": {
                     "home_win": el.find_elements(By.XPATH, ".//*[@class='odd-button__odd-value-new e2e-odd-current-value']")[0].text.strip(),
                     "away_win": el.find_elements(By.XPATH, ".//*[@class='odd-button__odd-value-new e2e-odd-current-value']")[1].text.strip(),
                     "access_time": current_datetime.strftime("%Y-%m-%d %H:%M:%S")
                 },
                 }
    return game_info


def get_bets_by_game_id(game_info) -> List[Dict[str, Union[str, int]]]:
    game_url = "https://production-superbet-offer-pl.freetls.fastly.net/matches/byId"
    params = {"matchIds": game_info["superbet_event_id"]}

    headers = {
        "authority": "production-superbet-offer-pl.freetls.fastly.net",
        "accept": "application/json, text/plain, */*",
        "accept-language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "if-none-match": 'W/"2b31c-bvT4nD83gAw8kznssTKh0vcVR04"',
        "origin": "https://superbet.pl",
        "referer": "https://superbet.pl/",
        "sec-ch-ua": '"Google Chrome";v="120", "Chromium";v="120", "Not?A_Brand";v="24"',
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
        bets_for_game = response.json()["data"][0]["odds"]
    else:
        logger.info(f"Failed to fetch data. Status code: {response.status_code}")
    return bets_for_game


def filter_data(data, bet_type):
    return [item for item in data if all(item.get(key) in value for key, value in bet_type.items())]


def main():
    games_ids = get_sb_games_info_from_page(SUPERBET_URL)

    for id in games_ids:
        json_data = get_bets_by_game_id(id)

        bet_type = {
            "pts": {"bgdi": [200949]},
            "ast": {"bgdi": [200950]},
            "reb": {"bgdi": [200951]},
            "thr": {"bgdi": [200992]},
            "stl": {"bgdi": [200984]},
            "tov": {"bgdi": [200985]}
        }

        filtered_raw_data = filter_data(json_data, bet_type["pts"])

        logger.info(f"Filtered Data contains {len(filtered_raw_data)} elements (bets)")
        logger.info(filtered_raw_data)
        time.sleep(1)


if __name__ == "__main__":
    main()

    bet = {
        "player_name": "Obi Toppin",
        "type": "pts",
        "condition": "36+",
        "odds": 1.72,
        "player_team": "NYK",
        "opponent_team": "BOS",
        "homegame": True,
        "analysis_data": {
            "injury_status": "OK",
            "sentiment": "5/10",
            "projected_matchup": "Jalen Brown",
            "unavailable_team_players": ["Julius Randle"]
        },
        "bet_resolution": {
            "is_hit": False,
            "actual": 34,
            "matchup": "Jalen Brown"
        }
    }
