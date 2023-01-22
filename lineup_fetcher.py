import requests
from bs4 import BeautifulSoup


def players_unlikely_to_play():
    global url, name
    url = "https://www.rotowire.com/basketball/nba-lineups.php"
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    li_elements = soup.find_all("li", class_="is-pct-play-50")
    players = []
    for li_element in li_elements:
        players.append(li_element.find('a'))
    for player in players:
        name = player.get_text()
        print(name)


if __name__ == "__main__":
    players_unlikely_to_play()
