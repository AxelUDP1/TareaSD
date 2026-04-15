from data_loader import load_data

data = load_data("../data/buildings.csv")

zones = {}

for row in data:
    z = row["zone"]
    zones[z] = zones.get(z, 0) + 1

print("Distribución por zonas:")
for z, count in zones.items():
    print(z, ":", count)