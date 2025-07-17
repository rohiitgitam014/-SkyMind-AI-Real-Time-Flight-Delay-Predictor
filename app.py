import streamlit as st
import pandas as pd
import requests
import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from datetime import datetime

st.set_page_config(page_title="🛫 SkyMind AI: Real-Time Flight Delay Predictor", layout="wide")
st.title("🛫 SkyMind AI: Real-Time Flight Delay Predictor")

# Fetch all countries dynamically from live OpenSky data
@st.cache_data(ttl=300)
def fetch_all_countries():
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        states = data.get("states", [])
        if not states:
            return []
        df = pd.DataFrame(states, columns=[
            "icao24", "callsign", "origin_country", "time_position", "last_contact",
            "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
            "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
            "spi", "position_source"
        ])
        countries = df["origin_country"].dropna().unique()
        return sorted(countries)
    else:
        return []

countries = fetch_all_countries()

if not countries:
    st.error("⚠️ Could not fetch live data or no countries available.")
    st.stop()

country = st.selectbox("🌍 Select Country", countries)

# Fetch flight data filtered by selected country
def fetch_flights_by_country(country):
    url = "https://opensky-network.org/api/states/all"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Failed to fetch live flight data.")
        return pd.DataFrame()
    data = response.json()
    states = data.get("states", [])
    if not states:
        return pd.DataFrame()
    df = pd.DataFrame(states, columns=[
        "icao24", "callsign", "origin_country", "time_position", "last_contact",
        "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
        "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk",
        "spi", "position_source"
    ])
    filtered = df[df["origin_country"] == country].copy()
    return filtered

if st.button("📡 Fetch & Analyze Flights"):

    flights_df = fetch_flights_by_country(country)

    if flights_df.empty:
        st.warning(f"No flights found for {country} at this moment.")
        st.stop()

    st.success(f"Fetched {len(flights_df)} flights from {country}")

    # Save or append to CSV
    csv_file = "flight_data.csv"
    try:
        # If file exists, append without headers
        existing_df = pd.read_csv(csv_file)
        flights_df.to_csv(csv_file, mode='a', header=False, index=False)
    except FileNotFoundError:
        flights_df.to_csv(csv_file, index=False)

    st.info(f"Data saved/appended to `{csv_file}`")

    # Load full CSV data for training
    full_df = pd.read_csv(csv_file)

    # Clean data: drop missing velocity or geo_altitude rows (required features)
    full_df = full_df.dropna(subset=["velocity", "geo_altitude"])

    # Create simulated delay label: velocity < 100 → delayed=1 else 0
    if "delay" not in full_df.columns:
        full_df["delay"] = (full_df["velocity"] >= 60) & (full_df["geo_altitude"] > 1000)
    full_df = full_df.dropna(subset=["delay"])

    X = full_df[["velocity", "geo_altitude"]]
    y = full_df["delay"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    st.write(f"### Model accuracy on historical data: {acc:.2%}")

    # Predict delay on latest fetched flights
    latest_df = flights_df.dropna(subset=["velocity", "geo_altitude"])
    if latest_df.empty:
        st.warning("No valid data in latest fetch to predict delays.")
        st.stop()

    X_live = latest_df[["velocity", "geo_altitude"]]
    predictions = model.predict(X_live)
    latest_df["Predicted Delay"] = predictions
    latest_df["Predicted Delay"] = latest_df["Predicted Delay"].map({0: "Not Delayed", 1: "Delayed"})
    latest_df["Prediction Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.subheader(f"🛫 Predicted Flight Delays for {country} (Latest Fetch)")
    st.dataframe(latest_df[[
        "icao24", "callsign", "origin_country", "velocity", "geo_altitude", "Predicted Delay","Prediction Timestamp"
    ]].reset_index(drop=True))
