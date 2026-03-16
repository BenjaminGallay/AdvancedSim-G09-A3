import pandas as pd

df = pd.read_csv('_roads3.csv')

roads = ['N1', 'N2']
target_roads = df.loc[(df['road'].str.startswith('N1' or 'N2')) & (df['road'].str.len() == 4)]
new_roads = target_roads['road'].unique().tolist()
roads = list(set(roads + new_roads))

print(roads)