import numpy
import pandas as pd
import numpy as np
import itertools
import math

from numpy.core.defchararray import isdigit
from pandasgui import show

if __name__ == "__main__":
    df = pd.read_csv('all_assessed_bets20230424.csv')
    df = df.drop_duplicates(subset=['closed_date', 'player_ESPN', 'bet_type', 'line', 'over_under'], keep='first')
    # Define the columns to group by
    group_cols = ['bet_type', 'over_under', "averages_2_games", "last_games_2_2", "averages_5_games"] #,'avg_diff_6_games','last_games_4_5','median','last_games_6_8','last_games_2_2','averages_2_games','averages_6_games','bets_hits']

    # group_cols = ['bet_type', 'over_under', 'bets_hits', 'averages', 'median']

    # Generate all possible combinations of values for the columns
    combinations = itertools.product(*[df[col].unique() for col in group_cols])

    # Create a dictionary to store the counts for each combination
    counts = {}
    results = {}
    results_df = pd.DataFrame()
    # Iterate through each combination and count the number of rows with is_hit True and False
    for combo in combinations:
        def condition(col, val: str):
            if pd.isna(val):
                return f'({col}.isnull())'
            elif type(val) in [int, numpy.float64]:
                return f'({col} == {val})'
            elif type(val) == str and isdigit(val):
                return f'({col} == "{val}")'
            else:
                return f'({col} == "{val}")'

        query = ' & '.join([condition(col, val) for col, val in zip(group_cols, combo)])
        rows = df.query(query)
        true_count = (rows['is_hit'] == True).sum()
        false_count = (rows['is_hit'] == False).sum()
        hit_ratio = true_count / (true_count + false_count + 1)
        # counts[combo] = {'True': true_count, 'False': false_count, 'hit_ratio': hit_ratio}
        # Add to results_df columns: query, hit_ratio, true_count, false_count
        results_df = results_df.append({'query': query, 'hit_ratio': hit_ratio, 'true_count': true_count, 'false_count': false_count}, ignore_index=True)
        if hit_ratio > 0.68 and true_count > 10:
            print(f"{query}: {hit_ratio:2f}, {true_count} True, {false_count} False")
    # Convert the dictionary to a pandas DataFrame for easy viewing
    results_df.to_csv('analysis_results_20230424.csv', index=False)
    # # Print the result
    show(results_df)
