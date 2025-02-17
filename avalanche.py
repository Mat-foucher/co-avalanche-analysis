import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
from folium.plugins import MarkerCluster
from folium.plugins import  HeatMap
import geopandas as gpd
from shapely.geometry import MultiPoint, Polygon, Point
from sklearn.cluster import DBSCAN
import numpy as np

file_path = "CAIC_Accident_Data_Nov_2024.xlsx"
df = pd.read_excel(file_path)

df.dropna(subset=['lat','lon'])

df['PrimaryActivity'] = df['PrimaryActivity'].str.lower().str.replace(" ","_")

# Define mapping dictionary
traveler_mapping = {
    "backcountry_tourer": "skier",
    "ski_patroller": "skier",
    "sidecountry_rider": "skier",
    "inbounds_rider": "skier",
    "hybrid_tourer": "skier",
    "human-powered_guide_client": "skier",
    
    "snowmobiler": "mechanized",
    "mechanised_guide": "mechanized",
    "mechanized_guided_client": "mechanized",
    "mechanized_guide": "mechanized",
    "mechanized_guiding_client": "mechanized",
    "snowbiker": "mechanized",
    "motorist": "mechanized",

    "hiker": "hiker",
    "climber": "hiker",
    "snowplayer": "hiker",
    "hunter": "hiker",
    "hybrid_rider": "hiker",
    "misc_recreation": "hiker",

    "miner": "occupational_hazard",
    "rescuer": "occupational_hazard",
    "ranger": "occupational_hazard",
    "highway_personnel": "occupational_hazard",
    "others_at_work": "occupational_hazard",

    
    "resident": "miscellaneous"
}

# Apply mapping to the dataframe
df["PrimaryActivity"] = df["PrimaryActivity"].map(traveler_mapping)

# Check unique categories to confirm mapping worked
print(df["PrimaryActivity"].unique())

# Color Code for Activity Type:
colordict  = {
    "skier": "blue",
    "mechanized": "red",
    "hiker": "green",
    "occupational_hazard": "orange",
    "micellaneous": "gray"
}




# Streamlit:

# Convert year to integer in case it is a string:
df["YYYY"] = df["YYYY"].astype(int)

## Dropdown to select the year:
selected_year = st.sidebar.selectbox("Select a Year", sorted(df["YYYY"].unique()), index=0)

## Filter the data based on selected year:
df_filtered = df[df["YYYY"] == selected_year]

## Convert lat/lon to numpy array for clustering:
coords = df_filtered[['lat', 'lon']].values

# Convert miles to radians:
eps_distance = 5 /3958.8

# Apply DBSCAN clustering
clustering = DBSCAN(eps=eps_distance, min_samples=2,metric='haversine').fit(np.radians(coords))

df_filtered["cluster"] = clustering.labels_

# Remove noise points:
df_filtered = df_filtered[df_filtered["cluster"] != 1]

# Convert to GeoDataFrame
gdf = gpd.GeoDataFrame(df_filtered, geometry=gpd.points_from_xy(df_filtered.lon, df_filtered.lat))

# Create a dict to store polygons and dominant traveler type:
polygons = []

for cluster in df_filtered["cluster"].unique():
    cluster_points = gdf[gdf["cluster"] == cluster]
    # Which traveler is the most frequent in this polygon:
    dominant_traveler = cluster_points["PrimaryActivity"].mode()[0]

    if len(cluster_points) >=3: # At least 3 points are needed to form a polygon.
        if len(cluster_points) >= 3:  # Only make polygons if there are enough points
            hull = MultiPoint([point for point in cluster_points.geometry]).convex_hull
        if hull.geom_type == "Polygon":
            polygons.append({"polygon": hull, "traveler_type": dominant_traveler})
        elif hull.geom_type == "LineString":  
            # If it's a line, buffer it slightly to create a small polygon
            polygons.append({"polygon": hull.buffer(0.001), "traveler_type": dominant_traveler})
        elif hull.geom_type == "Point":
            # If it's a point, make a tiny circular buffer
            polygons.append({"polygon": hull.buffer(0.002), "traveler_type": dominant_traveler})
        

        # Store polygon and its dominant traveler type:
        polygons.append({"polygon": hull, "traveler_type": dominant_traveler})

# The Map Making Section:
m = folium.Map(location=[39.5,-105.5],zoom_start=7)

# Plot the polygons:
for poly in polygons:
    folium.Polygon(
        locations=[(point[1], point[0]) for point in list(poly["polygon"].exterior.coords)],
        color=colordict.get(poly["traveler_type"],"gray"),
        fill_opacity=0.5,
        popup=f"Most at risk: {poly['traveler_type']}"
    ).add_to(m)

# Add individual points to the map as clusters:
marker_cluster = MarkerCluster().add_to(m)

# Plot the incidents:
for _, row in df_filtered.iterrows():
    folium.Marker(
        location=[row["lat"],row["lon"]],
        radius=5,
        popup=f"Traveler: {row['PrimaryActivity']}<br>Location: {row['Location']}<br>Date: {row['YYYY']}-{row['MM']}-{row['DD']}",
        color=colordict.get(row["PrimaryActivity"],"gray"),
        fill=True,
        fill_color=colordict.get(row["PrimaryActivity"],"gray")
    ).add_to(marker_cluster)



# # Heatmap Stuff:

# heat_data = df[['lat','lon']].dropna().values.tolist()

# HeatMap(heat_data).add_to(m)

# Save the Map:
folium_static(m)

st.markdown("""
### Forecast Zone Risk Legend:
- **Blue** = Most incidents involved skiers
- **Red** = Most incidents involved mechanized users (snowmobiles)
- **Green** = Most incidents involved hikers/climbers
- **Purple** = Most incidents involved occupational workers (patrollers, rescuers)
- **Gray** = No dominant traveler type
""")


#print(df_filtered["cluster"].value_counts())
