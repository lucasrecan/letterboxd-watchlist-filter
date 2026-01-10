For the moment, this script filters a `watchlist.csv` to create a `watchlist_filtered.csv` containing only films not produced in the USA according to TMDB.

It also creates a `watchlist_enriched.csv` to keep track of films already found on TMDB, allowing updates.

To execute : 

1. you need python
2. add your TMDB api key in `api_key.py`
3. export your letterboxd watchlist and put it in the same directory (it must include columns `Name` and `Year`)
4. run `main.py`

After execution, you can create a new list on letterboxd and import `watchlist_filtered.csv`.

Notes :

- Check the console after the script runs for any items that were not found on TMDB, which need to be checked manually (mini-series for example).
- You can change the country to filter out by editing the string 'United States of America' in the script (currently around line 147).
