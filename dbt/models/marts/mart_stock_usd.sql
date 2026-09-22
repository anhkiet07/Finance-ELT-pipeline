SELECT
    stock.ticker,
    stock.trade_date,
    stock.open_price,
    stock.high_price,
    stock.low_price,
    stock.close_price,
    stock.volume,
    fx.usd_vnd_rate,
    ROUND((stock.close_price * 1000) / fx.usd_vnd_rate, 4) AS close_price_usd
FROM {{ ref('stg_stock_price') }} AS stock
LEFT JOIN {{ ref('stg_fx_rate') }} AS fx
    ON stock.trade_date = fx.rate_date