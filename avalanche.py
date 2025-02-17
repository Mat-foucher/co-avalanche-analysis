import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from folium.plugins import  HeatMap
import geopandas as gpd
from shapely.geometry import MultiPoint, Polygon, Point
from sklearn.cluster import DBSCAN
from sklearn.cluster import KMeans
import numpy as np

file_path = "CAIC_Accident_Data_Nov_2024.xlsx"
df = pd.read_excel(file_path)

df = df[(df["lat"] != 0.0) & (df["lon"] != 0.0)]
print(df[['lat', 'lon']].describe())


df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")


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
eps_distance = 100 /3958.8

# # Apply DBSCAN clustering
# clustering = DBSCAN(eps=eps_distance, min_samples=1,metric='haversine').fit(np.radians(coords))

num_clusters = min(5, len(df_filtered))  # Prevents more clusters than points

if num_clusters > 1:  # Only run K-Means if we have more than 1 point
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init="auto")
    df_filtered.loc[:, "cluster"] = kmeans.fit_predict(coords)
else:
    df_filtered["cluster"] = np.zeros(len(df_filtered), dtype=int)  # Assign every point to one cluster if too few data points exist

# Ensure "cluster" column exists before filtering
if "cluster" not in df_filtered.columns:
    df_filtered["cluster"] = 0  # Assign all points to one cluster to prevent errors

# Now it's safe to filter
df_filtered = df_filtered[df_filtered["cluster"] != -1]


# Convert to GeoDataFrame
gdf = gpd.GeoDataFrame(df_filtered, geometry=gpd.points_from_xy(df_filtered.lon, df_filtered.lat))

# Create a dict to store polygons and dominant traveler type:
polygons = []
for cluster in df_filtered["cluster"].unique():
    cluster_points = gdf[gdf["cluster"] == cluster]

    if len(cluster_points) < 3:
        continue  # Skip clusters with too few points

    hull = MultiPoint(cluster_points.geometry.tolist()).convex_hull

    if hull.geom_type == "Polygon":
        polygons.append({"polygon": hull, "traveler_type": cluster_points["PrimaryActivity"].mode()[0]})

    elif hull.geom_type == "LineString":  
        polygons.append({"polygon": hull.buffer(0.001), "traveler_type": cluster_points["PrimaryActivity"].mode()[0]})

    elif hull.geom_type == "Point":
        polygons.append({"polygon": hull.buffer(0.002), "traveler_type": cluster_points["PrimaryActivity"].mode()[0]})

        

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
st_folium(m)

st.markdown("""
### Forecast Zone Risk Legend:
- **Blue** = Most incidents involved skiers
- **Red** = Most incidents involved mechanized users (snowmobiles)
- **Green** = Most incidents involved hikers/climbers
- **Purple** = Most incidents involved occupational workers (patrollers, rescuers)
- **Gray** = No dominant traveler type
""")


print(df_filtered[['lat', 'lon']].dropna())  # Show all non-null lat/lon values

