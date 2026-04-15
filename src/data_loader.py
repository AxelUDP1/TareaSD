import pandas as pd


ZONES = {
    "Z1": {
        "name": "Providencia",
        "lat_min": -33.445,
        "lat_max": -33.420,
        "lon_min": -70.640,
        "lon_max": -70.600
    },
    "Z2": {
        "name": "Las Condes",
        "lat_min": -33.420,
        "lat_max": -33.390,
        "lon_min": -70.600,
        "lon_max": -70.550
    },
    "Z3": {
        "name": "Maipú",
        "lat_min": -33.530,
        "lat_max": -33.490,
        "lon_min": -70.790,
        "lon_max": -70.740
    },
    "Z4": {
        "name": "Santiago Centro",
        "lat_min": -33.460,
        "lat_max": -33.430,
        "lon_min": -70.670,
        "lon_max": -70.630
    },
    "Z5": {
        "name": "Pudahuel",
        "lat_min": -33.470,
        "lat_max": -33.430,
        "lon_min": -70.810,
        "lon_max": -70.760
    }
}


def get_zone(latitude, longitude):
    """Devuelve la zona correspondiente según latitud y longitud"""

    for zone_id, zone_info in ZONES.items():
        if (
            zone_info["lat_min"] <= latitude <= zone_info["lat_max"]
            and zone_info["lon_min"] <= longitude <= zone_info["lon_max"]
        ):
            return zone_id

    return None


def load_data(file_path):
    """Carga el dataset, asigna zonas y devuelve una lista de diccionarios"""

    df = pd.read_csv(file_path)
    
    # Seleccionar solo columnas necesarias
    df = df[["latitude", "longitude", "confidence", "area_in_meters"]]

    required_columns = ["latitude", "longitude", "confidence", "area_in_meters"]

    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Falta la columna requerida: {column}")

    df["zone"] = df.apply(
        lambda row: get_zone(row["latitude"], row["longitude"]),
        axis=1
    )

    df = df[df["zone"].notnull()].copy()

    df = df.rename(columns={"area_in_meters": "area"})

    return df[["zone", "confidence", "area"]].to_dict(orient="records")