import pandas as pd
import numpy as np
import itertools
import math
from pandasgui import show

if __name__ == "__main__":
    df = pd.read_csv('all_assessed_bets20230329.csv')
    df = df.drop_duplicates(subset=['closed_date', 'player_ESPN', 'bet_type', 'line', 'over_under'], keep='first')
    # Define the columns to group by
    group_cols = ['bet_type', 'over_under', 'quantiles_0_4_0_6', 'quantiles_0_3_0_7',
                  'last_games_6_8', 'last_games_2_2', 'bets_hits', 'averages', 'median']

    # group_cols = ['bet_type', 'over_under', 'bets_hits', 'averages', 'median']

    # Generate all possible combinations of values for the columns
    combinations = itertools.product(*[df[col].unique() for col in group_cols])

    # Create a dictionary to store the counts for each combination
    counts = {}
    results = {}
    # Iterate through each combination and count the number of rows with is_hit True and False
    for combo in combinations:
        def condition(col, val):
            if pd.isna(val):
                return f'({col}.isnull())'
            else:
                return f'({col} == "{val}")'


        query = ' & '.join([condition(col, val) for col, val in zip(group_cols, combo)])
        rows = df.query(query)
        true_count = (rows['is_hit'] == True).sum()
        false_count = (rows['is_hit'] == False).sum()
        hit_ratio = true_count / (true_count + false_count + 1)
        counts[combo] = {'True': true_count, 'False': false_count, 'hit_ratio': hit_ratio}
        if hit_ratio > 0.67:
            print(f"{query}: {hit_ratio:2f}, {true_count} True, {false_count} False")
            results.update({query: hit_ratio})
    # Convert the dictionary to a pandas DataFrame for easy viewing
    grouped = pd.DataFrame.from_dict(counts, orient='index')
    # grouped.to_csv('analysis_result.csv', index=False)
    # # Print the result
    # show(grouped)
