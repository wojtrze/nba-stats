from pandas import DataFrame


class Player:
    def __init__(self, name_ESPN, age):
        self.name_ESPN = name_ESPN
        self.gamelogs = DataFrame()
