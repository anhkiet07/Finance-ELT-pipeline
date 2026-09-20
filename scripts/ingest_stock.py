import os
from dotenv import load_dotenv
import psycopg2
from vnstock.api.quote import Quote
import requests
import xml.etree.ElementTree as ET
from datetime import date

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
    quote = Quote(symbol=ticker, source="VCI")
    df = quote.history(start=start_date, end=end_date, interval="1D")
    df["ticker"] = ticker
    return df

VCB_FX_URL = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"

def fetch_fx_rates():
    response = requests.get(VCB_FX_URL, timeout=10)
    root = ET.fromstring(response.content)

    for exrate in root.findall("Exrate"):
        if exrate.get("CurrencyCode") == "USD":
            sell_rate = exrate.get("Sell").replace(",", "")
            return {
                "rate_date":date.today(),
                "usd_vnd_rate": float(sell_rate),
            }
    raise ValueError("USD exchange rate not found in the VCB response.")

def create_raw_stock_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_stock_price (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            trade_date DATE NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume BIGINT,
            ingested_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(ticker, trade_date)
        );
    """)
    conn.commit()
    cursor.close()

def create_raw_fx_table(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS raw_fx_rate (
            id SERIAL PRIMARY KEY,
            rate_date DATE NOT NULL,
            usd_vnd_rate NUMERIC,
            ingested_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(rate_date)
        );
    """)
    conn.commit()
    cursor.close()

def insert_fx_data(conn, fx_data):
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO raw_fx_rate (rate_date, usd_vnd_rate)
        VALUES (%s, %s)
        ON CONFLICT (rate_date) 
        DO UPDATE SET usd_vnd_rate = EXCLUDED.usd_vnd_rate,
                      ingested_at = NOW();
    """, (fx_data["rate_date"], fx_data["usd_vnd_rate"]))
    conn.commit()
    cursor.close()
    print(f"Inserted/Updated FX rate for date {fx_data['rate_date']}: {fx_data['usd_vnd_rate']} VND/USD.")

def insert_stock_data(conn, df):
    cursor = conn.cursor()
    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO raw_stock_price (ticker, trade_date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, trade_date) 
            DO UPDATE SET open = EXCLUDED.open,
                          high = EXCLUDED.high,
                          low = EXCLUDED.low,
                          close = EXCLUDED.close,
                          volume = EXCLUDED.volume,
                          ingested_at = NOW();
        """, (row['ticker'], row['time'], row['open'], row['high'], row['low'], row['close'], row['volume']))
    conn.commit()
    cursor.close()
    print(f"Inserted/Updated {len(df)} rows into raw_stock_price table.")

def test_connection():
    conn = psycopg2.connect(**DB_config)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    result = cursor.fetchone()
    print(f"Connected to database. Version: {result[0]}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    conn = psycopg2.connect(**DB_config)

    create_raw_stock_table(conn)
    create_raw_fx_table(conn)

    for ticker in TICKERS:
        df = fetch_stock_price(ticker, "2026-09-01", "2026-09-19")
        insert_stock_data(conn, df)
        
    fx_data = fetch_fx_rates()
    insert_fx_data(conn, fx_data)

    conn.close()