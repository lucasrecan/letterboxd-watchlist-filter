For the moment, this script filters a `watchlist.csv` to create a `watchlist_filtered.csv` according to the production country of each film according to TMDB.

It also creates a `watchlist_enriched.csv` to keep track of films already found on TMDB, allowing updates.

You can configure the country filter in `main.py` using three variables:

- `FILTER_COUNTRY`: the country to filter (e.g. "United States of America", "France")
- `EXCLUDE_COUNTRY`: 
    - True -> remove all films containing `FILTER_COUNTRY`
    - False -> keep only films containing `FILTER_COUNTRY`
- `ONLY_THIS_COUNTRY`: 
    - True -> keep only films produced exclusively in `FILTER_COUNTRY`
    - False -> keep films where `FILTER_COUNTRY` is one of the production countries
    
    (used only if `EXCLUDE_COUNTRY` is False)

To execute: 

1. you need Python
2. add your TMDB API key in `api_key.py`
3. export your Letterboxd watchlist and put it in the same directory (it must include columns `Name` and `Year`)
4. run `main.py`

After execution, you can create a new list on Letterboxd and import `watchlist_filtered.csv`.

Notes:

- Check the console after the script runs for any items that were not found on TMDB, which need to be checked manually (mini-series for example).
- Can be wrong sometimes (for example, Beef (2023) and The Hunt (2012) are incorrectly considered as produced only in France).
