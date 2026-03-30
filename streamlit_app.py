
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static # For better Folium integration
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(layout="wide")
st.title("Water Quality Data Explorer")

@st.cache_data # Cache data loading for performance
def load_data():
    narrow_df = pd.read_csv('narrowresult.csv')
    station_df = pd.read_csv('station.csv')

    # Preprocess narrow_df
    narrow_df['ActivityStartDate'] = pd.to_datetime(narrow_df['ActivityStartDate'], errors='coerce')
    narrow_df['ResultMeasureValue'] = pd.to_numeric(narrow_df['ResultMeasureValue'], errors='coerce')
    narrow_df.dropna(subset=['ActivityStartDate', 'ResultMeasureValue'], inplace=True)

    return narrow_df, station_df

narrow_df, station_df = load_data()

# --- Sidebar for Filters ---
st.sidebar.header("Filter Options")

# Characteristic Selection
characteristic_options = narrow_df['CharacteristicName'].unique()
selected_characteristic = st.sidebar.selectbox(
    "Select Water Quality Characteristic:",
    options=characteristic_options
)

# Filter narrow_df for the selected characteristic
filtered_char_df = narrow_df[narrow_df['CharacteristicName'] == selected_characteristic].copy()

if not filtered_char_df.empty:
    # Date Range Selection
    min_date = filtered_char_df['ActivityStartDate'].min().date()
    max_date = filtered_char_df['ActivityStartDate'].max().date()

    date_range = st.sidebar.date_input(
        "Select Date Range:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        filtered_char_df = filtered_char_df[
            (filtered_char_df['ActivityStartDate'] >= start_date) &
            (filtered_char_df['ActivityStartDate'] <= end_date)
        ]

    # Value Range Selection (dynamic based on characteristic)
    if not filtered_char_df.empty:
        min_val = float(filtered_char_df['ResultMeasureValue'].min())
        max_val = float(filtered_char_df['ResultMeasureValue'].max())

        # Handle case where min_val and max_val might be the same (e.g., single unique value)
        if min_val == max_val:
            value_range = st.sidebar.slider(
                f"Select {selected_characteristic} Value Range:",
                min_value=min_val - 1.0, 
                max_value=max_val + 1.0,
                value=(min_val, max_val)
            )
        else:
            value_range = st.sidebar.slider(
                f"Select {selected_characteristic} Value Range:",
                min_value=min_val, 
                max_value=max_val,
                value=(min_val, max_val)
            )

        filtered_char_df = filtered_char_df[
            (filtered_char_df['ResultMeasureValue'] >= value_range[0]) &
            (filtered_char_df['ResultMeasureValue'] <= value_range[1])
        ]
    else:
        st.sidebar.warning("No data available for the selected date range.")
else:
    st.sidebar.warning("No data available for the selected characteristic.")

# --- Main Content Area ---
if not filtered_char_df.empty:
    st.subheader(f"Filtered Data for {selected_characteristic}")

    # Get unique monitoring locations from the filtered data
    filtered_location_ids = filtered_char_df['MonitoringLocationIdentifier'].unique()
    mappable_filtered_sites = station_df[
        station_df['MonitoringLocationIdentifier'].isin(filtered_location_ids)
    ].copy()

    # Ensure lat/long are numeric and drop NaNs for mapping
    mappable_filtered_sites['LatitudeMeasure'] = pd.to_numeric(mappable_filtered_sites['LatitudeMeasure'], errors='coerce')
    mappable_filtered_sites['LongitudeMeasure'] = pd.to_numeric(mappable_filtered_sites['LongitudeMeasure'], errors='coerce')
    mappable_filtered_sites.dropna(subset=['LatitudeMeasure', 'LongitudeMeasure'], inplace=True)

    if not mappable_filtered_sites.empty:
        st.subheader("Monitoring Locations within Filtered Range")
        # Create a base map centered around the average of filtered sites
        initial_latitude = mappable_filtered_sites['LatitudeMeasure'].mean()
        initial_longitude = mappable_filtered_sites['LongitudeMeasure'].mean()

        m = folium.Map(location=[initial_latitude, initial_longitude], zoom_start=6)

        # Add markers for each filtered site
        for index, row in mappable_filtered_sites.iterrows():
            folium.Marker(
                location=[row['LatitudeMeasure'], row['LongitudeMeasure']],
                popup=f"{row['MonitoringLocationName']} ({row['MonitoringLocationIdentifier']})",
                tooltip=row['MonitoringLocationName']
            ).add_to(m)
        
        folium_static(m)

        st.subheader(f"Trend of {selected_characteristic} Over Time at Filtered Stations")
        
        # Merge with station names for plotting
        plot_df = pd.merge(filtered_char_df,
                           station_df[['MonitoringLocationIdentifier', 'MonitoringLocationName']].drop_duplicates(),
                           on='MonitoringLocationIdentifier',
                           how='left')

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.lineplot(
            data=plot_df,
            x='ActivityStartDate',
            y='ResultMeasureValue',
            hue='MonitoringLocationName',
            marker='o',
            errorbar=None,
            alpha=0.7,
            ax=ax
        )
        ax.set_title(f'{selected_characteristic} Over Time by Monitoring Site')
        ax.set_xlabel('Date')
        unit_code = plot_df['ResultMeasure/MeasureUnitCode'].dropna().iloc[0] if not plot_df['ResultMeasure/MeasureUnitCode'].dropna().empty else "Unit Unknown"
        ax.set_ylabel(f'{selected_characteristic} Value ({unit_code})')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend(title='Monitoring Site', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        st.pyplot(fig)

    else:
        st.warning("No stations found for mapping with the selected filters.")
else:
    st.info("Please adjust filters to see data.")
