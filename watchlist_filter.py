# watchlist_filter.py
import pandas as pd
import requests
import time
from pathlib import Path
import ast
import api_key

TMDB_API_KEY = api_key.api_key
TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}"
SLEEP_SECONDS = 0.05  # Small sleep to avoid bursts

def get_production_countries(title, year):
    """
    Query TMDB for a given movie title and year.
    Returns a list of production countries, empty if not found.
    """
    search_params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "year": int(year) if not pd.isna(year) else None
    }

    search_resp = requests.get(TMDB_SEARCH_URL, params=search_params, timeout=10)
    search_resp.raise_for_status()
    search_data = search_resp.json()

    if not search_data["results"]:
        return []

    movie_id = search_data["results"][0]["id"]

    details_resp = requests.get(
        TMDB_MOVIE_URL.format(movie_id),
        params={"api_key": TMDB_API_KEY},
        timeout=10
    )
    details_resp.raise_for_status()
    details_data = details_resp.json()

    return [c["name"] for c in details_data.get("production_countries", [])]


def filter_watchlist(
    df_input: pd.DataFrame,
    filter_country: str = "United States of America",
    exclude_country: bool = True,
    only_this_country: bool = False,
    enriched_csv_path: str = "watchlist_enriched.csv"
):
    """
    Enrich a watchlist DataFrame via TMDB and filter by country.
    
    Returns:
        df_filtered: filtered DataFrame
        not_found: list of titles not found on TMDB
    """
    df_input = df_input.copy()
    df_input["Year"] = df_input["Year"].astype("Int64")

    # Load enriched CSV if exists
    if Path(enriched_csv_path).exists():
        df_enriched = pd.read_csv(enriched_csv_path)
        df_enriched["Year"] = df_enriched["Year"].astype("Int64")
        df_enriched["Production Countries"] = df_enriched["Production Countries"].apply(
            lambda x: ast.literal_eval(x) if isinstance(x, str) and x else []
        )
        processed_keys = set(zip(df_enriched["Name"], df_enriched["Year"]))
    else:
        df_enriched = pd.DataFrame()
        processed_keys = set()

    # Detect new films to process
    df_to_process = df_input[
        ~df_input.apply(lambda r: (r["Name"], r["Year"]) in processed_keys, axis=1)
    ]

    not_found = []

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

        df_to_process["Production Countries"] = production_countries
        df_enriched = pd.concat([df_enriched, df_to_process], ignore_index=True)

        # Save enriched CSV for incremental updates
        df_enriched.to_csv(enriched_csv_path, index=False)

    # Filtering
    def country_filter(countries):
        if not isinstance(countries, list):
            return False
        if exclude_country:
            return filter_country not in countries
        else:
            if only_this_country:
                return len(countries) == 1 and countries[0].strip() == filter_country
            else:
                return filter_country in countries

    df_filtered = df_enriched[df_enriched["Production Countries"].apply(country_filter)]

    return df_filtered, not_found
