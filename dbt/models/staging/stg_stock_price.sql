SELECT
    ticker,
    trade_date,
    open::NUMERIC(18, 2) AS open_price,
    high::NUMERIC(18, 2) AS high_price,
    low::NUMERIC(18, 2) AS low_price,
    close::NUMERIC(18, 2) AS close_price,
    volume::BIGINT AS volume,
    ingested_at
FROM {{ source('raw', 'raw_stock_price') }}
