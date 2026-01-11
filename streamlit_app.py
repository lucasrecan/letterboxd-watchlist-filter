import streamlit as st
import pandas as pd
from watchlist_filter import filter_watchlist

# Page Configuration
st.set_page_config(
    page_title="Letterboxd Watchlist Filter"#,
    #layout="wide"
)

st.title("Letterboxd Watchlist Filter")
st.markdown("Filter your exported watchlist using the TMDB API.")

# =========================
# 1. IMPORT SECTION (Main Page)
# =========================
st.header("1. Import Watchlist")
uploaded_file = st.file_uploader("Upload your Letterboxd CSV file", type=["csv"])

df_input = None

if uploaded_file:
    try:
        # Reset file pointer to beginning to avoid "No columns to parse" error
        uploaded_file.seek(0)
        df_input = pd.read_csv(uploaded_file)
        
        # Basic validation to ensure it's a valid CSV
        if df_input.empty or len(df_input.columns) < 1:
            st.error("The file seems empty or invalid.")
            df_input = None
        else:
            st.info(f"File loaded. {len(df_input)} movies found.")
            with st.expander("Preview Data"):
                st.dataframe(df_input.head(3), width='stretch')
                
    except Exception as e:
        st.error(f"Error reading the file: {e}")
        st.stop()

# =========================
# 2. FILTERS CONFIGURATION
# =========================
filters = {}

# Standard TMDB Genre List
GENRES_LIST = [
    "Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", 
    "Drama", "Family", "Fantasy", "History", "Horror", "Music", "Mystery", 
    "Romance", "Science Fiction", "TV Movie", "Thriller", "War", "Western"
]

# if df_input is not None:
st.header("2. Configure Filters")
st.markdown("---")

col_details, col_people = st.columns(2)

# --- GROUP 1: MOVIE DETAILS ---
with col_details:
    st.subheader("Details")
        
    # Year
    if st.checkbox("Filter by Release Year", value=True):
        filters["year"] = st.slider("Release Period", 1900, 2030, (1990, 2024))
    
    st.markdown("---")

    # Runtime
    if st.checkbox("Filter by Runtime"):
        min_r, max_r = st.slider("Duration (minutes)", 0, 500, (60, 180))
        filters["runtime"] = (min_r, max_r)
    
    st.markdown("---")

    # Genre
    if st.checkbox("Filter by Genre"):
        sel_inc = st.multiselect("Include Genres", GENRES_LIST)
        
        # Logic strict ONLY for Include
        only_genre = False
        if sel_inc:
            st.caption(f"Keep movies that contain at least one of these: {', '.join(sel_inc)}")
            only_genre = st.checkbox(
                "Exclusive match? (Movies containing ONLY these genres and nothing else)", 
                value=False,
                key="genre_only"
            )
        
        sel_exc = st.multiselect("Exclude Genres", GENRES_LIST)
        
        if sel_inc: filters["genres_include"] = {"values": sel_inc, "only": only_genre}
        if sel_exc: filters["genres_exclude"] = {"values": sel_exc, "only": False}

    st.markdown("---")

    # Country
    if st.checkbox("Filter by Production Country"):
        c_mode = st.radio("Country Mode", ["Include", "Exclude"], horizontal=True)
        c_text = st.text_input("Countries (e.g., United States of America, France)", help="Separate by commas")
        c_list = [c.strip() for c in c_text.split(",") if c.strip()]
        
        c_only = False
        # Only show "Exclusive" option if Mode is Include AND list is not empty
        if c_mode == "Include" and c_list:
            st.caption(f"Keep movies produced in: {', '.join(c_list)}")
            c_only = st.checkbox(
                "Exclusive match? (Movies produced ONLY in these countries, no co-productions)", 
                value=False, 
                key="c_only"
            )
        
        if c_list:
            key = "production countries_include" if c_mode == "Include" else "production countries_exclude"
            filters[key] = {"values": c_list, "only": c_only}

