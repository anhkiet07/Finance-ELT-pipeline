CREATE SCHEMA IF NOT EXISTS public;

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
    UNIQUE (ticker, trade_date)
);

CREATE TABLE IF NOT EXISTS raw_fx_rate (
    id SERIAL PRIMARY KEY,
    rate_date DATE NOT NULL,
    usd_vnd_rate NUMERIC NOT NULL,
    ingested_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (rate_date)
);

INSERT INTO raw_stock_price (ticker, trade_date, open, high, low, close, volume)
VALUES
    ('VCB', '2026-09-20', 58.5, 59.0, 58.0, 58.9, 5000000),
    ('VCB', '2026-09-21', 58.9, 59.5, 58.5, 59.2, 4800000),
    ('TCB', '2026-09-20', 32.0, 32.5, 31.8, 32.3, 3000000),
    ('TCB', '2026-09-21', 32.3, 32.8, 32.0, 32.6, 2900000)
ON CONFLICT (ticker, trade_date) DO NOTHING;

INSERT INTO raw_fx_rate (rate_date, usd_vnd_rate)
VALUES
    ('2026-09-20', 26200.0),
    ('2026-09-21', 26210.0)
ON CONFLICT (rate_date) DO NOTHING;