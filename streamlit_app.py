import streamlit as st
import pandas as pd
from watchlist_filter import filter_watchlist

st.title("Letterboxd Watchlist Filter")
st.set_page_config(page_title="Letterboxd Watchlist Filter")

uploaded_file = st.file_uploader("Upload your Letterboxd watchlist CSV", type="csv")

filter_country = st.text_input("Country to filter", "United States of America")
exclude_country = st.checkbox("Exclude films with this country?", True)
only_this_country = st.checkbox("Only films exclusively in this country?", False)

if uploaded_file is not None and st.button("Generate CSV"):
    df_input = pd.read_csv(uploaded_file)
    
    with st.spinner("Processing... this may take a few seconds per film"):
        df_filtered, not_found = filter_watchlist(
            df_input,
            filter_country=filter_country,
            exclude_country=exclude_country,
            only_this_country=only_this_country
        )
    
    st.success(f"Filtered CSV ready! {len(df_filtered)} films kept.")
    
    st.download_button(
        "Download filtered CSV",
        df_filtered.to_csv(index=False).encode("utf-8"),
        file_name="watchlist_filtered.csv",
        mime="text/csv"
    )

    if not_found:
        st.write("The following films/series were not found on TMDB (check manually):")
        for title in not_found:
            st.write(f" - {title}")

st.markdown("---")
st.markdown(
    "Created by Ribou. "
    "Github: [lucasrecan](https://github.com/lucasrecan). "
    "Letterboxd: [Ribou_](https://letterboxd.com/ribou_/)."
)
st.markdown(
    "[Source code](https://github.com/lucasrecan/letterboxd-watchlist-filter)."
)