# --- GROUP 2: CAST & CREW ---
with col_people:
    st.subheader("People & Language")
        
    # Helper function for people inputs
    def people_filter_ui(label, key_prefix):
        st.markdown(f"**{label}**")
        inc_text = st.text_input(f"Include {label}", key=f"{key_prefix}_inc")
        inc = [x.strip() for x in inc_text.split(",") if x.strip()]
        
        only_mode = False
        if inc:
            only_mode = st.checkbox(
                f"Exclusive match? ({label} is ONLY these people)", 
                key=f"{key_prefix}_only"
            )
        
        exc_text = st.text_input(f"Exclude {label}", key=f"{key_prefix}_exc")
        exc = [x.strip() for x in exc_text.split(",") if x.strip()]
        
        return inc, exc, only_mode

    # Director
    if st.checkbox("Filter by Director"):
        st.caption("e.g., Alfonso Cuarón, Nick Park")
        d_inc, d_exc, d_only = people_filter_ui("Director", "dir")
        if d_inc: filters["director_include"] = {"values": d_inc, "only": d_only}
        if d_exc: filters["director_exclude"] = {"values": d_exc, "only": False}

    st.markdown("---")

    # Cast
    if st.checkbox("Filter by Cast"):
        st.caption("e.g., Ralph Fiennes, Tilda Swinton")
        a_inc, a_exc, a_only = people_filter_ui("Actor/Actress", "act")
        if a_inc: filters["cast_include"] = {"values": a_inc, "only": a_only}
        if a_exc: filters["cast_exclude"] = {"values": a_exc, "only": False}
    
    st.markdown("---")

    # Language
    if st.checkbox("Filter by Original Language"):
        st.caption("e.g., 'en' for English, 'fr' for French")
        l_inc_text = st.text_input("Include Language (ISO code)", key="lang_inc")
        l_exc_text = st.text_input("Exclude Language (ISO code)", key="lang_exc")
        
        l_inc = [x.strip() for x in l_inc_text.split(",") if x.strip()]
        l_exc = [x.strip() for x in l_exc_text.split(",") if x.strip()]
        
        if l_inc: filters["original language_include"] = {"values": l_inc, "only": False}
        if l_exc: filters["original language_exclude"] = {"values": l_exc, "only": False}

# =========================
# 3. RESULTS
# =========================
st.header("3. Results")
st.markdown("---")

col_btn, _, _ = st.columns([1, 2, 2])
with col_btn:
    run_filter = st.button("Generate CSV", type="primary", width='stretch',disabled=(uploaded_file is None))

if run_filter and df_input is not None:
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(i, total, movie_name):
        status_text.text(f"Processing {i}/{total}: {movie_name}")
        progress_bar.progress(i/total)

    try:
        with st.spinner("Querying TMDB..."):
            # Pass the already loaded dataframe
            df_filtered, not_found = filter_watchlist(df_input, filters=filters, progress_callback=update_progress)

        st.success(f"Processing Complete. {len(df_filtered)} movies remaining.")
        
        # Download & Preview
        c_res1, c_res2 = st.columns([1, 2])
        with c_res1:
            st.download_button(
                "Download Filtered CSV",
                df_filtered.to_csv(index=False).encode("utf-8"),
                file_name="watchlist_filtered.csv",
                mime="text/csv",
                type="primary",
                width='stretch'
            )
        with c_res2:
            with st.expander("View Filtered List"):
                st.dataframe(df_filtered, width='stretch')

        if not_found:
            st.warning(f"{len(not_found)} movies could not be identified on TMDB.")
            with st.expander("View missing movies"):
                st.write(not_found)

    except Exception as e:
        st.error(f"An error occurred during filtering: {e}")

if not uploaded_file:
    st.info("Please upload a CSV file in section 1 to begin.")


with st.expander("How does this app work?"):
    st.markdown("""
    **1. Upload your Letterboxd watchlist** Export your watchlist from Letterboxd as a CSV file and upload it here. 
    The app requires at least the **Name** and **Year** columns to identify films.

    **2. High-Speed Enrichment & Caching** The app checks our **Google Sheets cache** first. If a film is missing, it fetches metadata (Country, Director, Language, Runtime, Cast) from **TMDB**. 
    New data is automatically saved to the cache to make future runs instant.

    **3. Advanced Filtering** You can now filter your list using multiple criteria:
    * **Country**: Include or exclude specific countries.
    * **Director**: Keep or remove films from specific filmmakers.
    * **Language**: Filter by original version language.
    * **Year**: Define a specific release period.
    * And more.

    **4. Export & Sync** Download the final filtered CSV, which is ready to be imported back into a Letterboxd list. 
    *Note: A maintenance script runs periodically to ensure the cache remains clean and duplicate-free.*
    """)

st.markdown("---")
st.markdown(
    "Created by Ribou. "
    "Github: [lucasrecan](https://github.com/lucasrecan). "
    "Letterboxd: [Ribou_](https://letterboxd.com/ribou_/)."
)
st.markdown(
    "[Source code](https://github.com/lucasrecan/letterboxd-watchlist-filter/tree/webapp)"
)