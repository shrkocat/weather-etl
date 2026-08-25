"""
Weather ETL dashboard.

Reads directly from the same database the pipeline loads into and gives
a quick visual sanity check of the data: latest readings per location,
temperature trend over time, and basic summary stats.

Run with:
    streamlit run dashboard/app.py
"""

import sys
from pathlib import Path

# Allow `from src...` imports when run as `streamlit run dashboard/app.py`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from src.utils.db import get_engine
from src.extract import load_config

st.set_page_config(page_title="Weather ETL Dashboard", page_icon="🌤️", layout="wide")


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    config = load_config()
    table_name = config["database"]["table_name"]
    engine = get_engine()
    query = f"SELECT * FROM {table_name} ORDER BY observation_time DESC"
    try:
        return pd.read_sql(query, engine, parse_dates=["observation_time", "fetched_at"])
    except Exception as e:
        st.error(
            f"Couldn't read from the database ({e}). "
            f"Have you run the pipeline yet? Try: python -m src.main"
        )
        return pd.DataFrame()


def main():
    st.title("🌤️ Weather ETL Pipeline Dashboard")
    st.caption("Data extracted from Open-Meteo, cleaned, validated, and loaded via the pipeline in `src/`.")

    df = load_data()
    if df.empty:
        st.info("No data yet. Run `python -m src.main` to populate the database.")
        return

    locations = sorted(df["location_name"].unique())
    selected = st.multiselect("Locations", locations, default=locations)
    filtered = df[df["location_name"].isin(selected)]

    st.subheader("Latest readings")
    latest = (
        filtered.sort_values("observation_time")
        .groupby("location_name")
        .tail(1)
        .sort_values("location_name")
    )
    cols = st.columns(len(latest)) if len(latest) else [st]
    for col, (_, row) in zip(cols, latest.iterrows()):
        with col:
            st.metric(
                label=row["location_name"],
                value=f"{row['temperature_celsius']:.1f} °C",
                delta=f"{row['humidity_pct']:.0f}% humidity",
            )

    st.subheader("Temperature over time")
    pivot = filtered.pivot_table(
        index="observation_time", columns="location_name", values="temperature_celsius"
    )
    st.line_chart(pivot)

    st.subheader("Summary statistics")
    st.dataframe(
        filtered.groupby("location_name")[
            ["temperature_celsius", "humidity_pct", "wind_speed_kmh", "precipitation_mm"]
        ].describe().round(2)
    )

    st.subheader("Raw data")
    st.dataframe(filtered, use_container_width=True)


if __name__ == "__main__":
    main()
