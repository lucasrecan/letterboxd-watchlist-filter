import pandas as pd
import requests
import time
import ast
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st
import json
# =========================
# CONFIGURATION
# =========================

TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}"
SLEEP_SECONDS = 0.0
CAST_LIMIT = 10
# Create a global session for connection pooling
http_session = requests.Session()

# =========================
# GOOGLE SHEETS CONFIG
# =========================

SERVICE_ACCOUNT_JSON = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
SHEET_NAME = "Watchlist Enriched"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(SERVICE_ACCOUNT_JSON, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# =========================
# TMDB METADATA FUNCTION
# =========================

def get_movie_metadata(title, year):
    # 1. Search for the movie ID
    search_params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "year": int(year) if not pd.isna(year) else None,
    }
    # Using session for faster connection handling
    search_resp = http_session.get(TMDB_SEARCH_URL, params=search_params, timeout=10)
    search_resp.raise_for_status()
    results = search_resp.json().get("results")
    
    if not results:
        return None

    movie_id = results[0]["id"]

    # 2. Combined Details + Credits in ONE call using append_to_response
    # This divides the number of calls by 2 for the enrichment phase
    detail_params = {
        "api_key": TMDB_API_KEY,
        "append_to_response": "credits"
    }
    resp = http_session.get(TMDB_MOVIE_URL.format(movie_id), params=detail_params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    # Extract credits from the nested response
    credits_data = data.get("credits", {})
    directors = [c["name"] for c in credits_data.get("crew", []) if c.get("job") == "Director"]
    cast = [c["name"] for c in sorted(credits_data.get("cast", []), key=lambda x: x.get("order", 999))[:CAST_LIMIT]]

    return {
        "TMDB ID": movie_id,
        "Production Countries": [c["name"] for c in data.get("production_countries", [])],
        "Director": directors[0] if directors else "",
        "Cast": cast,
        "Genres": [g["name"] for g in data.get("genres", [])],
        "Original Language": data.get("original_language", ""),
        "Runtime": data.get("runtime"),
    }

# =========================
# MAIN FILTER FUNCTION
# =========================

def filter_watchlist(
    df_input: pd.DataFrame,
    filters: dict = None,
    progress_callback=None,
):
    df_input = df_input.copy()
    
    # Standardize input types for comparison
    df_input["Name"] = df_input["Name"].astype(str)
    df_input["Year"] = pd.to_numeric(df_input["Year"], errors="coerce").astype("Int64")

    columns = ["Name","Year","TMDB ID","Production Countries","Director","Cast","Genres","Original Language","Runtime"]
    df_enriched = pd.DataFrame(columns=columns)

    # =========================
    # LOAD CACHE
    # =========================
    records = sheet.get_all_records()
    if records:
        df_enriched = pd.DataFrame(records)
        # Ensure correct types for the cached data
        df_enriched["Name"] = df_enriched["Name"].astype(str)
        df_enriched["Year"] = pd.to_numeric(df_enriched["Year"], errors="coerce").astype("Int64")
        
        for col in ["Production Countries","Cast","Genres"]:
            if col in df_enriched.columns:
                df_enriched[col] = df_enriched[col].apply(lambda x: ast.literal_eval(x) if isinstance(x,str) and x.strip().startswith("[") else [])
    else:
        df_enriched = pd.DataFrame(columns=columns)

    # =========================
    # DETECT NEW FILMS
    # =========================
    # Create unique keys to avoid duplicates (e.g., films like '300' or '2046')
    processed_keys = set(zip(df_enriched["Name"], df_enriched["Year"]))
    df_to_process = df_input[~df_input.apply(lambda r: (r["Name"], r["Year"]) in processed_keys, axis=1)]
    not_found = []

    # =========================
    # ENRICH NEW FILMS
    # =========================
    if not df_to_process.empty:
        enriched_rows = []
        for i, (_, row) in enumerate(df_to_process.iterrows(), start=1):
            try:
                metadata = get_movie_metadata(row["Name"], row["Year"])
            except Exception:
                metadata = None

            if metadata is None:
                not_found.append(f"{row['Name']} ({row['Year']})")
                # Create empty structure for missing films to prevent re-processing
                metadata = {c:"" for c in columns if c not in ["Name","Year"]}
                metadata["Production Countries"] = []
                metadata["Cast"] = []
                metadata["Genres"] = []

            enriched_rows.append({"Name": str(row["Name"]), "Year": row["Year"], **metadata})
            if progress_callback: progress_callback(i, len(df_to_process), row["Name"])
            if SLEEP_SECONDS > 0.0:
                time.sleep(SLEEP_SECONDS)

        df_new = pd.DataFrame(enriched_rows)
        
        # Merge new movies into the local session DataFrame
        df_enriched = pd.concat([df_enriched, df_new], ignore_index=True)

        # =========================
        # INCREMENTAL SAVE TO GOOGLE SHEETS
        # =========================
        if not df_new.empty:
            df_to_append = df_new.copy()
            
            # Format lists as strings for Google Sheets
            for col in ["Production Countries", "Cast", "Genres"]:
                df_to_append[col] = df_to_append[col].apply(str)
            
            # Ensure numeric/IDs are clean strings for the API
            for col in ["Year", "Runtime", "TMDB ID"]:
                df_to_append[col] = df_to_append[col].astype(str).replace(["<NA>", "nan", "None"], "")
            
            df_to_append["Name"] = df_to_append["Name"].astype(str).fillna("")

            # Incremental append (no clear() needed)
            sheet.append_rows(
                df_to_append.values.tolist(), 
                value_input_option="USER_ENTERED"
            )

    # =========================
    # FINAL DEDUPLICATION
    # =========================
    df_enriched = df_enriched.drop_duplicates(subset=["Name", "Year"], keep="last")

    # =========================
    # APPLY FILTERS
    # =========================
    df_filtered = pd.merge(
        df_input[["Name", "Year"]], 
        df_enriched, 
        on=["Name", "Year"], 
        how="inner"
    )

    if filters:
        for key, val in filters.items():
            if key=="year":
                df_filtered = df_filtered[df_filtered["Year"].notna() & (df_filtered["Year"]>=val[0]) & (df_filtered["Year"]<=val[1])]
            elif key.endswith("_include") or key.endswith("_exclude"):
                only_mode = False
                if isinstance(val, dict):
                    only_mode = val.get("only", False)
                    val = val.get("values", [])
                
                col = key.split("_")[0].title().replace("_"," ")
                
                if col in ["Director","Original Language"]:
                    if key.endswith("_include"): 
                        df_filtered = df_filtered[df_filtered[col].isin(val)]
                    else: 
                        df_filtered = df_filtered[~df_filtered[col].isin(val)]
                else: 
                    if key.endswith("_include"):
                        if only_mode:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: set(x)==set(val))]
                        else:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: any(v in x for v in val))]
                    else:  # exclude
                        # Note: exclude with 'only' isn't standard, we keep logic for consistency
                        if only_mode:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: set(x)!=set(val))]
                        else:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: all(v not in x for v in val))]

    return df_filtered, not_found