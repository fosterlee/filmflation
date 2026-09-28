-- FilmFlation: Decade-over-decade inflation adjustment for The Sting
-- Source: U.S. Bureau of Labor Statistics CPI-U (All Items, Not Seasonally Adjusted)
-- via Snowflake Marketplace (SNOWFLAKE_PUBLIC_DATA_FREE)
-- Base: September 1936 (The Sting story setting)
-- Amounts: $11,000 (Opening Con, Joliet) and $500,000 (The Wire)

CREATE OR REPLACE TABLE FILMFLATION.PUBLIC.INFLATION_ADJUSTMENT_STING AS
WITH decade_cpi AS (
    SELECT DATE AS CPI_DATE, VALUE AS CPI_VALUE
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES
    WHERE VARIABLE = 'CPI:_All_items,_Not_seasonally_adjusted,_Monthly'
      AND GEO_ID = 'country/USA'
      AND DATE IN (
        '1936-09-30','1946-09-30','1956-09-30','1966-09-30','1976-09-30',
        '1986-09-30','1996-09-30','2006-09-30','2016-09-30','2025-09-30'
      )
),
with_base AS (
    SELECT
        CPI_DATE,
        CPI_VALUE,
        FIRST_VALUE(CPI_VALUE) OVER (ORDER BY CPI_DATE) AS BASE_CPI,
        LAG(CPI_VALUE) OVER (ORDER BY CPI_DATE)          AS PREV_CPI
    FROM decade_cpi
)
SELECT
    YEAR(CPI_DATE)                                          AS DECADE_YEAR,
    CPI_DATE,
    CPI_VALUE,
    ROUND(CPI_VALUE / BASE_CPI, 4)                         AS CUMULATIVE_MULTIPLIER,
    ROUND(1.00 * CPI_VALUE / BASE_CPI, 2)                  AS DOLLAR_1936_WORTH_TODAY,
    ROUND(11000.00 * CPI_VALUE / BASE_CPI, 2)              AS AMOUNT_11000_ADJUSTED,
    ROUND(500000.00 * CPI_VALUE / BASE_CPI, 2)             AS AMOUNT_500000_ADJUSTED,
    ROUND((CPI_VALUE / BASE_CPI - 1) * 100, 2)             AS CUMULATIVE_INFLATION_PCT,
    ROUND((CPI_VALUE / PREV_CPI - 1) * 100, 2)             AS DECADE_OVER_DECADE_PCT
FROM with_base
ORDER BY CPI_DATE;
