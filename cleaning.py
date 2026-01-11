import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = "service_account.json"
SHEET_NAME = "Watchlist Enriched"

def clean_duplicates():
    # 1. Authentication and Connection
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1

    # 2. Load Data from Google Sheets
    records = sheet.get_all_records()
    if not records:
        print("The spreadsheet is empty.")
        return
    
    df = pd.DataFrame(records)
    initial_count = len(df)

    # 3. Ensure uniform types for reliable comparison
    # We force Name to string and Year to a consistent numeric format
    df['Name'] = df['Name'].astype(str).str.strip()
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')

    # 4. Remove Duplicates based on Name and Year
    # This directly uses the columns without creating a temporary key
    df_cleaned = df.drop_duplicates(subset=['Name', 'Year'], keep='last')

    # 5. Update the spreadsheet
    if len(df_cleaned) < initial_count:
        # Full refresh: clear and rewrite
        sheet.clear()
        
        # Prepare the data: Headers + Values
        # We fill NaNs to avoid upload errors
        data_to_upload = [df_cleaned.columns.values.tolist()] + df_cleaned.fillna("").values.tolist()
        
        sheet.update(data_to_upload)
        print(f"Cleanup successful: {initial_count - len(df_cleaned)} duplicates removed.")
    else:
        print("No duplicates found. Your spreadsheet is already clean!")

if __name__ == "__main__":
    clean_duplicates()