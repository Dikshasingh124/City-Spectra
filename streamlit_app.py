import streamlit as st

# Example city data, could be loaded from DB or API
city_data = {
    'Pune': {'Commute': 30, 'Infrastructure': 8, 'Amenities': 7, 'Safety': 9, 'Budget': 6},
    'Bangalore': {'Commute': 45, 'Infrastructure': 7, 'Amenities': 8, 'Safety': 7, 'Budget': 5},
    'Gurugram': {'Commute': 40, 'Infrastructure': 7, 'Amenities': 6, 'Safety': 8, 'Budget': 7},
    'Noida': {'Commute': 35, 'Infrastructure': 6, 'Amenities': 7, 'Safety': 6, 'Budget': 8},
    'Chennai': {'Commute': 30, 'Infrastructure': 7, 'Amenities': 7, 'Safety': 7, 'Budget': 6},
}

st.title("City Spectra - Data Insights")

query_params = st.experimental_get_query_params()
default_city = list(city_data.keys())[0]
city = query_params.get("city", [default_city])[0]

city = st.selectbox("Select a City", list(city_data.keys()), index=list(city_data.keys()).index(city))

if city:
    data = city_data.get(city)
    st.subheader(f"Data for {city}")
    for k, v in data.items():
        st.write(f"**{k}:** {v}")
