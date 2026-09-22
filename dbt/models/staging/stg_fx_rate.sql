SELECT
    rate_date,
    usd_vnd_rate::NUMERIC(18, 2) AS usd_vnd_rate,
    ingested_at
FROM {{ source('raw', 'raw_fx_rate') }}
