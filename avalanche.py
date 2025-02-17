import pandas as pd
import streamlit as st
import folium
from streamlit_folium import folium_static
from folium.plugins import  HeatMap

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

# The Map Making Section:
m = folium.Map(location=[39.5,-105.5],zoom_start=7)


# Streamlit:

# Convert year to integer in case it is a string:
df["YYYY"] = df["YYYY"].astype(int)

## Dropdown to select the year:
selected_year = st.sidebar.selectbox("Select a Year", sorted(df["YYYY"].unique()), index=0)

## Filter the data based on selected year:
df_filtered = df[df["YYYY"] == selected_year]


# Plot the incidents:
for _, row in df.iterrows():
    folium.CircleMarker(
        location=[row["lat"],row["lon"]],
        radius=5,
        popup=f"Traveler: {row['PrimaryActivity']}<br>Location: {row['Location']}<br>Date: {row['YYYY']}-{row['MM']}-{row['DD']}",
        color=colordict.get(row["PrimaryActivity"],"gray"),
        fill=True,
        fill_color=colordict.get(row["PrimaryActivity"],"gray")
    ).add_to(m)

# Heatmap Stuff:

heat_data = df[['lat','lon']].dropna().values.tolist()

HeatMap(heat_data).add_to(m)

# Save the Map:
#m.save("avalanche_traveler_map.html")
folium_static(m)

#print("Map Saved! Now with Heatmap! Open 'avalanche_traveler_map.html in a web browser.")


