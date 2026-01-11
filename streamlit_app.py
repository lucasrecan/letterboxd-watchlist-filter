import streamlit as st
import pandas as pd
from watchlist_filter import filter_watchlist

st.set_page_config(page_title="Letterboxd Watchlist Filter")
st.title("Letterboxd Watchlist Filter")

uploaded_file = st.file_uploader("Upload your Letterboxd watchlist CSV", type="csv")

# =========================
# Filters dictionary
# =========================
filters = {}

if uploaded_file:
    st.subheader("Enable Filters")

    # --- Production Country ---
    if st.checkbox("Filter by Production Country"):
        st.markdown("Example: `United States of America, France`")
        include_exclude = st.radio("Mode",("Include","Exclude"), key="country_mode")
        countries = st.text_input("Countries (comma separated)", key="countries").split(",")
        countries = [c.strip() for c in countries if c.strip()]
        only_mode = st.checkbox("Include only these countries?", False, key="countries_only")
        if include_exclude=="Include": 
            filters["production countries_include"] = {"values": countries, "only": only_mode}
        else: 
            filters["production countries_exclude"] = {"values": countries, "only": False}

    # --- Year ---
    if st.checkbox("Filter by Year"):
        filters["year"] = st.slider("Year Range", 1900, 2030, (2000,2023))

    # --- Director ---
    if st.checkbox("Filter by Director"):
        st.markdown("Example: `Christopher Nolan, Kaurismaki`")
        inc = st.text_input("Include Director(s)").split(",")
        exc = st.text_input("Exclude Director(s)").split(",")
        inc = [x.strip() for x in inc if x.strip()]
        exc = [x.strip() for x in exc if x.strip()]
        only_mode = st.checkbox("Include only these directors?", False, key="director_only")
        filters["director_include"] = {"values": inc, "only": only_mode}
        filters["director_exclude"] = {"values": exc, "only": False}

    # --- Genre ---
    if st.checkbox("Filter by Genre"):
        st.markdown("Example: `Drama, Action`")
        inc = st.text_input("Include Genre(s)").split(",")
        exc = st.text_input("Exclude Genre(s)").split(",")
        inc = [x.strip() for x in inc if x.strip()]
        exc = [x.strip() for x in exc if x.strip()]
        only_mode = st.checkbox("Include only these genres?", False, key="genres_only")
        filters["genres_include"] = {"values": inc, "only": only_mode}
        filters["genres_exclude"] = {"values": exc, "only": False}

    # --- Cast ---
    if st.checkbox("Filter by Cast"):
        st.markdown("Example: `Brad Pitt, Leonardo DiCaprio`")
        inc = st.text_input("Include Actor(s)").split(",")
        exc = st.text_input("Exclude Actor(s)").split(",")
        inc = [x.strip() for x in inc if x.strip()]
        exc = [x.strip() for x in exc if x.strip()]
        only_mode = st.checkbox("Include only these actors?", False, key="cast_only")
        filters["cast_include"] = {"values": inc, "only": only_mode}
        filters["cast_exclude"] = {"values": exc, "only": False}

    # --- Original Language ---
    if st.checkbox("Filter by Language"):
        st.markdown("Example: `en, fr`")
        inc = st.text_input("Include Language(s)").split(",")
        exc = st.text_input("Exclude Language(s)").split(",")
        inc = [x.strip() for x in inc if x.strip()]
        exc = [x.strip() for x in exc if x.strip()]
        filters["original language_include"] = {"values": inc, "only": False}
        filters["original language_exclude"] = {"values": exc, "only": False}

    # --- Runtime ---
    if st.checkbox("Filter by Runtime"):
        min_runtime, max_runtime = st.slider("Runtime Range (minutes)", 0, 500, (0,300))
        filters["runtime"] = (min_runtime,max_runtime)

    # =========================
    # GENERATE CSV
    # =========================
    if st.button("Generate CSV"):
        df_input = pd.read_csv(uploaded_file)
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(i,total,movie_name):
            status_text.text(f"Processing: {movie_name} [{i}/{total}]")
            progress_bar.progress(i/total)

        with st.spinner("Processing..."):
            df_filtered, not_found = filter_watchlist(df_input, filters=filters, progress_callback=update_progress)

        st.success(f"Filtered CSV ready! {len(df_filtered)} films kept.")
        st.download_button(
            "Download filtered CSV",
            df_filtered.to_csv(index=False).encode("utf-8"),
            file_name="watchlist_filtered.csv",
            mime="text/csv"
        )

        if not_found:
            st.write("Films not found on TMDB:")
            for f in not_found: st.write(f" - {f}")
