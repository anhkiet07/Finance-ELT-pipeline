import os
from dotenv import load_dotenv
import psycopg2
from vnstock import Vnstock

load_dotenv(dotenv_path="../docker/.env")

DB_config = {
    "host" : "localhost",
    "port" : 5434,
    "user" : os.getenv("WAREHOUSE_DB_USER"),
    "password" : os.getenv("WAREHOUSE_DB_PASSWORD"),
    "dbname" : os.getenv("WAREHOUSE_DB_NAME")
}

TICKERS = ["VCB", "TCB", "ACB", "BID", "LPB"]

def fetch_stock_price(ticker: str, start_date: str, end_date: str):
    stock = Vnstock().stock(symbol=ticker, source="VCI")
    df = stock.quote.history(start=start_date, end=end_date, interval="1D")
    df["ticker"] = ticker
    return df

def test_connection():
    conn = psycopg2.connect(**DB_config)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    result = cursor.fetchone()
    print(f"Connected to database. Version: {result[0]}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    test_connection()
    
    df = fetch_stock_price("VCB", start_date="2026-09-01", end_date="2026-09-19")
    print(df)
  