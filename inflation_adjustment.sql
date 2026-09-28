-- FilmFlation: Decade-over-decade inflation adjustment
-- Source: U.S. Bureau of Labor Statistics CPI-U (All Items, Not Seasonally Adjusted)
-- via Snowflake Marketplace (SNOWFLAKE_PUBLIC_DATA_FREE)
-- Base: $8,000 bank deposit from It's a Wonderful Life, Dec 1945

CREATE OR REPLACE TABLE FILMFLATION.PUBLIC.INFLATION_ADJUSTMENT AS
WITH decade_cpi AS (
    SELECT DATE AS CPI_DATE, VALUE AS CPI_VALUE
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES
    WHERE VARIABLE = 'CPI:_All_items,_Not_seasonally_adjusted,_Monthly'
      AND GEO_ID = 'country/USA'
      AND DATE IN (
        '1945-12-31','1955-12-31','1965-12-31','1975-12-31',
        '1985-12-31','1995-12-31','2005-12-31','2015-12-31','2025-12-31'
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
    YEAR(CPI_DATE)                                        AS DECADE_YEAR,
    CPI_DATE,
    CPI_VALUE,
    ROUND(CPI_VALUE / BASE_CPI, 4)                       AS CUMULATIVE_MULTIPLIER,
    ROUND(1.00 * CPI_VALUE / BASE_CPI, 2)                AS DOLLAR_1945_WORTH_TODAY,
    ROUND(8000.00 * CPI_VALUE / BASE_CPI, 2)             AS AMOUNT_8000_ADJUSTED,
    ROUND(100.00 * CPI_VALUE / BASE_CPI, 2)              AS DOLLAR_100_ADJUSTED,
    ROUND((CPI_VALUE / BASE_CPI - 1) * 100, 2)           AS CUMULATIVE_INFLATION_PCT,
    ROUND((CPI_VALUE / PREV_CPI - 1) * 100, 2)           AS DECADE_OVER_DECADE_PCT
FROM with_base
ORDER BY CPI_DATE;
