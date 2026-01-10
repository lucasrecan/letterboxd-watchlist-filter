import pandas as pd
import requests
import time
from tqdm import tqdm
from pathlib import Path
import ast
import api_key

# =========================
# CONFIGURATION
# =========================

TMDB_API_KEY = api_key.api_key

# Input / output files
INPUT_CSV = "watchlist.csv"               # Raw Letterboxd export
ENRICHED_CSV = "watchlist_enriched.csv"  # Persistent enriched CSV to store all films and production countries
OUTPUT_CSV = "watchlist_filtered.csv"    # Final filtered view

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}"

SLEEP_SECONDS = 0.05  # Small sleep to avoid micro-bursts and prevent throttling by TMDB

# =========================
# COUNTRY FILTER CONFIGURATION
# =========================

FILTER_COUNTRY = "France"  # Country to filter
EXCLUDE_COUNTRY = False   # True -> remove films containing FILTER_COUNTRY
                         # False -> keep only films containing FILTER_COUNTRY
ONLY_THIS_COUNTRY = True # True -> keep only films exclusively produced in FILTER_COUNTRY (used only if EXCLUDE_COUNTRY=False)

# =========================
# LOAD CURRENT WATCHLIST
# =========================

df_input = pd.read_csv(INPUT_CSV)
df_input["Year"] = df_input["Year"].astype("Int64")  # Ensure year column is integer for TMDB queries

# =========================
# LOAD EXISTING ENRICHED CSV
# =========================

if Path(ENRICHED_CSV).exists():
    df_enriched = pd.read_csv(ENRICHED_CSV)
    df_enriched["Year"] = df_enriched["Year"].astype("Int64")
    
    # Convert production countries back to lists if they were read as strings
    # (lists appear as strings in the CSV when they contain commas)
    df_enriched["Production Countries"] = df_enriched["Production Countries"].apply(
        lambda x: ast.literal_eval(x) if isinstance(x, str) and x else []
    )
    
    processed_keys = set(zip(df_enriched["Name"], df_enriched["Year"]))
    print(f"{len(df_enriched)} films already enriched")
else:
    df_enriched = pd.DataFrame()
    processed_keys = set()
    print("No existing enriched CSV found, full processing will be done")

# =========================
# DETECT NEW FILMS TO PROCESS
# =========================

df_to_process = df_input[
    ~df_input.apply(lambda r: (r["Name"], r["Year"]) in processed_keys, axis=1)
]

print(f"{len(df_to_process)} new films to process")

# =========================
# FUNCTION TO QUERY TMDB
# =========================

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
        params={
            "api_key": TMDB_API_KEY,
            "append_to_response": "production_countries"
        },
        timeout=10
    )
    details_resp.raise_for_status()
    details_data = details_resp.json()

    return [c["name"] for c in details_data.get("production_countries", [])]

# =========================
# ENRICH NEW FILMS (INCREMENTAL)
# =========================

not_found = []  # List to keep track of films/series not found on TMDB

if not df_to_process.empty:
    production_countries = []

    for _, row in tqdm(df_to_process.iterrows(), total=len(df_to_process)):
        try:
            countries = get_production_countries(row["Name"], row["Year"])
            # If no countries found, log it (likely series or not in TMDB)
            if not countries:
                not_found.append(f"{row['Name']} ({row['Year']})")
        except Exception:
            countries = []
            not_found.append(f"{row['Name']} ({row['Year']})")  # Log errors too
        production_countries.append(countries)
        time.sleep(SLEEP_SECONDS)

    df_to_process = df_to_process.copy()
    df_to_process["Production Countries"] = production_countries

    df_enriched = pd.concat([df_enriched, df_to_process], ignore_index=True)

    df_enriched.to_csv(ENRICHED_CSV, index=False)
    print(f"Enriched CSV updated: {ENRICHED_CSV}")
else:
    print("No new films to process, skipping TMDB queries")

# =========================
# LOG ITEMS NOT FOUND
# =========================

if not_found:
    print("\nThe following films/series were not found on TMDB. Please check manually:")
    for title in not_found:
        print(f" - {title}")

# =========================
# GENERATE FILTERED VIEW
# =========================

if EXCLUDE_COUNTRY:
    # Remove all films containing FILTER_COUNTRY
    df_filtered = df_enriched[
        ~df_enriched["Production Countries"].apply(
            lambda c: isinstance(c, list) and FILTER_COUNTRY in c
        )
    ]
else:
    # Keep films with FILTER_COUNTRY
    if ONLY_THIS_COUNTRY:
        df_filtered = df_enriched[
            df_enriched["Production Countries"].apply(
                lambda c: isinstance(c, list) and c == [FILTER_COUNTRY]
            )
        ]
    else:
        df_filtered = df_enriched[
            df_enriched["Production Countries"].apply(
                lambda c: isinstance(c, list) and FILTER_COUNTRY in c
            )
        ]

df_filtered.to_csv(OUTPUT_CSV, index=False)

print(f"\nFiltered CSV generated: {OUTPUT_CSV}")
print(f"Films kept: {len(df_filtered)} / {len(df_enriched)}")
print(f"Country filter applied: {FILTER_COUNTRY}")
print(f"Exclude country? {EXCLUDE_COUNTRY}")
print(f"Only this country? {ONLY_THIS_COUNTRY}")
