import streamlit as st
import pandas as pd
import requests
import datetime
import os

# Title
st.set_page_config(page_title="🛫 SkyPulse AI: Intelligent Flight Delay Detector", layout="wide")
st.title("🛫 SkyPulse AI: Intelligent Flight Delay Detector")
st.markdown("Built with real-time flight data 🌍 and smart delay detection 🚨")

# Input country name
country = st.text_input("🌍 Enter Country (e.g., India, United States, Germany):", value="India")

# Fetch flights button
if st.button("🔄 Fetch Real-Time Flight Data"):
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        states = data.get("states", [])
        filtered = pd.DataFrame(states, columns=[
            "icao24", "callsign", "origin_country", "time_position", "last_contact",
            "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
            "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
            "spi", "position_source"
        ])
        
        # Filter for selected country
        filtered = filtered[filtered["origin_country"].str.contains(country, case=False, na=False)]

        if not filtered.empty:
            # Add timestamp
            filtered["timestamp"] = datetime.datetime.now()

            # Add delay column: 1 if velocity < 100
            filtered["delay"] = (filtered["velocity"] < 100).astype(int)

            # Show live flight data
            st.success(f"✅ {len(filtered)} flights fetched for {country}")
            st.dataframe(filtered[["icao24", "callsign", "origin_country", "velocity", "geo_altitude", "timestamp", "delay"]])

            # Save to CSV (append if exists)
            csv_file = "flight_data.csv"
            if os.path.exists(csv_file):
                old = pd.read_csv(csv_file)
                combined = pd.concat([old, filtered], ignore_index=True)
                combined.to_csv(csv_file, index=False)
            else:
                filtered.to_csv(csv_file, index=False)

        else:
            st.warning(f"⚠️ No flight data found for {country} at the moment.")
    else:
        st.error("❌ Failed to fetch data from OpenSky API")

# Display stored flight data
st.subheader("📁 Historical Flight Data (Saved in flight_data.csv)")
if os.path.exists("flight_data.csv"):
    csv_data = pd.read_csv("flight_data.csv")

    # Convert and format timestamp
    if "timestamp" in csv_data.columns:
        csv_data["timestamp"] = pd.to_datetime(csv_data["timestamp"])
        csv_data["timestamp"] = csv_data["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    st.dataframe(csv_data[[
        "icao24", "callsign", "origin_country", "velocity", "geo_altitude", "timestamp", "delay"
    ]].sort_values("timestamp", ascending=False).reset_index(drop=True))
else:
    st.info("📄 flight_data.csv not found. Click above button to fetch and save flight data.")
