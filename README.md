# Letterboxd Watchlist Filter - Web App

This web app allows you to filter your Letterboxd watchlist with advanced criteria (Country, Director, Language, etc.) using data from TMDB (The Movie Database).

It maintains an enriched persistent cache in Google Sheets, allowing for incremental updates and reducing API calls.

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
2. Export your watchlist from Letterboxd (watchlist -> Export watchlist on the right or got to https://letterboxd.com/your-username/watchlist/export/)
3. Upload your Letterboxd watchlist CSV.
4. Select the filter options.
5. Click **Generate CSV**.
6. Download the CSV file when it's ready.
6. When creating or editing a list on Letterboxd, choose import and select the downloaded file.

## To Do / Future Improvements

- **User guidance**: add instructions in the app on where to get the CSV from Letterboxd and the required column names.
- **Brief explanation in-app**: add a small section in the web app to explain how the filtering works.

## Credits

Created by **Ribou**  
- GitHub: [lucasrecan](https://github.com/lucasrecan)  
- Letterboxd: [Ribou_](https://letterboxd.com/ribou_/)  

The project uses:  
- [TMDB API](https://www.themoviedb.org/documentation/api) for film metadata  
- [Streamlit](https://streamlit.io/) for the web interface  
- [Google Sheets API](https://developers.google.com/sheets/api) for persistent caching
