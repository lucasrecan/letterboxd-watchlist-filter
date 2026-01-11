# Letterboxd Watchlist Filter - Web App

This web app allows you to filter your Letterboxd watchlist based on the production country of each film using data from TMDB (The Movie Database).  

It also keeps an **enriched cache** of films already processed in a Google Sheets spreadsheet, reducing repeated API queries and enabling incremental updates.

## Features

- Upload your Letterboxd watchlist CSV (must include columns `Name` and `Year`).
- Choose a country filter:
  - **Exclude films from this country**  
  - **Include only films from this country**
- Optionally, when including films from a country, you can choose to keep **only films produced exclusively** in that country.
- Generates a filtered CSV you can download and import into Letterboxd.
- Automatically updates a Google Sheet (`Watchlist Enriched`) with the production countries of newly processed films, so the next run will be faster.

## Limitations

- Some films or mini-series may **not be found on TMDB**; these will need manual checking.
- Occasionally, films may appear **in duplicate** in the Google Sheet or in the filtered CSV.
- TMDB data may be **inaccurate**, for example some films may be incorrectly marked as produced only in a certain country.

## How to Use

1. Go to the web app: [https://lb-watchlist-filter.streamlit.app/](https://lb-watchlist-filter.streamlit.app/)
2. Upload your Letterboxd watchlist CSV.
3. Select the filter options for country.
4. Click **Generate CSV**.
5. Download the filtered CSV to create a new list on Letterboxd.

## To Do / Future Improvements

- **Better error handling**: show user-friendly messages
- **Additional filters**: e.g., by genre, release year, director, or rating.
- **Progress indication**: show a loading bar or spinner during processing.
- **Duplicate handling**: prevent duplicate entries in the Google Sheet and filtered CSV.
- **User guidance**: add instructions in the app on where to get the CSV from Letterboxd and the required column names.

## Credits

Created by **Ribou**  
- GitHub: [lucasrecan](https://github.com/lucasrecan)  
- Letterboxd: [Ribou_](https://letterboxd.com/ribou_/)  

The project uses:  
- [TMDB API](https://www.themoviedb.org/documentation/api) for film metadata  
- [Streamlit](https://streamlit.io/) for the web interface  
- [Google Sheets API](https://developers.google.com/sheets/api) for persistent caching
