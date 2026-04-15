import pandas as pd

input_file = "../data/buildings_large.csv"
output_file = "../data/buildings.csv"

df = pd.read_csv(input_file, nrows=10000)

df.to_csv(output_file, index=False)

print("Dataset reducido listo")