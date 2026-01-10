# watchlist_filter.py

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

# =========================
# GOOGLE SHEETS CONFIG
# =========================

SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_NAME = "Watchlist Enriched"

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    SERVICE_ACCOUNT_FILE, scope
)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1


# =========================
# TMDB QUERY FUNCTION
# =========================

def get_production_countries(title, year):
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "year": int(year) if not pd.isna(year) else None,
    }

    resp = requests.get(TMDB_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    results = resp.json().get("results")

    if not results:
        return []

    movie_id = results[0]["id"]

    details_resp = requests.get(
        TMDB_MOVIE_URL.format(movie_id),
        params={"api_key": TMDB_API_KEY},
        timeout=10,
    )
    details_resp.raise_for_status()

    details_data = details_resp.json()
    return [c["name"] for c in details_data.get("production_countries", [])]


# =========================
# MAIN FILTER FUNCTION
# =========================

def filter_watchlist(
    df_input: pd.DataFrame,
    filter_country: str = "United States of America",
    exclude_country: bool = True,
    only_this_country: bool = False,
):

    # ---- Input normalization ----
    df_input = df_input.copy()
    df_input["Year"] = pd.to_numeric(
        df_input["Year"], errors="coerce"
    ).astype("Int64")

    # ---- Always initialize ----
    df_enriched = pd.DataFrame(
        columns=["Name", "Year", "Production Countries"]
    )
    processed_keys = set()

    # =========================
    # LOAD ENRICHED DATA
    # =========================

    records = sheet.get_all_records()

    if records:
        df_enriched = pd.DataFrame(records)

        df_enriched["Year"] = pd.to_numeric(
            df_enriched["Year"], errors="coerce"
        ).astype("Int64")

        df_enriched["Production Countries"] = df_enriched[
            "Production Countries"
        ].apply(
            lambda x: ast.literal_eval(x)
            if isinstance(x, str) and x.strip().startswith("[")
            else []
        )

        processed_keys = set(zip(df_enriched["Name"], df_enriched["Year"]))

    # =========================
    # DETECT NEW FILMS
    # =========================

    df_to_process = df_input[
        ~df_input.apply(
            lambda r: (r["Name"], r["Year"]) in processed_keys,
            axis=1,
        )
    ]

    not_found = []

    # =========================
    # ENRICH NEW FILMS
    # =========================

    if not df_to_process.empty:
        production_countries = []

        for _, row in df_to_process.iterrows():
            try:
                countries = get_production_countries(row["Name"], row["Year"])
                if not countries:
                    not_found.append(f"{row['Name']} ({row['Year']})")
            except Exception:
                countries = []
                not_found.append(f"{row['Name']} ({row['Year']})")

            production_countries.append(countries)
            time.sleep(SLEEP_SECONDS)

        df_to_process = df_to_process.copy()
        df_to_process["Production Countries"] = production_countries

        df_enriched = pd.concat(
            [df_enriched, df_to_process], ignore_index=True
        )

        # =========================
        # SAVE BACK TO GOOGLE SHEET
        # =========================

        df_save = df_enriched.copy()
        
        # Avoid duplicates
        df_save = df_save.drop_duplicates(subset=["Name", "Year"], keep="first")
        # Production Countries -> string
        df_save["Production Countries"] = df_save["Production Countries"].apply(str)

        # Year -> string, NA -> empty
        df_save["Year"] = df_save["Year"].astype("string").fillna("")

        # Name -> string, NA -> empty (sécurité)
        df_save["Name"] = df_save["Name"].astype("string").fillna("")

        sheet.clear()
        sheet.update(
            [df_save.columns.tolist()]
            + df_save.values.tolist()
        )

    # =========================
    # FILTERING
    # =========================

    def country_filter(countries):
        if not isinstance(countries, list):
            return False

        if only_this_country:
            return len(countries) == 1 and countries[0] == filter_country

        if exclude_country:
            return filter_country not in countries

        return filter_country in countries

    df_filtered = df_enriched[
        df_enriched["Production Countries"].apply(country_filter)
    ]

    return df_filtered, not_found
