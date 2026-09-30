-- ============================================================
-- FilmFlation: Snowflake Setup Script
-- Run as ACCOUNTADMIN. Execute top-to-bottom.
-- ============================================================

USE ROLE ACCOUNTADMIN;

-- ------------------------------------------------------------
-- 1. Dedicated Warehouse
-- ------------------------------------------------------------
CREATE WAREHOUSE IF NOT EXISTS FILMFLATION_WH
    WAREHOUSE_SIZE   = 'X-SMALL'
    AUTO_SUSPEND     = 60
    AUTO_RESUME      = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Dedicated warehouse for FilmFlation app';

-- ------------------------------------------------------------
-- 2. Database & Schema
-- ------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS FILMFLATION
    COMMENT = 'FilmFlation inflation-adjusted movie money app';

USE SCHEMA FILMFLATION.PUBLIC;

-- ------------------------------------------------------------
-- 3. UDTF: CALC_INFLATION
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION FILMFLATION.PUBLIC.CALC_INFLATION(
    BASE_YEAR  INT,
    BASE_MONTH INT,
    STEP_YEARS INT
)
RETURNS TABLE (
    PERIOD_YEAR            INT,
    CPI_DATE               DATE,
    CPI_VALUE              FLOAT,
    CUMULATIVE_MULTIPLIER  FLOAT,
    CUMULATIVE_INFLATION_PCT FLOAT,
    PERIOD_OVER_PERIOD_PCT FLOAT
)
AS
$$
WITH yearly_cpi AS (
    SELECT YEAR(date) AS yr,
           date,
           value,
           ROW_NUMBER() OVER (
               PARTITION BY YEAR(date)
               ORDER BY CASE WHEN MONTH(date) = BASE_MONTH THEN 0 ELSE 1 END,
                        date DESC
           ) AS rn
    FROM SNOWFLAKE_PUBLIC_DATA_FREE.PUBLIC_DATA_FREE.BUREAU_OF_LABOR_STATISTICS_PRICE_TIMESERIES
    WHERE variable = 'CPI:_All_items,_Not_seasonally_adjusted,_Monthly'
      AND geo_id = 'country/USA'
      AND YEAR(date) >= BASE_YEAR
),
picked AS (
    SELECT yr, date AS cpi_date, value AS cpi_value
    FROM yearly_cpi
    WHERE rn = 1
),
filtered AS (
    SELECT *
    FROM picked
    WHERE MOD(yr - BASE_YEAR, STEP_YEARS) = 0
       OR yr = (SELECT MAX(yr) FROM picked)
)
SELECT yr                                                                            AS PERIOD_YEAR,
       cpi_date                                                                      AS CPI_DATE,
       ROUND(cpi_value, 3)                                                           AS CPI_VALUE,
       ROUND(cpi_value / FIRST_VALUE(cpi_value) OVER (ORDER BY yr), 4)               AS CUMULATIVE_MULTIPLIER,
       ROUND((cpi_value / FIRST_VALUE(cpi_value) OVER (ORDER BY yr) - 1) * 100, 2)   AS CUMULATIVE_INFLATION_PCT,
       ROUND((cpi_value / LAG(cpi_value) OVER (ORDER BY yr) - 1) * 100, 2)           AS PERIOD_OVER_PERIOD_PCT
FROM filtered
ORDER BY yr
$$;

-- ------------------------------------------------------------
-- 4. Service Role (least-privilege RBAC)
-- ------------------------------------------------------------
CREATE ROLE IF NOT EXISTS FILMFLATION_APP_ROLE
    COMMENT = 'Least-privilege role for the FilmFlation Streamlit Community Cloud app';

GRANT USAGE ON WAREHOUSE FILMFLATION_WH
    TO ROLE FILMFLATION_APP_ROLE;

GRANT USAGE ON DATABASE FILMFLATION
    TO ROLE FILMFLATION_APP_ROLE;
GRANT USAGE ON SCHEMA FILMFLATION.PUBLIC
    TO ROLE FILMFLATION_APP_ROLE;

GRANT USAGE ON FUNCTION FILMFLATION.PUBLIC.CALC_INFLATION(INT, INT, INT)
    TO ROLE FILMFLATION_APP_ROLE;

GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE_PUBLIC_DATA_FREE
    TO ROLE FILMFLATION_APP_ROLE;

GRANT ROLE FILMFLATION_APP_ROLE TO ROLE ACCOUNTADMIN;

-- ------------------------------------------------------------
-- 5. Service User (RSA 2048 key-pair auth)
--
--    BEFORE running this section:
--    1. Generate a key pair locally:
--         openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out filmflation_rsa_key.p8 -nocrypt
--         openssl rsa -in filmflation_rsa_key.p8 -pubout -out filmflation_rsa_key.pub
--    2. Copy the public key (without the BEGIN/END lines)
--       and paste it into the RSA_PUBLIC_KEY value below.
--    3. Store the private key in Streamlit Community Cloud
--       secrets (never commit it to git).
-- ------------------------------------------------------------
CREATE USER IF NOT EXISTS FILMFLATION_SVC
    DEFAULT_ROLE      = FILMFLATION_APP_ROLE
    DEFAULT_WAREHOUSE = FILMFLATION_WH
    TYPE              = SERVICE
    COMMENT           = 'Service user for FilmFlation on Streamlit Community Cloud'
    RSA_PUBLIC_KEY    = '<Paste public key here before running>';

-- Rotate public key separately from CREATE USER
ALTER USER FILMFLATION_SVC SET RSA_PUBLIC_KEY = '<new-key-base64>';

GRANT ROLE FILMFLATION_APP_ROLE TO USER FILMFLATION_SVC;

-- ------------------------------------------------------------
-- 6. Verification
-- ------------------------------------------------------------
USE ROLE FILMFLATION_APP_ROLE;
USE WAREHOUSE FILMFLATION_WH;

SELECT * FROM TABLE(FILMFLATION.PUBLIC.CALC_INFLATION(1945, 12, 10));

SHOW GRANTS TO ROLE FILMFLATION_APP_ROLE;
SHOW GRANTS TO USER FILMFLATION_SVC;

USE ROLE ACCOUNTADMIN;