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

st.set_page_config(layout="wide")

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
#print(df["PrimaryActivity"].unique())

# Color Code for Activity Type:
colordict  = {
    "skier": "rgba(0, 0, 255, 0.5)",  # Blue with 50% opacity
    "mechanized": "rgba(255, 0, 0, 0.5)",  # Red with 50% opacity
    "hiker": "rgba(0, 255, 0, 0.5)",  # Green with 50% opacity
    "occupational_hazard": "rgba(255, 165, 0, 0.5)",  # Orange with 50% opacity
    "miscellaneous": "rgba(128, 128, 128, 0.5)"  # Gray with 50% opacity
}





# Streamlit:

# Convert year to integer in case it is a string:
df["YYYY"] = df["YYYY"].astype(int)

## Dropdown to select the year:
#selected_year = st.sidebar.selectbox("Select a Year", sorted(df["YYYY"].unique()), index=0)

## Filter the data based on selected year:
#df_filtered = df[df["YYYY"] == selected_year]
df_filtered = df

# Sidebar filter for activity types
traveler_filter = st.sidebar.multiselect(
    "Filter by Traveler Type", df["PrimaryActivity"].unique(), default=df["PrimaryActivity"].unique()
)

# Apply the filter
df_filtered = df_filtered[df_filtered["PrimaryActivity"].isin(traveler_filter)]

## Convert lat/lon to numpy array for clustering:
coords = df_filtered[['lat', 'lon']].values

# Convert miles to radians:
eps_distance = 7/3958.8

# # Apply DBSCAN clustering
# clustering = DBSCAN(eps=eps_distance, min_samples=1,metric='haversine').fit(np.radians(coords))

num_clusters = min(3, len(df_filtered))  # Prevents more clusters than points

if num_clusters > 1:  # Only run DBSCAN if we have enough points
    clustering = DBSCAN(eps=eps_distance, min_samples=2, metric='haversine').fit(np.radians(coords))
    df_filtered.loc[:, "cluster"] = clustering.labels_  # ✅ This is the correct way to get clusters
else:
    df_filtered.loc[:, "cluster"] = np.zeros(len(df_filtered), dtype=int)  # Assign every point to one cluster if too few data points exist


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

    hull = MultiPoint(cluster_points.geometry.tolist()).convex_hull.buffer(0.05)

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
        color=colordict.get(poly["traveler_type"], "gray"),  # Keeps the outline color
        fill=True,  # Enables fill
        fill_color=colordict.get(poly["traveler_type"], "gray"),  # Uses the same transparent fill color
        fill_opacity=0.5,  # Adjust transparency (0 = fully transparent, 1 = solid color)
        weight=2,  # Outline thickness
        interactive=True,  # ✅ Makes entire polygon clickable
        popup=folium.Popup(
            f"<b>Most at risk:</b> {poly['traveler_type']}<br>"
            f"<b>Incidents:</b> {len(df_filtered[df_filtered['cluster'] == cluster])}",
            max_width=300
        )
    ).add_to(m)


# Add individual points to the map as clusters:
marker_cluster = MarkerCluster(disableClusteringAtZoom=10).add_to(m)

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



# Heatmap Stuff:

# Weight heatmap points based on accident density
heat_data = df_filtered[['lat', 'lon']].dropna()
heat_data = heat_data.groupby(["lat", "lon"]).size().reset_index(name="count")

# Apply weighting to the heatmap intensity
heatmap_data = heat_data[['lat', 'lon', 'count']].values.tolist()

# Add weighted heatmap
HeatMap(heatmap_data, radius=10, blur=15, max_zoom=8).add_to(m)


# Save the Map:
st_folium(m, width=1200, height=800)

st.markdown("""
### Forecast Zone Risk Legend:
- **Blue** = Most incidents involved skiers
- **Red** = Most incidents involved mechanized users (snowmobiles)
- **Green** = Most incidents involved hikers/climbers
- **Purple** = Most incidents involved occupational workers (patrollers, rescuers)
- **Gray** = No dominant traveler type
""")

st.markdown("""
### About this App:
This is a geospatial visualization of the avalanche accident data provided by Avalanche.org
of recorded avalanche incidents since approximately 1953. The zones shaped in blue, red, green and orange all
represent the modes of travel used by the victim(s) of these incidents caught in avalanches in these areas.
The goal of this map is to determine which moe of travel, historically, is most likely to be caught in avalanches
in the zones seen.
""")


#print(df_filtered[['lat', 'lon']].dropna())  # Show all non-null lat/lon values

