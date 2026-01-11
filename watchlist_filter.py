import pandas as pd
import requests
import time
import ast
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import api_key

# =========================
# CONFIGURATION
# =========================

TMDB_API_KEY = api_key.api_key
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}"
SLEEP_SECONDS = 0.05
CAST_LIMIT = 10

# =========================
# GOOGLE SHEETS CONFIG
# =========================

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_NAME = "Watchlist Enriched"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# =========================
# TMDB METADATA FUNCTION
# =========================

def get_movie_metadata(title, year):
    search_params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "year": int(year) if not pd.isna(year) else None,
    }
    search_resp = requests.get(TMDB_SEARCH_URL, params=search_params, timeout=10)
    search_resp.raise_for_status()
    results = search_resp.json().get("results")
    if not results:
        return None

    movie_id = results[0]["id"]

    # Details
    details_resp = requests.get(TMDB_MOVIE_URL.format(movie_id), params={"api_key": TMDB_API_KEY}, timeout=10)
    details_resp.raise_for_status()
    details = details_resp.json()

    # Credits
    credits_resp = requests.get(TMDB_MOVIE_URL.format(movie_id)+"/credits", params={"api_key": TMDB_API_KEY}, timeout=10)
    credits_resp.raise_for_status()
    credits = credits_resp.json()

    directors = [c["name"] for c in credits.get("crew", []) if c.get("job")=="Director"]
    cast = [c["name"] for c in sorted(credits.get("cast", []), key=lambda x: x.get("order", 999))[:CAST_LIMIT]]

    return {
        "TMDB ID": movie_id,
        "Production Countries": [c["name"] for c in details.get("production_countries", [])],
        "Director": directors[0] if directors else "",
        "Cast": cast,
        "Genres": [g["name"] for g in details.get("genres", [])],
        "Original Language": details.get("original_language",""),
        "Runtime": details.get("runtime"),
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
    df_input["Year"] = pd.to_numeric(df_input["Year"], errors="coerce").astype("Int64")

    # Colonnes enrichies
    columns = ["Name","Year","TMDB ID","Production Countries","Director","Cast","Genres","Original Language","Runtime"]
    df_enriched = pd.DataFrame(columns=columns)

    # =========================
    # LOAD CACHE
    # =========================
    records = sheet.get_all_records()
    if records:
        df_enriched = pd.DataFrame(records)
        df_enriched["Year"] = pd.to_numeric(df_enriched["Year"], errors="coerce").astype("Int64")
        for col in ["Production Countries","Cast","Genres"]:
            if col in df_enriched.columns:
                df_enriched[col] = df_enriched[col].apply(lambda x: ast.literal_eval(x) if isinstance(x,str) and x.strip().startswith("[") else [])
    else:
        df_enriched = pd.DataFrame(columns=columns)

    processed_keys = set(zip(df_enriched["Name"], df_enriched["Year"]))

    # =========================
    # DETECT NEW FILMS
    # =========================
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
                metadata = {c:"" for c in columns if c not in ["Name","Year"]}
                metadata["Production Countries"] = []
                metadata["Cast"] = []
                metadata["Genres"] = []

            enriched_rows.append({"Name":row["Name"],"Year":row["Year"],**metadata})
            if progress_callback: progress_callback(i,len(df_to_process),row["Name"])
            time.sleep(SLEEP_SECONDS)

        df_new = pd.DataFrame(enriched_rows)
        df_enriched = pd.concat([df_enriched, df_new], ignore_index=True)

        # SAVE CACHE
        df_save = df_enriched.drop_duplicates(subset=["TMDB ID"], keep="first")
        for col in ["Production Countries","Cast","Genres"]:
            df_save[col] = df_save[col].apply(str)
        for col in ["Year","Runtime","TMDB ID"]:
            df_save[col] = df_save[col].astype("string").fillna("")
        df_save["Name"] = df_save["Name"].astype("string").fillna("")
        sheet.clear()
        sheet.update([df_save.columns.tolist()] + df_save.values.tolist())

    # =========================
    # APPLY FILTERS
    # =========================
    df_filtered = df_enriched.copy()

    if filters:
        for key, val in filters.items():
            if key=="year":  # tuple (min,max)
                df_filtered = df_filtered[df_filtered["Year"].notna() & (df_filtered["Year"]>=val[0]) & (df_filtered["Year"]<=val[1])]
            elif key.endswith("_include") or key.endswith("_exclude"):
                only_mode = False
                if isinstance(val, dict):  # dict {"values":[...],"only":True/False}
                    only_mode = val.get("only", False)
                    val = val.get("values", [])
                col = key.split("_")[0].title().replace("_"," ")
                if col in ["Director","Original Language"]:
                    if key.endswith("_include"): df_filtered = df_filtered[df_filtered[col].isin(val)]
                    else: df_filtered = df_filtered[~df_filtered[col].isin(val)]
                else: 
                    if key.endswith("_include"):
                        if only_mode:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: set(x)==set(val))]
                        else:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: any(v in x for v in val))]
                    else:  # exclude
                        if only_mode:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: set(x)!=set(val))]
                        else:
                            df_filtered = df_filtered[df_filtered[col].apply(lambda x: all(v not in x for v in val))]


    return df_filtered, not_found
