import dataframe as dataframe
import requests
from random import randint
from time import sleep
import json
import pandas as pd

NORMALIZED_TEAM_NAME = {
    "Boston Celtics": "bos",
    "Brooklyn Nets": "bkn",
    "New York Knicks": "ny",
    "Philadelphia 76ers": "phi",
    "Toronto Raptors": "tor",
    "Chicago Bulls": "chi",
    "Cleveland Cavaliers": "cle",
    "Detroit Pistons": "det",
    "Indiana Pacers": "ind",
    "Milwaukee Bucks": "mil",
    "Denver Nuggets": "den",
    "Minnesota Timberwolves": "min",
    "Oklahoma City Thunder": "okc",
    "Portland Trail Blazers": "por",
    "Utah Jazz": "utah",
    "Golden State Warriors": "gs",
    "Los Angeles Clippers": "lac",
    "Los Angeles Lakers": "lal",
    "Phoenix Suns": "phx",
    "Sacramento Kings": "sac",
    "Atlanta Hawks": "atl",
    "Charlotte Hornets": "cha",
    "Miami Heat": "mia",
    "Orlando Magic": "orl",
    "Washington Wizards": "wsh",
    "Dallas Mavericks": "dal",
    "Houston Rockets": "hou",
    "Memphis Grizzlies": "mem",
    "New Orleans Pelicans": "no",
    "San Antonio Spurs": "sa"
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:20.0) Gecko/20100101 Firefox/20.0'}


# w offers z jsona szukam zakładów na ARP
def game_betoffer_list(event_id,bet_type):
    sleep(randint(1, 3))
    url = f"https://eu-offering.kambicdn.org/offering/v2018/ub/betoffer/event/{event_id}.json?lang=pl_PL&market=PL&ncid=1685181683"
    resp = requests.get(url, headers)
    a = resp.json()
    offers = a['betOffers']
    event_offers = []
    home = NORMALIZED_TEAM_NAME[a['events'][0]['homeName']]
    away = NORMALIZED_TEAM_NAME[a['events'][0]['awayName']]
    for betoffer in offers:
        if betoffer['criterion']['englishLabel'] == "Points, rebounds & assists by the player - Including Overtime":
            #print (betoffer['criterion']['englishLabel'])
            name = betoffer['outcomes'][0]['participant']
            odds = betoffer['outcomes'][0]['odds']
            line = betoffer['outcomes'][0]['line']
            id = betoffer['outcomes'][0]['id']
            changed_date = betoffer['outcomes'][0]['changedDate']
            #closed_date = betoffer['closed']
            bet_type = 'ARP'
            offer_mapped = {"name": name,
                            "name_ESPN": ''.join(name.split(',')[::-1]).strip(),
                            "odds": odds/1000,
                            "line": line/1000,
                            "home": home,
                            "away": away,
                            "bet_type": bet_type,
                            "id": id,
                            "changed_date": changed_date
#                            "closed_date": closed_date
                            }
            event_offers.append(offer_mapped.copy())

        if betoffer['criterion']['englishLabel'] == "Points scored by the player - Including Overtime":
            #print (betoffer['criterion']['englishLabel'])
            name = betoffer['outcomes'][0]['participant']
            odds = betoffer['outcomes'][0]['odds']
            line = betoffer['outcomes'][0]['line']
            id = betoffer['outcomes'][0]['id']
            changed_date = betoffer['outcomes'][0]['changedDate']
#            closed_date = betoffer['closed']
            bet_type = 'PTS'
            offer_mapped = {"name": name,
                            "name_ESPN": ''.join(name.split(',')[::-1]).strip(),
                            "odds": odds/1000,
                            "line": line/1000,
                            "home": home,
                            "away": away,
                            "bet_type": bet_type,
                            "id": id,
                            "changed_date": changed_date,
#                            "closed_date": closed_date
                            }
            event_offers.append(offer_mapped.copy())
    return event_offers


def todays_games_list():
    url = "https://pl.unibet-43.com/sportsbook-feeds/views/filter/basketball/nba/matches?includeParticipants=true&useCombined=true&ncid=1635861681"
    resp = requests.get(url)
    a = resp.json()
    events = a['layout']['sections'][1]['widgets'][0]['matches']['events']
    result = []
    for event in events:
        if event['event']['group'] != 'NBA':
            continue
        event_id = event['event']['id']
        result.append(event_id)
    return result

excluded_games =[1007972409, 1007972410, 1007972411, 1007972412, 1007972413, 1018412231]

def all_today_bets():
    bet_type = ['ARP', 'PTS']  # do dodania jako parametr wejsciowy i podstawa wyboru, mapowania
    result = []
    today_games = todays_games_list()
    for game_id in today_games:
        if game_id in excluded_games:
            continue
        print(f'game_id: {game_id} - {len(result)} total offers count')
        # game_id = today_games[5]  # to jest id z listy, np '1008151243'
        result.extend(game_betoffer_list(event_id=game_id, bet_type=bet_type))
    return result


def all_today_bets_normalized():
    # metoda przetwarzające dane zakładów do formatu spójnego z ESPN (name-surname)
    betoffers = all_today_bets()
    for bet in betoffers:
        bet['name_ESPN'] = ''.join(bet['name'].split(',')[::-1]).strip()
    return betoffers


def normalize_UB_name_to_ESPN(UB_name):
    # transforms "Westbrook, Russel" to "RusselWestbrook"
    return ''.join(UB_name.split(',')[::-1]).strip()

def store_bets(bets):
    df = pd.DataFrame(bets)
    pd.read_csv('bets.csv').append(df).drop_duplicates().to_csv('bets.csv', index=False)
    #df.to_csv('bets.csv', index=False)

if __name__ == '__main__':
    bets = all_today_bets()
    #store_bets(bets)
    print(bets)

