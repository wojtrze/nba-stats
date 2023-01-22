from pandas import DataFrame
import pandas as pd


class Player:
    def __init__(self, name_ESPN: str):
        self.name_ESPN = name_ESPN
        self.gamelogs = self.get_player_gamelogs_from_csv(name_ESPN)
        self.gamelogs['ARP'] = self.gamelogs['AST'] + self.gamelogs['REB'] + self.gamelogs['PTS']

    def get_player_gamelogs_from_csv(self, name_ESPN: str) -> DataFrame:
        # FIXME: try to use context manager
        gamelogs = pd.read_csv(f'2022-players-logs.csv')
        gamelogs = gamelogs[(gamelogs['player_name_ESPN'] == name_ESPN)]
        gamelogs.drop_duplicates(subset=['Date'], inplace=True)
        gamelogs.sort_values(by=['Date'], inplace=True)
        return gamelogs


if __name__ == '__main__':
    player = Player('LeBronJames')
    print(player.gamelogs)
