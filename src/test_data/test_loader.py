from data_loader import load_data

data = load_data("../data/buildings.csv")

print("Cantidad de registros cargados:", len(data))

for row in data:
    print(row)